"""数据库适配器基类 - 定义统一接口"""

from abc import ABC, abstractmethod
from typing import List, Tuple
import numpy as np


class BaseAdapter(ABC):
    """向量数据库适配器基类"""

    def __init__(self, collection_name: str, dim: int):
        self.collection_name = collection_name
        self.dim = dim

    @abstractmethod
    def connect(self) -> None:
        """连接到数据库"""
        pass

    @abstractmethod
    def create_collection(self) -> None:
        """创建集合/表"""
        pass

    @abstractmethod
    def drop_collection(self) -> None:
        """删除集合/表"""
        pass

    @abstractmethod
    def insert_batch(
        self,
        vectors: np.ndarray,
        ids: List[int],
    ) -> float:
        """
        批量插入向量

        Args:
            vectors: shape (batch_size, dim) 的向量数组
            ids: 对应的 ID 列表

        Returns:
            本次插入耗时（秒）
        """
        pass

    @abstractmethod
    def build_index(self) -> float:
        """
        构建索引

        Returns:
            索引构建耗时（秒）
        """
        pass

    @abstractmethod
    def search(
        self,
        query: np.ndarray,
        top_k: int,
    ) -> List[int]:
        """
        搜索最近邻

        Args:
            query: shape (dim,) 的查询向量
            top_k: 返回的最近邻数量

        Returns:
            最近邻的 ID 列表
        """
        pass

    @abstractmethod
    def count(self) -> int:
        """返回集合中的向量数量"""
        pass

    @abstractmethod
    def close(self) -> None:
        """关闭连接"""
        pass

    @property
    @abstractmethod
    def db_name(self) -> str:
        """数据库名称标识"""
        pass
