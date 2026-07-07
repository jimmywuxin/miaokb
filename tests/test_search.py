"""search 黄金 query 回归测试 + v0.2.1 增量索引不退化。

设计思路：
  - tmpdir 写 3 个 .md fixture（主题各占一个），主题词词频够高
  - setUp 切 indexer.KB_ROOT + DB_PATH 到 fixture，跑首次 build_index
  - _search() 跑 cmd_search 同款 SQL，返回 top-N 行
  - 增量回归 case：改 fixture 内容后跑 build_index，验证 search top-1 不退化

跑法：
    cd 项目根目录
    python3 -m unittest tests.test_search -v
"""
import re
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import indexer  # noqa: E402


# ---- fixture 内容（主题词频拉满，search 能区分）-------------------------

LINGGUI = """\
# 七一活动方案-灵龟公园党史定向闯关

本次活动选址灵龟公园，内容为党史学习教育定向闯关。
灵龟公园是热门打卡地，灯光秀、夜景都很美。
灵龟公园开放时间早 6 点到晚 10 点，适合团建。
灵龟公园闯关活动已吸引周边单位 30 余家报名。
"""

ZHENGJIGUAN = """\
# 关于开展政绩观学习教育汇报

本次政绩观学习教育围绕树立正确政绩观展开。
学习教育期间，共组织 5 次专题学习。
政绩观的核心是人民至上，政绩观教育要常态化。
学习教育注重实效，推动形成正确政绩观氛围。
"""

DEEPSEEK = """\
# DeepSeek 配置笔记

DeepSeek 是一个国内可用的大模型 API 服务。
deepseek 配置方法：base_url + api_key。
deepseek 优势：中文能力强、价格便宜、推理速度快。
deepseek 注意事项：请求频率限制、流式输出协议。
"""


# ---- 测试类 --------------------------------------------------------------


class TestGoldenSearch(unittest.TestCase):
    """黄金 query 回归 - 防 v0.2.1 增量逻辑 + search TF 评分回退"""

    def setUp(self):
        """建临时 fixture，跑首次 build_index"""
        self.tmpdir = tempfile.mkdtemp(prefix="miaokb_test_")
        self.kb_root = Path(self.tmpdir)
        self.db_path = self.kb_root / "_test_kb.db"

        # 3 个主题文件
        (self.kb_root / "test_linggui.md").write_text(LINGGUI, encoding="utf-8")
        (self.kb_root / "test_zhengjiguan.md").write_text(ZHENGJIGUAN, encoding="utf-8")
        (self.kb_root / "test_deepseek.md").write_text(DEEPSEEK, encoding="utf-8")

        # 切 indexer 全局到 fixture
        self._real_kb_root = indexer.KB_ROOT
        self._real_db_path = indexer.DB_PATH
        indexer.KB_ROOT = self.kb_root
        indexer.DB_PATH = self.db_path

        # 首次索引
        self.stats = indexer.build_index()
        # sanity：3 个文件都进了库
        self.assertEqual(
            self.stats["added"], 3,
            f"首次索引应 added=3，实际 {self.stats}",
        )

    def tearDown(self):
        """恢复全局状态 + 清理"""
        indexer.KB_ROOT = self._real_kb_root
        indexer.DB_PATH = self._real_db_path
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def _search(self, query, top_n=1):
        """跑 cmd_search 同款 SQL，返回 top-N 行（rel_path, total_hits, score）。

        复用了 cmd_search 的 query 切词 + SQL，只是去掉 print 输出。
        任何对 cmd_search SQL 的修改必须同步到这里（见 AGENTS.md 强调的一致性）。
        """
        terms = []
        for m in re.finditer(r"[\u4e00-\u9fff]+|[a-zA-Z]+", query):
            seg = m.group()
            if seg[0].isascii():
                if len(seg) >= 2:
                    terms.append(seg.lower())
            else:
                if len(seg) >= 2:
                    terms.append(seg)
                if len(seg) >= 3:
                    for i in range(len(seg) - 1):
                        terms.append(seg[i:i + 2])
                if len(seg) >= 4:
                    for i in range(len(seg) - 2):
                        terms.append(seg[i:i + 3])
                        terms.append(seg[i:i + 3])
        if not terms:
            return []
        c = sqlite3.connect(str(self.db_path))
        cur = c.cursor()
        placeholders = ",".join("?" * len(terms))
        sql = f"""
            SELECT f.rel_path, SUM(t.freq) as total_hits,
                   CAST(SUM(t.freq) AS REAL) / f.token_count * 1000 as score
            FROM terms t
            JOIN files f ON f.id = t.file_id
            WHERE t.term IN ({placeholders})
            GROUP BY f.id
            ORDER BY score DESC
            LIMIT ?
        """
        cur.execute(sql, terms + [top_n])
        return cur.fetchall()

    # ---- 黄金 query ----

    def test_search_golden_linggui(self):
        """搜「灵龟公园」top-1 是 test_linggui.md"""
        rows = self._search("灵龟公园")
        self.assertGreater(len(rows), 0, "搜「灵龟公园」应至少 1 个命中")
        self.assertIn(
            "test_linggui.md", rows[0][0],
            f"top-1 应是 test_linggui.md，实际 {rows[0][0]}",
        )

    def test_search_golden_zhengjiguan(self):
        """搜「政绩观 学习教育」top-1 是 test_zhengjiguan.md"""
        rows = self._search("政绩观 学习教育")
        self.assertGreater(len(rows), 0, "搜「政绩观 学习教育」应至少 1 个命中")
        self.assertIn(
            "test_zhengjiguan.md", rows[0][0],
            f"top-1 应是 test_zhengjiguan.md，实际 {rows[0][0]}",
        )

    def test_search_golden_deepseek(self):
        """搜「deepseek」top-1 是 test_deepseek.md"""
        rows = self._search("deepseek")
        self.assertGreater(len(rows), 0, "搜「deepseek」应至少 1 个命中")
        self.assertIn(
            "test_deepseek.md", rows[0][0],
            f"top-1 应是 test_deepseek.md，实际 {rows[0][0]}",
        )

    def test_search_no_match_returns_empty(self):
        """无关 query 返空，不抛异常"""
        rows = self._search("xxxnotexistkeywordxxx")
        self.assertEqual(rows, [])

    # ---- v0.2.1 增量索引回归 ----

    def test_incremental_preserves_search(self):
        """改 fixture 内容后跑增量索引，黄金 query 排序不退化"""
        # 1) baseline：首次索引后搜「灵龟公园」top-1
        baseline = self._search("灵龟公园")
        self.assertGreater(len(baseline), 0)
        self.assertIn("test_linggui.md", baseline[0][0])

        # 2) 修改 test_linggui.md：append 一段新内容（模拟正常编辑）
        path = self.kb_root / "test_linggui.md"
        with path.open("a", encoding="utf-8") as f:
            f.write(
                "\n\n# 增补章节\n\n"
                "夜景灯光说明：灵龟公园夜景效果显著，夜跑人数翻倍。\n"
            )

        # 3) 再跑 build_index，这次走增量分支（内容真变了）
        stats = indexer.build_index()
        self.assertEqual(
            stats["modified"], 1,
            f"应有 1 个文件 modified，实际 {stats}",
        )
        self.assertFalse(
            stats["is_first_run"],
 "增量后不应再标 first_run",
        )

        # 4) 再搜「灵龟公园」top-1 还是 test_linggui.md
        after = self._search("灵龟公园")
        self.assertGreater(len(after), 0)
        self.assertIn(
            "test_linggui.md", after[0][0],
            f"增量索引后 top-1 退化，before={baseline[0]} after={after[0]}",
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

