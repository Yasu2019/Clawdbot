# -*- coding: utf-8 -*-
"""
becky_b64_to_paperless.py
D:/tmp/becky_attachments/ 以下に保存された .b64 ファイル群を
Base64 デコードして Paperless consume へコピーする。

k10_becky_puller.py --all がダウンロードした .b64 ファイルを処理する。
manifest.jsonl 不要。ファイルパスから元ファイル名を抽出する。

Usage:
  python scripts/becky_b64_to_paperless.py
  python scripts/becky_b64_to_paperless.py --dry-run   # ドライラン
"""
import argparse
import base64
import hashlib
import sys
import io
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

B64_DIR     = Path(r"D:\tmp\becky_attachments")
CONSUME_DIR = Path(r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\becky_attachments")
DONE_DB     = Path(r"D:\tmp\becky_b64_to_paperless_done.txt")

WHITELIST_EXT = {
    ".pdf", ".xls", ".xlsx", ".xlsm",
    ".doc", ".docx", ".ppt", ".pptx",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff",
    ".txt", ".csv", ".xml", ".html",
}
DANGEROUS_EXT = {
    ".exe", ".com", ".js", ".vbs", ".bat", ".ps1", ".cmd",
    ".scr", ".pif", ".hta", ".jar", ".msi", ".wsf", ".lnk",
}


def load_done() -> set:
    if not DONE_DB.exists():
        return set()
    return set(DONE_DB.read_text(encoding="utf-8").splitlines())


def mark_done(path_str: str) -> None:
    with open(DONE_DB, "a", encoding="utf-8") as f:
        f.write(path_str + "\n")


def safe_filename(name: str, max_len: int = 120) -> str:
    keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-() ")
    cleaned = "".join(c if c in keep else "_" for c in name).strip()
    if len(cleaned) > max_len:
        stem, ext = cleaned[:max_len-10], cleaned[-10:] if "." in cleaned[-10:] else ""
        cleaned = stem + ext
    return cleaned or "attachment"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    CONSUME_DIR.mkdir(parents=True, exist_ok=True)

    done = load_done()
    b64_files = list(B64_DIR.rglob("*.b64"))
    print(f"[INFO] .b64 ファイル: {len(b64_files)}件")

    ok = err = skip = blocked = 0

    for b64_path in sorted(b64_files):
        key = str(b64_path)
        if key in done:
            skip += 1
            continue

        # 元ファイル名 = .b64 を除いた拡張子
        orig_name = b64_path.stem   # e.g. "document.pdf" from "document.pdf.b64"
        ext = Path(orig_name).suffix.lower()

        if ext in DANGEROUS_EXT:
            print(f"  [BLOCK] {orig_name}")
            mark_done(key)
            blocked += 1
            continue

        if ext not in WHITELIST_EXT:
            mark_done(key)
            skip += 1
            continue

        try:
            raw = b64_path.read_bytes()
            decoded = base64.b64decode(raw)
        except Exception as e:
            print(f"  [ERR decode] {b64_path.name}: {e}")
            err += 1
            continue

        # 出力ファイル名: SHA256 前8桁_元ファイル名
        sha8 = hashlib.sha256(decoded).hexdigest()[:8]
        out_name = f"{sha8}_{safe_filename(orig_name)}"
        out_path = CONSUME_DIR / out_name

        if out_path.exists():
            mark_done(key)
            skip += 1
            continue

        if not args.dry_run:
            try:
                out_path.write_bytes(decoded)
                mark_done(key)
            except Exception as e:
                print(f"  [ERR write] {out_name}: {e}")
                err += 1
                continue

        ok += 1
        if ok % 500 == 0 or ok <= 5:
            print(f"  [{ok}] {out_name} ({len(decoded):,}B)", flush=True)

    print()
    print(f"完了: デコード={ok}件 / スキップ={skip}件 / ブロック={blocked}件 / エラー={err}件")
    print(f"出力先: {CONSUME_DIR} — Paperless が自動取り込み")


if __name__ == "__main__":
    main()
