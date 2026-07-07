# miaokb

> 私人知识库语义搜索与整理工具

一个纯本地、跨平台的命令行工具，用来管理你的私人知识库（Markdown / Word / PDF / Excel），解决「**找不到**」「**理不清**」「**联不上**」三个长期痛点。

## ✨ 特性

- 🔍 **智能搜索**：基于 TF 评分的中文混合切词（整块 + 2-gram + 3-gram），命中长文档里的关键短语
- 📋 **整理建议**：自动发现多版本文件、完全重复文件、散落待归位文件
- 🔗 **文章关联**：基于关键词共现，推荐与某文件相关的其他文档
- 🗃️ **纯本地**：索引存 SQLite（`~/.miaokb/kb.db`），数据不出本机
- 🌐 **跨平台**：macOS / Windows / Linux 都能跑（Python 3.9+）
- 📦 **零依赖**：核心功能只用 Python 标准库，可选 `python-docx` / `pypdf` 扩展文件类型

## 🚀 安装

```bash
# 1. 克隆仓库
git clone https://github.com/jimmywuxin/miaokb.git
cd miaokb

# 2. （推荐）创建虚拟环境
python3 -m venv venv
source venv/bin/activate     # macOS / Linux
# venv\Scripts\activate      # Windows

# 3. （可选）安装扩展依赖
pip install -r requirements.txt
```

## 🎯 快速开始

```bash
# 1. 构建索引（首次或内容更新后）。知识库路径 3 种方式任选：
#
#    a. 命令行参数（跨平台最直接）
python3 indexer.py "/path/to/your/knowledge-base"
#
#    b. 环境变量（适合写进 shell rc / 计划任务）
export KB_ROOT="/path/to/your/knowledge-base"    # macOS / Linux
$env:KB_ROOT = "D:\knowledge-base"               # Windows PowerShell
python3 indexer.py
#
#    c. 改 DEFAULT_KB_ROOT 常量（不推荐，每次切机器都得改源码）

# 2. 搜索
python3 kb.py search "七一活动 定向闯关"

# 3. 整理建议
python3 kb.py organize

# 4. 文章关联
python3 kb.py relate "政绩观"

# 5. 索引统计
python3 kb.py stats
```

## 📖 命令详解

### `indexer.py` 接受路径的方式

`KB_ROOT` 解析优先级：**环境变量 > CLI 参数 > DEFAULT_KB_ROOT**。

| 平台 | 设置环境变量 | 命令行参数 |
| --- | --- | --- |
| macOS / Linux | `export KB_ROOT=/path/to/kb` | `python3 indexer.py /path/to/kb` |
| Windows PowerShell | `$env:KB_ROOT = "D:\kb"` | `python3 indexer.py "D:\kb"` |
| Windows CMD | `set KB_ROOT=D:\kb` | `python3 indexer.py D:\kb` |

### `kb.py stats`
显示索引统计：文件数、词条数、词频总数、TOP 10 高频词。

### `kb.py search <query> [--top N]`
关键词搜索，返回最相关的 N 个文件（默认 10）。

**支持的查询**：
- 纯中文：`灵龟公园`
- 中英混合：`deepseek 配置`
- 多关键词空格分隔：`政绩观 学习教育`（任一命中即可，加权累加）

### `kb.py organize [path]`
扫描指定路径（默认整个知识库），输出整理建议：
- **多版本文件**：同目录下文件名含「草稿/初稿/定稿/修改/新」等关键词
- **完全重复**：基于内容哈希找出完全相同的文件
- **临时文档**：`临时文档/` 目录下的文件，建议审视归位
- **根目录散落**：未归类的根目录文件

### `kb.py relate <file> [--top N]`
根据文件内容的高频词，推荐共现词数最多的 N 个相关文档（默认 5）。

支持部分文件名匹配，如 `relate 政绩观` 会找到 `党课材料_树立和践行正确政绩观.md`。

## 🗂️ 支持的文件类型

| 类型 | 支持 | 依赖 |
|---|---|---|
| `.md` / `.txt` | ✅ 内置 | 无 |
| `.docx` | ✅ 扩展 | `python-docx` |
| `.pdf` | ✅ 扩展 | `pypdf` |
| `.xlsx` | ✅ 扩展 | `openpyxl` |
| `.pptx` | ⚠️ 仅文件名 | — |
| `.html` | ⚠️ 仅文件名 | — |

## 🏗️ 架构

详见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

简要：
```
miaokb/
├── indexer.py          # 索引器：扫文件 → 抽内容 → 写 SQLite
├── kb.py               # CLI：search / organize / relate / stats
├── docs/
│   ├── ARCHITECTURE.md
│   └── ROADMAP.md
├── tests/              # 单元测试（待补）
├── requirements.txt
├── AGENTS.md           # 给 AI agent 看的项目说明
├── CHANGELOG.md
├── LICENSE
└── README.md
```

## 🤖 给 AI 助手

如果你让 Codex / Claude Code / Hermes 等 AI 帮忙开发这个项目，请先读 [AGENTS.md](AGENTS.md)。

## 📅 路线图

详见 [docs/ROADMAP.md](docs/ROADMAP.md)。

## 📜 许可

MIT License — 详见 [LICENSE](LICENSE)。

## 🙋 作者

Jimmy Wu ([@jimmywuxin](https://github.com/jimmywuxin))
