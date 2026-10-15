# Chroma 代码实践

> [!tip] ChromaDB 引擎启动时在做什么？
> 打开 SQLite 文件、初始化 HNSW 索引、分配内存结构。

## 一、运行模式

**ChromaDB 的运行模式有两种类型：**

| 模式              | 说明                              | 类比                  |
| --------------- | ------------------------------- | ------------------- |
| 嵌入式（in-process） | ChromaDB 直接跑在应用进程内部，文件在本地加载和存储  | 类似 SQLite           |
| 客户端-服务器模式       | 单独起一个 ChromaDB 服务进程，通过 HTTP 连接它 | 类似 MySQL/PostgreSQL |

```plaintext
┌─────────────────────────────────────────────┐
│             <你的 Python 进程>               │
│                                             │
│   你的代码  ←→  ChromaDB 引擎  ←→  磁盘文件    │
│                                             │
└─────────────────────────────────────────────┘
          ↑ 这就是 in-process（嵌入式）
          
          ChromaDB 的代码直接跑在进程内部
```

```plaintext
┌────────────────────┐          ┌──────────────────────┐
│ <你的 Python 进程> │  ←HTTP→  │  <ChromaDB 服务进程>  │
│                    │          │  （独立运行的程序）   │
│  client 代码       │          │  引擎 ←→ 磁盘文件     │
└────────────────────┘          └──────────────────────┘
          ↑ 这是 client/server 模式
          ChromaDB 跑在另一个进程里，你通过网络连接它
```

### 1. 嵌入式模式（In-process，含内存与持久化）

In-process 模式下，ChromaDB 引擎会在 client 实例化时启动（打开 SQLite 文件、初始化 HNSW 索引、分配内存结构）。

```python
import chromadb

# 1.【内存模式】在内存中启动 Chroma，并返回一个用于连接的临时客户端。数据不持久化，程序结束就丢失。
client = chromadb.Client()

# 2.【持久化模式】启动时加载本地数据（如果存在），产生的数据也会存储到本地
# `path`：Chroma 在磁盘上存储数据库文件、以及启动时加载文件的位置
client = chromadb.PersistentClient(path="/path/to/save/to")
```

### 2. 客户端-服务器模式

需在服务器后台运行 `chroma run --path /db_path`。适合微服务架构和多并发场景。

参考： https://docs.chroma.org.cn/docs/run-chroma/client-server

```python
# 初始化 Chroma HTTP 客户端
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
```

### 3. 其它运行模式

ChromaDB 还有云端（Chroma Cloud）的运行模式。

### 在 LangChain 中切换运行模式

在 `LangChain` 的 `Chroma` 对象中，设置不同参数即可切换部署形态，三种模式与上文一一对应。

```python
# pip install langchain-chroma langchain-openai chromadb

import chromadb
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# 使用 OpenAI 接入 Embedding 模型
embeddings = OpenAIEmbeddings(model="your-embedding-model")

# （1）内存模式：程序运行结束后，数据会丢失
vectorstore_memory = Chroma(
    collection_name="kitchen_memory_store",
    embedding_function=embeddings
)

# （2）本地持久化模式：数据保存在本地 SQLite 和 Parquet 文件中
vectorstore_persist = Chroma(
    collection_name="kitchen_persist_store",
    persist_directory="./chroma_local_db",  # 指定本地保存路径
    embedding_function=embeddings
)

# （3）客户端/服务端模式：需先在后台运行 `chroma run --path /db_path`
chroma_client = chromadb.HttpClient(host="localhost", port=8000)
vectorstore_server = Chroma(
    client=chroma_client,
    collection_name="kitchen_server_store",
    embedding_function=embeddings
)
```

## 二、增删改查

以下代码是 LangChain 封装下的 Chroma 完整功能链路，这里使用本地持久化模式作为演示载体。

