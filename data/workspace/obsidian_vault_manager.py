#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOLVED_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_EXTENSIONS = {".md", ".markdown"}


def resolve_vault_root() -> Path:
    candidates = [
        PROJECT_ROOT / "data" / "state" / "Obsidian Vault" / "Clawstack_Project",
        RESOLVED_PROJECT_ROOT / "data" / "state" / "Obsidian Vault" / "Clawstack_Project",
        ROOT / "state" / "Obsidian Vault" / "Clawstack_Project",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if any(path.is_file() and path.suffix.lower() in DEFAULT_EXTENSIONS for path in candidate.rglob("*")):
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


VAULT_ROOT = resolve_vault_root()
STATE_DIR = VAULT_ROOT / ".openclaw"
INDEX_PATH = STATE_DIR / "obsidian_index.json"
STATUS_PATH = STATE_DIR / "obsidian_index_status.json"
INBOX_PATH = VAULT_ROOT / "AI_Inbox.md"
REPORTS_DIR = VAULT_ROOT / "OpenClaw_Reports"
EMAIL_SEARCH_SCRIPT = ROOT / "workspace" / "email_search_query.py"
PRIORITY_PATH_PATTERNS: tuple[tuple[str, int, str], ...] = (
    ("task.md", 12, "active_tasks"),
    ("implementation_plan_", 10, "implementation_plan"),
    ("walkthrough.md", 8, "walkthrough"),
    ("PORTAL_APPS.md", 7, "app_catalog"),
    ("AI_Inbox.md", 3, "ai_inbox"),
)
STOP_WORDS = {
    "the",
    "and",
    "for",
    "that",
    "with",
    "this",
    "from",
    "have",
    "your",
    "into",
    "about",
    "using",
    "will",
    "were",
    "when",
    "where",
    "task",
    "plan",
    "note",
    "notes",
    "todo",
    "done",
    "project",
    "clawstack",
    "openclaw",
    "obsidian",
    "です",
    "する",
    "した",
    "して",
    "ある",
    "いる",
    "こと",
    "ため",
    "よう",
    "ない",
    "から",
    "まで",
    "について",
}

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def write_status(payload: dict[str, Any]) -> None:
    ensure_state_dir()
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def relative_note_path(path: Path) -> str:
    return path.relative_to(VAULT_ROOT).as_posix()


def extract_links(text: str) -> list[str]:
    return sorted(set(re.findall(r"\[\[([^\]]+)\]\]", text)))


def extract_tags(text: str) -> list[str]:
    return sorted(set(re.findall(r"(?<!\w)#([A-Za-z0-9_\-/]+)", text)))


def extract_headings(text: str) -> list[str]:
    headings: list[str] = []
    for line in text.splitlines():
        if line.startswith("#"):
            headings.append(normalize_space(line.lstrip("#")))
    return headings


def extract_frontmatter(text: str) -> dict[str, Any]:
    if not text.startswith("---\n"):
        return {}
    end = text.find("\n---", 4)
    if end < 0:
        return {}
    block = text[4:end].strip()
    result: dict[str, Any] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        result[key.strip()] = value.strip()
    return result


def choose_title(path: Path, text: str) -> str:
    frontmatter = extract_frontmatter(text)
    if frontmatter.get("title"):
        return str(frontmatter["title"])
    for line in text.splitlines():
        if line.startswith("# "):
            return normalize_space(line[2:])
    return path.stem


def build_preview(text: str, max_len: int = 220) -> str:
    lines = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("---") or stripped.startswith("#"):
            continue
        lines.append(stripped)
        if len(" ".join(lines)) >= max_len:
            break
    preview = normalize_space(" ".join(lines))
    return preview[:max_len]


def tokenize(text: str) -> list[str]:
    raw_tokens = re.findall(r"[A-Za-z0-9_\-/.]{2,}|[一-龠ぁ-んァ-ヶ]{2,}", text)
    tokens = []
    for token in raw_tokens:
        lowered = token.lower()
        if lowered in STOP_WORDS:
            continue
        tokens.append(lowered)
    return tokens


def note_record(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace")
    stat = path.stat()
    title = choose_title(path, text)
    headings = extract_headings(text)
    tags = extract_tags(text)
    links = extract_links(text)
    preview = build_preview(text)
    todos_open = len(re.findall(r"^- \[ \]", text, flags=re.MULTILINE))
    todos_done = len(re.findall(r"^- \[x\]", text, flags=re.MULTILINE | re.IGNORECASE))
    keywords = [token for token, _count in Counter(tokenize(" ".join([title, " ".join(headings), preview]))).most_common(15)]
    return {
        "path": relative_note_path(path),
        "title": title,
        "headings": headings[:20],
        "tags": tags,
        "links": links[:50],
        "preview": preview,
        "keywords": keywords,
        "todosOpen": todos_open,
        "todosDone": todos_done,
        "modifiedAt": datetime.fromtimestamp(stat.st_mtime, JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "size": stat.st_size,
        "body": text[:12000],
    }


def iter_note_files() -> list[Path]:
    files: list[Path] = []
    for path in VAULT_ROOT.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() not in DEFAULT_EXTENSIONS:
            continue
        if ".openclaw" in path.parts:
            continue
        files.append(path)
    return sorted(files)


def build_index() -> dict[str, Any]:
    ensure_state_dir()
    status = {
        "startedAt": now_jst_text(),
        "vaultRoot": str(VAULT_ROOT),
        "stage": "indexing",
    }
    write_status(status)
    notes = [note_record(path) for path in iter_note_files()]
    payload = {
        "generatedAt": now_jst_text(),
        "vaultRoot": str(VAULT_ROOT),
        "noteCount": len(notes),
        "notes": notes,
    }
    INDEX_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    status.update(
        {
            "stage": "completed",
            "finishedAt": now_jst_text(),
            "noteCount": len(notes),
            "indexPath": str(INDEX_PATH),
        }
    )
    write_status(status)
    return payload


def load_index() -> dict[str, Any]:
    if not INDEX_PATH.exists():
        return build_index()
    return json.loads(INDEX_PATH.read_text(encoding="utf-8"))


def score_note(note: dict[str, Any], query_terms: list[str], include_path_boost: bool = True) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    path = str(note.get("path", ""))
    title = str(note.get("title", "")).lower()
    body = str(note.get("body", "")).lower()
    headings = " ".join(note.get("headings", [])).lower()
    tags = " ".join(note.get("tags", [])).lower()
    keywords = " ".join(note.get("keywords", [])).lower()
    for term in query_terms:
        if term in path.lower():
            score += 7
            reasons.append(f"path_term:{term}")
        if term in title:
            score += 9
            reasons.append(f"title:{term}")
        if term in headings:
            score += 5
            reasons.append(f"heading:{term}")
        if term in tags:
            score += 4
            reasons.append(f"tag:{term}")
        if term in keywords:
            score += 3
            reasons.append(f"keyword:{term}")
        if term in body:
            score += 1
    if include_path_boost and score > 0:
        for pattern, boost, label in PRIORITY_PATH_PATTERNS:
            if pattern in path:
                score += boost
                reasons.append(f"path:{label}")
    return score, reasons[:5]


def search_notes(query: str, limit: int, tag: str | None = None) -> dict[str, Any]:
    index = load_index()
    query_terms = [term.lower() for term in tokenize(query)]
    if not query_terms:
        query_terms = [query.lower()]
    results = []
    for note in index.get("notes", []):
        if tag and tag not in note.get("tags", []):
            continue
        score, reasons = score_note(note, query_terms)
        if score <= 0:
            continue
        results.append(
            {
                "path": note["path"],
                "title": note["title"],
                "preview": note["preview"],
                "modifiedAt": note["modifiedAt"],
                "tags": note["tags"],
                "todosOpen": note["todosOpen"],
                "score": score,
                "reasons": reasons,
            }
        )
    results.sort(key=lambda item: (-item["score"], item["path"]))
    return {
        "query": query,
        "tag": tag,
        "resultCount": len(results),
        "results": results[:limit],
    }


def project_context(query: str, limit: int) -> dict[str, Any]:
    index = load_index()
    query_terms = [term.lower() for term in tokenize(query)]
    if not query_terms:
        query_terms = [query.lower()]
    preferred = ("task.md", "implementation_plan_", "walkthrough.md", "PORTAL_APPS.md", "AI_Inbox.md")
    results = []
    for note in index.get("notes", []):
        path = str(note.get("path", ""))
        if not any(pattern in path for pattern in preferred):
            continue
        base_score, reasons = score_note(note, query_terms, include_path_boost=False)
        if base_score <= 0:
            continue
        score = base_score
        for pattern, boost, label in PRIORITY_PATH_PATTERNS:
            if pattern in path:
                score += boost + 15
                reasons.append(f"path:{label}")
        results.append(
            {
                "path": note["path"],
                "title": note["title"],
                "preview": note["preview"],
                "modifiedAt": note["modifiedAt"],
                "tags": note["tags"],
                "todosOpen": note["todosOpen"],
                "score": score,
                "reasons": reasons[:5],
            }
        )
    if not results:
        fallback = search_notes(query, limit, tag=None)
        fallback["mode"] = "fallback_search"
        return fallback
    results.sort(key=lambda item: (-item["score"], item["path"]))
    return {
        "mode": "project_context",
        "query": query,
        "resultCount": len(results),
        "results": results[:limit],
    }


def append_inbox(title: str, body: str, tags: list[str]) -> dict[str, Any]:
    ensure_state_dir()
    if not INBOX_PATH.exists():
        INBOX_PATH.write_text("# AI Inbox\n\n", encoding="utf-8")
    tag_text = " ".join(f"#{tag}" for tag in tags if tag)
    entry = [
        f"## {title}",
        "",
        f"- Added: {now_jst_text()}",
        f"- Source: OpenClaw",
        f"- Tags: {tag_text or '#ai_inbox'}",
        "",
        body.strip(),
        "",
    ]
    with INBOX_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(entry))
    return {
        "ok": True,
        "path": relative_note_path(INBOX_PATH),
        "title": title,
        "addedAt": now_jst_text(),
    }


def summarize_index(limit: int) -> dict[str, Any]:
    index = load_index()
    notes = index.get("notes", [])
    latest = sorted(notes, key=lambda item: item.get("modifiedAt", ""), reverse=True)[:limit]
    return {
        "generatedAt": index.get("generatedAt"),
        "noteCount": index.get("noteCount", 0),
        "latestNotes": [
            {
                "path": item["path"],
                "title": item["title"],
                "modifiedAt": item["modifiedAt"],
                "tags": item["tags"],
                "todosOpen": item["todosOpen"],
            }
            for item in latest
        ],
    }


def run_json_command(command: list[str], timeout_seconds: int = 120) -> dict[str, Any]:
    proc = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_seconds,
    )
    return json.loads(proc.stdout)


def complaint_report_markdown(query: str, payload: dict[str, Any]) -> str:
    lines = [
        "# Customer Complaints Latest",
        "",
        f"- Query: {query}",
        f"- Range: {payload.get('start_date', '-')} to {payload.get('end_date', '-')}",
        f"- Generated: {now_jst_text()}",
        f"- Result count: {payload.get('result_count', 0)}",
        "",
        "## Summary",
        "",
        payload.get("summary", "No summary available."),
        "",
        "## Items",
        "",
    ]
    results = payload.get("results", [])
    if not results:
        lines.append("No complaint candidates found.")
        lines.append("")
        return "\n".join(lines)
    for idx, row in enumerate(results, start=1):
        lines.extend(
            [
                f"### {idx}. {row.get('normalized_subject') or row.get('subject') or '-'}",
                "",
                f"- Date: {row.get('email_date') or '-'}",
                f"- Sender: {row.get('sender') or '-'}",
                f"- Source ID: {row.get('source_id') or '-'}",
                "",
                row.get("snippet") or "-",
                "",
            ]
        )
    return "\n".join(lines)


def complaint_report(query: str, limit: int, write_note: bool) -> dict[str, Any]:
    payload = run_json_command([sys.executable, str(EMAIL_SEARCH_SCRIPT), "complaint-context", query, "--limit", str(limit)])
    result: dict[str, Any] = {
        "query": query,
        "resultCount": payload.get("result_count", 0),
        "startDate": payload.get("start_date"),
        "endDate": payload.get("end_date"),
        "summary": payload.get("summary"),
        "results": payload.get("results", []),
    }
    if write_note:
        REPORTS_DIR.mkdir(parents=True, exist_ok=True)
        report_path = REPORTS_DIR / "Customer_Complaints_Latest.md"
        report_path.write_text(complaint_report_markdown(query, payload), encoding="utf-8")
        result["notePath"] = relative_note_path(report_path)
        result["writtenAt"] = now_jst_text()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Manage the shared Obsidian vault for OpenClaw.")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-index")
    build.set_defaults(func=lambda args: build_index())

    search = sub.add_parser("search")
    search.add_argument("query")
    search.add_argument("--limit", type=int, default=10)
    search.add_argument("--tag")
    search.set_defaults(func=lambda args: search_notes(args.query, args.limit, args.tag))

    context = sub.add_parser("project-context")
    context.add_argument("query")
    context.add_argument("--limit", type=int, default=8)
    context.set_defaults(func=lambda args: project_context(args.query, args.limit))

    inbox = sub.add_parser("add-inbox")
    inbox.add_argument("--title", required=True)
    inbox.add_argument("--body", required=True)
    inbox.add_argument("--tags", nargs="*", default=["ai_inbox"])
    inbox.set_defaults(func=lambda args: append_inbox(args.title, args.body, args.tags))

    summary = sub.add_parser("summary")
    summary.add_argument("--limit", type=int, default=10)
    summary.set_defaults(func=lambda args: summarize_index(args.limit))

    complaints = sub.add_parser("complaint-report")
    complaints.add_argument("query")
    complaints.add_argument("--limit", type=int, default=10)
    complaints.add_argument("--write-note", action="store_true")
    complaints.set_defaults(func=lambda args: complaint_report(args.query, args.limit, args.write_note))
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
