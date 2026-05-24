#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
legal_rag_indexer.py

Administrative & Legal RAG (inspired by Digital Agency "Gennai" design philosophy).
Indexes regulatory frameworks, IATF16949, ISO9001, e-Gov administrative articles,
and quality standards into a high-performance SQLite FTS5 search index.
This runs completely locally, offline, and secure (no cloud data leaks).

Usage:
  python data/workspace/apps/legal_rag/legal_rag_indexer.py --init
  python data/workspace/apps/legal_rag/legal_rag_indexer.py --search "IATF16949 購買管理"
"""

from __future__ import annotations
import sys

# P023: Windows cp932 Encoding protection standard
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import os
import sqlite3
import argparse
from pathlib import Path
from datetime import datetime

WORKSPACE = Path(__file__).resolve().parents[2] # Points to data/workspace
DB_PATH = WORKSPACE / "apps" / "legal_rag" / "legal_rag.db"

# Sample Administrative & Quality Auditing Data presets
LEGAL_PRESETS = [
    {
        "title": "IATF 16949:2016 基準要件 - 8.4.1.1 一般購買プロセス",
        "category": "IATF16949",
        "source": "IATF16949 標準規格書",
        "content": (
            "組織は、外部から提供されるプロセス、製品、及びサービスが、顧客要求事項並びに適用される法律及び規制上の要求事項に適合していることを確実にしなければならない。\n"
            "これには、外部供給者の選定プロセス、パフォーマンス評価、及び品質マネジメントシステム（QMS）の開発監視が含まれる。\n"
            "特に自動車産業特有の品質基準であるため、供給者のQMSとして最低限 ISO 9001 認証、そして段階的な IATF 16949 への準拠が求められる。"
        )
    },
    {
        "title": "ISO 9001:2015 基準要件 - 8.4.2 外部から提供されるプロセス、製品及びサービスの管理の方式及び程度",
        "category": "ISO9001",
        "source": "ISO9001 標準規格書",
        "content": (
            "組織は、外部から提供されるプロセス、製品及びサービスが、顧客に一貫して適合した製品及びサービスを引き渡す組織の能力に悪影響を及ぼさないことを確実にしなければならない。\n"
            "管理の方式及び程度には、外部供給者に対する評価、検証活動の確立、及び供給者に対する情報伝達の正確性が含まれる。"
        )
    },
    {
        "title": "デジタル庁「行政手続きのデジタル化・最適化ガイドライン」 - 交付金・補助金システムの標準設計",
        "category": "デジタル庁ガイドライン",
        "source": "デジタル庁オープンデータ",
        "content": (
            "行政手続きのデジタル化においては、ユーザー中心設計（UCD）に基づき、申請者の二重入力を防ぐためのRAG（Retrieval-Augmented Generation）および共通用語データベース（Glossary）の活用を推奨する。\n"
            "特にjGrants等の補助金電子申請システムにおいては、申請データに含まれる専門用語や申請コードを、共通知識DBと自動照合することで審査工程を50%以上削減する。"
        )
    },
    {
        "title": "品質保証監査マニュアル - 製品出荷成績書の管理・保管要件",
        "category": "社内規定",
        "source": "品質保証部標準マニュアル",
        "content": (
            "得意先へ送付する「出荷検査成績書（出荷成績書）」は、製品のトレーサビリティを担保するため、最低10年間電子保管しなければならない。\n"
            "得意先（例：メクテック株式会社など）に送付する成績書メールは、送信された時点で監査証跡として保存され、自動的に受領確認ログが生成される必要がある。\n"
            "メールによる送付完了をもって一連の出荷トランザクションは完結し、不要な警告や例外通知（テレグラムなど）は抑制される。"
        )
    }
]

def init_db():
    """Initializes the legal RAG database and FTS5 search indexing tables."""
    print(f"[LegalRAG] Initializing database at: {DB_PATH}")
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    con = sqlite3.connect(DB_PATH)
    try:
        # Create standard metadata table
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS legal_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                category TEXT NOT NULL,
                source TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        
        # Create FTS5 search index table for high speed full-text search
        con.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS legal_fts USING fts5(
                title,
                category,
                content,
                content='legal_documents',
                content_rowid='id'
            )
            """
        )
        
        # Insert presets if empty
        count = con.execute("SELECT COUNT(*) FROM legal_documents").fetchone()[0]
        if count == 0:
            print("[LegalRAG] Seeding default administrative & auditing presets...")
            now = datetime.now().isoformat()
            for item in LEGAL_PRESETS:
                cursor = con.cursor()
                cursor.execute(
                    """
                    INSERT INTO legal_documents (title, category, source, content, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (item["title"], item["category"], item["source"], item["content"], now)
                )
                rowid = cursor.lastrowid
                
                # Update FTS index
                con.execute(
                    """
                    INSERT INTO legal_fts (rowid, title, category, content)
                    VALUES (?, ?, ?, ?)
                    """,
                    (rowid, item["title"], item["category"], item["content"])
                )
            con.commit()
            print(f"[LegalRAG] Successfully seeded {len(LEGAL_PRESETS)} preset documents.")
        else:
            print(f"[LegalRAG] Database already exists with {count} documents.")
            
    except Exception as e:
        print(f"[LegalRAG] Error initializing database: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        con.close()

def search_documents(query: str, limit: int = 5) -> list[dict]:
    """Performs full-text search against administrative and legal databases."""
    if not DB_PATH.exists():
        print("[LegalRAG] Database not initialized. Please run with --init first.")
        return []
        
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        # Match using SQLite FTS5 for maximum speed
        rows = con.execute(
            """
            SELECT d.title, d.category, d.source, d.content, bm25(legal_fts) AS score
            FROM legal_fts
            JOIN legal_documents d ON d.id = legal_fts.rowid
            WHERE legal_fts MATCH ?
            ORDER BY score
            LIMIT ?
            """,
            (query, limit)
        ).fetchall()
        
        # Fallback to standard LIKE if FTS yields zero matches
        if not rows:
            needle = f"%{query}%"
            rows = con.execute(
                """
                SELECT title, category, source, content, 0.0 AS score
                FROM legal_documents
                WHERE title LIKE ? OR category LIKE ? OR content LIKE ?
                LIMIT ?
                """,
                (needle, needle, needle, limit)
            ).fetchall()
            
        results = []
        for r in rows:
            results.append({
                "title": r["title"],
                "category": r["category"],
                "source": r["source"],
                "content": r["content"],
                "score": r["score"]
            })
        return results
    except Exception as e:
        print(f"[LegalRAG] Error searching documents: {e}", file=sys.stderr)
        return []
    finally:
        con.close()

def main():
    parser = argparse.ArgumentParser(description="Clawstack Gennai Administrative & Legal RAG Engine")
    parser.add_argument("--init", action="store_true", help="Initialize and seed standard RAG database")
    parser.add_argument("--search", type=str, help="Search legal standard databases")
    args = parser.parse_args()
    
    if args.init:
        init_db()
        return
        
    if args.search:
        print(f"Searching Legal RAG for: '{args.search}'")
        res = search_documents(args.search)
        print("-" * 60)
        for idx, item in enumerate(res, start=1):
            print(f"[{idx}] Title: {item['title']} (Score: {item['score']})")
            print(f"    Category: {item['category']} | Source: {item['source']}")
            print(f"    Content: {item['content'][:150]}...")
            print("-" * 60)
        return
        
    # Default behavior: run auto init to protect seamless execution
    if not DB_PATH.exists():
        init_db()

if __name__ == "__main__":
    main()
