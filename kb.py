"""kb CLI - 知识库搜索/整理/关联

用法:
    kb search <query>      关键词搜索
    kb organize [path]     扫描多版本/孤儿文件，输出整理建议
    kb relate <file>       推荐相关文章
    kb stats               索引统计
"""
from __future__ import annotations
import sys
import sqlite3
import argparse
from pathlib import Path
from collections import defaultdict, Counter

DB_PATH = Path.home() / ".miaokb" / "kb.db"
KB_ROOT = Path("/Volumes/mac mini outside/知识库")

# 根目录允许保留的「故意散落」文件,organize 规则 2 不报它们
# 加白名单时把文件名直接列进来,精确匹配(不要用 glob,够用且可预测)
ROOT_WHITELIST = {"索引.md", "项目笔记-模板.md", "README.md"}


def conn():
    if not DB_PATH.exists():
        print(f"❌ 索引不存在，先跑: python3 indexer.py")
        sys.exit(1)
    return sqlite3.connect(DB_PATH)


def cmd_search(query: str, top: int = 10):
    """TF-style 词频评分：query 拆词，每词贡献该词在文档中的归一化频率"""
    c = conn()
    cur = c.cursor()
    # 简单切词（和 indexer 保持一致：整块 + 2-gram + 3-gram 双重）
    import re
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
                    terms.append(seg[i:i+2])
            if len(seg) >= 4:
                for i in range(len(seg) - 2):
                    terms.append(seg[i:i+3])
                    terms.append(seg[i:i+3])
    if not terms:
        print("请输入有效关键词")
        return
    placeholders = ",".join("?" * len(terms))
    # 每个命中文件：sum(freq / total_terms_in_file) * 100
    sql = f"""
        SELECT f.rel_path, f.summary, f.token_count, f.mtime, SUM(t.freq) as total_hits,
               CAST(SUM(t.freq) AS REAL) / f.token_count * 1000 as score
        FROM terms t
        JOIN files f ON f.id = t.file_id
        WHERE t.term IN ({placeholders})
        GROUP BY f.id
        ORDER BY score DESC
        LIMIT ?
    """
    cur.execute(sql, terms + [top])
    rows = cur.fetchall()
    if not rows:
        print(f"没找到匹配 '{query}' 的文件")
        return
    print(f"🔍 搜索: {query}  (命中 {len(rows)} 个文件)\n")
    for i, (rel, summary, tc, mtime, hits, score) in enumerate(rows, 1):
        print(f"--- [{i}] {rel}")
        print(f"    命中: {hits}次  评分: {score:.2f}  字数: {tc}")
        print(f"    修改: {mtime[:10]}")
        if summary:
            print(f"    摘要: {summary[:120]}")
        print()


def cmd_organize(path: str = ""):
    """扫描疑似多版本/孤儿的文件"""
    c = conn()
    cur = c.cursor()
    if path:
        cur.execute("SELECT * FROM files WHERE rel_path LIKE ?", (path + "%",))
    else:
        cur.execute("SELECT * FROM files")
    files = cur.fetchall()
    if not files:
        print("没文件")
        return

    # 规则 1: 同目录文件名包含「（第N稿）」「修改草稿」「_新」等关键词
    version_kw = ["草稿", "初稿", "定稿", "修改", "新版", "新)", "(新)", "新."]
    by_dir = defaultdict(list)
    for f in files:
        rel = f[1]
        by_dir[Path(rel).parent].append(f)

    print("📋 整理建议\n")

    multi_version = []
    for d, flist in by_dir.items():
        if len(flist) < 2:
            continue
        # 检查是否有版本关键字
        versioned = [f for f in flist if any(kw in f[1] for kw in version_kw)]
        if versioned and len(flist) >= 2:
            multi_version.append((d, flist))

    if multi_version:
        print(f"【多版本文件】{len(multi_version)} 个目录下发现疑似多版本：\n")
        for d, flist in multi_version:
            print(f"📁 {d}/")
            for f in flist:
                rel = f[1]
                size_kb = f[3] / 1024
                print(f"   - {Path(rel).name}  ({size_kb:.1f}KB, {f[5][:10]})")
            print()
    else:
        print("【多版本文件】无明显多版本\n")

    # 规则 2: 根目录散落文件(不分类)。白名单里的文件是故意保留的,不报。
    cur.execute("SELECT rel_path, size, mtime FROM files WHERE rel_path NOT LIKE '%/%'")
    root_files = cur.fetchall()
    root_files = [(rel, size, mtime) for rel, size, mtime in root_files
                  if Path(rel).name not in ROOT_WHITELIST]
    if root_files:
        print(f"【根目录散落】{len(root_files)} 个文件未归类：\n")
        for rel, size, mtime in root_files:
            print(f"   📄 {rel}  ({size/1024:.1f}KB, {mtime[:10]})")
        print()

    # 规则 3: 临时文档目录
    cur.execute("SELECT rel_path, size, mtime FROM files WHERE rel_path LIKE '临时文档/%'")
    temp_files = cur.fetchall()
    if temp_files:
        print(f"【临时文档目录】{len(temp_files)} 个文件，建议审视是否归位：\n")
        for rel, size, mtime in temp_files:
            print(f"   📄 {rel}  ({size/1024:.1f}KB, {mtime[:10]})")
        print()

    # 规则 4: 内容高度相似（同 hash）
    cur.execute("""
        SELECT content_hash, rel_path FROM files
        WHERE content_hash IN (SELECT content_hash FROM files GROUP BY content_hash HAVING COUNT(*) > 1)
        ORDER BY content_hash
    """)
    dup_rows = cur.fetchall()
    if dup_rows:
        print(f"【完全重复】{len(dup_rows)} 个文件内容完全相同：\n")
        seen = set()
        for h, rel in dup_rows:
            if h in seen:
                continue
            seen.add(h)
            same = [r for hh, r in dup_rows if hh == h]
            print(f"   🔁 相同内容:")
            for r in same:
                print(f"      - {r}")
            print()


