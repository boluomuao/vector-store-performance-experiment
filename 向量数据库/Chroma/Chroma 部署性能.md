# Chroma 部署性能

单节点模式的 Chroma 易于部署和维护，同时提供稳健性能，满足广泛的生产应用需求。

为了帮助你判断单节点 Chroma 是否适合你的用例，我们进行了一系列压力测试和性能实验，以探究系统的能力边界，发现其局限性和极端情况。我们在多种硬件配置下分析了这些边界，以确定针对不同工作负载的合适部署方案。本文档将介绍这些发现，以及一些能最大化 Chroma 部署效能的通用原则。

## 结果摘要

大致来说，以下是 Chroma 在不同 EC2 实例类型上，处理典型工作负载时，你可以预期的性能表现：
- 1024 维度的嵌入向量
- 小文档（100-200 词）
- 每条记录包含三个元数据字段。

**不建议**在内存小于 2GB 的系统上部署 Chroma。请注意，下表中的延迟数据是针对小规模集合的。随着集合增长，延迟会增加：完整分析请见下文 延迟与集合规模。

## 内存与集合规模

Chroma 使用 [`hnswlib`](https://github.com/nmslib/hnswlib) 的分支高效索引和搜索嵌入向量。HNSW 算法要求嵌入索引驻留在内存中以便查询或更新。因此，可用系统内存量定义了 Chroma 集合（或并发多集合）大小的上限。如果集合超过可用内存，操作系统开始将内存交换到磁盘，写入和查询延迟会急剧上升。索引的内存布局不适合交换，系统很快就会变得不可用。

因此，用户应始终规划配置足够的内存，以容纳预期的总嵌入向量数量。为了分析需要多少内存，我们在不同规格的 EC2 实例上启动了一个 Chroma 实例，然后持续插入嵌入向量，直到每个系统无响应。正如预期，这个失效点与内存和嵌入向量数量呈线性相关。对于 1024 维的嵌入向量（含三条元数据和小文档），公式为 `N = R * 0.245`，其中 `N` 为最大集合规模（百万），`R` 为所需内存（GB）。请记住，除了 Chroma 所需的内存外，你还需要为系统的其他需求预留至少 1GB 内存。
这个规律在我们测试到的约 700 万嵌入向量范围内都成立。在此规模下，Chroma 依然快速稳定，我们没有发现 Chroma 数据库的严格上限。

## 磁盘空间与集合规模

Chroma 会将每个集合持久化保存到磁盘。所需空间大小由两部分组成：HNSW 嵌入索引空间，以及用于存储文档和元数据的 SQLite 数据库空间。

计算持久化 HNSW 索引所需空间的方法与计算内存大小类似。一个经验法则是，确保系统的存储空间至少与其内存大小相当，并额外预留数 GB 以容纳操作系统和其他应用程序的开销。

SQLite 数据库所需的空间变化很大，完全取决于是否在 Chroma 中保存文档和元数据，以及它们的大小。参考：一个包含约 4 万篇文档（每篇约 1000 词）和约 60 万条元数据记录的集合，其 SQLite 数据库大小约为 1.7GB。元数据数据库的大小没有严格的上限：SQLite 本身支持 TB 级别的数据库，并能有效地分页到磁盘。

在大多数实际用例中，很可能是内存中 HNSW 索引的大小和性能，远在元数据数据库之前，就成为 Chroma 集合规模的限制因素。

## 延迟与集合规模

随着集合变大、索引规模增长，写入和查询操作耗时都会增加。延迟的增长速度起初相当平缓，之后大致呈线性增长，其拐点和斜率取决于可用 CPU 的数量和速度。某些实例（如 `t3.2xlarge`）图表末端的极端峰值，发生在实例达到其内存限制时。

### 查询延迟

![查询延迟性能](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/query_latency_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=da5e5509f146fe3f079c5239f6506116)

查询延迟性能

### 写入延迟

![写入延迟性能](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/insert_latency_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=90fe425f981baffd65649c917b22874f)

写入延迟性能

==若使用多个集合，性能取决于集合总嵌入数。将一个大集合拆分成多个小集合并无助益，只要能同时装入内存。==

## 并发

系统能并行处理并发操作。对于写入，由于写入操作会先记录到日志中，然后每隔 N 次操作批量刷新一次，因此平均延迟不会随着写入线程数的增加而波动，但会随着批次大小的增加而增加，因为更大的批次更可能触发刷新阈值。查询操作的并行度最高可达实例可用的 vCPU 数量，超过此数量后请求开始排队，导致延迟线性增加。
![并发写入](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/concurrent_writes_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=f20f71d580352a5d6bb42dd2e8630f46)

并发写入

![并发查询](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/concurrent_queries_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=ebfdd475a8ff80daaa8a2f2b8d5c9f08)

并发查询

当并发度（如批量插入数据时）可由你控制时，关于如何优化用户数以获得最大吞吐量的讨论，请参阅下文 [写入吞吐量](https://docs.trychroma.com/guides/deploy/performance#insert-throughput)。

## CPU 速度、核心数与类型

![CPU 平均查询延迟](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/cpu_mean_query_latency_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=17a975af27d01c146fe34b32553fb5b6)

CPU 平均查询延迟

## 写入吞吐量

常见问题：批量写入数据能多快？最佳方式是什么？

首要因素是并发写入请求数。如 [并发](https://docs.trychroma.com/guides/deploy/performance#concurrency) 所述，增加并发有利于写入吞吐量。其次考虑请求批大小。由于小批次的固定开销较高，性能会随着批次大小增加而提升，直到 CPU 饱和。达到 CPU 饱和后，批次大小约在 150 左右，吞吐量进入平台期。

实验证实：在 100-500 的批次大小范围内，总体吞吐量（跨批次大小和请求数的总插入嵌入向量数）保持相当稳定：

![并发写入](https://mintcdn.com/chroma-8943dec5/OHTRZei6ss2glLVb/images/concurrent_inserts_1_0_10-light.png?w=280&fit=max&auto=format&n=OHTRZei6ss2glLVb&q=85&s=a576838a7b3e78057e0cd6e4c18678c4)

并发写入

鉴于较小的批次具有更低、更一致的延迟，并且更不容易导致超时错误，我们建议选择此曲线中批次大小偏小的一侧：在 50 到 250 之间的任何值都是合理的选择。

## 结论

当部署在合适的硬件上时，用户可以放心地依赖 Chroma 来处理接近数千万嵌入向量的用例。其读写操作的平均延迟和上限延迟使其成为除超大规模 AI 应用之外的良好平台，可能支持数千名并发人类用户（具体取决于你应用程序的后端访问模式）。然而，作为一个单节点解决方案，它无法无限扩展。
