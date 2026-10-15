"""Chroma 向量数据库适配器 - 支持远程模式和本地内存模式"""

import time
import numpy as np
from typing import List

import chromadb

from .base import BaseAdapter
import config


class ChromaAdapter(BaseAdapter):
    """Chroma 适配器 - 支持远程和本地内存模式"""

    def __init__(self, collection_name: str, dim: int, local_mode: bool = False):
        super().__init__(collection_name, dim)
        self.local_mode = local_mode
        self.client = None
        self.collection = None

    @property
    def db_name(self) -> str:
        if self.local_mode:
            return "Chroma-Local"
        return "Chroma"

    def connect(self) -> None:
        if self.local_mode:
            # 本地内存模式：数据仅存于内存，程序结束即释放
            print(f"  [Chroma-Local] 本地内存模式")
            self.client = chromadb.Client()
        else:
            # 远程模式
            print(f"  [Chroma] 连接到 {config.CHROMA_CONFIG['host']}:{config.CHROMA_CONFIG['port']}")
            self.client = chromadb.HttpClient(
                host=config.CHROMA_CONFIG["host"],
                port=config.CHROMA_CONFIG["port"],
            )
            # 测试连接
            self.client.heartbeat()

    def create_collection(self) -> None:
        # 如果已存在则先删除
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass

        self.collection = self.client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "l2"},
        )
        print(f"  [Chroma] 创建集合: {self.collection_name}")

    def drop_collection(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"  [Chroma] 删除集合: {self.collection_name}")
        except Exception:
            pass

    def insert_batch(self, vectors: np.ndarray, ids: List[int]) -> float:
        start = time.perf_counter()
        # Chroma 需要字符串 ID
        str_ids = [str(i) for i in ids]
        self.collection.add(
            ids=str_ids,
            embeddings=vectors.tolist(),
        )
        elapsed = time.perf_counter() - start
        return elapsed

    def build_index(self) -> float:
        # Chroma 使用 HNSW 索引，在数据插入时自动构建
        start = time.perf_counter()
        _ = self.collection.get()
        elapsed = time.perf_counter() - start
        print(f"  [Chroma] 索引确认完成 ({elapsed:.2f}s)")
        return elapsed

    def search(self, query: np.ndarray, top_k: int) -> List[int]:
        results = self.collection.query(
            query_embeddings=[query.tolist()],
            n_results=top_k,
            include=[],
        )
        # results["ids"] 是 [[str_id1, str_id2, ...]]
        return [int(rid) for rid in results["ids"][0]]

    def count(self) -> int:
        if self.collection:
            return self.collection.count()
        return 0

    def close(self) -> None:
        # 本地内存模式：数据随进程结束自动释放
        # 远程模式：HttpClient 不需要显式关闭
        print(f"  [Chroma] 连接已关闭")
