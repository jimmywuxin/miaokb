"""tokenize 切词逻辑回归测试。

indexer 和 kb.py 都内联了同一套切词逻辑（见 AGENTS.md：query 和 indexer 必须完全一致）。
本测试只覆盖 indexer.tokenize；kb.py 端的 query 切词有任何变更必须同步、并补一条对应 case。

跑法：
    cd 项目根目录
    python3 -m unittest tests.test_tokenize -v
"""
import sys
import unittest
from pathlib import Path

# tests/ 在子目录里,把项目根加进 sys.path 让 from indexer import tokenize 能找到
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from indexer import tokenize  # noqa: E402


class TestTokenize(unittest.TestCase):
    """切词逻辑回归 - 防 silent bug。

    关键不变量：
      1. 中文 ≥2 字整块保留
      2. 中文 ≥3 字拆出所有 2-gram（相邻 2 字组合）
      3. 中文 ≥4 字额外拆 3-gram，每个 3-gram 加权出现 2 次（提升相对权重）
      4. 英文 ≥2 字保留并小写化，1 字过滤
      5. Markdown 标记字符 / URL 整段被过滤，不进 tokens
    """

    # ---- 中文 ----

    def test_chinese_block_kept(self):
        """中文 ≥2 字整块保留"""
        self.assertIn("灵龟公园", tokenize("灵龟公园"))

    def test_chinese_bigrams_extracted(self):
        """中文 ≥3 字拆出所有相邻 2-gram"""
        tokens = tokenize("灵龟公园")
        for bg in ["灵龟", "龟公", "公园"]:
            self.assertIn(bg, tokens, f"缺 2-gram: {bg}")

    def test_chinese_trigrams_double_weighted(self):
        """中文 ≥4 字 3-gram 双重加权（出现 2 次）"""
        tokens = tokenize("灵龟公园")
        # 4 字产 2 个 3-gram:「灵龟公」「龟公园」,每个出现 2 次
        self.assertEqual(tokens.count("灵龟公"), 2,
                         "3-gram「灵龟公」应双重加权")
        self.assertEqual(tokens.count("龟公园"), 2,
                         "3-gram「龟公园」应双重加权")

    def test_three_char_no_trigram(self):
        """3 字中文不应触发 3-gram(只产整块 + 2-gram,不双重加权)"""
        tokens = tokenize("龟公园")
        # len < 4 不走 3-gram 分支，所以「龟公园」整块只出现 1 次
        self.assertEqual(tokens.count("龟公园"), 1,
                         "3 字中文不应双重加权")
        self.assertIn("龟公", tokens)
        self.assertIn("公园", tokens)

    def test_single_chinese_filtered(self):
        """1 字中文不进 tokens"""
        tokens = tokenize("党")
        self.assertNotIn("党", tokens)

    # ---- 英文 ----

    def test_english_lower_and_kept(self):
        """英文 ≥2 字保留并小写化"""
        self.assertIn("deepseek", tokenize("DeepSeek 配置"))
        # 大写形式不应出现
        self.assertNotIn("DeepSeek", tokenize("DeepSeek 配置"))

    def test_single_english_filtered(self):
        """1 字英文不进 tokens"""
        tokens = tokenize("a I 党")
        self.assertNotIn("a", tokens)
        self.assertNotIn("i", tokens)
        # 「党」也是 1 字中文,同样不进
        self.assertNotIn("党", tokens)

    # ---- 中英混合 ----

    def test_mixed_chinese_english(self):
        """中英按词切分,各自走对应分支"""
        tokens = tokenize("政绩观 学习教育 deepseek")
        # 3 字中文「政绩观」整块保留
        self.assertIn("政绩观", tokens)
        # 4 字中文「学习教育」应有 3-gram 双重加权
        self.assertIn("学习教育", tokens)
        self.assertEqual(tokens.count("学习教"), 2)
        self.assertEqual(tokens.count("习教育"), 2)
        # 英文 8 字,小写化保留 1 次
        self.assertEqual(tokens.count("deepseek"), 1)

    # ---- 标记 / URL 过滤 ----

    def test_markdown_marks_removed(self):
        """Markdown 标记字符 # * ` 等不进 tokens"""
        tokens = tokenize("# 标题 **加粗** 内容")
        for mark in ["#", "*", "`"]:
            self.assertNotIn(mark, tokens)
        # 中文内容正常保留
        self.assertIn("标题", tokens)
        self.assertIn("加粗", tokens)
        self.assertIn("内容", tokens)

    def test_url_filtered_entirely(self):
        """整段 URL 被过滤,URL 内的 example / com / https 都不进"""
        tokens = tokenize(
            "看到 https://example.com 就去 学习deepseek 配置"
        )
        # URL 整段被 re.sub 替换成空格,所以 example/com/https 不应在 tokens
        self.assertNotIn("example", tokens)
        self.assertNotIn("com", tokens)
        self.assertNotIn("https", tokens)
        # 非 URL 内容正常保留
        self.assertIn("学习", tokens)
        self.assertIn("deepseek", tokens)
        self.assertIn("配置", tokens)

    def test_brackets_and_pipes_filtered(self):
        """[ ] ( ) | < > 等字符被替换,标签内容里单词仍进 tokens"""
        # 字符 < > [ ] 被 re.sub 替换成空格,「div」「内容」仍进
        tokens = tokenize("<div>内容</div>")
        for ch in ["<", ">", "[", "]"]:
            self.assertNotIn(ch, tokens)
        self.assertIn("div", tokens)
        self.assertIn("内容", tokens)


if __name__ == "__main__":
    unittest.main(verbosity=2)

