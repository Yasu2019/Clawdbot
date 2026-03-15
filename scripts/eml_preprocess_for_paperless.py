from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
from datetime import datetime, timezone
from email import policy
from email.header import decode_header
from email.parser import BytesParser
from email.utils import getaddresses, parsedate_to_datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
EMAIL_ROOT = REPO_ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "email"
GENERATED_ROOT = REPO_ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "email_generated"
TXT_ROOT = GENERATED_ROOT / "txt"
HTML_ROOT = GENERATED_ROOT / "html"
ATTACHMENT_ROOT = GENERATED_ROOT / "attachments"
STATE_DIR = REPO_ROOT / "data" / "state" / "email_preprocess"
STATE_FILE = STATE_DIR / "state.json"
STATUS_FILE = STATE_DIR / "harness_status.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def ensure_dirs() -> None:
    for path in (TXT_ROOT, HTML_ROOT, ATTACHMENT_ROOT, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def decode_mime_text(value: str | None) -> str:
    if not value:
        return ""
    parts: list[str] = []
    for chunk, encoding in decode_header(value):
        if isinstance(chunk, bytes):
            parts.append(chunk.decode(encoding or "utf-8", errors="ignore"))
        else:
            parts.append(str(chunk))
    return "".join(parts).strip()


def sanitize_filename(name: str, fallback: str = "item") -> str:
    cleaned = decode_mime_text(name or "").strip()
    cleaned = re.sub(r"[<>:\"/\\\\|?*\x00-\x1f]", "_", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
    return cleaned or fallback


def shorten_filename(name: str, max_len: int = 96) -> str:
    safe = sanitize_filename(name)
    if len(safe) <= max_len:
        return safe
    stem, ext = os.path.splitext(safe)
    digest = hashlib.sha1(safe.encode("utf-8")).hexdigest()[:10]
    keep = max_len - len(ext) - len(digest) - 1
    keep = max(16, keep)
    return f"{stem[:keep]}_{digest}{ext}"


def fit_filename_to_parent(parent: Path, name: str, max_total_len: int = 235) -> str:
    safe = sanitize_filename(name)
    candidate = parent / safe
    if len(str(candidate)) <= max_total_len:
        return safe

    stem, ext = os.path.splitext(safe)
    digest = hashlib.sha1(safe.encode("utf-8")).hexdigest()[:10]
    budget = max_total_len - len(str(parent)) - len(ext) - len(digest) - 2
    budget = max(12, budget)
    return f"{stem[:budget]}_{digest}{ext}"


def format_addresses(raw_value: str | None) -> str:
    if not raw_value:
        return "-"
    parts: list[str] = []
    for name, address in getaddresses([raw_value]):
        disp = decode_mime_text(name)
        if disp and address:
            parts.append(f"{disp} <{address}>")
        elif address:
            parts.append(address)
        elif disp:
            parts.append(disp)
    return "; ".join(parts) if parts else decode_mime_text(raw_value) or "-"


def format_date(raw_value: str | None) -> str:
    if not raw_value:
        return "-"
    decoded = decode_mime_text(raw_value)
    try:
        return parsedate_to_datetime(decoded).astimezone().isoformat()
    except Exception:
        return decoded or "-"


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"version": 1, "processed": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "processed": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def write_status(**extra: object) -> None:
    payload = {
        "service": "email_preprocess_for_paperless",
        "updatedAt": utc_now(),
    }
    payload.update(extra)
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def rel_to_email_root(path: Path) -> Path:
    return path.relative_to(EMAIL_ROOT)


def base_output_parts(eml_path: Path) -> tuple[Path, str]:
    rel = rel_to_email_root(eml_path)
    digest = hashlib.sha1(str(rel).encode("utf-8")).hexdigest()[:10]
    stem = shorten_filename(eml_path.stem, max_len=48)
    name = f"{stem}_{digest}"
    parent = rel.parent
    return parent, name


def short_rel_bucket(path: Path) -> Path:
    rel = rel_to_email_root(path)
    digest = hashlib.sha1(str(rel.parent).encode("utf-8")).hexdigest()[:8]
    top = sanitize_filename(rel.parts[0], fallback="email") if rel.parts else "email"
    return Path(top) / digest


def collect_bodies(msg) -> tuple[str, str]:
    plain_parts: list[str] = []
    html_parts: list[str] = []

    def append_part(part) -> None:
        disposition = str(part.get("Content-Disposition", ""))
        if "attachment" in disposition.lower():
            return
        content_type = part.get_content_type()
        try:
            payload = part.get_content()
        except Exception:
            payload = part.get_payload(decode=True)
            if isinstance(payload, bytes):
                payload = payload.decode(part.get_content_charset() or "utf-8", errors="ignore")
        text = str(payload or "").strip()
        if not text:
            return
        if content_type == "text/plain":
            plain_parts.append(text)
        elif content_type == "text/html":
            html_parts.append(text)

    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_maintype() == "text":
                append_part(part)
    else:
        append_part(msg)

    plain = "\n\n".join(plain_parts).strip()
    html_body = "\n<hr/>\n".join(html_parts).strip()
    return plain, html_body


def extract_attachments(msg, out_dir: Path, dry_run: bool) -> list[dict]:
    attachments: list[dict] = []
    counter = 0
    for part in msg.walk():
        filename = part.get_filename()
        disposition = str(part.get("Content-Disposition", ""))
        if not filename and "attachment" not in disposition.lower():
            continue
        payload = part.get_payload(decode=True)
        if payload is None:
            continue
        counter += 1
        raw_name = shorten_filename(filename or f"attachment_{counter}.bin")
        safe_name = fit_filename_to_parent(out_dir, raw_name)
        target = out_dir / safe_name
        if not dry_run:
            out_dir.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload)
        attachments.append(
            {
                "filename": safe_name,
                "size": len(payload),
                "contentType": part.get_content_type(),
                "target": str(target),
            }
        )
    return attachments


def build_txt(meta: dict, plain_body: str, attachments: list[dict]) -> str:
    attachment_lines = "\n".join(
        f"- {item['filename']} ({item['contentType']}, {item['size']} bytes)" for item in attachments
    ) or "-"
    return (
        f"Subject: {meta['subject']}\n"
        f"From: {meta['from']}\n"
        f"To: {meta['to']}\n"
        f"Date: {meta['date']}\n"
        f"Source EML: {meta['source']}\n"
        f"Attachments:\n{attachment_lines}\n\n"
        f"Body:\n{plain_body or '-'}\n"
    )


def build_html(meta: dict, plain_body: str, html_body: str, attachments: list[dict]) -> str:
    attachment_items = "".join(
        f"<li>{html.escape(item['filename'])} ({html.escape(item['contentType'])}, {item['size']} bytes)</li>"
        for item in attachments
    ) or "<li>-</li>"
    body_html = html_body or f"<pre>{html.escape(plain_body or '-') }</pre>"
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(meta['subject'])}</title>
</head>
<body>
  <h1>{html.escape(meta['subject'])}</h1>
  <p><strong>From:</strong> {html.escape(meta['from'])}</p>
  <p><strong>To:</strong> {html.escape(meta['to'])}</p>
  <p><strong>Date:</strong> {html.escape(meta['date'])}</p>
  <p><strong>Source EML:</strong> {html.escape(meta['source'])}</p>
  <h2>Attachments</h2>
  <ul>{attachment_items}</ul>
  <h2>Body</h2>
  {body_html}
