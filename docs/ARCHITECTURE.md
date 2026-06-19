# 架构说明

> miaokb 的技术架构详解。代码量 ~250 行，刻意保持简单。

## 总览

miaokb 是**单进程、纯本地**的 Python CLI。核心数据流：

```
┌─────────────────┐
│  用户知识库目录  │   (/Volumes/.../知识库/)
│  (.md/.docx/...)│
└────────┬────────┘
         │ rglob + 读文件
         ▼
┌─────────────────┐
│   indexer.py    │   1. 抽文本
│   (索引器)       │   2. 切词
│                 │   3. 算词频
└────────┬────────┘
         │ INSERT
         ▼
┌─────────────────┐
│   SQLite 索引   │   ~/.miaokb/kb.db
│   files / terms │
└────────┬────────┘
         │ SELECT
         ▼
┌─────────────────┐
│     kb.py       │   search / organize
│   (CLI 入口)    │   relate / stats
└─────────────────┘
```

## 模块划分

### `indexer.py` — 索引器

**职责**：把文件系统 → SQLite 倒排索引。

**核心数据结构**：

```sql
-- 文件元数据
CREATE TABLE files (
    id INTEGER PRIMARY KEY,
    path TEXT UNIQUE,           -- 绝对路径
    rel_path TEXT,              -- 相对知识库根的路径
    size INTEGER,               -- 字节
    mtime TEXT,                 -- ISO 格式最后修改时间
    content_hash TEXT,          -- MD5 前 12 位（用于找完全重复）
    token_count INTEGER,        -- 该文件的总词数
    summary TEXT                -- 前 200 字符摘要
);

-- 倒排索引（term → file_id → 频次）
CREATE TABLE terms (
    term TEXT,
    file_id INTEGER,
    freq INTEGER,
    PRIMARY KEY (term, file_id)
);
CREATE INDEX idx_terms_term ON terms(term);
```

**关键函数**：

| 函数 | 职责 |
|---|---|
| `tokenize(text)` | 中文混合切词（详见下）|
| `extract_text(path)` | 读文件内容，按扩展名分发（v0.1 只 md/txt）|
| `build_index()` | 主流程：遍历 → 切词 → 写库 |
| `file_hash(content)` | MD5 截断，用于完全重复检测 |

### `kb.py` — CLI 入口

**职责**：解析参数 → 查库 → 打印结果。

**4 个子命令**：

| 命令 | 实现逻辑 |
|---|---|
| `search` | query 切词 → `IN (...)` 查 terms → JOIN files → 按 TF 评分排序 |
| `organize` | 全表扫描 + 4 条规则（多版本/重复/临时/散落）|
| `relate` | 找文件 → 拿 top 20 高频词 → 去其他文件查共现词数 |
| `stats` | 简单 COUNT/SUM |

## 核心算法

### 1. 中文切词

**问题**：中文没有空格分词，单纯整块匹配召回率低（搜「灵龟公园」找不到「灵龟公园党史定向闯关」），单纯 2-gram 精度差（搜「公园」会匹配大量无关）。

**方案**：**整块 + 2-gram + 3-gram 双重加权**

```python
def tokenize(text):
    tokens = []
    for m in re.finditer(r'[\u4e00-\u9fff]+|[a-zA-Z]+', text):
        seg = m.group()
        if seg[0].isascii():
            if len(seg) >= 2:
                tokens.append(seg.lower())
        else:
            if len(seg) >= 2:
                tokens.append(seg)              # 整块
            if len(seg) >= 3:
                for i in range(len(seg) - 1):
                    tokens.append(seg[i:i+2])   # 2-gram
            if len(seg) >= 4:
                for i in range(len(seg) - 2):
                    tokens.append(seg[i:i+3])   # 3-gram（双重加权）
                    tokens.append(seg[i:i+3])
    return tokens
```

**关键点**：
- 3-gram **加 2 次**提升权重（精准短语优先于散 2-gram）
- 停用词过滤：`的/了/和/是/在/...`（中文 + 英文）
- 低频过滤：`freq < 2` 直接丢弃（省空间、降噪声）

**黄金规则**：`indexer.py` 和 `kb.py` 的切词逻辑**必须完全一致**，否则 search 0 命中。

