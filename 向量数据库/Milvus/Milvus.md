# Milvus 向量数据库

## 一、产品介绍

Milvus 是一个高性能、云原生的向量数据库，专为可扩展的向量 ANN（Approximate Nearest Neighbor，近似最近邻）搜索而构建。它通过高效地组织和搜索海量非结构化数据（如文本、图像和多模态信息）来为 AI 应用提供动力。

Milvus 使用 Go 和 C++ 编写，实现了 CPU/GPU 硬件加速，以达到一流的向量搜索性能。得益于其完全分布式、K8s 原生（K8s-native）的架构，Milvus 可以水平扩展，在数十亿向量上处理数万条搜索查询，并通过实时流式更新保持数据新鲜。Milvus 同时支持单机部署的 Standalone 模式；Milvus Lite 是一个轻量版本，可通过 `pip install` 在 Python 中快速上手。

- 开源许可证：**Apache 2.0**
- 治理组织：**LF AI & Data Foundation**（Linux 基金会旗下），主要贡献者为 **Zilliz**
- 托管云服务：**Zilliz Cloud**（提供 Serverless、Dedicated 和 BYOC 选项）

## 二、核心特点

**1. 大规模场景下的高性能与高可用**

Milvus 采用计算与存储分离（separates compute and storage）的分布式架构，可以水平扩展并适应不同的流量模式：针对读密集负载独立增加 Query Node，针对写密集负载增加 Data Node。K8s 上的无状态微服务允许从故障中快速恢复，保证高可用。对副本（replicas）的支持通过在多个 Query Node 上加载数据段，进一步增强了容错能力和吞吐量。

**2. 多种向量索引类型与硬件加速**

Milvus 将系统与核心向量搜索引擎分离，支持所有主流向量索引类型，针对不同场景优化，包括 HNSW、IVF、FLAT（暴力搜索）、SCANN 和 DiskANN，并提供基于量化的变体和 mmap。Milvus 针对元数据过滤、范围搜索等高级特性优化了向量搜索，并实现了硬件加速，支持 GPU 索引，如 NVIDIA 的 CAGRA。

**3. 稀疏向量：全文检索与混合检索**

除了通过稠密向量进行语义搜索外，Milvus 还原生支持以 BM25 实现全文检索（full text search），以及 SPLADE、BGE-M3 等学习型稀疏嵌入。用户可以在同一个集合中存储稀疏向量和稠密向量，并定义函数对多个搜索请求的结果进行重排序（rerank），实现语义搜索 + 全文检索的混合检索。

**4. 灵活的多租户与冷热存储**

Milvus 通过数据库（database）、集合（collection）、分区（partition）或分区键（partition key）级别的隔离来支持多租户。灵活的策略允许单个集群处理从数百到数百万的租户，同时确保优化的搜索性能和灵活的访问控制。通过冷热存储（hot/cold storage）增强成本效益：频繁访问的热数据可存储在内存或 SSD 上以获得更好性能，较少访问的冷数据保存在较慢、更经济的存储上。

**5. 数据安全与细粒度访问控制**

Milvus 通过强制用户认证、TLS 加密和基于角色的访问控制（RBAC）确保数据安全。用户认证确保只有拥有有效凭证的授权用户才能访问数据库，TLS 加密保护网络内的所有通信，RBAC 则根据角色为用户分配特定权限，实现细粒度访问控制。

**6. 生态与集成**

Milvus 与 LangChain、LlamaIndex、OpenAI、HuggingFace 等 AI 开发工具集成，适配了开源嵌入模型与嵌入服务（文本、图像、视频模态）。生态还包括：Attu（GUI 管理）、Birdwatcher（系统调试）、Prometheus/Grafana（监控）、Milvus CDC（数据同步）、VTS（数据迁移），以及 Spark、Kafka、Fivetran、Airbyte 等数据连接器。

## 三、快速开始

### 1. 安装与创建客户端

```bash
pip install -U pymilvus
```

创建客户端。Milvus 支持三种连接方式：

```python
from pymilvus import MilvusClient

# (a) Milvus Lite：嵌入式、基于本地文件，适合开发/测试
#     pip install "pymilvus[milvus-lite]"
client = MilvusClient("milvus_demo.db")

# (b) 自托管 Standalone / Cluster
client = MilvusClient(
    uri="http://localhost:19530",
    token="<username:password>",
)

# (c) Zilliz Cloud 托管服务
client = MilvusClient(
    uri="<endpoint_of_zilliz_cloud>",
    token="<zilliz_cloud_api_key>",
)
```

### 2. 创建集合（Collection）

```python
client.create_collection(
    collection_name="demo_collection",
    dimension=768,  # 演示所用向量为 768 维
)
```

上述“快速创建”会自动生成一个 `id` 字段（INT64、主键、auto_id）、一个 `vector` 字段（FLOAT_VECTOR）、一个 AUTOINDEX 索引，并自动加载集合。

如需自定义 Schema：

```python
from pymilvus import DataType

schema = client.create_schema(auto_id=False, enable_dynamic_field=True)
schema.add_field("id", DataType.INT64, is_primary=True)
schema.add_field("text", DataType.VARCHAR, max_length=512)
schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=768)

index_params = client.prepare_index_params()
index_params.add_index(field_name="embedding", index_type="AUTOINDEX", metric_type="COSINE")

client.create_collection(
    collection_name="demo_collection",
    schema=schema,
    index_params=index_params,
)
```

> 注意：集合必须在搜索/查询前被加载（load）到内存；向量维度必须与 Schema 完全一致。

