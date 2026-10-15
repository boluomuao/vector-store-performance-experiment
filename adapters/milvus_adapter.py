"""Milvus 向量数据库适配器"""

import time
import numpy as np
from typing import List

from pymilvus import (
    connections,
    Collection,
    CollectionSchema,
    FieldSchema,
    DataType,
    utility,
)

from .base import BaseAdapter
import config


class MilvusAdapter(BaseAdapter):
    """Milvus 适配器"""

    def __init__(self, collection_name: str, dim: int):
        super().__init__(collection_name, dim)
        self.collection = None

    @property
    def db_name(self) -> str:
        return "Milvus"

    def connect(self) -> None:
        print(f"  [Milvus] 连接到 {config.MILVUS_CONFIG['host']}:{config.MILVUS_CONFIG['port']}")
        connections.connect(
            alias="default",
            host=config.MILVUS_CONFIG["host"],
            port=config.MILVUS_CONFIG["port"],
        )

    def create_collection(self) -> None:
        # 如果已存在则先删除
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)

        # 定义 Schema
        fields = [
            FieldSchema(
                name="id",
                dtype=DataType.INT64,
                is_primary=True,
                auto_id=False,
            ),
            FieldSchema(
                name="embedding",
                dtype=DataType.FLOAT_VECTOR,
                dim=self.dim,
            ),
        ]
        schema = CollectionSchema(fields=fields, description="Benchmark collection")
        self.collection = Collection(
            name=self.collection_name,
            schema=schema,
        )
        print(f"  [Milvus] 创建集合: {self.collection_name}")

    def drop_collection(self) -> None:
        if utility.has_collection(self.collection_name):
            utility.drop_collection(self.collection_name)
            print(f"  [Milvus] 删除集合: {self.collection_name}")

    def insert_batch(self, vectors: np.ndarray, ids: List[int]) -> float:
        start = time.perf_counter()
        data = [ids, vectors.tolist()]
        self.collection.insert(data)
        elapsed = time.perf_counter() - start
        return elapsed

    def build_index(self) -> float:
        start = time.perf_counter()
        index_params = {
            "index_type": config.MILVUS_INDEX_PARAMS["index_type"],
            "metric_type": config.MILVUS_INDEX_PARAMS["metric_type"],
            "params": config.MILVUS_INDEX_PARAMS["params"],
        }
        self.collection.create_index(
            field_name="embedding",
            index_params=index_params,
        )
        elapsed = time.perf_counter() - start
        print(f"  [Milvus] 索引构建完成 ({elapsed:.2f}s)")
        return elapsed

    def search(self, query: np.ndarray, top_k: int) -> List[int]:
        self.collection.load()
        search_params = config.MILVUS_SEARCH_PARAMS
        results = self.collection.search(
            data=[query.tolist()],
            anns_field="embedding",
            param=search_params,
            limit=top_k,
            output_fields=[],
        )
        return [hit.id for hit in results[0]]

    def count(self) -> int:
        if self.collection:
            self.collection.flush()
            return self.collection.num_entities
        return 0

    def close(self) -> None:
        connections.disconnect("default")
        print(f"  [Milvus] 连接已关闭")
