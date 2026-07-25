# -*- coding: utf-8 -*-
"""
becky_ingest_attachments.py  (K10 side)

Decodes Becky .b64 attachments from D:\\tmp\\becky_attachments\\
and copies them to Paperless consume directory.

Usage:
  # Matsushita-specific (first run):
  python scripts/becky_ingest_attachments.py --filter matsushita.02.sojiro@mektec.nokgrp.com

  # All emails (background):
  python scripts/becky_ingest_attachments.py --all
"""
import argparse
import base64
import email
import hashlib
import io
import json
import shutil
import sys
from datetime import timezone
from email.header import decode_header
from email.utils import parsedate_to_datetime
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

BACKUP_DIR   = Path(r"F:\tmp\becky_backup")
MANIFEST     = Path(r"F:\tmp\becky_attachments\manifest.jsonl")
CONSUME_DIR  = Path(r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\becky_attachments")

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


def decode_str(value):
    if not value:
        return ""
    parts = []
    for chunk, enc in decode_header(value):
        if isinstance(chunk, bytes):
            try:
                parts.append(chunk.decode(enc or "utf-8", errors="ignore"))
            except (LookupError, TypeError):
                parts.append(chunk.decode("utf-8", errors="ignore"))
        else:
            parts.append(str(chunk))
    return "".join(parts).strip()


def safe_filename(name: str) -> str:
    keep = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-() ")
    return "".join(c if c in keep else "_" for c in name).strip() or "unknown"


def decode_b64_content(raw: bytes) -> bytes:
    """Base64 decode; fall back to raw if already binary."""
    try:
        return base64.b64decode(raw)
    except Exception:
        return raw


def load_manifest() -> dict[str, list[dict]]:
    """Load manifest.jsonl keyed by bmf_sha256[:16]."""
    index: dict[str, list[dict]] = {}
    if not MANIFEST.exists():
        print("[WARN] manifest.jsonl not found")
        return index
    with open(MANIFEST, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                entry = json.loads(line)
                key = entry.get("bmf_sha256", "")[:16]
                index.setdefault(key, []).append(entry)
            except Exception:
                pass
    print(f"[INFO] manifest loaded: {sum(len(v) for v in index.values())} entries "
          f"across {len(index)} emails")
    return index


def email_matches_filter(msg, filter_addr: str) -> bool:
    if not filter_addr:
        return True
    filter_lower = filter_addr.lower()
    for hdr in ("From", "To", "Cc", "Reply-To"):
        if filter_lower in decode_str(msg.get(hdr, "")).lower():
            return True
    return False


def ingest_email_attachments(
    bmf_path: Path,
    manifest_index: dict[str, list[dict]],
    consume_dir: Path,
    filter_addr: str = "",
    processed_set: set = None,
) -> tuple[int, int]:
    """
    Returns (decoded_count, skipped_count).
    """
    if processed_set is None:
        processed_set = set()

    try:
        raw = bmf_path.read_bytes()
    except Exception:
        return 0, 0

    try:
        msg = email.message_from_bytes(raw)
    except Exception:
        return 0, 0

    if not email_matches_filter(msg, filter_addr):
        return 0, 0

    # Get date and subject for filename prefix
    try:
        dt = parsedate_to_datetime(msg.get("Date", ""))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        date_str = dt.strftime("%Y%m%d")
    except Exception:
        date_str = "unknown"

    subj = safe_filename(decode_str(msg.get("Subject", "no_subject")))[:50]
    frm  = safe_filename(decode_str(msg.get("From", "unknown")))[:30]

    # Find attachment entries in manifest
    bmf_key = bmf_path.stem  # filename without .bmf = sha256[:16]
    entries = manifest_index.get(bmf_key, [])
    if not entries:
        return 0, 0

    decoded = 0
    skipped = 0

    for entry in entries:
        saved_as   = Path(entry["saved_as"])
        attach_name = entry.get("attach_name", "unknown")
        ext = Path(attach_name).suffix.lower()

        if ext in DANGEROUS_EXT:
            print(f"  [BLOCKED] {attach_name}")
            continue
        if ext not in WHITELIST_EXT:
            skipped += 1
            continue
        if not saved_as.exists():
            skipped += 1
            continue

        content_sha = entry.get("sha256", "")
        if content_sha and content_sha in processed_set:
            skipped += 1
            continue

        # Output filename: {date}_{subject}_{attach_name}
        safe_orig = safe_filename(attach_name)
        out_name  = f"{date_str}_{subj[:30]}_{safe_orig}"
        out_path  = consume_dir / out_name

        if out_path.exists():
            if content_sha:
                processed_set.add(content_sha)
            skipped += 1
            continue

        try:
            raw_b64 = saved_as.read_bytes()
            decoded_data = decode_b64_content(raw_b64)
            out_path.write_bytes(decoded_data)
            if content_sha:
                processed_set.add(content_sha)
            decoded += 1
            print(f"  [OK] {out_name} ({len(decoded_data):,}B)")
        except Exception as e:
            print(f"  [ERR] {attach_name}: {e}")

    return decoded, skipped


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--filter", default="", help="Email address substring filter")
    parser.add_argument("--all", action="store_true", help="Process all emails (no filter)")
    parser.add_argument("--limit", type=int, default=0, help="Max emails to process (0=unlimited)")
    args = parser.parse_args()

    if not args.all and not args.filter:
        print("Use --filter <email> or --all")
        sys.exit(1)

    filter_addr = "" if args.all else args.filter
    label = "all" if args.all else args.filter

    CONSUME_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[START] Becky attachment ingest — filter: {label}")
    print(f"[INFO]  Backup dir : {BACKUP_DIR}")
    print(f"[INFO]  Consume dir: {CONSUME_DIR}")
    print()

    manifest_index = load_manifest()
    if not manifest_index:
        print("[ABORT] No manifest data — run transfer first")
        sys.exit(1)

    bmf_files = sorted(BACKUP_DIR.rglob("*.bmf"))
    print(f"[INFO] {len(bmf_files)} .bmf files in backup")
    print()

    processed_set: set = set()
    total_decoded = 0
    total_skipped = 0
    emails_with_attach = 0
    processed_emails = 0

    for i, bmf_path in enumerate(bmf_files):
        if args.limit and processed_emails >= args.limit:
            break

        d, s = ingest_email_attachments(
            bmf_path, manifest_index, CONSUME_DIR, filter_addr, processed_set
        )

        if d > 0 or s > 0:
            emails_with_attach += 1
            total_decoded += d
            total_skipped  += s

        if d > 0:
            processed_emails += 1

        if (i + 1) % 1000 == 0:
            print(f"--- {i+1}/{len(bmf_files)} scanned | "
                  f"decoded={total_decoded} | emails={emails_with_attach} ---")

    print()
    print("=" * 50)
    print(f"スキャン: {len(bmf_files)} .bmf")
    print(f"添付あり: {emails_with_attach} メール")
    print(f"デコード成功: {total_decoded} 件")
    print(f"スキップ: {total_skipped} 件")
    print(f"保存先: {CONSUME_DIR}")
    print()
    print("Paperless が自動的に取り込みます（consume 監視）")


if __name__ == "__main__":
    main()
