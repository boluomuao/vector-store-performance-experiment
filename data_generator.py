"""数据生成模块 - 生成模拟数据和类真实嵌入数据"""

import numpy as np
from typing import Tuple


def generate_normal_data(
    num_vectors: int,
    dim: int,
    seed: int = 42,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成正态分布的随机向量数据 (L2 归一化)

    Args:
        num_vectors: 向量数量
        dim: 向量维度
        seed: 随机种子

    Returns:
        (base_vectors, query_vectors)
        base_vectors: shape (num_vectors, dim)
        query_vectors: shape (100, dim) - 固定 100 条查询向量
    """
    rng = np.random.RandomState(seed)

    # 生成基础数据（正态分布）
    base_vectors = rng.randn(num_vectors, dim).astype(np.float32)
    # L2 归一化
    norms = np.linalg.norm(base_vectors, axis=1, keepdims=True)
    base_vectors = base_vectors / norms

    # 生成查询向量（与基础数据同分布）
    num_queries = 100
    query_vectors = rng.randn(num_queries, dim).astype(np.float32)
    norms_q = np.linalg.norm(query_vectors, axis=1, keepdims=True)
    query_vectors = query_vectors / norms_q

    return base_vectors, query_vectors


def generate_clustered_data(
    num_vectors: int,
    dim: int,
    seed: int = 42,
    num_clusters: int = 50,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    生成聚类分布数据，模拟真实嵌入空间（如 BERT/Sentence-BERT 嵌入）

    真实嵌入通常呈现聚类结构：语义相似的文档聚集在一起，
    不同主题的文档形成不同的簇。

    Args:
        num_vectors: 向量数量
        dim: 向量维度
        seed: 随机种子
        num_clusters: 聚类中心数

    Returns:
        (base_vectors, query_vectors)
    """
    rng = np.random.RandomState(seed)

    # 生成聚类中心
    centers = rng.randn(num_clusters, dim).astype(np.float32)
    center_norms = np.linalg.norm(centers, axis=1, keepdims=True)
    centers = centers / center_norms

    # 为每个向量分配一个簇，并在簇中心附近添加噪声
    assignments = rng.randint(0, num_clusters, size=num_vectors)
    base_vectors = centers[assignments] + rng.randn(num_vectors, dim).astype(np.float32) * 0.1
    # L2 归一化
    norms = np.linalg.norm(base_vectors, axis=1, keepdims=True)
    base_vectors = base_vectors / norms

    # 查询向量：一半来自簇中心附近（模拟语义查询），一半随机
    num_queries = 100
    num_semantic = num_queries // 2
    # 语义查询
    query_centers = rng.choice(num_clusters, size=num_semantic)
    semantic_queries = centers[query_centers] + rng.randn(num_semantic, dim).astype(np.float32) * 0.05
    # 随机查询
    random_queries = rng.randn(num_queries - num_semantic, dim).astype(np.float32)

    query_vectors = np.vstack([semantic_queries, random_queries]).astype(np.float32)
    norms_q = np.linalg.norm(query_vectors, axis=1, keepdims=True)
    query_vectors = query_vectors / norms_q

    return base_vectors, query_vectors


def generate_dataset(
    dataset_name: str,
    config: dict,
) -> Tuple[np.ndarray, np.ndarray]:
    """
    根据配置生成数据集

    Args:
        dataset_name: 数据集名称
        config: 数据集配置字典

    Returns:
        (base_vectors, query_vectors)
    """
    num_vectors = config["num_vectors"]
    dim = config["dim"]
    distribution = config["distribution"]

    print(f"  生成数据: {dataset_name} ({num_vectors:,} 向量, {dim} 维, {distribution} 分布)")

    if distribution == "normal":
        return generate_normal_data(num_vectors, dim)
    elif distribution == "clustered":
        return generate_clustered_data(num_vectors, dim)
    else:
        raise ValueError(f"未知的分布类型: {distribution}")
