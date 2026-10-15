"""Milvus 向量数据库适配器 - 支持远程模式和本地模式(milvus-lite)"""

import os
import time
import numpy as np
from typing import List

from pymilvus import MilvusClient

from .base import BaseAdapter
import config


class MilvusAdapter(BaseAdapter):
    """Milvus 适配器 - 支持远程和本地模式"""

    def __init__(self, collection_name: str, dim: int, local_mode: bool = False):
        super().__init__(collection_name, dim)
        self.local_mode = local_mode
        self.client = None
        self._local_db_path = None

    @property
    def db_name(self) -> str:
        if self.local_mode:
            return "Milvus-Local"
        return "Milvus"

    def connect(self) -> None:
        if self.local_mode:
            # 本地模式：使用 milvus-lite，数据存到临时文件
            self._local_db_path = f"./milvus_bench_{self.collection_name}.db"
            # 清理可能存在的旧文件
            if os.path.exists(self._local_db_path):
                os.remove(self._local_db_path)
            print(f"  [Milvus-Local] 本地模式，数据文件: {self._local_db_path}")
            self.client = MilvusClient(uri=self._local_db_path)
        else:
            # 远程模式
            uri = f"http://{config.MILVUS_CONFIG['host']}:{config.MILVUS_CONFIG['port']}"
            print(f"  [Milvus] 连接到 {uri}")
            self.client = MilvusClient(uri=uri)

    def create_collection(self) -> None:
        # 如果已存在则先删除
        if self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)

        # 创建集合
        self.client.create_collection(
            collection_name=self.collection_name,
            dimension=self.dim,
            metric_type="L2",
            primary_field_name="id",
            vector_field_name="embedding",
            id_type="INT64",
        )
        print(f"  [Milvus] 创建集合: {self.collection_name}")

    def drop_collection(self) -> None:
        if self.client.has_collection(self.collection_name):
            self.client.drop_collection(self.collection_name)
            print(f"  [Milvus] 删除集合: {self.collection_name}")

    def insert_batch(self, vectors: np.ndarray, ids: List[int]) -> float:
        start = time.perf_counter()
        data = [
            {"id": int(idx), "embedding": vec.tolist()}
            for idx, vec in zip(ids, vectors)
        ]
        self.client.insert(
            collection_name=self.collection_name,
            data=data,
        )
        elapsed = time.perf_counter() - start
        return elapsed

    def build_index(self) -> float:
        start = time.perf_counter()
        index_params = self.client.prepare_index_params()
        index_params.add_index(
            field_name="embedding",
            index_type=config.MILVUS_INDEX_PARAMS["index_type"],
            metric_type=config.MILVUS_INDEX_PARAMS["metric_type"],
            params=config.MILVUS_INDEX_PARAMS["params"],
        )
        self.client.create_index(
            collection_name=self.collection_name,
            index_params=index_params,
        )
        elapsed = time.perf_counter() - start
        print(f"  [Milvus] 索引构建完成 ({elapsed:.2f}s)")
        return elapsed

    def search(self, query: np.ndarray, top_k: int) -> List[int]:
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query.tolist()],
            limit=top_k,
            search_params=config.MILVUS_SEARCH_PARAMS,
        )
        return [hit["id"] for hit in results[0]]

    def count(self) -> int:
        if self.client:
            stats = self.client.get_collection_stats(self.collection_name)
            return int(stats.get("row_count", 0))
        return 0

    def close(self) -> None:
        if self.client:
            self.client.close()
        # 本地模式：删除本地数据文件
        if self.local_mode and self._local_db_path:
            if os.path.exists(self._local_db_path):
                os.remove(self._local_db_path)
                print(f"  [Milvus-Local] 已清理本地数据文件: {self._local_db_path}")
        print(f"  [Milvus] 连接已关闭")
