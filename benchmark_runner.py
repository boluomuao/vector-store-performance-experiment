"""基准测试运行器 - 执行所有数据库的读写性能测试"""

import time
import numpy as np
from typing import List, Dict
from tabulate import tabulate

from adapters.base import BaseAdapter
from adapters import MilvusAdapter, ChromaAdapter, QdrantAdapter, PgvectorAdapter
from data_generator import generate_dataset
from utils import BenchmarkResult, Timer, compute_recall, brute_force_knn, percentile
import config


def create_adapter(db_type: str, collection_name: str, dim: int, local_mode: bool = False) -> BaseAdapter:
    """根据类型创建对应的适配器"""
    if db_type == "milvus":
        return MilvusAdapter(collection_name, dim, local_mode=local_mode)
    elif db_type == "chroma":
        return ChromaAdapter(collection_name, dim, local_mode=local_mode)
    elif db_type == "qdrant":
        return QdrantAdapter(collection_name, dim, local_mode=local_mode)
    elif db_type == "pgvector":
        if local_mode:
            raise ValueError("pgvector 不支持本地模式，需要 PostgreSQL 服务")
        return PgvectorAdapter(collection_name, dim)
    else:
        raise ValueError(f"未知的数据库类型: {db_type}")


def run_write_benchmark(
    adapter: BaseAdapter,
    base_vectors: np.ndarray,
    batch_size: int = config.WRITE_BATCH_SIZE,
) -> Dict:
    """
    执行写入基准测试

    Returns:
        {
            "insert_latencies": List[float],  # 每批插入延迟 (ms)
            "insert_total_time": float,        # 总写入时间 (s)
            "insert_throughput": float,        # 吞吐量 (vectors/sec)
            "index_build_time": float,         # 索引构建时间 (s)
        }
    """
    num_vectors = base_vectors.shape[0]
    insert_latencies = []

    print(f"  写入测试: {num_vectors:,} 向量, 批次大小={batch_size}")

    # 分批插入
    total_insert_time = 0.0
    for start_idx in range(0, num_vectors, batch_size):
        end_idx = min(start_idx + batch_size, num_vectors)
        batch_vectors = base_vectors[start_idx:end_idx]
        batch_ids = list(range(start_idx, end_idx))

        elapsed = adapter.insert_batch(batch_vectors, batch_ids)
        insert_latencies.append(elapsed * 1000)  # 转为 ms
        total_insert_time += elapsed

        # 进度显示
        progress = end_idx / num_vectors * 100
        if end_idx % (batch_size * 10) == 0 or end_idx == num_vectors:
            print(f"    已写入 {end_idx:,}/{num_vectors:,} ({progress:.0f}%)")

    # 构建索引
    print(f"  构建索引...")
    index_build_time = adapter.build_index()

    # 计算指标
    insert_throughput = num_vectors / total_insert_time if total_insert_time > 0 else 0

    return {
        "insert_latencies": insert_latencies,
        "insert_total_time": total_insert_time,
        "insert_throughput": insert_throughput,
        "index_build_time": index_build_time,
    }


def run_read_benchmark(
    adapter: BaseAdapter,
    query_vectors: np.ndarray,
    base_vectors: np.ndarray,
    top_k: int = config.SEARCH_PARAMS["top_k"],
    num_queries: int = config.SEARCH_PARAMS["num_queries"],
    num_warmup: int = config.NUM_WARMUP_QUERIES,
    compute_recall_flag: bool = True,
) -> Dict:
    """
    执行读取基准测试

    Returns:
        {
            "search_latencies": List[float],  # 每次查询延迟 (ms)
            "search_qps": float,              # QPS
            "recall_at_k": float,             # Recall@K
        }
    """
    search_latencies = []
    all_results = []

    # 只使用前 num_queries 条查询
    queries = query_vectors[:num_queries]

    print(f"  查询测试: {num_queries} 次查询, top_k={top_k}")

    # 预热阶段（不计入统计）
    print(f"  预热中 ({num_warmup} 次)...")
    for i in range(min(num_warmup, len(queries))):
        adapter.search(queries[i], top_k)

    # 正式查询
    for i, query in enumerate(queries):
        start = time.perf_counter()
        result_ids = adapter.search(query, top_k)
        elapsed = (time.perf_counter() - start) * 1000  # ms
        search_latencies.append(elapsed)
        all_results.append(result_ids)

        if (i + 1) % 20 == 0:
            print(f"    已查询 {i+1}/{num_queries}")

    # 计算 Recall@K（使用暴力搜索作为 ground truth）
    recall_at_k = 0.0
    if compute_recall_flag and len(base_vectors) <= 100_000:
        print(f"  计算 Recall@{top_k} (暴力搜索 ground truth)...")
        ground_truth = brute_force_knn(base_vectors, queries, top_k)
        results_array = np.array(all_results)
        recall_at_k = compute_recall(ground_truth, results_array)
        print(f"  Recall@{top_k} = {recall_at_k:.4f}")
    elif compute_recall_flag:
        print(f"  数据量过大 ({len(base_vectors):,})，跳过 Recall 计算")

    # 计算 QPS
    total_search_time = sum(search_latencies) / 1000  # sec
    search_qps = num_queries / total_search_time if total_search_time > 0 else 0

    return {
        "search_latencies": search_latencies,
        "search_qps": search_qps,
        "recall_at_k": recall_at_k,
    }