def cmd_relate(file: str, top: int = 5):
    """推荐相关文章：基于关键词共现"""
    c = conn()
    cur = c.cursor()
    # 找文件
    cur.execute("SELECT id, rel_path, summary FROM files WHERE rel_path LIKE ?", (f"%{file}%",))
    matches = cur.fetchall()
    if not matches:
        print(f"没找到文件: {file}")
        print("提示：可以用部分文件名搜索")
        return
    if len(matches) > 1:
        print(f"匹配多个文件，使用第一个: {matches[0][1]}\n")
    fid, rel, summary = matches[0]
    print(f"📎 关联推荐：{rel}\n")
    if summary:
        print(f"摘要: {summary[:150]}\n")

    # 拿这个文件的高频词，去其他文件查共现
    cur.execute("SELECT term, freq FROM terms WHERE file_id = ? ORDER BY freq DESC LIMIT 20", (fid,))
    my_terms = cur.fetchall()
    if not my_terms:
        print("该文件没有可关联的关键词")
        return

    # 每个候选文件计算与该文件的共现词数
    term_set = {t for t, _ in my_terms}
    placeholders = ",".join("?" * len(term_set))
    cur.execute(f"""
        SELECT f.rel_path, COUNT(DISTINCT t.term) as common, SUM(t.freq) as total
        FROM terms t
        JOIN files f ON f.id = t.file_id
        WHERE t.term IN ({placeholders}) AND f.id != ?
        GROUP BY f.id
        ORDER BY common DESC, total DESC
        LIMIT ?
    """, list(term_set) + [fid, top])
    rows = cur.fetchall()

    if not rows:
        print("没找到相关文章")
        return
    for i, (r, common, total) in enumerate(rows, 1):
        print(f"   [{i}] {r}")
        print(f"       共现词: {common} 个, 总频次: {total}")
        print()


def cmd_stats():
    c = conn()
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM files")
    n_files = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT term) FROM terms")
    n_terms = cur.fetchone()[0]
    cur.execute("SELECT SUM(token_count) FROM files")
    total_tokens = cur.fetchone()[0] or 0
    cur.execute("SELECT term, SUM(freq) as total FROM terms GROUP BY term ORDER BY total DESC LIMIT 10")
    top_terms = cur.fetchall()
    print("📊 索引统计\n")
    print(f"  文件数: {n_files}")
    print(f"  词条数: {n_terms}")
    print(f"  词频总数: {total_tokens:,}")
    print(f"\n  高频词 TOP 10:")
    for term, total in top_terms:
        print(f"     {term:15s}  {total}")


def main():
    p = argparse.ArgumentParser(prog="kb", description="本地知识库 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="关键词搜索")
    s.add_argument("query")
    s.add_argument("--top", type=int, default=10)

    o = sub.add_parser("organize", help="扫描整理建议")
    o.add_argument("path", nargs="?", default="")

    r = sub.add_parser("relate", help="推荐相关文章")
    r.add_argument("file")
    r.add_argument("--top", type=int, default=5)

    sub.add_parser("stats", help="索引统计")

    args = p.parse_args()
    if args.cmd == "search":
        cmd_search(args.query, args.top)
    elif args.cmd == "organize":
        cmd_organize(args.path)
    elif args.cmd == "relate":
        cmd_relate(args.file, args.top)
    elif args.cmd == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
