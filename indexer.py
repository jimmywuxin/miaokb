"""kb 索引器：扫知识库 → 抽内容 → 建索引（SQLite + 简单倒排）

不做语义向量（demo 阶段先验证「整 + 联」的实际价值，词袋 + 词频就够看出效果）。
"""
from __future__ import annotations
import os
import re
import json
import sqlite3
import hashlib
from pathlib import Path
from datetime import datetime
from collections import Counter

# 知识库根目录
KB_ROOT = Path("/Volumes/mac mini outside/知识库")
INDEX_DIR = Path.home() / ".kb_demo"
DB_PATH = INDEX_DIR / "kb.db"

# 支持的文本文件类型
TEXT_EXT = {".md", ".txt"}
# 跳过这些
SKIP_DIRS = {".DS_Store", "__pycache__"}


def extract_text(path: Path) -> str:
    """读取文本文件内容，docx/pdf 暂不支持（demo 阶段只跑 md）"""
    try:
        if path.suffix.lower() in TEXT_EXT:
            return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return ""
    return ""


def tokenize(text: str) -> list[str]:
    """中文：保留整块 + 2-gram；英文：单词"""
    # 去掉 markdown 标记、html 标签
    text = re.sub(r"[#*`>_\-\[\]()<>|]", " ", text)
    text = re.sub(r"https?://\S+", " ", text)
    tokens = []
    for m in re.finditer(r"[\u4e00-\u9fff]+|[a-zA-Z]+", text):
        seg = m.group()
        if seg[0].isascii():
            if len(seg) >= 2:
                tokens.append(seg.lower())
        else:
            # 中文：整块 + 2-gram 必加；3-gram 选加（命中「灵龟公园」这种短语）
            if len(seg) >= 2:
                tokens.append(seg)
            if len(seg) >= 3:
                for i in range(len(seg) - 1):
                    tokens.append(seg[i:i+2])
            if len(seg) >= 4:
                # 3-gram 加权（出现次数 = 2，提升相对权重）
                for i in range(len(seg) - 2):
                    tokens.append(seg[i:i+3])
                    tokens.append(seg[i:i+3])  # 双重权重
    return tokens


def file_hash(content: str) -> str:
    return hashlib.md5(content.encode("utf-8")).hexdigest()[:12]


def build_index() -> dict:
    """扫一遍知识库，写入 SQLite"""
    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        DROP TABLE IF EXISTS files;
        DROP TABLE IF EXISTS terms;
        CREATE TABLE files (
            id INTEGER PRIMARY KEY,
            path TEXT UNIQUE,
            rel_path TEXT,
            size INTEGER,
            mtime TEXT,
            content_hash TEXT,
            token_count INTEGER,
            summary TEXT
        );
        CREATE TABLE terms (
            term TEXT,
            file_id INTEGER,
            freq INTEGER,
            PRIMARY KEY (term, file_id)
        );
        CREATE INDEX idx_terms_term ON terms(term);
    """)
    cur = conn.cursor()

    file_count = 0
    skipped_count = 0
    for path in KB_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if any(part.startswith(".") for part in path.parts):
            continue
        if path.suffix.lower() not in TEXT_EXT:
            skipped_count += 1
            continue

        content = extract_text(path)
        if not content.strip():
            continue

        # 内容 + 文件名一起索引（文件名常常是关键线索）
        full_text = path.name + "\n" + content
        tokens = tokenize(full_text)
        if not tokens:
            continue

        # 文件级摘要：取前 200 字符
        summary = re.sub(r"\s+", " ", content)[:200].strip()

        cur.execute(
            "INSERT INTO files (path, rel_path, size, mtime, content_hash, token_count, summary) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(path),
                str(path.relative_to(KB_ROOT)),
                path.stat().st_size,
                datetime.fromtimestamp(path.stat().st_mtime).isoformat(),
                file_hash(content),
                len(tokens),
                summary,
            ),
        )
        file_id = cur.lastrowid

        # 词频
        freq = Counter(tokens)
        # 过滤停用词 + 太低频（仅出现 1 次的扔掉省空间）
        STOP = {
            "的", "了", "和", "是", "在", "我", "有", "不", "这", "也", "就", "都",
            "而", "及", "或", "与", "等", "中", "为", "对", "可", "上", "下", "一个",
            "the", "a", "an", "of", "to", "in", "is", "it", "and", "or", "for", "on",
        }
        for term, f in freq.items():
            if term in STOP or f < 2 or len(term) < 2:
                continue
            cur.execute(
                "INSERT INTO terms (term, file_id, freq) VALUES (?, ?, ?)",
                (term, file_id, f),
            )

        file_count += 1

    conn.commit()
    conn.close()
    return {"files": file_count, "skipped": skipped_count, "db": str(DB_PATH)}


if __name__ == "__main__":
    import sys
    print("开始索引…")
    result = build_index()
    print(f"✅ 索引完成")
    print(f"   文本文件: {result['files']}")
    print(f"   跳过(非 md/txt): {result['skipped']}")
    print(f"   索引位置: {result['db']}")
