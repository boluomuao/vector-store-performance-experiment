"""Qdrant 向量数据库适配器 - 支持远程模式和本地内存模式"""

import time
import numpy as np
from typing import List

from qdrant_client import QdrantClient
from qdrant_client.http.models import (
    Distance,
    VectorParams,
    PointStruct,
    HnswConfigDiff,
    SearchParams,
)

from .base import BaseAdapter
import config


class QdrantAdapter(BaseAdapter):
    """Qdrant 适配器 - 支持远程和本地内存模式"""

    def __init__(self, collection_name: str, dim: int, local_mode: bool = False):
        super().__init__(collection_name, dim)
        self.local_mode = local_mode
        self.client = None

    @property
    def db_name(self) -> str:
        if self.local_mode:
            return "Qdrant-Local"
        return "Qdrant"

    def connect(self) -> None:
        if self.local_mode:
            # 本地内存模式：数据仅存于内存，程序结束即释放
            print(f"  [Qdrant-Local] 本地内存模式")
            self.client = QdrantClient(":memory:")
        else:
            # 远程模式
            print(f"  [Qdrant] 连接到 {config.QDRANT_CONFIG['host']}:{config.QDRANT_CONFIG['port']}")
            self.client = QdrantClient(
                host=config.QDRANT_CONFIG["host"],
                port=config.QDRANT_CONFIG["port"],
                prefer_grpc=True,
            )

    def create_collection(self) -> None:
        # 如果已存在则先删除
        try:
            self.client.delete_collection(collection_name=self.collection_name)
        except Exception:
            pass

        # 创建集合
        self.client.create_collection(
            collection_name=self.collection_name,
            vectors_config=VectorParams(
                size=self.dim,
                distance=Distance.EUCLID,
            ),
            hnsw_config=HnswConfigDiff(
                m=config.QDRANT_INDEX_PARAMS["m"],
                ef_construct=config.QDRANT_INDEX_PARAMS["ef_construct"],
            ),
        )
        print(f"  [Qdrant] 创建集合: {self.collection_name}")

    def drop_collection(self) -> None:
        try:
            self.client.delete_collection(collection_name=self.collection_name)
            print(f"  [Qdrant] 删除集合: {self.collection_name}")
        except Exception:
            pass

    def insert_batch(self, vectors: np.ndarray, ids: List[int]) -> float:
        start = time.perf_counter()
        points = [
            PointStruct(
                id=int(idx),
                vector=vec.tolist(),
            )
            for idx, vec in zip(ids, vectors)
        ]
        self.client.upsert(
            collection_name=self.collection_name,
            points=points,
            wait=True,
        )
        elapsed = time.perf_counter() - start
        return elapsed

    def build_index(self) -> float:
        # Qdrant 的 HNSW 索引在数据插入时自动构建
        start = time.perf_counter()
        self.client.flush(collection_name=self.collection_name)
        elapsed = time.perf_counter() - start
        print(f"  [Qdrant] 索引确认完成 ({elapsed:.2f}s)")
        return elapsed

    def search(self, query: np.ndarray, top_k: int) -> List[int]:
        results = self.client.search(
            collection_name=self.collection_name,
            query_vector=query.tolist(),
            limit=top_k,
            search_params=SearchParams(
                hnsw_ef=config.QDRANT_SEARCH_PARAMS["hnsw_ef"],
            ),
        )
        return [hit.id for hit in results]

    def count(self) -> int:
        if self.client:
            info = self.client.get_collection(collection_name=self.collection_name)
            return info.points_count
        return 0

    def close(self) -> None:
        if self.client:
            self.client.close()
        # 本地内存模式：数据随进程结束自动释放
        print(f"  [Qdrant] 连接已关闭")