</body>
</html>
"""


def process_eml(eml_path: Path, dry_run: bool) -> dict:
    with eml_path.open("rb") as fp:
        msg = BytesParser(policy=policy.default).parse(fp)

    parent_rel, base_name = base_output_parts(eml_path)
    short_bucket = short_rel_bucket(eml_path)
    txt_path = TXT_ROOT / short_bucket / f"{base_name}.txt"
    html_path = HTML_ROOT / short_bucket / f"{base_name}.html"
    attachment_dir = ATTACHMENT_ROOT / short_bucket / base_name

    meta = {
        "source": str(eml_path),
        "subject": decode_mime_text(msg.get("subject", "")) or eml_path.stem,
        "from": format_addresses(msg.get("from")),
        "to": format_addresses(msg.get("to")),
        "date": format_date(msg.get("date")),
    }
    plain_body, html_body = collect_bodies(msg)
    attachments = extract_attachments(msg, attachment_dir, dry_run=dry_run)
    txt_content = build_txt(meta, plain_body, attachments)
    html_content = build_html(meta, plain_body, html_body, attachments)

    if not dry_run:
        txt_path.parent.mkdir(parents=True, exist_ok=True)
        html_path.parent.mkdir(parents=True, exist_ok=True)
        txt_path.write_text(txt_content, encoding="utf-8")
        html_path.write_text(html_content, encoding="utf-8")

    return {
        "source": str(eml_path),
        "txt": str(txt_path),
        "html": str(html_path),
        "attachmentCount": len(attachments),
        "attachments": attachments,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    ensure_dirs()
    state = load_state()
    processed = state.setdefault("processed", {})
    eml_paths = sorted(EMAIL_ROOT.rglob("*.eml"))
    if args.limit > 0:
        eml_paths = eml_paths[: args.limit]

    write_status(state="starting", totalCandidates=len(eml_paths), dryRun=args.dry_run)

    generated = 0
    skipped = 0
    last_result: dict | None = None

    for eml_path in eml_paths:
        stat = eml_path.stat()
        key = str(eml_path)
        fingerprint = f"{stat.st_mtime_ns}:{stat.st_size}"
        if processed.get(key) == fingerprint:
            skipped += 1
            continue
        result = process_eml(eml_path, dry_run=args.dry_run)
        processed[key] = fingerprint
        generated += 1
        last_result = result
        write_status(
            state="processing",
            generated=generated,
            skipped=skipped,
            lastSource=result["source"],
            lastTxt=result["txt"],
            lastHtml=result["html"],
            lastAttachmentCount=result["attachmentCount"],
            dryRun=args.dry_run,
        )

    state["updatedAt"] = utc_now()
    if not args.dry_run:
        save_state(state)

    write_status(
        state="completed",
        generated=generated,
        skipped=skipped,
        totalCandidates=len(eml_paths),
        lastResult=last_result,
        dryRun=args.dry_run,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
