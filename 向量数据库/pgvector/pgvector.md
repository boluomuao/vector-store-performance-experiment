# pgvector 向量数据库扩展

## 一、产品介绍

pgvector 是面向 **Postgres** 的开源向量相似度搜索扩展，支持将向量与业务数据统一存储在同一张表中。

pgvector 支持：

- 精确（exact）和近似（approximate）最近邻搜索
- 单精度、半精度、二进制（binary）和稀疏（sparse）向量
- L2 距离、内积、余弦距离、L1 距离、Hamming 距离和 Jaccard 距离
- 任何提供了 Postgres 客户端的语言

此外，还拥有 Postgres 的全部能力：**ACID 合规、时间点恢复（point-in-time recovery）、JOIN**，以及其它 Postgres 特性。当向量数量很大时，可使用量化（quantization）来扩展。

- 开源许可证：**PostgreSQL License**（PostgreSQL 许可证）
- 最新版本：**v0.8.7**（支持 PostgreSQL 13+）

## 二、核心特点

**1. 与 Postgres 生态无缝集成**

作为 PostgreSQL 扩展，pgvector 天然继承 ACID 合规、时间点恢复（point-in-time recovery）、JOIN 等 Postgres 核心能力。支持结合全文检索进行混合检索（hybrid search），可使用 Reciprocal Rank Fusion（RRF）或 cross-encoder 组合结果。此外还支持过滤（filtering）、多租户（multitenancy）、迭代索引扫描（iterative index scans）、子向量索引（subvectors）、二进制量化（binary quantization）等高级特性。

**2. 多类型向量存储**

pgvector 支持四种向量类型：单精度浮点向量（`vector`）、半精度浮点向量（`halfvec`）、二进制向量（`bit`）和稀疏向量（`sparsevec`），覆盖从低维稠密向量到高维稀疏向量的多种场景，并可借助量化（quantization）手段扩展存储规模。

**3. 灵活的索引策略**

默认执行精确最近邻搜索（perfect recall）；添加索引后可切换为近似最近邻搜索，以牺牲部分召回率换取速度。支持 HNSW 和 IVFFlat 两种索引类型，分别适用于不同性能与资源约束场景。

**4. 丰富的距离度量**

支持 L2 距离、内积、余弦距离、L1 距离、汉明距离和 Jaccard 距离六种距离函数，均可被实现为 SQL 运算符（operator），可以直接在SQL语句中使用，而不需要调用函数，便于在查询中灵活组合。

**5. 广泛的语言支持**

可用任何提供 Postgres 客户端的语言调用 pgvector，甚至可以"用一种语言生成并存储向量，用另一种语言查询"。官方维护了数十种语言的示例库（Go、Java、Python、Rust、JavaScript/TypeScript、.NET、Ruby、PHP 等）。

## 三、快速开始

### 1. 安装

**Linux / Mac（编译安装，支持 Postgres 13+）：**

```bash
cd /tmp
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
make
make install # 可能需要 sudo
```

**Windows（使用 nmake）：**

```bat
set "PGROOT=C:\Program Files\PostgreSQL\18"
cd %TEMP%
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
nmake /F Makefile.win
nmake /F Makefile.win install
```

另外，还可通过 Docker、Homebrew、PGXN、APT、Yum、pkg、APK、conda-forge 安装，或使用已预装 pgvector 的托管 Postgres 服务。

### 2. 启用扩展并创建表

```sql
-- 在需要的每个数据库中执行一次
CREATE EXTENSION vector;

-- 创建一个列： 3 维向量
CREATE TABLE items (id bigserial PRIMARY KEY, embedding vector(3));
```

### 3. 写入数据

```sql
INSERT INTO items (embedding) VALUES ('[1,2,3]'), ('[4,5,6]');
```

### 4. 检索

```sql
-- 按 L2 距离获取最近邻
SELECT * FROM items ORDER BY embedding <-> '[3,1,2]' LIMIT 5;
```

还支持内积（`<#>`）、余弦距离（`<=>`）和 L1 距离（`<+>`）。

> 注意：`<#>` 返回的是负内积，因为 Postgres 仅支持运算符上的升序索引扫描。

## 四、高级操作

### 1. 其它写入方式（Storing）