### 2. 搜索评分

**TF 归一化评分**：

```sql
SELECT f.rel_path, f.summary, f.token_count, f.mtime,
       SUM(t.freq) as total_hits,
       CAST(SUM(t.freq) AS REAL) / f.token_count * 1000 as score
FROM terms t
JOIN files f ON f.id = t.file_id
WHERE t.term IN (?, ?, ...)        -- query 切出来的所有词
GROUP BY f.id
ORDER BY score DESC
LIMIT ?
```

**公式**：`score = (命中总词频 / 文件总词数) × 1000`

**为什么这样**：
- 短文档每词权重大，长文档稀释 → 防止长文档霸榜
- × 1000 是为了让分数看起来是「个位数级别」，方便人眼读

**未来**：v0.2 加 IDF 权重（`log(N / df)`），区分常见词和稀有词。

### 3. 整理规则

`organize` 的 4 条规则：

| 规则 | 检测方式 | 输出 |
|---|---|---|
| 多版本文件 | 同目录 + 文件名含 `草稿/初稿/定稿/修改/新版/(新)` | 整目录列出 |
| 完全重复 | content_hash 重复 | 两两配对列出 |
| 临时文档 | 路径前缀 `临时文档/` | 全部列出 |
| 根目录散落 | rel_path 不含 `/` | 全部列出 |

**已知误报**：
- 「工作资料/计划总结/」本身就有 30 个文件，被整组标为多版本
- 「索引.md」「项目笔记-模板.md」是有意保留的散落文件
- **v0.2 改进**：加白名单 + 按修改时间分组 + 启发式（找"系列文件"模式）

### 4. 关联推荐

**核心思想**：用目标文件的**高频词集合**，去其他文件查**共现词数**。

```sql
-- 拿目标文件 top 20 高频词
SELECT term, freq FROM terms WHERE file_id = ? ORDER BY freq DESC LIMIT 20

-- 查其他文件与这批词的共现
SELECT f.rel_path,
       COUNT(DISTINCT t.term) as common,  -- 多少个词同时出现
       SUM(t.freq) as total               -- 总频次（加权）
FROM terms t
JOIN files f ON f.id = t.file_id
WHERE t.term IN (?, ?, ...) AND f.id != ?
GROUP BY f.id
ORDER BY common DESC, total DESC
LIMIT ?
```

**排序逻辑**：先按 `共现词数`，再按 `总频次`——前者是「主题相关性」，后者是「内容深度」。

## 数据规模假设

| 规模 | 性能 | 索引大小 |
|---|---|---|
| 100 文件 | < 1 秒 | ~5 MB |
| 1000 文件 | ~5 秒 | ~50 MB |
| 10000 文件 | ~60 秒 | ~500 MB |

SQLite 在单文件、单用户场景下**完全够用**，无需切到 Elasticsearch / pgvector。

## 安全与隐私

- **零网络**：v0.x 默认不联网，所有处理本地完成
- **数据全在 `~/.miaokb/`**：用户自管，可备份、可删除、可迁移
- **不读隐藏目录**：`if any(part.startswith(".") for part in path.parts): continue`
- **不修改原文件**：indexer 只读，kb.py 只读

## 未来扩展点（v0.2+）

```
indexer.py
├── extract_text()  ──→ 加 docx/pdf/xlsx 分支
├── tokenize()      ──→ 加 jieba 精确模式
└── build_index()   ──→ 增量更新（按 mtime）

kb.py
├── search     ──→ 加 LLM query 改写 / rerank
├── organize   ──→ 加白名单配置 + 启发式
├── relate     ──→ 加 LLM 摘要版
└── stats      ──→ 不变

新文件
├── config.py  ──→ 用户配置（停用词、忽略规则、路径）
├── llm.py     ──→ LLM 客户端封装
└── gui/       ──→ Tauri 桌面 GUI（v0.4+）
```

## 设计原则

1. **简单优先**：能用标准库就不用第三方依赖
2. **纯本地**：数据不出本机是底线
3. **可验证**：每次改动跑 4 个核心命令 + 黄金 query
4. **不破坏兼容**：schema 只增不改
5. **慢一点没事**：用户 1 个人用，不是 1000 QPS 服务
