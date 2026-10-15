# Qdrant 向量数据库

## 一、产品介绍

Qdrant（读作 quadrant）是一个向量相似度搜索引擎与向量数据库，提供生产级服务及便捷的 API，用于存储、搜索和管理点（point），即附带额外载荷（payload）的向量。Qdrant 针对扩展过滤（extended filtering）能力做了专门设计，适用于各类基于神经网络或语义的匹配、分面搜索（faceted search）等应用。

Qdrant 使用 Rust 编写，在高负载下依然保持高性能与稳定性。服务采用 client-server 架构，对外提供 REST（OpenAPI 3.0）和 gRPC 两种接口，并提供 Python、JavaScript/TypeScript、Rust、Go、.NET、Java 官方客户端。此外，Qdrant Edge 是面向边缘设备与资源受限环境的轻量版本，以进程内（in-process）方式运行，可将本地数据与 Qdrant 服务端同步。

- 开源许可证：**Apache 2.0**
- 最新版本：**v1.19.2**
- 托管云服务：**Qdrant Cloud**（Managed Cloud，含免费套餐），另提供 Hybrid Cloud 与 Private Cloud 部署选项

## 二、核心特点

**1. 基于 Payload 的高级过滤**

Qdrant 允许为向量附加任意 JSON 载荷（payload），并通过丰富的条件进行过滤，包括关键词匹配、全文匹配、数值范围、地理位置（geo）等，可用 `must`、`should`、`must_not` 子句组合。Payload 索引会扩展 HNSW 图结构（filterable HNSW），使过滤条件在语义搜索阶段即生效，以单次图遍历完成"过滤 + 检索"，避免了前置过滤（pre-filtering）与后置过滤（post-filtering）各自的缺陷；查询规划器（query planner）会结合 payload 索引信息选择最优执行策略。

**2. 向量量化与磁盘存储**

内置量化（quantization）能力可将内存占用最多降低 97%，并允许在搜索速度与精度之间灵活权衡。支持标量量化（Scalar Quantization）、二值量化（Binary Quantization）、乘积量化（Product Quantization）和 TurboQuant 等多种方法。向量与 HNSW 索引均可卸载到磁盘（on-disk），且可在已有集合上随时启用，热点数据自然保留在缓存中，用以控制大规模数据下的内存成本。

**3. 稠密、稀疏与多向量检索**

Qdrant 支持用于语义相似度的稠密向量（dense vector）、用于全文检索的稀疏向量（sparse vector），以及面向多嵌入对象或 ColBERT 等后期交互（late interaction）模型的多向量（multivector）检索。单个点可通过命名向量（named vectors）同时存储多个向量，各自拥有独立的维度与距离度量。

**4. 混合检索与多阶段查询**

通过统一的 Query API，可在一次请求中组合多路向量检索（prefetch），并使用 Reciprocal Rank Fusion（RRF）或 Distribution-Based Score Fusion（DBSF）等融合策略合并结果，兼顾语义理解与关键词精确匹配。Prefetch 支持嵌套，可实现"粗召回 + 精排"等多阶段检索流程。

**5. 分布式部署与水平扩展**

Qdrant 通过分片（sharding）与副本（replication）实现水平扩展，支持在不停机的情况下更新或调整集合规模。每个分片由多个段（segment）组成，可通过段配置在写入速度与搜索吞吐之间取舍。

**6. 灵活的多租户**

多租户（multitenancy）支持三种隔离方式：基于 payload 的分区（适合大量规模相近的小租户）、用户自定义分片（为租户分配专属分片，适合少量大租户），以及将两者结合的分层多租户（tiered multitenancy，小租户共享分片、大租户提升为专属分片）。针对租户字段可开启 `is_tenant` 索引优化，仅为各租户构建子索引。

**7. 高级检索能力**

除常规 Top-K 检索外，Qdrant 还提供分面聚合（Faceting）、基于正负样本的推荐（Recommendation）、限定向量空间区域的探索（Discovery），以及最大边际相关性（MMR）、相关性反馈查询（Relevance Feedback Query）等结果相关性调优工具。

**8. 性能与可靠性**

利用 x86-64 与 Neon 架构的 SIMD 指令实现硬件加速；支持 NVIDIA 与 AMD GPU 加速索引构建；使用 `io_uring` 异步 I/O 提升磁盘吞吐（包括网络挂载存储）；通过预写日志（Write-Ahead Logging，WAL）在更新确认后保证数据持久化，即使发生断电也不会丢失。

**9. 安全与访问控制**

