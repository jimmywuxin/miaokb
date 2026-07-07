# 更新日志 (Changelog)

本项目的所有重要变更都将记录在此文件中。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [语义化版本](https://semver.org/lang/zh-CN/)。

## [Unreleased]

### 计划中
- 跨平台一键安装脚本（`install.sh` / `install.bat`）
- 配置文件（自定义停用词、知识库路径、忽略规则）
- 接入 LLM 做语义搜索（MiniMax / DeepSeek / OpenAI 兼容）
- 桌面 GUI（Tauri 套壳）

## [0.2.1] - 2026-07-08

### Added
- `organize` 规则 2 「根目录散落」新增白名单 `ROOT_WHITELIST`，默认屏蔽 `索引.md` / `项目笔记-模板.md` / `README.md`，不再误报

### Changed
- **`indexer.py` 改为增量索引**：对比上一轮的快照（path → mtime + content_hash）和这一轮 rglob 结果，只处理变化的 4 类：
  - mtime 一致 → fast path 跳过（连 hash 都不用算）
  - mtime 变了但 hash 没变（被 touch）→ 仅更新 mtime
  - 真改了 / 新增了 → 重抽内容 + 重写 terms
  - 老有、这轮没扫到 → 删除 files + terms 行
- `files` / `terms` 表 schema 不变，向后兼容，老 db 直接继承可用

### Notes
- 首次跑（空 db）走相同代码路径，老快照为空 = 全部走 INSERT，等价全量重建
- 输出报告从「文本文件: N」改为 `新增 N 修改 N 删除 N 跳过 N` + 首次 / 增量标签 + 耗时（秒）
- 已验证黄金 query「灵龟公园」/「政绩观 学习教育」排序不退化

## [0.2.0] - 2026-07-07

### Added
- 支持 `.docx` / `.pdf` / `.xlsx` 文件解析（`python-docx` / `pypdf` / `openpyxl`，均为可选依赖）
- 索引文件类型从 2 种（`.md` / `.txt`）扩展到 5 种
- `KB_ROOT` 支持环境变量（`KB_ROOT=/path`）或 CLI 参数（`python3 indexer.py /path`），跨平台不用改源码
- 缺失可选依赖时静默跳过对应类型，不影响其他类型正常工作

### Changed
- `indexer.py` 的 `extract_text()` 重构为按扩展名分发到对应提取器
- 模块顶部常量拆分为 `DEFAULT_KB_ROOT`（兜底值）+ `KB_ROOT`（运行时生效值）
- 新增 `resolve_kb_root()` 函数封装路径解析优先级：env > CLI > default

### Notes
- 抽提成功率 100%（在 297 个文件 / 5 种类型上验证）
- 黄金 query 排序不退化：「灵龟公园」/「政绩观 学习教育」均返回相关文件

## [0.1.0] - 2026-06-09

### 🎉 首次发布 (Demo 版)

#### 已实现
- `indexer.py`：扫描知识库，构建 SQLite 倒排索引
  - 支持 `.md` / `.txt`
  - 中文混合切词：整块 + 2-gram + 3-gram 双重加权
  - 文件名 + 内容同时索引
  - 停用词过滤、低频词过滤
- `kb.py`：CLI 入口，提供 4 个子命令
  - `stats`：索引统计 + TOP 10 高频词
  - `search <query>`：TF 评分关键词搜索
  - `organize [path]`：多版本/重复/散落文件检测
  - `relate <file>`：基于关键词共现的关联推荐

#### 已知限制
- 不支持 docx / pdf / xlsx（需要装扩展依赖，v0.2 计划）
- 没有 LLM，纯词频匹配
- 整理建议的「多版本」检测会误报本就多文件的目录（v0.2 改进）
- 根目录散落文件检测会把 `索引.md` 和 `项目笔记-模板.md` 这种有意保留的文件也报出来（需要白名单机制）

#### 验证场景
- 在 97 个 md / 270 个文件的真实知识库上跑通
- 「灵龟公园」搜索 → 准确返回最新「第四稿」
- 「政绩观 学习教育」搜索 → 排序合理（汇报 > 大纲 > 党课材料）
- `organize` → 发现 2 个完全重复文件 + 4 个临时文档待归位
- `relate 政绩观` → 推荐出 PPT 大纲 / 民主生活会 / 总结讲话稿
