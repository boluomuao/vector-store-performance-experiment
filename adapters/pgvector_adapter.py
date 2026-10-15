"""pgvector 向量数据库适配器 (PostgreSQL + pgvector 扩展)"""

import time
import numpy as np
from typing import List

import psycopg
from pgvector.psycopg import register_vector

from .base import BaseAdapter
import config


class PgvectorAdapter(BaseAdapter):
    """pgvector 适配器"""

    def __init__(self, collection_name: str, dim: int):
        super().__init__(collection_name, dim)
        self.conn = None
        self.cur = None

    @property
    def db_name(self) -> str:
        return "pgvector"

    def connect(self) -> None:
        print(f"  [pgvector] 连接到 {config.PGVECTOR_CONFIG['host']}:{config.PGVECTOR_CONFIG['port']}")
        self.conn = psycopg.connect(
            host=config.PGVECTOR_CONFIG["host"],
            port=config.PGVECTOR_CONFIG["port"],
            user=config.PGVECTOR_CONFIG["user"],
            password=config.PGVECTOR_CONFIG["password"],
            dbname=config.PGVECTOR_CONFIG["dbname"],
            autocommit=True,
        )
        self.cur = self.conn.cursor()
        # 注册 pgvector 扩展
        register_vector(self.cur)
        # 确保 pgvector 扩展已启用
        self.cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        print(f"  [pgvector] 连接成功, pgvector 扩展已就绪")

    def create_collection(self) -> None:
        # 删除已有表
        self.cur.execute(f"DROP TABLE IF EXISTS {self.collection_name};")

        # 创建表
        self.cur.execute(f"""
            CREATE TABLE {self.collection_name} (
                id BIGINT PRIMARY KEY,
                embedding vector({self.dim})
            );
        """)
        print(f"  [pgvector] 创建表: {self.collection_name}")

    def drop_collection(self) -> None:
        self.cur.execute(f"DROP TABLE IF EXISTS {self.collection_name};")
        print(f"  [pgvector] 删除表: {self.collection_name}")

    def insert_batch(self, vectors: np.ndarray, ids: List[int]) -> float:
        start = time.perf_counter()
        # 使用 COPY 协议进行高速批量插入
        # 先构建数据行
        rows = []
        for idx, vec in zip(ids, vectors):
            vec_str = "[" + ",".join(f"{v:.6f}" for v in vec) + "]"
            rows.append((idx, vec_str))

        # 使用 executemany 批量插入
        self.cur.executemany(
            f"INSERT INTO {self.collection_name} (id, embedding) VALUES (%s, %s::vector);",
            rows,
        )
        elapsed = time.perf_counter() - start
        return elapsed

    def build_index(self) -> float:
        start = time.perf_counter()
        index_type = config.PGVECTOR_INDEX_PARAMS["index_type"]
        m = config.PGVECTOR_INDEX_PARAMS["m"]
        ef_construction = config.PGVECTOR_INDEX_PARAMS["ef_construction"]

        if index_type == "hnsw":
            self.cur.execute(f"""
                CREATE INDEX ON {self.collection_name}
                USING hnsw (embedding vector_l2_ops)
                WITH (m = {m}, ef_construction = {ef_construction});
            """)
        elif index_type == "ivfflat":
            # ivfflat 需要指定 lists 参数
            # 推荐 lists = sqrt(num_vectors)
            self.cur.execute(f"""
                CREATE INDEX ON {self.collection_name}
                USING ivfflat (embedding vector_l2_ops)
                WITH (lists = 100);
            """)

        elapsed = time.perf_counter() - start
        print(f"  [pgvector] HNSW 索引构建完成 ({elapsed:.2f}s)")
        return elapsed

    def search(self, query: np.ndarray, top_k: int) -> List[int]:
        vec_str = "[" + ",".join(f"{v:.6f}" for v in query) + "]"
        self.cur.execute(f"""
            SELECT id
            FROM {self.collection_name}
            ORDER BY embedding <-> %s::vector
            LIMIT %s;
        """, (vec_str, top_k))
        rows = self.cur.fetchall()
        return [row[0] for row in rows]

    def count(self) -> int:
        if self.cur:
            self.cur.execute(f"SELECT COUNT(*) FROM {self.collection_name};")
            return self.cur.fetchone()[0]
        return 0

    def close(self) -> None:
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
        print(f"  [pgvector] 连接已关闭")
