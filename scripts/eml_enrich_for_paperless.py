from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from eml_preprocess_for_paperless import (
    EMAIL_ROOT,
    GENERATED_ROOT,
    REPO_ROOT,
    base_output_parts,
    decode_mime_text,
    rel_to_email_root,
    sanitize_filename,
    short_rel_bucket,
)


PDF_ROOT = GENERATED_ROOT / "pdf"
KNOWLEDGE_ROOT = GENERATED_ROOT / "knowledge"
STATE_DIR = REPO_ROOT / "data" / "state" / "email_enrich"
STATE_FILE = STATE_DIR / "state.json"
STATUS_FILE = STATE_DIR / "harness_status.json"

BROWSER_CANDIDATES = (
    Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
    Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
    Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
)
PIPELINE_VERSION = "v2"


def utc_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def ensure_dirs() -> None:
    for path in (PDF_ROOT, KNOWLEDGE_ROOT, STATE_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_status(**extra: object) -> None:
    payload = {
        "service": "email_enrich_for_paperless",
        "updatedAt": utc_now(),
    }
    payload.update(extra)
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_state() -> dict:
    if not STATE_FILE.exists():
        return {"version": 1, "processed": {}}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"version": 1, "processed": {}}


def save_state(state: dict) -> None:
    STATE_FILE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def detect_browser() -> Path | None:
    for candidate in BROWSER_CANDIDATES:
        if candidate.exists():
            return candidate
    return None


def derive_paths(eml_path: Path) -> dict[str, Path]:
    parent_rel, base_name = base_output_parts(eml_path)
    short_bucket = short_rel_bucket(eml_path)
    txt_path = GENERATED_ROOT / "txt" / short_bucket / f"{base_name}.txt"
    html_path = GENERATED_ROOT / "html" / short_bucket / f"{base_name}.html"
    legacy_txt = GENERATED_ROOT / "txt" / parent_rel / f"{base_name}.txt"
    legacy_html = GENERATED_ROOT / "html" / parent_rel / f"{base_name}.html"
    if not txt_path.exists() and legacy_txt.exists():
        txt_path = legacy_txt
    if not html_path.exists() and legacy_html.exists():
        html_path = legacy_html
    pdf_path = PDF_ROOT / short_bucket / f"{base_name}.pdf"
    knowledge_dir = KNOWLEDGE_ROOT / short_bucket
    summary_json = knowledge_dir / f"{base_name}.json"
    summary_md = knowledge_dir / f"{base_name}.md"
    return {
        "txt": txt_path,
        "html": html_path,
        "pdf": pdf_path,
        "summary_json": summary_json,
        "summary_md": summary_md,
    }


def fingerprint_for(eml_path: Path, txt_path: Path, html_path: Path, model: str) -> str:
    parts = [str(eml_path), model, PIPELINE_VERSION]
    for path in (eml_path, txt_path, html_path):
        stat = path.stat()
        parts.append(f"{stat.st_mtime_ns}:{stat.st_size}")
    return "|".join(parts)


def render_html_to_pdf(browser_path: Path, html_path: Path, pdf_path: Path) -> None:
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="email-pdf-", dir=str(STATE_DIR)) as temp_dir:
        command = [
            str(browser_path),
            "--headless",
            "--disable-gpu",
            "--allow-file-access-from-files",
            f"--user-data-dir={temp_dir}",
            f"--print-to-pdf={pdf_path}",
            "--print-to-pdf-no-header",
            html_path.resolve().as_uri(),
        ]
        subprocess.run(command, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)


def parse_subject_from_txt(txt_content: str, fallback: str) -> str:
    for line in txt_content.splitlines():
        if line.startswith("Subject: "):
            return decode_mime_text(line.split(": ", 1)[1].strip()) or fallback
    return fallback


def normalize_body(txt_content: str, max_chars: int = 12000) -> str:
    marker = "\nBody:\n"
    body = txt_content.split(marker, 1)[1] if marker in txt_content else txt_content
    body = body.strip()
    if len(body) > max_chars:
        body = body[:max_chars] + "\n[truncated]"
    return body