def run_single_test(
    db_type: str,
    dataset_name: str,
    dataset_config: dict,
    local_mode: bool = False,
) -> BenchmarkResult:
    """
    对单个数据库 + 单个数据集执行完整测试

    Args:
        db_type: 数据库类型
        dataset_name: 数据集名称
        dataset_config: 数据集配置
        local_mode: 是否使用本地模式

    Returns:
        BenchmarkResult
    """
    dim = dataset_config["dim"]
    num_vectors = dataset_config["num_vectors"]
    collection_name = f"{config.COLLECTION_PREFIX}{dataset_name}_{dim}d"

    mode_str = "本地模式" if local_mode else "远程模式"
    print(f"\n{'='*60}")
    print(f"测试: {db_type} ({mode_str}) | 数据集: {dataset_name}")
    print(f"  向量数: {num_vectors:,}, 维度: {dim}")
    print(f"{'='*60}")

    # 生成数据
    base_vectors, query_vectors = generate_dataset(dataset_name, dataset_config)

    # 创建适配器
    adapter = create_adapter(db_type, collection_name, dim, local_mode=local_mode)

    try:
        # 连接
        adapter.connect()

        # 清理旧数据 & 创建集合
        adapter.drop_collection()
        adapter.create_collection()

        # 写入测试
        write_result = run_write_benchmark(adapter, base_vectors)

        # 验证数据量
        count = adapter.count()
        print(f"  数据验证: 集合中有 {count:,} 条记录")

        # 读取测试
        read_result = run_read_benchmark(
            adapter,
            query_vectors,
            base_vectors,
        )

        # 构建结果
        result = BenchmarkResult(
            db_name=adapter.db_name,
            dataset_name=dataset_name,
            num_vectors=num_vectors,
            dim=dim,
            insert_throughput=write_result["insert_throughput"],
            insert_latency_avg=np.mean(write_result["insert_latencies"]),
            insert_latency_p99=percentile(write_result["insert_latencies"], 99),
            insert_total_time=write_result["insert_total_time"],
            index_build_time=write_result["index_build_time"],
            search_latency_avg=np.mean(read_result["search_latencies"]),
            search_latency_p99=percentile(read_result["search_latencies"], 99),
            search_qps=read_result["search_qps"],
            recall_at_k=read_result["recall_at_k"],
        )

        return result

    except Exception as e:
        print(f"  [ERROR] 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return BenchmarkResult(
            db_name=db_type,
            dataset_name=dataset_name,
            num_vectors=num_vectors,
            dim=dim,
        )
    finally:
        try:
            adapter.close()
        except Exception:
            pass


def run_all_benchmarks(
    db_types: List[str] = None,
    dataset_names: List[str] = None,
    local_mode: bool = False,
) -> List[BenchmarkResult]:
    """
    运行所有基准测试

    Args:
        db_types: 要测试的数据库列表，默认全部
        dataset_names: 要使用的数据集列表，默认使用 DEFAULT_DATASETS
        local_mode: 是否使用本地模式（本地模式下 pgvector 不参与）

    Returns:
        所有测试结果的列表
    """
    if local_mode:
        # 本地模式：只有 milvus/chroma/qdrant 支持
        if db_types is None:
            db_types = ["milvus", "chroma", "qdrant"]
        else:
            # 过滤掉不支持本地模式的数据库
            db_types = [db for db in db_types if db in ("milvus", "chroma", "qdrant")]
    else:
        if db_types is None:
            db_types = ["milvus", "chroma", "qdrant", "pgvector"]

    if dataset_names is None:
        dataset_names = config.DEFAULT_DATASETS

    results = []

    for dataset_name in dataset_names:
        if dataset_name not in config.DATASETS:
            print(f"警告: 未知的数据集 '{dataset_name}'，跳过")
            continue

        dataset_config = config.DATASETS[dataset_name]

        for db_type in db_types:
            result = run_single_test(db_type, dataset_name, dataset_config, local_mode=local_mode)
            results.append(result)

    return results


def print_results(results: List[BenchmarkResult]):
    """打印结果表格"""
    if not results:
        print("没有测试结果")
        return

    print("\n")
    print("=" * 120)
    print("基准测试结果汇总")
    print("=" * 120)

    # 按数据集分组显示
    datasets = {}
    for r in results:
        if r.dataset_name not in datasets:
            datasets[r.dataset_name] = []
        datasets[r.dataset_name].append(r)

    for dataset_name, group in datasets.items():
        print(f"\n--- 数据集: {dataset_name} ---")
        table_data = [r.to_dict() for r in group]
        print(tabulate(table_data, headers="keys", tablefmt="grid"))

    # 总体对比表
    print(f"\n\n{'='*120}")
    print("总体对比")
    print("=" * 120)
    table_data = [r.to_dict() for r in results]
    print(tabulate(table_data, headers="keys", tablefmt="grid"))


def save_results(results: List[BenchmarkResult], filepath: str = "results.txt"):
    """保存结果到文件"""
    import io
    buf = io.StringIO()

    buf.write("向量数据库性能基准测试结果\n")
    buf.write("=" * 120 + "\n\n")

    table_data = [r.to_dict() for r in results]
    buf.write(tabulate(table_data, headers="keys", tablefmt="grid"))
    buf.write("\n")

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(buf.getvalue())

    print(f"\n结果已保存到: {filepath}")
