# -*- coding: utf-8 -*-
"""収集資料(web_material_index 30万件)に日本語で全文検索できる索引を作る。

2026-08-08 導入。背景(実測):
  universal_growth.db の web_material_fts は既定トークナイザのFTS5で、
  空白区切りのため日本語が1トークンも切り出せない。
    injection -> 47,308件 / progressive -> 32,863件 ヒットするのに
    「順送」「充填」 -> 0件。
  英語資料は引けるのに日本語のノウハウが引けない状態だった。

設計上の判断:
  - 本体DB(38GB)は収集デーモンが常時書き込み中。ロック競合と巻き戻し不能な
    事故を避けるため、**別ファイル**に索引を作り本体はread-onlyでしか開かない。
    不要になればこのファイルを消すだけで完全に元に戻る。
  - tokenize='trigram' は3文字以上でしかマッチしない(実測: 順送=2文字は0件、
    順送金型=4文字はヒット)。2文字語は検索側でLIKEに退避する。
  - acquisition_id を rowid にして本体へ突き合わせる。
  - 増分実行: 記録済みの最大IDより後だけ追加するので何度でも流せる。

usage:
  python scripts/build_ja_fts_index.py            # 増分構築
  python scripts/build_ja_fts_index.py --rebuild  # 作り直し
  python scripts/build_ja_fts_index.py --stats
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
MAIN_DB = REPO / "data" / "workspace" / "universal_growth.db"
INDEX_DB = REPO / "data" / "workspace" / "universal_growth_fts_ja.db"
BATCH = 5000


def open_main() -> sqlite3.Connection:
    """本体DBは必ず読み取り専用で開く(誤って書かないため)。"""
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    return con


def open_index() -> sqlite3.Connection:
    con = sqlite3.connect(INDEX_DB, timeout=60)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def ensure_schema(idx: sqlite3.Connection) -> None:
    idx.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS material_ja
                   USING fts5(title, domain_tags, source, tokenize='trigram')""")
    # growth_records の know_how は日本語の実ノウハウ(最大1万字超のIATF解説など)。
    # 収集資料(英語メタデータ中心)より実務価値が高いので別テーブルで索引する。
    idx.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS knowhow_ja
                   USING fts5(challenge, know_how, domain, source,
                              tokenize='trigram')""")
    idx.execute("""CREATE TABLE IF NOT EXISTS build_state
                   (key TEXT PRIMARY KEY, value TEXT)""")
    idx.commit()


def build_knowhow(main_con: sqlite3.Connection, idx: sqlite3.Connection,
                  min_chars: int) -> int:
    """growth_records.know_how を索引する。中身の薄いスタブは入れない。"""
    last_id = int(get_state(idx, "last_growth_id", "0"))
    t0 = time.time()
    added = 0
    while True:
        rows = main_con.execute(
            "SELECT id, challenge, know_how, domain, source FROM growth_records "
            "WHERE id > ? AND know_how IS NOT NULL AND LENGTH(know_how) >= ? "
            "ORDER BY id LIMIT ?", (last_id, min_chars, BATCH)).fetchall()
        if not rows:
            break
        idx.executemany(
            "INSERT INTO knowhow_ja(rowid, challenge, know_how, domain, source) "
            "VALUES(?,?,?,?,?)",
            [(r["id"], r["challenge"] or "", r["know_how"] or "",
              r["domain"] or "", r["source"] or "") for r in rows])
        last_id = rows[-1]["id"]
        added += len(rows)
        set_state(idx, "last_growth_id", last_id)
        idx.commit()
        print(f"\r  know_how {added} 件追加 (最終ID {last_id})", end="", flush=True)
    if added:
        print(f"\n  know_how 索引: {added} 件 / {time.time()-t0:.0f} 秒")
    return added


def get_state(idx: sqlite3.Connection, key: str, default: str = "0") -> str:
    r = idx.execute("SELECT value FROM build_state WHERE key=?", (key,)).fetchone()
    return r[0] if r else default


def set_state(idx: sqlite3.Connection, key: str, value: str) -> None:
    idx.execute("INSERT INTO build_state(key,value) VALUES(?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key, str(value)))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rebuild", action="store_true", help="索引を作り直す")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="追加件数の上限(0=無制限)")
    ap.add_argument("--min-knowhow-chars", type=int, default=200,
                    help="know_howがこの文字数未満のスタブは索引しない")
    a = ap.parse_args()

    if not MAIN_DB.exists():
        print(f"本体DBがありません: {MAIN_DB}")
        return 3

    if a.rebuild and INDEX_DB.exists():
        INDEX_DB.unlink()
        print(f"既存索引を削除しました: {INDEX_DB}")

    idx = open_index()
    ensure_schema(idx)

    if a.stats:
        n = idx.execute("SELECT COUNT(*) FROM material_ja").fetchone()[0]
        nk = idx.execute("SELECT COUNT(*) FROM knowhow_ja").fetchone()[0]
        print(f"know_how索引: {nk} 件")
        last = get_state(idx, "last_acquisition_id")
        size = INDEX_DB.stat().st_size / 1024 ** 2 if INDEX_DB.exists() else 0
        print(f"索引: {n} 件 / 最終ID {last} / {size:.0f} MB  ({INDEX_DB})")
        return 0

    main_con = open_main()
    build_knowhow(main_con, idx, a.min_knowhow_chars)

    total = main_con.execute("SELECT COUNT(*) FROM web_material_index").fetchone()[0]
    last_id = int(get_state(idx, "last_acquisition_id", "0"))
    print(f"本体: {total} 件 / 索引済み最終ID: {last_id}")

    t0 = time.time()
    added = 0
    while True:
        rows = main_con.execute(
            "SELECT acquisition_id, title, domain_tags, source "
            "FROM web_material_index WHERE acquisition_id > ? "
            "ORDER BY acquisition_id LIMIT ?", (last_id, BATCH)).fetchall()
        if not rows:
            break
        idx.executemany(
            "INSERT INTO material_ja(rowid, title, domain_tags, source) VALUES(?,?,?,?)",
            [(r["acquisition_id"], r["title"] or "", r["domain_tags"] or "",
              r["source"] or "") for r in rows])
        last_id = rows[-1]["acquisition_id"]
        added += len(rows)
        set_state(idx, "last_acquisition_id", last_id)
        idx.commit()
        el = time.time() - t0
        print(f"\r  {added} 件追加 (最終ID {last_id}, {added/el*60:.0f} 件/分)",
              end="", flush=True)
        if a.limit and added >= a.limit:
            break

    idx.commit()
    n = idx.execute("SELECT COUNT(*) FROM material_ja").fetchone()[0]
    size = INDEX_DB.stat().st_size / 1024 ** 2
    print(f"\n完了: {added} 件追加 / 索引合計 {n} 件 / {size:.0f} MB / "
          f"{time.time()-t0:.0f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