def call_ollama(ollama_url: str, model: str, prompt: str) -> str:
    request = urllib.request.Request(
        f"{ollama_url.rstrip('/')}/api/generate",
        data=json.dumps(
            {
                "model": model,
                "prompt": prompt,
                "stream": False,
                "think": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 260,
                },
            }
        ).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=240) as response:
        payload = json.loads(response.read().decode("utf-8"))
    return str(payload.get("response", "")).strip()


def summarize_email(subject: str, txt_content: str, model: str, ollama_url: str) -> dict:
    body = normalize_body(txt_content)
    prompt = f"""You are summarizing one business email for local knowledge capture.
Return only this plain text format:
SUMMARY_JA: <one concise Japanese paragraph>
KEY_POINTS:
- <point>
- <point>
ACTION_ITEMS:
- <action or none>
TAGS: tag1, tag2, tag3
URGENCY: low|medium|high
CONFIDENCE: low|medium|high

Rules:
- Use Japanese for summary, key points, and action items.
- Keep key points to 2 to 5 bullets.
- If no action is needed, write one bullet as "- none".
- Do not add code fences.
- Do not return JSON.

Subject: {subject}

Email body:
{body}
"""
    raw = call_ollama(ollama_url=ollama_url, model=model, prompt=prompt)
    data = {
        "summary_ja": "",
        "key_points": [],
        "action_items": [],
        "tags": ["email"],
        "urgency": "medium",
        "confidence": "medium",
        "raw_response": raw,
    }
    current = None
    for line in raw.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("SUMMARY_JA:"):
            data["summary_ja"] = stripped.split(":", 1)[1].strip()
            current = None
            continue
        if stripped == "KEY_POINTS:":
            current = "key_points"
            continue
        if stripped == "ACTION_ITEMS:":
            current = "action_items"
            continue
        if stripped.startswith("TAGS:"):
            tags = [item.strip() for item in stripped.split(":", 1)[1].split(",") if item.strip()]
            if tags:
                data["tags"] = tags
            current = None
            continue
        if stripped.startswith("URGENCY:"):
            data["urgency"] = stripped.split(":", 1)[1].strip().lower() or "medium"
            current = None
            continue
        if stripped.startswith("CONFIDENCE:"):
            data["confidence"] = stripped.split(":", 1)[1].strip().lower() or "medium"
            current = None
            continue
        if stripped.startswith("-") and current in ("key_points", "action_items"):
            data[current].append(stripped[1:].strip())

    if not data["summary_ja"]:
        data["summary_ja"] = raw[:1200]
        data["tags"] = ["email", "fallback"]
        data["confidence"] = "low"
    data["subject"] = subject
    return data


def build_summary_markdown(eml_path: Path, pdf_path: Path, summary: dict) -> str:
    key_points = summary.get("key_points") or []
    action_items = summary.get("action_items") or []
    tags = summary.get("tags") or []
    key_points_block = "\n".join(f"- {item}" for item in key_points) or "- none"
    actions_block = "\n".join(f"- {item}" for item in action_items) or "- none"
    tags_block = ", ".join(str(tag) for tag in tags) or "email"
    rel = rel_to_email_root(eml_path)
    return (
        f"# {summary.get('subject', eml_path.stem)}\n\n"
        f"- Source EML: `{eml_path}`\n"
        f"- PDF: `{pdf_path}`\n"
        f"- Relative bucket: `{rel.parent}`\n"
        f"- Urgency: `{summary.get('urgency', 'medium')}`\n"
        f"- Confidence: `{summary.get('confidence', 'low')}`\n"
        f"- Tags: `{tags_block}`\n\n"
        f"## Summary\n{summary.get('summary_ja', '-')}\n\n"
        f"## Key Points\n{key_points_block}\n\n"
        f"## Action Items\n{actions_block}\n"
    )


