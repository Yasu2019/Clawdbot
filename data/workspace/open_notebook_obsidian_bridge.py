#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parent.parent
PROJECT_ROOT = Path(__file__).parent.parent.parent
RESOLVED_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def resolve_vault_root() -> Path:
    candidates = [
        PROJECT_ROOT / "data" / "state" / "Obsidian Vault" / "Clawstack_Project",
        RESOLVED_PROJECT_ROOT / "data" / "state" / "Obsidian Vault" / "Clawstack_Project",
        ROOT / "state" / "Obsidian Vault" / "Clawstack_Project",
    ]
    for candidate in candidates:
        if not candidate.exists():
            continue
        if any(path.is_file() and path.suffix.lower() == ".md" for path in candidate.rglob("*")):
            return candidate
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


VAULT_ROOT = resolve_vault_root()
INBOX_PATH = VAULT_ROOT / "AI_Inbox.md"
RESEARCH_DIR = VAULT_ROOT / "05_Research_Summaries"
REPORTS_DIR = VAULT_ROOT / "OpenClaw_Reports"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^\w\- ]+", "", text, flags=re.UNICODE).strip()
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned[:80] or "open_notebook_summary"


def build_markdown(
    title: str,
    source_type: str,
    source_title: str | None,
    source_url: str | None,
    body: str,
    tags: list[str],
) -> str:
    tag_line = " ".join(f"#{tag}" for tag in tags if tag)
    lines = [
        f"# {title}",
        "",
        f"- Added: {now_jst_text()}",
        "- Source: Open Notebook",
        f"- Source Type: {source_type}",
    ]
    if source_title:
        lines.append(f"- Source Title: {source_title}")
    if source_url:
        lines.append(f"- Source URL: {source_url}")
    lines.append(f"- Tags: {tag_line or '#open_notebook'}")
    lines.extend(["", "## Summary", "", body.strip(), ""])
    return "\n".join(lines)


def append_inbox(markdown: str, title: str) -> Path:
    INBOX_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not INBOX_PATH.exists():
        INBOX_PATH.write_text("# AI Inbox\n\n", encoding="utf-8")
    entry = markdown.replace(f"# {title}", f"## {title}", 1)
    with INBOX_PATH.open("a", encoding="utf-8") as handle:
        handle.write("\n" + entry + "\n")
    return INBOX_PATH


def write_research(markdown: str, title: str) -> Path:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(JST).strftime('%Y-%m-%d')}_{slugify(title)}.md"
    path = RESEARCH_DIR / filename
    path.write_text(markdown, encoding="utf-8")
    return path


def write_report(markdown: str, title: str) -> Path:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    filename = f"{datetime.now(JST).strftime('%Y-%m-%d')}_{slugify(title)}.md"
    path = REPORTS_DIR / filename
    path.write_text(markdown, encoding="utf-8")
    return path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Promote Open Notebook output into the shared Obsidian vault.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--source-type", required=True, choices=["pdf", "web", "youtube", "audio", "mixed", "other"])
    parser.add_argument("--source-title")
    parser.add_argument("--source-url")
    parser.add_argument("--body", required=True)
    parser.add_argument("--tags", nargs="*", default=["open_notebook", "draft"])
    parser.add_argument("--write-target", choices=["inbox", "research", "report"], default="inbox")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    markdown = build_markdown(
        title=args.title,
        source_type=args.source_type,
        source_title=args.source_title,
        source_url=args.source_url,
        body=args.body,
        tags=args.tags,
    )
    if args.write_target == "research":
        path = write_research(markdown, args.title)
    elif args.write_target == "report":
        path = write_report(markdown, args.title)
    else:
        path = append_inbox(markdown, args.title)
    print(
        json.dumps(
            {
                "ok": True,
                "writtenAt": now_jst_text(),
                "path": str(path),
                "writeTarget": args.write_target,
                "title": args.title,
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