```sql
-- 批量加载（COPY）
COPY items (embedding) FROM STDIN WITH (FORMAT BINARY);

-- Upsert
INSERT INTO items (id, embedding) VALUES (1, '[1,2,3]'), (2, '[4,5,6]')
ON CONFLICT (id) DO UPDATE SET embedding = EXCLUDED.embedding;

-- 更新
UPDATE items SET embedding = '[1,2,3]' WHERE id = 1;

-- 删除
DELETE FROM items WHERE id = 1;
```

### 2. 距离查询详细用法（Querying）

```sql
-- 内积（注意 <#> 返回负内积）
SELECT * FROM items ORDER BY embedding <#> '[3,1,2]' LIMIT 5;

-- 余弦距离
SELECT * FROM items ORDER BY embedding <=> '[3,1,2]' LIMIT 5;

-- 获取距离值
SELECT embedding <-> '[3,1,2]' AS distance FROM items;

-- 余弦相似度（1 - 余弦距离）
SELECT 1 - (embedding <=> '[3,1,2]') AS cosine_similarity FROM items;

-- 搜索一定距离范围内的行（需配合 ORDER BY 与 LIMIT 才能使用索引）
SELECT * FROM items WHERE embedding <-> '[3,1,2]' < 5;
```

### 3. 创建索引（近似搜索）

**HNSW：**

```sql
CREATE INDEX ON items USING hnsw (embedding vector_l2_ops);
-- 内积：vector_ip_ops    余弦：vector_cosine_ops    L1：vector_l1_ops
-- 可指定参数（m 默认 16，ef_construction 默认 64）
CREATE INDEX ON items USING hnsw (embedding vector_l2_ops) WITH (m = 16, ef_construction = 64);
```

查询时调整候选列表大小（默认 40）：

```sql
SET hnsw.ef_search = 100;
```

**IVFFlat：**

```sql
CREATE INDEX ON items USING ivfflat (embedding vector_l2_ops) WITH (lists = 100);
-- 内积：vector_ip_ops    余弦：vector_cosine_ops    汉明：bit_hamming_ops
```

查询时指定 probes 数量（默认 1）：

```sql
SET ivfflat.probes = 10;
```

> 使用 IVFFlat 获得良好召回率的三条要点：在表已有数据后创建索引；选择合适的 lists 数量（不超过 100 万行时用 `rows / 1000`，超过 100 万行时用 `sqrt(rows)`）；查询时指定合适的 probes 数量（起始值 `sqrt(lists)`）。

### 4. 混合检索（结合全文检索）

```sql
SELECT id, content FROM items, plainto_tsquery('hello search') query
WHERE textsearch @@ query ORDER BY ts_rank_cd(textsearch, query) DESC LIMIT 5;
```

## 五、部署架构

pgvector 不是一个独立的数据库服务，而是 **PostgreSQL 的一个扩展（extension）**，因此其部署架构依附于 PostgreSQL 本身，官方提供了**基于官方 Postgres 镜像预装 pgvector** 的 Docker 镜像。

### 官方镜像（Docker）

官方在 Docker Hub 提供 `pgvector/pgvector` 镜像，它在 Postgres 官方镜像基础上加入了 pgvector：

```bash
docker pull pgvector/pgvector:pg18-trixie
```

它的运行方式与 Postgres 官方镜像完全一致（替换 `18` 为你的 Postgres 版本）。官方支持的标签包括：

- `pg18-trixie`, `0.8.7-pg18-trixie`
- `pg18-bookworm`, `0.8.7-pg18-bookworm`, `pg18`, `0.8.7-pg18`
- `pg17-trixie`, `0.8.7-pg17-trixie`
- `pg17-bookworm`, `0.8.7-pg17-bookworm`, `pg17`, `0.8.7-pg17`
- `pg16-trixie` / `pg16-bookworm` / `pg16`, `0.8.7-pg16*`
- `pg15-trixie` / `pg15-bookworm` / `pg15`, `0.8.7-pg15*`
- `pg14-trixie` / `pg14-bookworm` / `pg14`, `0.8.7-pg14*`
- `pg13-trixie` / `pg13-bookworm` / `pg13`, `0.8.7-pg13*`

也可自行构建镜像：

