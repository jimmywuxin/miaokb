# AGENTS.md

> 给 AI 编程助手（Codex / Claude Code / Hermes / Cursor / Aider 等）看的项目说明
>
> 人类读者请看 [README.md](README.md)。

## 项目一句话

**miaokb** = 私人知识库语义搜索与整理工具，纯本地 Python CLI。

## 当前状态

- **版本**：v0.1.0（Demo 阶段）
- **已完成**：核心 CLI（search / organize / relate / stats）+ SQLite 倒排索引
- **未做**：GUI、LLM 集成、docx/pdf 解析（已在 roadmap）
- **代码量**：~250 行 Python

## 技术栈

- **语言**：Python 3.9+（测试过 3.9 / 3.11）
- **核心依赖**：**零**（只用标准库）
- **可选依赖**：`python-docx` / `pypdf` / `openpyxl`（v0.2 计划加入）
- **存储**：SQLite（标准库 `sqlite3`）
- **跨平台**：macOS / Windows / Linux

## 目录结构

```
miaokb/
├── indexer.py          # 索引器：扫文件 → 抽内容 → 写 SQLite
├── kb.py               # CLI：search / organize / relate / stats
├── docs/
│   ├── ARCHITECTURE.md # 架构详解
│   └── ROADMAP.md      # 路线图
├── tests/              # 单元测试（v0.3 补）
├── requirements.txt    # 可选依赖
├── AGENTS.md           # 本文件
├── CHANGELOG.md
├── LICENSE             # MIT
└── README.md
```

## 关键设计决策

### 1. 为什么是 SQLite 倒排索引而不是向量数据库？
- v0.1 demo 阶段先验证「词频 + 切词」够不够用
- 用户已经验证 demo 准：搜「灵龟公园」能找到第四稿；搜「政绩观 学习教育」排序合理
- 向量数据库是 v0.3+ 才考虑的事（先看 LLM 接入后效果提升多大）

### 2. 为什么是 2-gram + 3-gram 双重加权？
- 中文不像英文有空格分词
- 单字切会撞停用词；2 字切会撞歧义（如「灵龟」/「龟公」/「公园」独立看都没意义）
- 整块保留 + 2-gram 拆词 + 3-gram 加权，平衡**精度**和**召回**
- **重要规则**：query 和 indexer 的切词逻辑必须**完全一致**，否则 search 0 命中

### 3. 为什么用 TF 评分而不是 TF-IDF？
- Demo 阶段数据量小（97-270 文件），TF 够用
- 词频归一化（`freq / total_tokens * 1000`）已经能区分长短文档
- TF-IDF 留给 v0.2，当索引量 > 1000 文件时再加

### 4. 为什么不一开始就做 GUI？
- 用户的偏好是「**先 demo 再定长线**」
- CLI 1-2 小时能跑通，GUI 1-2 天
- 先验证核心价值（搜索/整理/关联准不准），GUI 是包装问题

## 编程约定

### Python 风格
- 3.9+ 兼容（不用 walrus 运算符在 3.9 里其实支持，但避免 `match` 语句以保 3.9 兼容）
- 类型注解：核心函数都加，参数类型和返回类型
- 注释：中文（用户偏好），简短
- 字符串：`"双引号"` 主用，docstring 用三引号

### 文件命名
- 入口文件 `kb.py`（CLI 短名）
- 索引器 `indexer.py`（明确职责）
- 文档全在 `docs/`，除了 `README.md` / `CHANGELOG.md` / `LICENSE` / `AGENTS.md`（GitHub 习惯）

### 数据库 schema
- `files(id, path, rel_path, size, mtime, content_hash, token_count, summary)`
- `terms(term, file_id, freq)` + `idx_terms_term` 索引
- schema 变更**只增不改**（v0.x 兼容），破坏性变更走 `migrate_vN.py` 脚本

### 错误处理
- 文件读取失败：`errors="ignore"` 静默跳过，不中断整个索引过程
- 索引不存在：CLI 入口给友好提示「先跑 python3 indexer.py」
- query 无效：直接提示，不抛异常

## 任务执行清单

如果用户让你「**加 docx/pdf 支持**」：

1. 看 `indexer.py` 的 `extract_text()` 函数（line ~50 附近）
2. 加 `if path.suffix.lower() == ".docx":` 分支，用 `python-docx` 抽段落
3. 同理加 `.pdf`（用 `pypdf` 的 `PdfReader`）
4. 把依赖加到 `requirements.txt`
5. 跑 `python3 indexer.py` 验证
6. 跑 `python3 kb.py stats` 看文件数变化
7. 更新 `CHANGELOG.md` 的 Unreleased 段

如果用户让你「**加 LLM 语义搜索**」：

1. 不要碰 `search` 命令的现有逻辑，**新增** `kb.py llm-search` 子命令
2. 优先用 LLM 做 **query 改写**（把"灵龟公园"改成"七一活动 党史学习 定向闯关"），再走原有 search
3. 备选：用 LLM 做 **rerank**（拿 search top 20，让 LLM 排前 5）
4. **不要**直接拿整个文档喂 LLM（贵、慢、容易超 token）

## 不要做的事

- ❌ 不要把 `kb.py` 拆成包（`miaokb/` 目录 + `__init__.py`），保持单文件
- ❌ 不要引入 FastAPI / Flask / 任何 web 框架（v0.x 阶段）
- ❌ 不要默认联网（必须显式 `--online` 或独立命令才允许）
- ❌ 不要把 `~/.miaokb/kb.db` 路径硬编码到代码里
- ❌ 不要删除或重命名 `files` / `terms` 表（破坏性 schema 变更）

## 测试

v0.3 之前**没有自动化测试**（Demo 阶段用户手动验证）。v0.3 计划：

```
tests/
├── test_tokenize.py     # 切词逻辑
├── test_search.py       # 搜索准确性（准备一组 query + 期望文件 fixture）
├── test_organize.py     # 整理规则
└── test_relate.py       # 关联推荐
```

## 验证流程

每次改动后跑：

```bash
# 1. 重建索引
python3 indexer.py /Volumes/mac\ mini\ outside/知识库

# 2. 跑核心 4 个命令
python3 kb.py stats
python3 kb.py search "灵龟公园" --top 3
python3 kb.py organize 2>&1 | head -20
python3 kb.py relate "政绩观" --top 3

# 3. 确认 search 没退化（用户验证过的 query）
#    - "灵龟公园" → 期望：临时文档/七一活动方案-灵龟公园党史定向闯关（第四稿）.md
#    - "政绩观 学习教育" → 期望：工作资料/计划总结/关于开展...汇报.md 排第一
```

## 用户偏好（开发相关）

- 短、直接、看结论
- 任务交代后不参与只验收，**交付一次出完整方案+清单**
- 修改前**先商量**，别擅自改配置
- 中文字符串 + 中文注释
- 中文用「」（直角引号），不用 ""
- 飞书长消息偏好 Markdown