### 3. 写入数据

```python
from pymilvus import model

embedding_fn = model.dense.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

docs = ["AI advances in 2024", "ML basics for beginners"]
vectors = embedding_fn.encode_documents(docs)

data = [
    {"id": 1, "text": docs[0], "embedding": vectors[0]},
    {"id": 2, "text": docs[1], "embedding": vectors[1]},
]
res = client.insert(collection_name="demo_collection", data=data)
```

### 4. 向量检索

```python
query_vectors = embedding_fn.encode_queries(["What is artificial intelligence?"])

res = client.search(
    collection_name="demo_collection",       # 目标集合
    data=query_vectors,                      # 支持批量查询向量
    anns_field="embedding",
    limit=10,                                # TopK
    output_fields=["text", "id"],            # 返回字段
    filter='age > 20 and status == "active"',# 元数据过滤
    search_params={"metric_type": "COSINE", "params": {"nprobe": 10}},
)
```

常用操作补充：

```python
# 按过滤条件查询
client.query(collection_name="demo_collection", filter='id in [1, 2, 3]',
             output_fields=["text"], limit=100)
# 按主键获取
client.get(collection_name="demo_collection", ids=[1, 2, 3], output_fields=["text"])
# 删除
client.delete(collection_name="demo_collection", ids=[1, 2, 3])
```

> 建议使用 `pip install "pymilvus[model]"` 获得内置嵌入函数；查询所用的嵌入模型必须与入库时相同。大批量插入建议按批（如每批 1000 行）处理。

## 四、部署架构

Milvus 提供多种部署形态，官方均提供镜像或部署清单：

| 部署形态 | 说明 | 官方镜像 / 方式 |
| --- | --- | --- |
| **Milvus Lite** | 嵌入式、进程内、基于本地文件，用于快速原型和开发 | `pip install "pymilvus[milvus-lite]"`，无需独立服务 |
| **Milvus Standalone** | 单机部署，使用 Docker Compose 一键启动 | 镜像 `milvusdb/milvus`（Docker Hub） |
| **Milvus Distributed (Cluster)** | 完全分布式、K8s 原生，生产级水平扩展 | Kubernetes + Helm 部署 |
| **Zilliz Cloud** | 全托管服务 | Serverless / Dedicated / BYOC |

### 官方镜像

- **Milvus 主镜像**：`milvusdb/milvus`（Docker Hub），标签为版本号，例如 `milvusdb/milvus:v3.0.2`。
- Docker 镜像由官方发布；Standalone 的 `docker-compose.yml` 中同时使用以下官方/上游镜像：
  - `quay.io/coreos/etcd:v3.5.25`（元数据与 Service Discovery）
  - `milvusdb/minio:RELEASE.2024-12-18T13-15-44Z`（对象存储）

### Standalone 官方 docker-compose 结构

Milvus 官方 Standalone 部署由三个核心组件构成（摘自官方 `deployments/docker/standalone/docker-compose.yml`）：

```yaml
services:
  etcd:
    container_name: milvus-etcd
    image: quay.io/coreos/etcd:v3.5.25
    environment:
      - ETCD_AUTO_COMPACTION_MODE=revision
      - ETCD_AUTO_COMPACTION_RETENTION=1000
      - ETCD_QUOTA_BACKEND_BYTES=4294967296
      - ETCD_SNAPSHOT_COUNT=50000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/etcd:/etcd
    command: etcd -advertise-client-urls=http://etcd:2379 -listen-client-urls http://0.0.0.0:2379 --data-dir /etcd

  minio:
    container_name: milvus-minio
    image: milvusdb/minio:RELEASE.2024-12-18T13-15-44Z
    environment:
      MINIO_ACCESS_KEY: minioadmin
      MINIO_SECRET_KEY: minioadmin
    ports:
      - "9001:9001"
      - "9000:9000"
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/minio:/minio_data
    command: minio server /minio_data --console-address ":9001"

  standalone:
    container_name: milvus-standalone
    image: milvusdb/milvus:v3.0.2
    command: ["milvus", "run", "standalone"]
    security_opt:
      - seccomp:unconfined
    environment:
      MINIO_REGION: us-east-1
      ETCD_ENDPOINTS: etcd:2379
      MINIO_ADDRESS: minio:9000
    volumes:
      - ${DOCKER_VOLUME_DIRECTORY:-.}/volumes/milvus:/var/lib/milvus
    ports:
      - "19530:19530"   # 对外服务端口（SDK 连接端口）
      - "9091:9091"     # 健康检查 / 指标端口
    depends_on:
      - etcd
      - minio
```

- **etcd**：存储 Milvus 元数据并承担服务发现。
- **MinIO**：对象/日志存储，持久化向量数据与索引文件。
- **standalone**：Milvus 主服务，对外暴露 `19530`（SDK 连接）和 `9091`（健康检查、指标）。
- 持久化数据默认保存在 `./volumes/{etcd,minio,milvus}`。

### 连接端口

- **19530**：Milvus 默认的 gRPC/RESTful 服务端口，Python/Node/Java/Go SDK 通过它连接。
- **9091**：指标/健康检查端口；Milvus 还提供 `/healthz` 健康检查端点。

## 参考

- 官方网站：https://milvus.io/
- 官方文档：https://milvus.io/docs
- 官方仓库：https://github.com/milvus-io/milvus
- 论文引用：
  - *Milvus: A Purpose-Built Vector Data Management System* (SIGMOD 2021)
  - *Manu: a cloud native vector database management system* (VLDB 2022)
