"""公共工具函数"""

import time
import numpy as np
from typing import List, Dict, Any
from dataclasses import dataclass, field


@dataclass
class BenchmarkResult:
    """单个基准测试结果"""
    db_name: str
    dataset_name: str
    num_vectors: int
    dim: int

    # 写入指标
    insert_throughput: float = 0.0      # vectors/sec
    insert_latency_avg: float = 0.0     # ms
    insert_latency_p99: float = 0.0     # ms
    insert_total_time: float = 0.0      # sec

    # 读取指标
    search_latency_avg: float = 0.0     # ms
    search_latency_p99: float = 0.0     # ms
    search_qps: float = 0.0            # queries/sec
    recall_at_k: float = 0.0           # 0~1

    # 索引构建
    index_build_time: float = 0.0       # sec

    def to_dict(self) -> Dict[str, Any]:
        return {
            "数据库": self.db_name,
            "数据集": self.dataset_name,
            "向量数": f"{self.num_vectors:,}",
            "维度": self.dim,
            "写入吞吐(v/s)": f"{self.insert_throughput:,.0f}",
            "写入延迟avg(ms)": f"{self.insert_latency_avg:.2f}",
            "写入延迟P99(ms)": f"{self.insert_latency_p99:.2f}",
            "索引构建(s)": f"{self.index_build_time:.2f}",
            "查询延迟avg(ms)": f"{self.search_latency_avg:.2f}",
            "查询延迟P99(ms)": f"{self.search_latency_p99:.2f}",
            "查询QPS": f"{self.search_qps:,.1f}",
            "Recall@K": f"{self.recall_at_k:.4f}",
        }


class Timer:
    """高精度计时器"""

    def __init__(self):
        self._start = None
        self._elapsed = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self._elapsed = time.perf_counter() - self._start

    @property
    def elapsed(self) -> float:
        return self._elapsed

    @property
    def elapsed_ms(self) -> float:
        return self._elapsed * 1000


def compute_recall(
    ground_truth: np.ndarray,
    results: np.ndarray,
) -> float:
    """
    计算 Recall@K

    Args:
        ground_truth: shape (num_queries, k) - 暴力搜索的真实最近邻 ID
        results: shape (num_queries, k) - 数据库返回的最近邻 ID

    Returns:
        recall 值 (0~1)
    """
    if ground_truth.shape != results.shape:
        min_k = min(ground_truth.shape[1], results.shape[1])
        ground_truth = ground_truth[:, :min_k]
        results = results[:, :min_k]

    total = 0
    for gt, res in zip(ground_truth, results):
        gt_set = set(gt)
        res_set = set(res)
        total += len(gt_set & res_set)

    return total / ground_truth.size


def brute_force_knn(
    base_vectors: np.ndarray,
    query_vectors: np.ndarray,
    k: int,
) -> np.ndarray:
    """
    暴力 KNN 搜索，用于计算 Recall 的 ground truth

    Args:
        base_vectors: shape (n, dim)
        query_vectors: shape (num_queries, dim)
        k: top-k

    Returns:
        shape (num_queries, k) 的最近邻索引数组
    """
    # 使用 L2 距离
    # (a-b)^2 = a^2 - 2ab + b^2
    a_sq = np.sum(base_vectors ** 2, axis=1, keepdims=True)   # (n, 1)
    b_sq = np.sum(query_vectors ** 2, axis=1, keepdims=True)  # (q, 1)
    dist = a_sq.T - 2 * base_vectors @ query_vectors.T + b_sq  # (n, q)

    # 取每列最小的 k 个索引
    indices = np.argpartition(dist, k, axis=0)[:k, :]  # (k, q)
    return indices.T  # (q, k)


def percentile(latencies: List[float], p: float) -> float:
    """计算百分位延迟"""
    if not latencies:
        return 0.0
    sorted_lat = sorted(latencies)
    idx = int(len(sorted_lat) * p / 100.0)
    idx = min(idx, len(sorted_lat) - 1)
    return sorted_lat[idx]
