# -*- coding: utf-8 -*-
"""
K10 側: Vivobook の Becky ファイルサーバーから .bmf/.eml を Pull して既存受信サーバーへ投入
Vivobook のファイルは一切変更しない (GET のみ使用)

使い方:
  python scripts/k10_becky_puller.py           # .bmf/.eml のみ取り込み
  python scripts/k10_becky_puller.py --all     # .b64(添付)も含む
  python scripts/k10_becky_puller.py --status  # 処理済み件数を表示
"""
import json
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime

VIVOBOOK_URL      = "http://100.65.182.27:8200"
# Paperless が監視する consume ディレクトリに直接書き込む
PAPERLESS_EML_DIR = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\email\becky_vivobook"
K10_B64_DIR       = r"D:\tmp\becky_attachments"          # .b64 → ローカル保存
DB_PATH          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "becky_pull_history.db")
INTER_FILE_SLEEP = 0.2   # 秒 (K10 受信サーバーへの流量制御)
CONNECT_TIMEOUT  = 600   # /list は 302,351件スキャンで時間がかかる (旧 60s → 10分)
FILE_TIMEOUT     = 30


# ────────────────────────────────────────
# DB 管理
# ────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''CREATE TABLE IF NOT EXISTS pulled_files (
        path      TEXT PRIMARY KEY,
        size      INTEGER,
        ext       TEXT,
        pulled_at TEXT
    )''')
    conn.commit()
    conn.close()

def is_pulled(path):
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute("SELECT 1 FROM pulled_files WHERE path=?", (path,)).fetchone()
    conn.close()
    return r is not None

def mark_pulled(path, size, ext):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT OR IGNORE INTO pulled_files (path, size, ext, pulled_at) VALUES (?,?,?,?)",
        (path, size, ext, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()

def show_status():
    if not os.path.exists(DB_PATH):
        print("処理済みDBなし (まだ1回も実行していません)")
        return
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT ext, COUNT(*), SUM(size) FROM pulled_files GROUP BY ext").fetchall()
    total = conn.execute("SELECT COUNT(*) FROM pulled_files").fetchone()[0]
    conn.close()
    print(f"処理済みファイル: {total}件")
    for ext, cnt, sz in rows:
        print(f"  {ext}: {cnt}件 ({sz//1024//1024:.1f} MB)")


# ────────────────────────────────────────
# Vivobook との通信
# ────────────────────────────────────────

def check_vivobook():
    url = f"{VIVOBOOK_URL}/health"
    try:
        with urllib.request.urlopen(url, timeout=10) as r:
            h = json.loads(r.read())
            if not h.get("exists"):
                print(f"[WARNING] Vivobook側でEドライブが見つかりません: {h.get('path')}")
                print("  E: ドライブを接続してから再試行してください。")
                return False
            return True
    except Exception as e:
        print(f"[ERROR] Vivobookに接続できません ({VIVOBOOK_URL}): {e}")
        print("  Vivobook で vivobook_becky_fileserver.py が起動しているか確認してください。")
        return False

def get_file_list():
    url = f"{VIVOBOOK_URL}/list"
    with urllib.request.urlopen(url, timeout=CONNECT_TIMEOUT) as r:
        return json.loads(r.read())

def download_file(rel_path):
    url = f"{VIVOBOOK_URL}/file?path={urllib.parse.quote(rel_path)}"
    with urllib.request.urlopen(url, timeout=FILE_TIMEOUT) as r:
        return r.read()


# ────────────────────────────────────────
# 取り込み処理
# ────────────────────────────────────────

def save_eml_to_paperless(data):
    # 月別サブディレクトリに保存 (PAPERLESS_CONSUMER_SUBDIRS_AS_TAGS=true でタグ付け)
    try:
        import email as email_lib
        from email.utils import parsedate_to_datetime
        msg = email_lib.message_from_bytes(data)
        dt = parsedate_to_datetime(msg.get("Date", ""))
        ym = dt.strftime("%Y-%m")
    except Exception:
        ym = datetime.now().strftime("%Y-%m")

    out_dir = os.path.join(PAPERLESS_EML_DIR, ym)
    os.makedirs(out_dir, exist_ok=True)
    fname = f"becky_{int(time.time()*1000)}_{len(data)}.eml"
    with open(os.path.join(out_dir, fname), 'wb') as f:
        f.write(data)

def save_b64_locally(rel_path, data):
    out_dir = os.path.join(K10_B64_DIR, os.path.dirname(rel_path))
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(K10_B64_DIR, rel_path.replace("/", os.sep))
    with open(out_path, 'wb') as f:
        f.write(data)

def pull_cycle(include_b64=False):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Vivobookに接続中 ({VIVOBOOK_URL})")

    if not check_vivobook():
        return

    try:
        result = get_file_list()
    except Exception as e:
        print(f"[ERROR] ファイル一覧取得失敗: {e}")
        return

    all_files = result.get("files", [])
    total = result.get("count", 0)
    print(f"[INFO] Vivobook上のファイル数: {total}")

    # 拡張子でフィルタ
    target_ext = {'.bmf', '.eml'}
    if include_b64:
        target_ext.add('.b64')

    targets = [f for f in all_files if os.path.splitext(f["path"])[1].lower() in target_ext]
    pending = [f for f in targets if not is_pulled(f["path"])]
    print(f"[INFO] 未処理: {len(pending)}件 / 対象: {len(targets)}件")

    if not pending:
        print("[INFO] 新規ファイルなし。完了。")
        return

    new_count = err_count = 0

    for i, f in enumerate(pending):
        path = f["path"]
        size = f["size"]
        ext  = os.path.splitext(path)[1].lower()

        try:
            data = download_file(path)

            if ext in ('.bmf', '.eml'):
                save_eml_to_paperless(data)
            elif ext == '.b64':
                save_b64_locally(path, data)

            mark_pulled(path, size, ext)
            new_count += 1

            if new_count % 200 == 0 or (new_count <= 10):
                print(f"  [{new_count}/{len(pending)}] {path}")

            time.sleep(INTER_FILE_SLEEP)

        except urllib.error.URLError as e:
            print(f"[ERROR] {path}: {e}")
            err_count += 1
            time.sleep(3)
        except Exception as e:
            print(f"[ERROR] {path}: {e}")
            err_count += 1

    print()
    print(f"[DONE] 送信: {new_count}件 / エラー: {err_count}件")
    print(f"  再実行すると差分のみ取り込みます (DBで重複排除)。")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--status" in args:
        show_status()
        sys.exit(0)

    include_b64 = "--all" in args

    print("=" * 60)
    print("K10 Becky Pull インジェスター")
    print(f"  Vivobook:  {VIVOBOOK_URL}")
    print(f"  Paperless保存先: {PAPERLESS_EML_DIR}")
    print(f"  処理済みDB: {DB_PATH}")
    if include_b64:
        print(f"  .b64保存先: {K10_B64_DIR}")
        print("  モード: .bmf/.eml + .b64(添付)")
    else:
        print("  モード: .bmf/.eml のみ (--all で添付も含む)")
    print("=" * 60)

    init_db()
    pull_cycle(include_b64=include_b64)
