# -*- coding: utf-8 -*-
"""収集済みPDF(98,107件/310GB)からテキストを抽出し、日本語で全文検索できる索引を作る。

2026-08-08 導入。背景(実測):
  web_material_index には has_local_file=1 の実ファイルが 112,770件あり、
  うちPDFが 98,107件 / 310.20 GB。ところがDBにはタイトルとURLしか無く
  (abstractすら未保存)、中身は一切検索できなかった。
  jstage 7,745件は日本語の学術文献で、北極星(プレス/金型)に直結する。

方式:
  - pdftotext -enc UTF-8 で抽出(実測 0.35〜0.67秒/PDF、文字化けゼロ)。
    失敗時のみ pypdf にフォールバックする。
  - 索引は **別ファイル**(universal_growth_fts_ja.db)の FTS5 trigram テーブル。
    本体38GBは収集デーモンが常時書き込み中のため read-only でしか開かない。
  - 中断・再開可能。処理済みは done_pdf テーブルで記録し二度と再処理しない。

文字コード規約(グローバルルール 2026-08-08):
  - 抽出は UTF-8 を明示。decode は errors='replace' で必ず成功させたうえで、
    U+FFFD と化け記号(縺/繧/繝)の混入数を数えて記録する。
  - 化け率が高い文書は skipped として索引に入れない(検索ノイズになるため)。
  - 書き込み後に読み戻して往復検証する(--verify)。

usage:
  python scripts/extract_pdf_text_index.py --pattern jstage --limit 200
  python scripts/extract_pdf_text_index.py --pattern jstage --workers 4
  python scripts/extract_pdf_text_index.py --workers 4          # 全件
  python scripts/extract_pdf_text_index.py --stats
  python scripts/extract_pdf_text_index.py --verify
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import os
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # P023

REPO = Path(r"D:\Clawdbot_Docker_20260125")
MAIN_DB = REPO / "data" / "workspace" / "universal_growth.db"
INDEX_DB = REPO / "data" / "workspace" / "universal_growth_fts_ja.db"
MAX_TEXT_CHARS = 200_000     # 1文書あたりの保存上限(索引肥大を防ぐ)
MOJIBAKE_MARKS = "縺繧繝"
MAX_BAD_RATIO = 0.02         # U+FFFD等がこの割合を超えたら索引に入れない
PDFTOTEXT_TIMEOUT = 120


def open_main() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{MAIN_DB}?mode=ro", uri=True, timeout=60)
    con.row_factory = sqlite3.Row
    return con


def open_index() -> sqlite3.Connection:
    con = sqlite3.connect(INDEX_DB, timeout=120)
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def ensure_schema(idx: sqlite3.Connection) -> None:
    idx.execute("""CREATE VIRTUAL TABLE IF NOT EXISTS pdftext_ja
                   USING fts5(title, body, source, path, tokenize='trigram')""")
    idx.execute("""CREATE TABLE IF NOT EXISTS done_pdf(
                     path TEXT PRIMARY KEY,
                     acquisition_id INTEGER,
                     chars INTEGER,
                     bad INTEGER,
                     status TEXT,
                     done_at TEXT)""")
    idx.commit()


def extract(path: str) -> tuple[str, int]:
    """(本文, 化け文字数)。UTF-8を明示して取り出す。"""
    try:
        r = subprocess.run(["pdftotext", "-enc", "UTF-8", "-q", path, "-"],
                           capture_output=True, timeout=PDFTOTEXT_TIMEOUT)
        txt = r.stdout.decode("utf-8", errors="replace")
    except Exception:
        txt = ""
    if len(txt.strip()) < 200:
        try:
            from pypdf import PdfReader
            rd = PdfReader(path)
            txt = "\n".join((pg.extract_text() or "") for pg in rd.pages[:80])
        except Exception:
            pass
    bad = txt.count("\ufffd") + sum(txt.count(m) for m in MOJIBAKE_MARKS)
    return txt[:MAX_TEXT_CHARS], bad


def work(item: tuple) -> dict:
    aid, path, title, source = item
    t0 = time.time()
    txt, bad = extract(path)
    n = len(txt.strip())
    if n < 200:
        status = "empty"
    elif bad / max(n, 1) > MAX_BAD_RATIO:
        status = "mojibake"      # 化けが多い文書は索引に入れない
    else:
        status = "ok"
    return {"aid": aid, "path": path, "title": title or "", "source": source or "",
            "text": txt if status == "ok" else "", "chars": n, "bad": bad,
            "status": status, "sec": time.time() - t0}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pattern", default=None,
                    help="local_path に含まれる文字列で絞る(例: jstage)")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--workers", type=int, default=4,
                    help="並列数。RL学習とCPUを分け合うため既定は控えめ")
    ap.add_argument("--stats", action="store_true")
    ap.add_argument("--verify", action="store_true", help="往復検証を行う")
    a = ap.parse_args()

    idx = open_index()
    ensure_schema(idx)

    if a.stats:
        n = idx.execute("SELECT COUNT(*) FROM pdftext_ja").fetchone()[0]
        print(f"PDF本文索引: {n} 件")
        for r in idx.execute("SELECT status, COUNT(*) FROM done_pdf GROUP BY 1 ORDER BY 2 DESC"):
            print(f"  {r[0]}: {r[1]}")
        size = INDEX_DB.stat().st_size / 1024 ** 2
        print(f"索引ファイル: {size:.0f} MB")
        return 0

    if a.verify:
        row = idx.execute("SELECT rowid, title, substr(body,1,300) FROM pdftext_ja "
                          "WHERE body LIKE '%成形%' LIMIT 1").fetchone()
        if not row:
            print("検証対象がまだありません")
            return 1
        body = row[2]
        bad = body.count("\ufffd") + sum(body.count(m) for m in MOJIBAKE_MARKS)
        print(f"往復検証 rowid={row[0]}")
        print(f"  タイトル: {row[1][:70]}")
        print(f"  本文先頭: {body[:120]}")
        print(f"  U+FFFD/化け記号: {bad} 件 -> {'OK' if bad == 0 else '要確認'}")
        return 0 if bad == 0 else 2

    main_con = open_main()
    done = {r[0] for r in idx.execute("SELECT path FROM done_pdf")}
    sql = ("SELECT acquisition_id, local_path, title, source FROM web_material_index "
           "WHERE has_local_file=1 AND local_path LIKE '%.pdf'")
    params: list = []
    if a.pattern:
        sql += " AND local_path LIKE ?"
        params.append(f"%{a.pattern}%")
    sql += " ORDER BY acquisition_id"
    todo = [(r["acquisition_id"], r["local_path"], r["title"], r["source"])
            for r in main_con.execute(sql, params)
            if r["local_path"] not in done and os.path.exists(r["local_path"])]
    if a.limit:
        todo = todo[:a.limit]
    print(f"対象PDF: {len(todo)} 件 (処理済み {len(done)} 件を除外) / 並列 {a.workers}")
    if not todo:
        return 0

    t0 = time.time()
    n_ok = n_skip = 0
    buf_fts: list = []
    buf_done: list = []
    with cf.ThreadPoolExecutor(max_workers=a.workers) as ex:
        for i, res in enumerate(ex.map(work, todo), 1):
            if res["status"] == "ok":
                buf_fts.append((res["aid"], res["title"], res["text"],
                                res["source"], res["path"]))
                n_ok += 1
            else:
                n_skip += 1
            buf_done.append((res["path"], res["aid"], res["chars"], res["bad"],
                             res["status"], time.strftime("%Y-%m-%dT%H:%M:%S")))
            if len(buf_done) >= 50:
                if buf_fts:
                    idx.executemany("INSERT INTO pdftext_ja(rowid,title,body,source,path) "
                                    "VALUES(?,?,?,?,?)", buf_fts)
                    buf_fts = []
                idx.executemany("INSERT OR REPLACE INTO done_pdf"
                                "(path,acquisition_id,chars,bad,status,done_at) "
                                "VALUES(?,?,?,?,?,?)", buf_done)
                buf_done = []
                idx.commit()
                el = time.time() - t0
                print(f"\r  {i}/{len(todo)} 件 (索引 {n_ok} / 除外 {n_skip}) "
                      f"{i/el*60:.0f} 件/分", end="", flush=True)
    if buf_fts:
        idx.executemany("INSERT INTO pdftext_ja(rowid,title,body,source,path) "
                        "VALUES(?,?,?,?,?)", buf_fts)
    if buf_done:
        idx.executemany("INSERT OR REPLACE INTO done_pdf"
                        "(path,acquisition_id,chars,bad,status,done_at) "
                        "VALUES(?,?,?,?,?,?)", buf_done)
    idx.commit()
    print(f"\n完了: 索引 {n_ok} 件 / 除外 {n_skip} 件 / {time.time()-t0:.0f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
