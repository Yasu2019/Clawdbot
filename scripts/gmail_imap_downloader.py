# -*- coding: utf-8 -*-
"""
gmail_imap_downloader.py
Gmail IMAP から指定日付以前のメールを .eml として consume/email/gmail/ に保存する。
添付ファイルは consume/gmail_attachments/ に展開して Paperless が自動取り込み。

前提条件:
  1. Gmail 設定 → 転送とPOP/IMAP → IMAP を有効化
  2. Googleアカウント → セキュリティ → アプリパスワードを発行
     https://myaccount.google.com/apppasswords

Usage:
  python scripts/gmail_imap_downloader.py --user y.suzuki.hk@gmail.com --app-password XXXX-XXXX-XXXX-XXXX
  python scripts/gmail_imap_downloader.py --user y.suzuki.hk@gmail.com --app-password XXXX --dry-run
  python scripts/gmail_imap_downloader.py --user y.suzuki.hk@gmail.com --app-password XXXX --before 2013-06-01
"""

import argparse
import base64
import email
import email.message
import hashlib
import imaplib
import io
import os
import pathlib
import re
import sqlite3
import sys
import time
from datetime import datetime, timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

def _load_dotenv(env_path: pathlib.Path) -> None:
    """Simple .env loader — sets os.environ without overwriting existing vars."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = val.strip()

_REPO_ROOT_ENV = pathlib.Path(__file__).resolve().parents[1]
_load_dotenv(_REPO_ROOT_ENV / ".env")

# ── パス設定 ──────────────────────────────────────────────────────────
REPO_ROOT      = pathlib.Path(__file__).resolve().parents[1]
EML_DIR        = REPO_ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "email" / "gmail"
ATTACH_DIR     = REPO_ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "gmail_attachments"
HIST_DB        = REPO_ROOT / "scripts" / "gmail_pull_history.db"
LOG_FILE       = REPO_ROOT / "data" / "workspace" / "gmail_imap_downloader.log"

# 取り込み対象の添付拡張子
WHITELIST_EXT = {
    ".pdf", ".xls", ".xlsx", ".xlsm",
    ".doc", ".docx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff",
    ".txt", ".csv", ".xml", ".html", ".zip",
}
DANGEROUS_EXT = {
    ".exe", ".com", ".js", ".vbs", ".bat", ".ps1", ".cmd",
    ".scr", ".pif", ".hta", ".jar", ".msi", ".wsf", ".lnk",
}

IMAP_HOST = "imap.gmail.com"
IMAP_PORT = 993
BATCH     = 200   # IMAP fetch chunk size


def log(msg: str) -> None:
    ts = datetime.now().strftime("%m/%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def init_db() -> sqlite3.Connection:
    HIST_DB.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(HIST_DB))
    con.execute("""
        CREATE TABLE IF NOT EXISTS pulled (
            uid      TEXT PRIMARY KEY,
            msg_id   TEXT,
            subject  TEXT,
            date_str TEXT,
            eml_path TEXT,
            saved_at TEXT
        )
    """)
    con.execute("CREATE INDEX IF NOT EXISTS idx_uid ON pulled(uid)")
    con.commit()
    return con


def is_pulled(con: sqlite3.Connection, uid: str) -> bool:
    return con.execute("SELECT 1 FROM pulled WHERE uid=?", (uid,)).fetchone() is not None


def mark_pulled(con: sqlite3.Connection, uid: str, msg_id: str,
                subject: str, date_str: str, eml_path: str) -> None:
    con.execute(
        "INSERT OR IGNORE INTO pulled(uid,msg_id,subject,date_str,eml_path,saved_at) VALUES(?,?,?,?,?,?)",
        (uid, msg_id, subject, date_str, eml_path, datetime.now(timezone.utc).isoformat())
    )
    con.commit()


def decode_hdr(value: str | None) -> str:
    if not value:
        return ""
    parts = []
    for chunk, enc in decode_header(value):
        if isinstance(chunk, bytes):
            enc = (enc or "utf-8").lower()
            aliases = {"windows-874": "cp874", "iso-8859-11": "cp874",
                       "windows-1252": "cp1252", "x-windows-iso2022jp": "iso2022_jp"}
            enc = aliases.get(enc, enc)
            try:
                parts.append(chunk.decode(enc, errors="replace"))
            except (LookupError, UnicodeDecodeError):
                parts.append(chunk.decode("latin-1", errors="replace"))
        else:
            parts.append(chunk)
    return "".join(parts)


def safe_filename(name: str, max_len: int = 120) -> str:
    keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-() ")
    cleaned = "".join(c if c in keep else "_" for c in name).strip()
    return (cleaned[:max_len] or "attachment")


def extract_attachments(msg: email.message.Message, dry_run: bool) -> int:
    saved = 0
    for part in msg.walk():
        cd = part.get("Content-Disposition", "")
        if not cd or "attachment" not in cd.lower():
            continue
        fname_raw = part.get_filename()
        if not fname_raw:
            continue
        fname = decode_hdr(fname_raw)
        ext = pathlib.Path(fname).suffix.lower()
        if ext in DANGEROUS_EXT:
            log(f"  [BLOCK] {fname}")
            continue
        if ext not in WHITELIST_EXT:
            continue
        payload = part.get_payload(decode=True)
        if not payload:
            continue
        sha8 = hashlib.sha256(payload).hexdigest()[:8]
        out_name = f"{sha8}_{safe_filename(fname)}"
        out_path = ATTACH_DIR / out_name
        if not out_path.exists() and not dry_run:
            ATTACH_DIR.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(payload)
            saved += 1
    return saved


def date_to_dir(msg: email.message.Message) -> str:
    """Return YYYY-MM string from the message Date header, fallback today."""
    try:
        dt = parsedate_to_datetime(msg.get("Date", ""))
        return dt.strftime("%Y-%m")
    except Exception:
        return datetime.now().strftime("%Y-%m")


def connect_imap(user: str, app_password: str) -> imaplib.IMAP4_SSL:
    log(f"IMAP 接続: {IMAP_HOST}:{IMAP_PORT} as {user}")
    imap = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
    imap.login(user, app_password)
    log("ログイン成功")
    return imap


_ALLMAIL_PATTERN = re.compile(rb"\\All\b")
_SUBETE_BYTES = "すべて".encode("utf-8")

def _find_allmail_folder(imap: imaplib.IMAP4_SSL) -> bytes | None:
    """LIST で All Mail フォルダのバイト列名を返す。"""
    typ, data = imap.list()
    if typ != "OK":
        return None
    for item in data:
        if not isinstance(item, bytes):
            continue
        if _ALLMAIL_PATTERN.search(item) or b"All Mail" in item or _SUBETE_BYTES in item:
            m = re.search(rb'"([^"]+)"$', item) or re.search(rb'(\S+)$', item)
            if m:
                return m.group(1)
    return None


def search_uids_before(imap: imaplib.IMAP4_SSL, before_date: str) -> list[str]:
    """
    Gmail [Gmail]/All Mail フォルダから before_date (YYYY-MM-DD) 以前の UID 一覧を取得。
    """
    # LIST でフォルダ名を動的検索
    allmail = _find_allmail_folder(imap)
    selected = None
    if allmail:
        try:
            typ, data = imap.select(allmail, readonly=True)
            if typ == "OK":
                selected = allmail.decode("utf-8", errors="replace")
                log(f"フォルダ選択: {selected} ({data[0].decode()} 件)")
        except Exception as e:
            log(f"  [WARN] フォルダ選択失敗: {e}")

    if not selected:
        # フォールバック: ASCII フォルダ名のみ試行
        for folder in (b'"[Gmail]/All Mail"', b'INBOX'):
            try:
                typ, data = imap.select(folder, readonly=True)
                if typ == "OK":
                    selected = folder.decode()
                    log(f"フォルダ選択 (fallback): {selected} ({data[0].decode()} 件)")
                    break
            except Exception:
                continue

    if not selected:
        raise RuntimeError("All Mail フォルダが見つかりません。Gmail IMAP 設定を確認してください。")

    # BEFORE は D-Mon-YYYY 形式 (IMAP standard)
    dt = datetime.strptime(before_date, "%Y-%m-%d")
    imap_date = dt.strftime("%d-%b-%Y")  # e.g. "01-Jun-2013"
    log(f"検索条件: BEFORE {imap_date}")

    typ, data = imap.uid("SEARCH", None, f"BEFORE {imap_date}")
    if typ != "OK" or not data[0]:
        return []
    uids = data[0].decode().split()
    log(f"対象メール: {len(uids)} 件 (before {before_date})")
    return uids


def main():
    parser = argparse.ArgumentParser(description="Gmail IMAP → Paperless downloader")
    _default_user = os.environ.get("Gmail_Apri_Name") or os.environ.get("GMAIL_USER") or "y.suzuki.hk@gmail.com"
    _default_pw   = os.environ.get("Gmail_PW", "")
    parser.add_argument("--user",         default=_default_user, help="Gmail アドレス (.env: Gmail_Apri_Name)")
    parser.add_argument("--app-password", default=_default_pw,   help="App Password (.env: Gmail_PW)")
    parser.add_argument("--before",       default="2013-06-01", help="この日付以前を取得 (YYYY-MM-DD)")
    parser.add_argument("--dry-run",      action="store_true", help="ファイル書き込みなし")
    parser.add_argument("--limit",        type=int, default=0, help="取得上限件数 (0=無制限)")
    args = parser.parse_args()

    EML_DIR.mkdir(parents=True, exist_ok=True)
    ATTACH_DIR.mkdir(parents=True, exist_ok=True)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    log("=== Gmail IMAP ダウンローダー 起動 ===")
    log(f"取得期間: before {args.before}")
    log(f"保存先 .eml: {EML_DIR}")
    log(f"保存先 添付: {ATTACH_DIR}")

    con = init_db()
    already = con.execute("SELECT COUNT(*) FROM pulled").fetchone()[0]
    log(f"取得済み (DB): {already} 件")

    imap = connect_imap(args.user, args.app_password.replace(" ", ""))
    uids = search_uids_before(imap, args.before)

    if args.limit:
        uids = uids[:args.limit]

    total = len(uids)
    new_dl = 0
    skip   = 0
    attach_saved = 0
    err    = 0

    for i in range(0, total, BATCH):
        chunk = uids[i:i+BATCH]
        uid_str = ",".join(chunk)

        typ, data = imap.uid("FETCH", uid_str, "(RFC822)")
        if typ != "OK":
            log(f"  [WARN] FETCH エラー (chunk {i})")
            continue

        j = 0
        while j < len(data):
            item = data[j]
            if isinstance(item, tuple):
                uid_match = re.search(rb"UID (\d+)", data[j][0])
                if not uid_match:
                    j += 1
                    continue
                uid_bytes = uid_match.group(1).decode()

                if is_pulled(con, uid_bytes):
                    skip += 1
                    j += 2
                    continue

                raw = item[1]
                try:
                    msg = email.message_from_bytes(raw)
                except Exception as e:
                    log(f"  [ERR parse] uid={uid_bytes}: {e}")
                    err += 1
                    j += 2
                    continue

                subj   = decode_hdr(msg.get("Subject", "(no subject)"))[:80]
                msg_id = msg.get("Message-ID", uid_bytes)
                ym     = date_to_dir(msg)
                sha8   = hashlib.sha256(raw).hexdigest()[:8]
                eml_name = f"{sha8}_{uid_bytes}.eml"
                eml_path  = EML_DIR / ym / eml_name

                if not args.dry_run:
                    eml_path.parent.mkdir(parents=True, exist_ok=True)
                    eml_path.write_bytes(raw)
                    att = extract_attachments(msg, args.dry_run)
                    attach_saved += att

                mark_pulled(con, uid_bytes, msg_id, subj, ym, str(eml_path))
                new_dl += 1

                if new_dl % 200 == 0 or new_dl <= 3:
                    pct = (i + BATCH) / total * 100
                    log(f"  [{new_dl}/{total}] {pct:.1f}% — {subj[:50]}")

            j += 1

        # IMAP サーバー負荷軽減
        time.sleep(0.1)

    imap.logout()

    log("=== 完了 ===")
    log(f"  新規 DL: {new_dl} 件")
    log(f"  スキップ: {skip} 件")
    log(f"  添付展開: {attach_saved} 件")
    log(f"  エラー: {err} 件")
    log(f"  .eml 保存先: {EML_DIR}")
    log(f"  添付 保存先: {ATTACH_DIR}")
    log("")
    log("次のステップ: python scripts/eml_preprocess_for_paperless.py")


if __name__ == "__main__":
    main()