```bash
git clone --branch v0.8.7 https://github.com/pgvector/pgvector.git
cd pgvector
docker build --pull --build-arg PG_MAJOR=18 -t myuser/pgvector .
```

> 如果增大了 `maintenance_work_mem`，请确保 `--shm-size` 至少为其大小，以避免并行 HNSW 索引构建报错：`docker run --shm-size=1g ...`。

### 其它安装方式

| 方式 | 命令 |
| --- | --- |
| Homebrew | `brew install pgvector` |
| PGXN | `pgxn install vector` |
| APT (Debian/Ubuntu) | `sudo apt install postgresql-18-pgvector` |
| Yum / DNF | `sudo yum install pgvector_18` |
| pkg (FreeBSD) | `pkg install postgresql18-pgvector` |
| APK (Alpine) | `apk add postgresql-pgvector` |
| conda-forge | `conda install -c conda-forge pgvector` |

### 部署与扩展形态

| 形态 | 说明 |
| --- | --- |
| **单实例 PostgreSQL** | 直接启用 `vector` 扩展即可，最基础的部署方式 |
| **垂直扩展** | 在单实例上增加内存、CPU、存储，并调优参数以监控性能 |
| **水平扩展** | 使用副本（replicas），或结合 Citus、PgDog 等方案进行分片 |
| **缩小工作集** | 使用 `halfvec` 类型代替 `vector`；对索引使用二进制量化（配合重排序） |

### 升级

安装最新版本后（使用与初次安装相同的方式），在需要升级的每个数据库中执行：

```sql
ALTER EXTENSION vector UPDATE;
```

查看当前数据库中的版本：

```sql
SELECT extversion FROM pg_extension WHERE extname = 'vector';
```

## 常见问题（官方 FAQ 摘录）

- **单表可存储多少向量？** 默认情况下，非分区表在 Postgres 中有 32 TB 限制；分区表可以有成千上万个该大小的分区。
- **是否支持复制？** 支持。pgvector 使用预写日志（WAL），支持复制和时间点恢复。
- **如何为超过 2,000 维的向量建立索引？** 可使用半精度向量或半精度索引（最高 4,000 维），或使用二进制量化（最高 64,000 维）；也可索引子向量或进行降维。
- **能否在同一列中存储不同维度的向量？** 可以，使用 `vector` 类型（而非 `vector(n)`）；但只能对维度相同的行创建索引（借助表达式索引和部分索引）。

## 附录：技术规格

### 向量类型

| 类型 | 说明 | 最大维度 / 元素数 |
| --- | --- | --- |
| `vector` | 单精度浮点向量，每个向量占 `4 * dimensions + 8` 字节 | 最多 16,000 维 |
| `halfvec` | 半精度浮点向量，每个向量占 `2 * dimensions + 8` 字节 | 最多 16,000 维 |
| `bit` | 二进制向量，占 `dimensions / 8 + 8` 字节 | 最多 64,000 维 |
| `sparsevec` | 稀疏向量，占 `8 * 非零元素 + 16` 字节 | 最多 16,000 个非零元素 |

所有元素必须为有限值（不允许 NaN、Infinity、-Infinity）。

### 距离运算符

| 运算符 | 描述 |
| --- | --- |
| `<->` | L2 / 欧氏距离（Euclidean） |
| `<#>` | 负内积（negative inner product） |
| `<=>` | 余弦距离（cosine distance） |
| `<+>` | L1 / 曼哈顿距离（taxicab） |
| `<~>` | 汉明距离（binary vectors） |
| `<%>` | Jaccard 距离（binary vectors） |

> 注意：`<#>` 返回的是**负内积**，因为 Postgres 仅支持运算符上的升序索引扫描。

### 索引类型

| 索引 | 说明 |
| --- | --- |
| **HNSW** | 多层图索引，查询性能更好（速度-召回率权衡），但构建时间更慢、内存占用更多；可在表中无数据时创建 |
| **IVFFlat** | 倒排文件索引，构建更快、内存占用更少，但查询性能较低；需在表已有数据后创建 |

## 参考

- 官方仓库： https://github.com/pgvector/pgvector
- Docker Hub： https://hub.docker.com/r/pgvector/pgvector