```python
import uuid
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from langchain_chroma import Chroma

# 初始化模型与数据库
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
db = Chroma(
    collection_name="kitchen_management",
    persist_directory="./kitchen_db",
    embedding_function=embeddings
)

# ==========================================
# 添加数据 (Add Documents)
# ==========================================
# 构造模拟数据：采用 LangChain 的 Document 对象，数据包含文本内容和结构化元数据
docs = [
    Document(
        page_content="铸铁锅保养指南：每次使用完毕后必须完全擦干，并涂抹薄薄一层植物油，以防生锈。严禁使用洗洁精猛烈刷洗。",
        metadata={"category": "equipment_maintenance", "tool": "cast_iron_pan"}
    ),
    Document(
        page_content="厨房动线设计原则：洗涤区、备餐区、烹饪区应形成高效的黄金三角，减少厨师在烹饪过程中的无效走动。",
        metadata={"category": "kitchen_management", "concept": "workflow"}
    ),
    Document(
        page_content="低温慢煮（Sous-vide）三文鱼的秘诀在于精确控温。建议将水温设定在 50°C，慢煮 45 分钟，可获得最佳口感。",
        metadata={"category": "recipe", "technique": "sous_vide"}
    ),
    Document(
        page_content="主厨猫咪的特制配方：三文鱼猫薄荷舒芙蕾，需要将新鲜打发的蛋清与特制猫薄荷粉轻柔翻拌，保证极致蓬松。",
        metadata={"category": "recipe", "author": "cat_chef"}
    )
]

# 生成显式的 UUID，方便后续的精准更新和删除
doc_ids = [str(uuid.uuid4()) for _ in docs]

# 写入 Chroma (Chroma 会自动调用 OpenAI API 计算 Embedding 并保存到磁盘)
db.add_documents(documents=docs, ids=doc_ids)
print("✅ 数据写入完成！\n")


# ==========================================
# 检索数据 (Search Documents)
# ==========================================

# --- 1. 相似度检索 (Similarity Search) ---
query = "如何防止锅具生锈？"
print(f"🔍 基础检索: '{query}'")
results = db.similarity_search_with_score(query, k=1)
for doc, score in results:
    # 距离分数越低（L2 距离），相似度越高
    print(f"得分: {score:.4f} | 内容: {doc.page_content}\n")

# --- 2. 带元数据过滤的检索 (Metadata Filtering) ---
query = "给我推荐一个鱼类菜谱。"
print(f"🔍 过滤检索: '{query}'")
# Chroma 支持丰富的过滤语法，如 $eq, $ne, $in, $gt 等
filtered_results = db.similarity_search(
    query,
    k=1,
    filter={"author": {"$eq": "cat_chef"}}
)
print("(仅限作者为 cat_chef)")
for doc in filtered_results:
    print(f"匹配内容: {doc.page_content} | 元数据: {doc.metadata}\n")

# --- 3. 最大边际相关性检索 (MMR Search) ---
# MMR 算法：在保证结果与查询相关的前提下，尽量增加返回结果的多样性，避免信息冗余。
query = "厨房里关于三文鱼的做法或者规定有哪些？"
print(f"🔍 MMR 检索: '{query}'")
# fetch_k: 先从数据库取回多少条候选结果；k: 最终返回多少条结果
mmr_results = db.max_marginal_relevance_search(query, k=2, fetch_k=4)
for i, doc in enumerate(mmr_results):
    print(f"结果 {i+1}: {doc.page_content}")
print()


# ==========================================
# 更新文档 (Update Document)
# ==========================================
update_id = doc_ids[0]  # 获取铸铁锅指南的 ID
updated_doc = Document(
    page_content="更新版铸铁锅保养指南：除涂抹植物油外，可放入烤箱微烤 5 分钟让油脂充分渗入。绝对禁止进洗碗机。",
    metadata={"category": "equipment_maintenance", "tool": "cast_iron_pan", "version": "2.0"}
)
print(f"更新文档 ID: {update_id}")
db.update_document(document_id=update_id, document=updated_doc)

# 获取数据，验证更新
check_update = db.get(ids=[update_id])
print(f"🔄 更新后内容: {check_update['documents'][0]}\n")


# ==========================================
# 删除文档 (Delete Document)
# ==========================================
delete_id = doc_ids[1]  # 删除动线设计的文档
print(f"🗑️ 删除文档 ID: {delete_id}")
db.delete(ids=[delete_id])

# 获取数据，验证删除
check_delete = db.get(ids=[delete_id])
print(f"删除后查询结果: {check_delete['documents']} (应为空列表)")
```

## 三、RAG 场景实践

典型 RAG 流水线（原生 `chromadb`）：

```python
# 典型 RAG 流水线
from openai import OpenAI
import chromadb  # 或 qdrant_client, pinecone 等

# 1. 初始化
client = chromadb.PersistentClient(path="./db")
collection = client.get_or_create_collection("docs")

# 2. 文档向量化入库
def add_documents(texts: list[str], ids: list[str], metadatas: list[dict]):
    embeddings = OpenAI().embeddings.create(
        model="text-embedding-3-small",
        input=texts
    ).data

    collection.add(
        embeddings=[e.embedding for e in embeddings],
        documents=texts,
        ids=ids,
        metadatas=metadatas  # 存储来源、日期等过滤字段
    )

# 3. 检索增强生成
def retrieve(query: str, top_k: int = 5, filter: dict = None) -> list[str]:
    query_vec = OpenAI().embeddings.create(
        input=query, model="text-embedding-3-small"
    ).data[0].embedding

    results = collection.query(
        query_embeddings=[query_vec],
        n_results=top_k,
        where=filter  # 元数据过滤，如 {"source": "api_docs"}
    )
    return results["documents"][0]
```
