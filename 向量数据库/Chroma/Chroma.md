# Chroma 向量数据库


## 一、产品介绍

Chroma 是面向 AI 的开源数据基础设施，内置了上手所需的一切能力，可直接运行在本地机器上。

Chroma 提供检索所需的一切：存储带元数据的嵌入（embeddings），使用稠密与稀疏向量搜索，按元数据过滤，并可跨文本、图像等多种模态进行检索。

- 开源许可证：**Apache 2.0**
- 官方仓库：https://github.com/chroma-core/chroma
- 托管服务：**Chroma Cloud**（快速、可扩展、Serverless 的数据库即服务）

## 二、核心特点

**1. 灵活的嵌入支持**

支持使用任意嵌入模型，包括 OpenAI、Cohere、Hugging Face、sentence-transformers 等。Chroma 会自动为文本处理嵌入和索引，也可自定义嵌入模型。

**2. 多模态检索**

可与文本一起索引和搜索图像、音频及其他模态的数据。

**3. 全文与正则搜索**

无需嵌入，即可对数据进行关键词搜索与正则表达式搜索。

**4. 向量搜索**

支持稠密、稀疏和混合（hybrid）搜索，可按相似度查询并组合多种搜索策略。

**5. 元数据过滤**

查询时可按元数据条件过滤结果，支持多种过滤操作符。

**6. 文档存储与元数据管理**

Chroma 支持存储文档及其关联的元数据，并在文档和嵌入上建立索引，以实现高效检索与过滤。

**7. 部署灵活**

可本地运行、自托管，或使用 Chroma Cloud 托管服务。

**8. 多语言客户端**

提供 Python、TypeScript、Rust 客户端；Python 还提供"仅客户端"精简包（thin client）以减小安装体积。

**9. 可观测性**

内置 OpenTelemetry 钩子，支持链路追踪。

> 注意：OSS（开源）Chroma 不包含 Chroma Cloud 专属特性，例如 `Schema()`、`Search()`；如果仅使用稠密向量 + 单一嵌入函数，则属于 OSS 常规基线。混合稠密/稀疏检索通常被视为 Chroma Cloud 能力（除非在 OSS 中自行实现替代方案）。

## 三、快速开始

### 1. 安装与创建客户端

**Python：**

```bash
pip install chromadb
```

Chroma 提供多种客户端（client）形态，对应不同的持久化与运行方式：

```python
import chromadb

# (a) 内存客户端：在内存中启动一个 Chroma 实例，进程退出后数据丢失（适合测试）
chroma_client = chromadb.Client()

# (b) 持久化客户端：数据落盘到指定路径
chroma_client = chromadb.PersistentClient(path="./chroma-data")

# (c) HTTP 客户端：连接到运行中的 Chroma 服务（client-server 模式）
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
chroma_client.heartbeat()  # 探活
```

**TypeScript：**

```bash
npm install chromadb @chroma-core/default-embed
```

```typescript
import { ChromaClient } from "chromadb";
const client = new ChromaClient();
```

### 2. 创建集合（Collection）

集合（Collection）用于存储嵌入、文档及附加元数据，并对嵌入和文档建立索引，以实现高效检索与过滤。

```python
collection = chroma_client.create_collection(name="my_collection")

# 若希望避免重复创建，可使用 get_or_create_collection
collection = chroma_client.get_or_create_collection(name="my_collection")
```

### 3. 写入数据

Chroma 会自动存储文本并完成嵌入与索引。必须为文档提供唯一的字符串 ID。

```python
collection.add(
    ids=["id1", "id2"],
    documents=[
        "This is a document about pineapple",
        "This is a document about oranges",
    ],
)
```

> 若要避免重复写入，可将 `add` 换成 `upsert`。

### 4. 检索

```python
results = collection.query(
    query_texts=["This is a query document about hawaii"],  # Chroma 会为其自动生成嵌入
    n_results=2,                                            # 返回结果数量（默认 10）
)
print(results)
```

返回结果示例（摘自官方文档）：

```python
{
  'documents': [[
      'This is a document about pineapple',
      'This is a document about oranges'
  ]],
  'ids': [['id1', 'id2']],
  'distances': [[1.0404009819030762, 1.243080496788025]],
  'uris': None,
  'data': None,
  'metadatas': [[None, None]],
  'embeddings': None,
}
```

### 5. 完整示例

