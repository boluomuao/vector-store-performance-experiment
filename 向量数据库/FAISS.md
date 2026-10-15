**FAISS**是一个C++编写、提供Python接口的Embedding算法库。

**运行**
**FAISS**通过`import faiss`内嵌在代码中，跑在应用服务的内存里。 ^567a69

**存储**
FAISS在内存中构建索引，并在磁盘上保存为一个`.index`的二进制文件。

**检索**
FAISS检索时返回ID。需要在关系型数据库中通过ID查询对应的文本。