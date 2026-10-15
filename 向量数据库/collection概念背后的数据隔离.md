**Milvus、ChromaDB、Qdrant、Weaviate** 中均使用`Collection` (**Pinecone** 中使用 `Namespace`) 来表示数据组织与隔离的容器。

但定位稍有不同：
- **Milvus 的 Collection**：高度结构化，**几乎等同于关系型数据库中的表**。你需要预先定义严格的 `Schema`（字段名、数据类型、向量维度等），拥有主键约束、分区和索引等高级特性[](https://milvus.io/docs/zh/v2.6.x/manage-collections.md#1)[](https://blog.51cto.com/mecode/14932930#1)。它适用于生产环境的大规模、高性能场景。

- **ChromaDB 的 Collection**：轻量且灵活，**更像是一个带有元数据的“文档容器”**。它不需要预定义 Schema，添加数据时自动处理 ID、Embedding、元数据和文档内容[](https://docs.trychroma.com/docs/collections/manage-collections.md)[](https://docs.trychroma.com/reference/architecture/overview)。它主要面向快速原型开发和中小规模应用[](https://blog.csdn.net/weixin_40815218/article/details/149887155#1)。

一个Collection通常包含：
- **向量**：文本、图片等内容的 Embedding
- **原始数据**：如文本片段、文件名、图片地址
- **元数据**：如来源、时间、作者、分类标签
- **相似度计算配置**：如余弦相似度、欧氏距离、点积
- **索引结构**：用于加速相似度检索

进阶阅读：

| 向量数据库    | 常见层级关系                                      |
| -------- | ------------------------------------------- |
| Milvus   | Database → Collection → Partition → Segment |
| Qdrant   | Collection → Point                          |
| Weaviate | Collection（以前叫 Class）→ Object               |
| ChromaDB | Collection → Document / Embedding           |

区分collection的目的：
1. 逻辑隔离数据
不同主题/类型的文档放在不同的collection中，不同用户、业务或者项目的数据也可以分开存放。
2. 元数据管理
Milvus 和 Weaviate 通常需要在 Collection 中定义字段或属性；ChromaDB 相对灵活，但通常也应保持同一 Collection 内数据结构一致。
3. 配置独立的检索算法、向量空间
可以为collection配置不同向量索引，或者配置不同的相似度计算方式（如余弦相似度、欧氏距离等）。甚至配置不同的embedding模型，这会构建出不同的向量空间。