# -*- coding: utf-8 -*-
"""蓄積知識をMarkdownとして書き出す(人間が読め、graphify/RAGが取り込める形にする)。

2026-08-08 導入。背景(実測):
  universal_growth.db(38GB) には growth_records 70,509件と収集PDF 98,107件
  /310.20GB があるが、DBの中でしか存在せず、人間もgraphifyもLightRAGも読めない。
  一方で全部をMD化するのは非現実的(テキストだけで数十GB)。
  価値密度の高い順に materialize する:
    - growth_records の know_how 200字以上 = 4,582件(1000字以上は508件)
    - PDF本文のうち北極星(プレス/金型/成形/公差)関連

文字コード規約(グローバルルール 2026-08-08):
  - 書き込みは必ず encoding="utf-8" を明示する
  - 書き込み後に読み戻し、U+FFFD と化け記号(縺/繧/繝)が無いことを検証する
  - 検証に失敗したファイルは削除し、件数を報告する(壊れたMDを残さない)

usage:
  python scripts/export_knowledge_md.py --what knowhow
  python scripts/export_knowledge_md.py --what pdf --limit 500
  python scripts/export_knowledge_md.py --what knowhow --dry-run
"""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
MAIN_DB = REPO / "data" / "workspace" / "universal_growth.db"
INDEX_DB = REPO / "data" / "workspace" / "universal_growth_fts_ja.db"
OUT_ROOT = REPO / "data" / "workspace" / "knowledge_export"
MOJIBAKE_MARKS = "縺繧繝"
NORTH_STAR = re.compile(
    r"(progressive die|stamping|sheet metal|deep draw|blanking|press forming|"
    r"die design|springback|forming limit|injection mold|mold filling|weld line|"
    r"warpage|tolerance stack|プレス|金型|絞り|成形|公差|板金|打抜|順送)", re.I)


def safe_name(s: str, maxlen: int = 70) -> str:
    s = re.sub(r'[\\/:*?"<>|\r\n\t]', "_", s or "").strip()
    s = re.sub(r"_{2,}", "_", s)
    return (s[:maxlen] or "untitled").rstrip("._ ")


def write_md_verified(path: Path, text: str) -> tuple[bool, int]:
    """UTF-8で書き、読み戻して化けが無いか検証する。(成功, 化け文字数)"""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    back = path.read_text(encoding="utf-8")
    bad = back.count("\ufffd") + sum(back.count(m) for m in MOJIBAKE_MARKS)
    if bad or back != text:
        path.unlink(missing_ok=True)
        return False, bad
    return True, 0


def export_knowhow(min_chars: int, limit: int, dry: bool) -> None:
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "SELECT id, timestamp, domain, challenge, know_how, source, difficulty "
        "FROM growth_records WHERE know_how IS NOT NULL AND LENGTH(know_how) >= ? "
        "ORDER BY LENGTH(know_how) DESC", (min_chars,)).fetchall()
    if limit:
        rows = rows[:limit]
    print(f"know_how {min_chars}字以上: {len(rows)} 件")
    if dry:
        for r in rows[:10]:
            print(f"  [{r['domain']}] {str(r['challenge'])[:60]} ({len(r['know_how'])}字)")
        return

    ok = ng = 0
    t0 = time.time()
    for r in rows:
        domain = safe_name(r["domain"] or "UNKNOWN", 40)
        out = OUT_ROOT / "knowhow" / domain / f"{r['id']:06d}_{safe_name(r['challenge'])}.md"
        body = (
            f"---\n"
            f"id: {r['id']}\n"
            f"domain: {r['domain']}\n"
            f"source: {r['source']}\n"
            f"timestamp: {r['timestamp']}\n"
            f"difficulty: {r['difficulty']}\n"
            f"origin: universal_growth.db/growth_records\n"
            f"---\n\n"
            f"# {r['challenge']}\n\n"
            f"{r['know_how']}\n"
        )
        good, bad = write_md_verified(out, body)
        if good:
            ok += 1
        else:
            ng += 1
            print(f"\n  検証失敗(削除): id={r['id']} 化け={bad}")
        if (ok + ng) % 200 == 0:
            print(f"\r  {ok+ng}/{len(rows)} 件 ({(ok+ng)/(time.time()-t0)*60:.0f} 件/分)",
                  end="", flush=True)
    print(f"\n完了: {ok} 件出力 / 検証失敗 {ng} 件 -> {OUT_ROOT/'knowhow'}")


def export_pdf(limit: int, dry: bool) -> None:
    if not INDEX_DB.exists():
        print("PDF本文索引がまだありません(extract_pdf_text_index.py を先に実行)")
        return
    idx = sqlite3.connect(f"file:{INDEX_DB}?mode=ro", uri=True, timeout=60)
    idx.row_factory = sqlite3.Row
    rows = idx.execute(
        "SELECT rowid, title, body, source, path FROM pdftext_ja").fetchall()
    picked = [r for r in rows if NORTH_STAR.search((r["title"] or "") + (r["body"] or "")[:3000])]
    if limit:
        picked = picked[:limit]
    print(f"PDF本文索引 {len(rows)} 件中、北極星関連 {len(picked)} 件")
    if dry:
        for r in picked[:10]:
            print(f"  [{r['source']}] {str(r['title'])[:70]}")
        return

    ok = ng = 0
    t0 = time.time()
    for r in picked:
        out = (OUT_ROOT / "pdf" / safe_name(r["source"] or "unknown", 30) /
               f"{r['rowid']:07d}_{safe_name(r['title'])}.md")
        body = (
            f"---\n"
            f"acquisition_id: {r['rowid']}\n"
            f"source: {r['source']}\n"
            f"local_path: {r['path']}\n"
            f"origin: universal_growth.db/web_material_index + pdftotext\n"
            f"---\n\n"
            f"# {r['title']}\n\n"
            f"{r['body']}\n"
        )
        good, bad = write_md_verified(out, body)
        if good:
            ok += 1
        else:
            ng += 1
        if (ok + ng) % 100 == 0:
            print(f"\r  {ok+ng}/{len(picked)} 件 ({(ok+ng)/(time.time()-t0)*60:.0f} 件/分)",
                  end="", flush=True)
    print(f"\n完了: {ok} 件出力 / 検証失敗 {ng} 件 -> {OUT_ROOT/'pdf'}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--what", choices=["knowhow", "pdf"], required=True)
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    if a.what == "knowhow":
        export_knowhow(a.min_chars, a.limit, a.dry_run)
    else:
        export_pdf(a.limit, a.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