支持 API Key 认证，包括只读 API Key（面向仅查询的服务或用户）以及按集合细粒度授权读写的访问令牌；支持网络绑定、TLS 加密通信与审计日志（audit logging）。Qdrant Cloud 默认启用上述能力，自托管开源部署需在上线前显式配置。

**10. 生态与集成**

内置 Web UI，可用于浏览集合、管理数据、调用 REST API 并监控部署健康状况；提供完善的指标（metrics）、遥测（telemetry）等可观测性能力。Qdrant 与嵌入模型提供商、AI 应用框架、数据管道工具、可观测性平台以及低代码/无代码自动化平台集成；Python 客户端可配合 FastEmbed 在客户端侧生成嵌入，Qdrant Cloud 亦提供服务端推理（Cloud Inference）。

## 三、快速开始

### 1. 启动服务

从 Docker Hub 拉取最新镜像并启动服务：

```bash
docker pull qdrant/qdrant

docker run -p 6333:6333 -p 6334:6334 \
    -v "$(pwd)/qdrant_storage:/qdrant/storage:z" \
    qdrant/qdrant
```

默认配置下，所有数据存储在 `./qdrant_storage` 目录。服务启动后可通过以下地址访问：

- REST API：`localhost:6333`
- Web UI：`localhost:6333/dashboard`
- gRPC API：`localhost:6334`

> 注意：上述命令启动的是未启用认证、监听所有网卡的非安全部署，上线前需参考官方安全文档完成加固。

### 2. 安装与创建客户端

```bash
pip install qdrant-client
# 如需在客户端侧生成嵌入：pip install "qdrant-client[fastembed]"
```

```python
from qdrant_client import QdrantClient

# (a) 本地模式：进程内运行，无需独立服务，适合开发/测试
client = QdrantClient(":memory:")              # 内存模式，进程退出后数据丢失
client = QdrantClient(path="./qdrant_local")   # 持久化到本地目录

# (b) 自托管服务（client-server 模式）
client = QdrantClient(url="http://localhost:6333")

# (c) Qdrant Cloud 托管服务
client = QdrantClient(
    url="<qdrant_cloud_endpoint>",
    api_key="<qdrant_cloud_api_key>",
)
```

### 3. 创建集合（Collection）

集合（Collection）是可在其中进行搜索的点（向量 + payload）的命名集合。同一集合内的向量必须维度相同，并使用同一种距离度量进行比较。

```python
from qdrant_client.models import Distance, VectorParams

client.create_collection(
    collection_name="test_collection",
    vectors_config=VectorParams(size=4, distance=Distance.DOT),  # 4 维向量，点积距离
)
```

### 4. 写入数据

Payload 用于存储与向量关联的其它数据：

```python
from qdrant_client.models import PointStruct

operation_info = client.upsert(
    collection_name="test_collection",
    wait=True,
    points=[
        PointStruct(id=1, vector=[0.05, 0.61, 0.76, 0.74], payload={"city": "Berlin"}),
        PointStruct(id=2, vector=[0.19, 0.81, 0.75, 0.11], payload={"city": "London"}),
        PointStruct(id=3, vector=[0.36, 0.55, 0.47, 0.94], payload={"city": "Moscow"}),
        PointStruct(id=4, vector=[0.18, 0.01, 0.85, 0.80], payload={"city": "New York"}),
        PointStruct(id=5, vector=[0.24, 0.18, 0.22, 0.44], payload={"city": "Beijing"}),
        PointStruct(id=6, vector=[0.35, 0.08, 0.11, 0.44], payload={"city": "Mumbai"}),
    ],
)
print(operation_info)
# operation_id=0 status=<UpdateStatus.COMPLETED: 'completed'>
```

### 5. 检索

```python
search_result = client.query_points(
    collection_name="test_collection",
    query=[0.2, 0.1, 0.9, 0.7],
    with_payload=False,
    limit=3,
).points
```

返回结果按相似度从高到低排列（摘自官方文档）：

```json
[
  { "id": 4, "version": 0, "score": 1.362, "payload": null, "vector": null },
  { "id": 1, "version": 0, "score": 1.273, "payload": null, "vector": null },
  { "id": 3, "version": 0, "score": 1.208, "payload": null, "vector": null }
]
```

> 默认情况下返回结果不包含 payload 与向量，需通过 `with_payload`、`with_vectors` 参数显式开启。

### 6. 添加过滤条件