```python
import chromadb

chroma_client = chromadb.Client()

# 使用 get_or_create_collection 避免每次都新建集合
collection = chroma_client.get_or_create_collection(name="my_collection")

# 使用 upsert 避免重复添加相同文档
collection.upsert(
    documents=[
        "This is a document about pineapple",
        "This is a document about oranges",
    ],
    ids=["id1", "id2"],
)

results = collection.query(
    query_texts=["This is a query document about florida"],
    n_results=2,
)
print(results)
```

> 上述示例使用内存客户端，数据在程序终止后即丢失。如需持久化，请使用持久化客户端（PersistentClient）或 client-server 模式。

## 四、部署架构

Chroma 支持本地嵌入式、单机服务（client-server）以及 Chroma Cloud 三种主要形态。

### 运行本地服务

安装 `chromadb` 后会获得 Chroma CLI，可用 `chroma run` 启动本地服务：

```bash
chroma run
# 或指定数据目录
chroma run --path ./getting-started
```

默认地址为 `localhost:8000`。

### 官方镜像（Docker）

Chroma 官方提供 Docker 镜像，发布在 **Docker Hub** 与 **GitHub Container Registry（ghcr.io）**：

- Docker Hub：`chromadb/chroma`
- GHCR：`ghcr.io/chroma-core/chroma`

启动服务并持久化数据：

```bash
docker run -v ./chroma-data:/data -p 8000:8000 chromadb/chroma
```

该命令以默认配置启动服务，数据存储在 `./chroma-data` 目录。随后客户端即可连接：

```python
import chromadb

chroma_client = chromadb.HttpClient(host='localhost', port=8000)
chroma_client.heartbeat()
```

### 配置

Chroma 使用 YAML 文件进行配置。默认配置可参考官方示例文件 `single_node_full.yaml`。若使用自定义配置，可将配置文件挂载到容器内的 `/config.yaml`：

```bash
echo "allow_reset: true" > config.yaml
docker run -v ./chroma-data:/data -v ./config.yaml:/config.yaml -p 8000:8000 chromadb/chroma
```

### 可观测性（OpenTelemetry）

Chroma 内置 OpenTelemetry 钩子，可结合 OpenTelemetry Collector 与 Zipkin 搭建可观测性栈。官方给出的 `docker-compose.yml` 由三部分组成：Chroma 服务、OpenTelemetry Collector 和 Zipkin：

```yaml
services:
  zipkin:
    image: openzipkin/zipkin
    ports:
      - "9411:9411"
    depends_on: [otel-collector]
    networks:
      - internal
  otel-collector:
    image: otel/opentelemetry-collector-contrib:0.111.0
    command: ["--config=/etc/otel-collector-config.yaml"]
    volumes:
      - ${PWD}/otel-collector-config.yaml:/etc/otel-collector-config.yaml
    networks:
      - internal
  server:
    image: chromadb/chroma
    volumes:
      - chroma_data:/data
    ports:
      - "8000:8000"
    networks:
      - internal
    environment:
      - CHROMA_OPEN_TELEMETRY__ENDPOINT=http://otel-collector:4317/
      - CHROMA_OPEN_TELEMETRY__SERVICE_NAME=chroma
    depends_on:
      - otel-collector
      - zipkin

networks:
  internal:

volumes:
  chroma_data:
```

启动：

```bash
docker compose up --build -d
```

启动后可在 `http://localhost:9411` 访问 Zipkin 查看链路；调用 `curl http://localhost:8000/api/v2/heartbeat` 可快速生成一条示例 track。

### 部署形态一览

| 形态 | 说明 | 方式 |
| --- | --- | --- |
| **本地嵌入式** | 内存 / 持久化，进程内运行，适合开发、测试 | Python `Client()` / `PersistentClient()` |
| **单机服务（client-server）** | 独立服务进程，多客户端连接 | `chroma run` 或 `docker run chromadb/chroma`（默认端口 8000） |
| **Chroma Cloud** | 全托管、Serverless | https://www.trychroma.com |

## 参考

- 官方网站：https://www.trychroma.com
- 官方文档：https://docs.trychroma.com
- 文档索引（llms.txt）：https://docs.trychroma.com/llms.txt
- 官方仓库：https://github.com/chroma-core/chroma
- Docker Hub：https://hub.docker.com/r/chromadb/chroma
- GHCR：https://github.com/chroma-core/chroma/pkgs/container/chroma
