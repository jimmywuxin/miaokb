# 路线图 (Roadmap)

> miaokb 接下来要做的事。按优先级排，每阶段独立可用。

## 已完成

- [x] **v0.1.0**（2026-06-09）— Demo 版
  - [x] SQLite 倒排索引
  - [x] 中文混合切词（2-gram + 3-gram 双重加权）
  - [x] `search` / `organize` / `relate` / `stats` 4 个命令
  - [x] 用户手动验证：3 个核心痛点（找/整/联）demo 准
  - [x] 7 个项目文档（README/CHANGELOG/LICENSE/AGENTS/架构/路线图）
  - [x] GitHub repo 建立

---

## v0.2 — 文件类型覆盖（1-2 周）

**目标**：从「97 个 md」覆盖到「全部 270 个文件」。

### 必做
- [ ] `.docx` 解析（`python-docx`）
- [ ] `.pdf` 解析（`pypdf`）
- [ ] `.xlsx` 解析（`openpyxl`）
- [ ] `requirements.txt` 正式发布
- [ ] 增量索引（按 mtime 跳过未变文件）

### 改进
- [ ] `organize` 加白名单（`索引.md` / `项目笔记-模板.md` 不再误报）
- [ ] `organize` 按时间聚类（找「2025年」「2026年」开头的系列文件）
- [ ] 跨平台路径处理（`pathlib.Path` 替代字符串拼接）

### 验收
- 索引覆盖 270 个文件
- `search` 能搜到 docx 内容
- 增量重建 < 5 秒

---

## v0.3 — 测试 + TF-IDF（2-3 周）

**目标**：代码质量 + 搜索精度。

### 必做
- [ ] `tests/test_tokenize.py`（切词单元测试）
- [ ] `tests/test_search.py`（黄金 query fixture）
- [ ] `tests/test_organize.py`（4 条规则覆盖）
- [ ] `tests/test_relate.py`（关联准确性）
- [ ] TF-IDF 评分替换 TF（按文件数加 IDF 权重）

### 改进
- [ ] 配置文件 `~/.miaokb/config.toml`
  - 自定义停用词
  - 忽略目录（`.git`, `node_modules` 等）
  - 知识库路径（避免每次命令行传）
- [ ] 跨平台安装脚本
  - macOS / Linux: `install.sh`
  - Windows: `install.bat` / `install.ps1`
- [ ] 错误处理：文件锁、编码错误、权限问题

### 验收
- 测试覆盖率 > 80%
- 「政绩观 学习教育」排序变化（应该汇报 > 大纲 > 党课材料 不变，但分数更合理）

---

## v0.4 — LLM 增强（1-2 个月）

**目标**：从「关键词匹配」升级到「真语义」。

### 必做
- [ ] LLM 客户端封装 `llm.py`
  - 支持 MiniMax（用户主用）
  - 支持 DeepSeek / OpenAI 兼容
  - 配置走 `~/.miaokb/config.toml`（API key、base_url）
- [ ] `search --semantic` 子命令
  - 用 LLM 做 query 改写（"灵龟公园" → "七一活动 党史学习 定向闯关"）
  - 再走原有 search 索引
- [ ] `relate --llm` 子命令
  - 拿 top 20 文件，让 LLM 重排序
  - 输出「为什么相关」的一句话解释

### 改进
- [ ] 关键词摘要（每个文件 100 字以内摘要存 DB）
- [ ] 跨文档主题聚类（"给我讲讲党建相关的所有内容"）

### 验收
- 语义搜索能处理同义词（搜「普法」能找到「法治宣传」）
- LLM 解释的相关性 > 纯词频

### 不做
- ❌ 不做向量数据库（数据量小，LLM rerank 够用）
- ❌ 不做端到端 embedding（贵、慢、跨平台部署麻烦）

---

## v0.5 — 桌面 GUI（2-3 个月）

**目标**：从 CLI 升级到 Tauri 桌面 app。

### 必做
- [ ] Tauri 项目初始化
- [ ] 前端：搜索框 + 结果列表 + 标签页（搜索/整理/关联）
- [ ] 后端：把 `kb.py` 逻辑封装成 sidecar binary
- [ ] macOS `.dmg` 打包
- [ ] Windows `.msi` / `.exe` 打包

### 设计
- 单窗口，左侧导航（搜索/整理/关联/统计/设置）
- 搜索框支持实时建议（基于已有文件名）
- 结果点击 → 系统默认 app 打开

### 验收
- macOS + Windows 双平台安装包
- 启动 < 2 秒
- 1000 文件搜索 < 500ms

---

## v1.0 — 正式版（6 个月+）

**目标**：可对外发布。

- [ ] 完整文档站（GitHub Pages / Vercel）
- [ ] 视频演示
- [ ] 用户手册（中英双语）
- [ ] 性能优化（10000 文件 < 1 秒搜索）
- [ ] 可选云端同步（用户自配 WebDAV）

---

## 不在路线图里（明确不做）

- ❌ 多用户 / 协作
- ❌ 云端 SaaS
- ❌ 移动端 App
- ❌ 实时同步
- ❌ 文件内容编辑（这是 Notion / Obsidian 的活）
- ❌ 复杂的权限管理

## 决策原则

每加一个功能前问 3 个问题：

1. **真的解决痛点吗？**——Jimmy 实际用得上吗？还是「有了更好」？
2. **复杂度值不值？**——能砍掉就砍掉，简单是竞争力
3. **能跨平台吗？**——macOS / Windows / Linux 行为要一致

## 反馈

试用中遇到问题或新需求，在 GitHub Issues 提：
https://github.com/jimmywuxin/miaokb/issues
