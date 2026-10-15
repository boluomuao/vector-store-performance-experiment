"""
向量数据库性能基准测试 - 主入口

支持的数据库: Milvus, Chroma, Qdrant, pgvector
测试模式:
  - 远程模式 (默认): 连接远程服务，全部 4 个数据库参与
  - 本地模式 (--local): 嵌入式运行，仅 Milvus/Chroma/Qdrant 参与

测试指标:
  - 写入: 吞吐量 (vectors/sec), 平均延迟, P99 延迟
  - 读取: 查询延迟 (avg/P99), QPS, Recall@K

用法:
  # 远程模式 - 运行全部默认测试
  python main.py

  # 本地模式 - 嵌入式运行 (无网络服务)
  python main.py --local

  # 只测试特定数据库
  python main.py --dbs milvus qdrant

  # 使用特定数据集
  python main.py --datasets small_normal small_high

  # 列出所有可用数据集
  python main.py --list-datasets

  # 运行完整测试（包含大规模数据集）
  python main.py --all
"""

import argparse
import sys
import time

import config
from benchmark_runner import run_all_benchmarks, print_results, save_results


def list_datasets():
    """列出所有可用数据集"""
    print("\n可用数据集:")
    print("-" * 80)
    for name, cfg in config.DATASETS.items():
        print(f"  {name:20s} | {cfg['num_vectors']:>12,} 向量 | {cfg['dim']:>5} 维 | {cfg['description']}")
    print()


def main():
    parser = argparse.ArgumentParser(
        description="向量数据库性能基准测试",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--dbs",
        nargs="+",
        choices=["milvus", "chroma", "qdrant", "pgvector"],
        default=None,
        help="要测试的数据库列表 (默认: 全部)",
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=None,
        help="要使用的数据集列表 (默认: small_normal, small_high, medium, real_cluster)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="运行所有数据集（包括大规模数据集）",
    )
    parser.add_argument(
        "--local",
        action="store_true",
        help="本地模式: 嵌入式运行，无需远程服务 (仅 Milvus/Chroma/Qdrant)",
    )
    parser.add_argument(
        "--list-datasets",
        action="store_true",
        help="列出所有可用数据集",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="results.txt",
        help="结果输出文件路径 (默认: results.txt)",
    )

    args = parser.parse_args()

    if args.list_datasets:
        list_datasets()
        return

    # 确定数据集
    if args.all:
        dataset_names = list(config.DATASETS.keys())
    elif args.datasets:
        dataset_names = args.datasets
    else:
        dataset_names = config.DEFAULT_DATASETS

    # 确定数据库
    local_mode = args.local
    if local_mode:
        db_types = args.dbs or ["milvus", "chroma", "qdrant"]
        # 本地模式下过滤掉 pgvector
        db_types = [db for db in db_types if db != "pgvector"]
    else:
        db_types = args.dbs or ["milvus", "chroma", "qdrant", "pgvector"]

    mode_str = "本地模式" if local_mode else "远程模式"
    print("=" * 80)
    print("向量数据库性能基准测试")
    print("=" * 80)
    print(f"  运行模式: {mode_str}")
    print(f"  数据库: {', '.join(db_types)}")
    print(f"  数据集: {', '.join(dataset_names)}")
    print(f"  写入批次大小: {config.WRITE_BATCH_SIZE}")
    print(f"  查询次数: {config.SEARCH_PARAMS['num_queries']}")
    print(f"  Top-K: {config.SEARCH_PARAMS['top_k']}")
    print("=" * 80)

    start_time = time.time()

    # 运行测试
    results = run_all_benchmarks(
        db_types=db_types,
        dataset_names=dataset_names,
        local_mode=local_mode,
    )

    elapsed = time.time() - start_time
    print(f"\n总耗时: {elapsed:.1f}s ({elapsed/60:.1f}min)")

    # 打印结果
    print_results(results)

    # 保存结果
    save_results(results, args.output)

    print("\n测试完成!")


if __name__ == "__main__":
    main()