def process_one(
    eml_path: Path,
    browser_path: Path,
    model: str,
    ollama_url: str,
    dry_run: bool,
) -> dict:
    paths = derive_paths(eml_path)
    txt_path = paths["txt"]
    html_path = paths["html"]
    pdf_path = paths["pdf"]
    summary_json = paths["summary_json"]
    summary_md = paths["summary_md"]

    if not txt_path.exists() or not html_path.exists():
        raise FileNotFoundError(f"Missing preprocess outputs for {eml_path}")

    txt_content = txt_path.read_text(encoding="utf-8", errors="ignore")
    subject = parse_subject_from_txt(txt_content, fallback=sanitize_filename(eml_path.stem, "email"))
    summary = summarize_email(subject=subject, txt_content=txt_content, model=model, ollama_url=ollama_url)
    summary["source"] = str(eml_path)
    summary["pdf"] = str(pdf_path)
    summary["updatedAt"] = utc_now()

    if not dry_run:
        render_html_to_pdf(browser_path=browser_path, html_path=html_path, pdf_path=pdf_path)
        summary_json.parent.mkdir(parents=True, exist_ok=True)
        summary_md.parent.mkdir(parents=True, exist_ok=True)
        summary_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary_md.write_text(build_summary_markdown(eml_path, pdf_path, summary), encoding="utf-8")

    return {
        "source": str(eml_path),
        "pdf": str(pdf_path),
        "summaryJson": str(summary_json),
        "summaryMd": str(summary_md),
        "subject": subject,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--model", default=os.getenv("EMAIL_ENRICH_MODEL", "qwen3:8b"))
    parser.add_argument("--ollama-url", default=os.getenv("OLLAMA_URL", "http://127.0.0.1:11434"))
    args = parser.parse_args()

    ensure_dirs()
    browser_path = detect_browser()
    if browser_path is None:
        write_status(state="config_error", error="No supported browser found for PDF rendering")
        return 2

    state = load_state()
    processed = state.setdefault("processed", {})
    eml_paths = sorted(EMAIL_ROOT.rglob("*.eml"))
    if args.limit > 0:
        eml_paths = eml_paths[: args.limit]

    write_status(
        state="starting",
        totalCandidates=len(eml_paths),
        dryRun=args.dry_run,
        model=args.model,
        browser=str(browser_path),
    )

    generated = 0
    skipped = 0
    failed = 0
    last_result: dict | None = None
    last_error: str | None = None

    for eml_path in eml_paths:
        paths = derive_paths(eml_path)
        txt_path = paths["txt"]
        html_path = paths["html"]
        if not txt_path.exists() or not html_path.exists():
            failed += 1
            last_error = "preprocess outputs missing"
            write_status(
                state="processing",
                generated=generated,
                skipped=skipped,
                failed=failed,
                lastSource=str(eml_path),
                lastError=last_error,
                dryRun=args.dry_run,
                model=args.model,
            )
            continue

        fingerprint = fingerprint_for(eml_path, txt_path, html_path, args.model)
        key = str(eml_path)
        if processed.get(key) == fingerprint:
            skipped += 1
            continue

        try:
            result = process_one(
                eml_path=eml_path,
                browser_path=browser_path,
                model=args.model,
                ollama_url=args.ollama_url,
                dry_run=args.dry_run,
            )
        except (subprocess.SubprocessError, TimeoutError, urllib.error.URLError, FileNotFoundError) as exc:
            failed += 1
            last_error = str(exc)
            write_status(
                state="processing",
                generated=generated,
                skipped=skipped,
                failed=failed,
                lastSource=str(eml_path),
                lastError=last_error,
                dryRun=args.dry_run,
                model=args.model,
            )
            continue

        generated += 1
        processed[key] = fingerprint
        last_result = result
        last_error = None
        write_status(
            state="processing",
            generated=generated,
            skipped=skipped,
            failed=failed,
            lastSource=result["source"],
            lastPdf=result["pdf"],
            lastSummary=result["summaryJson"],
            lastSubject=result["subject"],
            dryRun=args.dry_run,
            model=args.model,
        )

    state["updatedAt"] = utc_now()
    if not args.dry_run:
        save_state(state)

    write_status(
        state="completed",
        generated=generated,
        skipped=skipped,
        failed=failed,
        totalCandidates=len(eml_paths),
        lastResult=last_result,
        lastError=last_error,
        dryRun=args.dry_run,
        model=args.model,
        browser=str(browser_path),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