```python
from qdrant_client.models import Filter, FieldCondition, MatchValue

search_result = client.query_points(
    collection_name="test_collection",
    query=[0.2, 0.1, 0.9, 0.7],
    query_filter=Filter(
        must=[FieldCondition(key="city", match=MatchValue(value="London"))]
    ),
    with_payload=True,
    limit=3,
).points
# [{"id": 2, "version": 0, "score": 0.871, "payload": {"city": "London"}, "vector": null}]
```

## 四、高级操作

### 1. 创建 Payload 索引

Payload 索引用于加速对特定字段的过滤，概念上类似关系数据库中的列索引。建议在写入数据前创建：filterable HNSW 只有在 payload 索引已存在时构建，才能获得额外的过滤感知边；若在数据写入后再创建，需要重建 HNSW 索引才能生效。

```python
client.create_payload_index(
    collection_name="test_collection",
    field_name="city",
    field_schema="keyword",
)
```

### 2. 混合检索（稠密 + 稀疏）

创建同时包含稠密向量与稀疏向量的集合：

```python
from qdrant_client import models

client.create_collection(
    collection_name="hybrid_collection",
    vectors_config={"dense": models.VectorParams(size=4, distance=models.Distance.COSINE)},
    sparse_vectors_config={"sparse": models.SparseVectorParams()},
)
```

通过 `prefetch` 分别检索两路向量，再使用 RRF 融合结果：

```python
client.query_points(
    collection_name="hybrid_collection",
    prefetch=[
        models.Prefetch(
            query=models.SparseVector(indices=[1, 42], values=[0.22, 0.8]),
            using="sparse",
            limit=20,
        ),
        models.Prefetch(
            query=[0.01, 0.45, 0.67, 0.12],  # 稠密向量
            using="dense",
            limit=20,
        ),
    ],
    query=models.RrfQuery(rrf=models.Rrf()),  # Reciprocal Rank Fusion，使用默认参数
    limit=10,
)
```

### 3. 多租户（基于 Payload 分区）

在单个集合中为每个点添加租户标识字段（如 `group_id`），为该字段创建 `is_tenant` 关键词索引，查询时按租户字段过滤：

```python
client.create_payload_index(
    collection_name="test_collection",
    field_name="group_id",
    field_schema=models.KeywordIndexParams(type="keyword", is_tenant=True),
)
```

> 为每个租户单独建集合通常不是最高效的方式：每个集合都有独立的资源开销，仅当租户数量有限且需要严格隔离时才建议使用多集合方案。

## 五、部署架构

Qdrant 提供从进程内嵌入、单节点容器到 Kubernetes 集群与全托管云服务的多种部署形态：

| 部署形态 | 说明 | 官方镜像 / 方式 |
| --- | --- | --- |
| **Qdrant Edge** | 轻量级进程内向量搜索引擎，支持 Python 与 Rust，适合边缘设备、离线场景 | `qdrant_edge` 库，无需独立服务 |
| **Docker 单节点** | 官方推荐的开发/测试方式 | 镜像 `qdrant/qdrant`（Docker Hub） |
| **Docker Compose** | 单节点或多节点自建，可用于生产（需自行补齐高可用、备份、监控等） | 镜像 `qdrant/qdrant` |
| **Kubernetes（Helm）** | 社区支持的 Helm Chart，可部署分布式集群 | `helm install qdrant qdrant/qdrant` |
| **Private Cloud** | 企业版 Kubernetes Operator，自有基础设施、无需连接云端 | Qdrant Private Cloud Enterprise Operator |
| **Hybrid Cloud** | 由 Qdrant Cloud 统一管理、运行在用户自有集群上 | Qdrant Cloud 控制台 |
| **Managed Cloud** | 全托管服务，含免费套餐 | https://cloud.qdrant.io |

### 官方镜像

- **Qdrant 主镜像**：`qdrant/qdrant`（Docker Hub），最新版本始终发布在 Docker Hub，标签为版本号，例如 `qdrant/qdrant:v1.19.2`。
- 容器内数据目录为 `/qdrant/storage`，默认配置文件为 `/qdrant/config/production.yaml`。

覆盖默认配置：

```bash
docker run -p 6333:6333 \
    -v $(pwd)/path/to/data:/qdrant/storage \
    -v $(pwd)/path/to/custom_config.yaml:/qdrant/config/production.yaml \
    qdrant/qdrant
```

### 官方 docker-compose 示例（单节点）

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    restart: always
    container_name: qdrant
    ports:
      - 6333:6333
      - 6334:6334
    expose:
      - 6333
      - 6334
      - 6335
    configs:
      - source: qdrant_config
        target: /qdrant/config/production.yaml
    volumes:
      - ./qdrant_data:/qdrant/storage

configs:
  qdrant_config:
    content: |
      log_level: INFO
```

与 Milvus Standalone 依赖 etcd、MinIO 不同，Qdrant 为单一服务进程，元数据、向量与索引均由自身管理并持久化到本地存储，无需额外的外部组件。

### Kubernetes（Helm）

```bash
helm repo add qdrant https://qdrant.to/helm
helm install qdrant qdrant/qdrant
```

> Helm Chart 可部署分布式集群，但不具备 Qdrant Cloud / Private Cloud Operator 提供的零停机升级、自动分片再平衡（shard rebalancing）、重分片（resharding）、完整集群备份与灾难恢复等能力，需自行搭建与维护，且仅提供社区支持。

### 连接端口

每个 Qdrant 实例需开放三个端口：

- **6333**：HTTP（REST）API，同时提供健康检查与指标（metrics）端点，Web UI 位于 `/dashboard`。
- **6334**：gRPC API。
- **6335**：分布式部署时节点间通信端口。

集群内所有实例必须能够通过上述端口互相通信，并允许客户端访问 6333 与 6334 端口。

### 部署环境要求

- **CPU 架构**：仅支持 64 位系统，包括 x86_64/amd64 与 AArch64/arm64。
- **存储**：持久化存储需提供块级访问（block-level）且兼容 POSIX 的文件系统，iSCSI 等块级网络存储亦可；**不支持** NFS 等网络文件系统及 S3 等对象存储。将向量卸载到磁盘时建议使用 SSD 或 NVMe。
- **资源规划**：CPU 与内存需求取决于向量数量、维度、payload 及其索引、存储方式、副本数与量化配置。

## 附录：技术规格

### 距离度量

| 度量 | 参数值 | 说明 |
| --- | --- | --- |
| 点积 | `Dot` | Dot product |
| 余弦相似度 | `Cosine` | Cosine similarity |
| 欧氏距离 | `Euclid` | Euclidean distance |
| 曼哈顿距离 | `Manhattan` | Manhattan (L1) distance |

### 向量数据类型

| 类型 | 说明 |
| --- | --- |
| `float32` | 默认类型，每个维度存储为 32 位浮点数 |
| `float16` | 半精度浮点 |
| `uint8` | 无符号 8 位整数，适合已量化的嵌入 |
| `turbo4` | 4 位存储 |

### 索引类型

| 索引 | 说明 |
| --- | --- |
| **HNSW（稠密向量索引）** | Qdrant 当前唯一的稠密向量索引；默认 `m: 16`、`ef_construct: 100`，搜索参数 `ef` 默认等于 `ef_construct`；数据量低于 `full_scan_threshold`（默认 10000 KB）时查询规划器改用全量扫描 |
| **Filterable HNSW** | 在 HNSW 图中加入过滤感知边，实现单次遍历的过滤检索 |
| **稀疏向量索引** | 面向稀疏向量的倒排索引，用于全文/关键词检索 |
| **Payload 索引** | 加速 payload 字段过滤，类型见下表 |

**Payload 索引类型：**

| 类型 | 适用过滤条件 |
| --- | --- |
| `keyword` | Match（可选前缀匹配） |
| `integer` | Match、Range |
| `float` | Range |
| `bool` | Match |
| `geo` | Geo Bounding Box、Geo Radius |
| `datetime` | Range |
| `text` | Full Text 全文匹配 |
| `uuid` | 类似 keyword，针对 UUID 值优化 |

### 量化方法

| 方法 | 压缩比 | 说明 |
| --- | --- | --- |
| **Scalar Quantization** | 4x | 将 32 位浮点分量压缩为 8 位整数，精度损失极小 |
| **TurboQuant** | 最高 32x | 在多数嵌入模型上保持较高召回率 |
| **Binary Quantization** | 最高 32x | 每个分量压缩为 1~2 位，适合高维、中心化分布的向量 |
| **Product Quantization** | 最高 64x | 内存最小化优先时使用 |

## 参考

- 官方网站：https://qdrant.tech/
- 官方文档：https://qdrant.tech/documentation/
- API 文档（OpenAPI）：https://api.qdrant.tech/
- 官方仓库：https://github.com/qdrant/qdrant
- Python 客户端：https://github.com/qdrant/qdrant-client
- Helm Chart：https://github.com/qdrant/qdrant-helm
- Docker Hub：https://hub.docker.com/r/qdrant/qdrant
- 托管云服务：https://cloud.qdrant.io/
