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
AI_ROOT = VAULT_ROOT / "_ai"
AI_INSIGHTS_DIR = AI_ROOT / "insights"
AI_HUBS_DIR = AI_ROOT / "hubs"
AI_RELATIONS_DIR = AI_ROOT / "relations"
AI_REPORTS_DIR = AI_ROOT / "reports"
AI_BATCHES_DIR = AI_ROOT / "batches"
EMAIL_SEARCH_SCRIPT = ROOT / "workspace" / "email_search_query.py"
SECOND_BRAIN_EXCLUDE_PATH = ROOT / "workspace" / "obsidian_second_brain_exclude_patterns.txt"
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
    "is",
    "of",
    "or",
    "in",
    "to",
    "as",
    "add",
    "current",
    "generated",
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
DEFAULT_SECOND_BRAIN_EXCLUDES = (
    "Archive/",
    "archive/",
    "Logs/",
    "logs/",
    "tmp/",
    "temp/",
    ".cache/",
    ".trash/",
    ".obsidian/workspace",
    ".obsidian/cache",
    "Daily/",
    "Journal/",
    "AI Chat/",
    "Chat Logs/",
    "_ai/",
    ".openclaw/",
    "URL集/",
    "リンク集/",
    "添付一覧/",
    "スクリーンショット/",
    "*_log.md",
    "*_logs.md",
)

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def ensure_state_dir() -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)


def ensure_second_brain_dirs() -> None:
    for path in (AI_ROOT, AI_INSIGHTS_DIR, AI_HUBS_DIR, AI_RELATIONS_DIR, AI_REPORTS_DIR, AI_BATCHES_DIR):
        path.mkdir(parents=True, exist_ok=True)


def write_status(payload: dict[str, Any]) -> None:
    ensure_state_dir()
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def relative_note_path(path: Path) -> str:
    return path.relative_to(VAULT_ROOT).as_posix()


def safe_batch_slug(text: str) -> str:
    slug = re.sub(r"[^\w\- ]+", "_", text, flags=re.UNICODE).strip()
    slug = re.sub(r"\s+", "_", slug)
    return slug[:80] or "batch"


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
        if re.fullmatch(r"[0-9.]+", lowered):
            continue
        if lowered in STOP_WORDS:
            continue
        tokens.append(lowered)
    return tokens


def jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


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


def load_exclude_patterns(path: Path | None = None) -> list[str]:
    if path and path.exists():
        source = path
    elif SECOND_BRAIN_EXCLUDE_PATH.exists():
        source = SECOND_BRAIN_EXCLUDE_PATH
    else:
        return list(DEFAULT_SECOND_BRAIN_EXCLUDES)
    patterns: list[str] = []
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        patterns.append(stripped)
    return patterns or list(DEFAULT_SECOND_BRAIN_EXCLUDES)


def path_matches_pattern(path_text: str, pattern: str) -> bool:
    normalized_path = path_text.replace("\\", "/")
    normalized_pattern = pattern.replace("\\", "/")
    if "*" in normalized_pattern:
        regex = "^" + re.escape(normalized_pattern).replace(r"\*", ".*") + "$"
        return re.search(regex, normalized_path, flags=re.IGNORECASE) is not None
    return normalized_pattern.lower() in normalized_path.lower()


def is_excluded_path(path_text: str, patterns: list[str]) -> bool:
    return any(path_matches_pattern(path_text, pattern) for pattern in patterns)


def select_second_brain_notes(
    notes: list[dict[str, Any]],
    include_paths: list[str],
    limit: int,
    query: str | None,
    exclude_patterns: list[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    normalized_paths = [p.strip().replace("\\", "/").strip("/") for p in include_paths if p.strip()]
    query_terms = [term.lower() for term in tokenize(query or "")]
    selected: list[dict[str, Any]] = []
    skipped: list[str] = []
    for note in notes:
        path = str(note.get("path", ""))
        if is_excluded_path(path, exclude_patterns):
            skipped.append(path)
            continue
        if normalized_paths and not any(path.lower().startswith(prefix.lower()) for prefix in normalized_paths):
            continue
        note_copy = dict(note)
        note_copy["_selectionScore"] = 0
        note_copy["_selectionReasons"] = []
        if query_terms:
            score, reasons = score_note(note_copy, query_terms)
            if score <= 0:
                continue
            note_copy["_selectionScore"] = score
            note_copy["_selectionReasons"] = reasons
        else:
            modified_score = parse_dt(note_copy.get("modifiedAt"))
            freshness = modified_score.timestamp() if modified_score else 0
            note_copy["_selectionScore"] = int(freshness)
            note_copy["_selectionReasons"] = ["recent"]
        selected.append(note_copy)
    selected.sort(key=lambda item: (-int(item.get("_selectionScore", 0)), str(item.get("path", ""))))
    return selected[:limit], skipped


def note_topic_tokens(note: dict[str, Any]) -> list[str]:
    body = str(note.get("body", ""))
    title = str(note.get("title", ""))
    headings = " ".join(note.get("headings", []))
    tags = " ".join(note.get("tags", []))
    keywords = " ".join(note.get("keywords", []))
    return tokenize(" ".join([title, headings, tags, keywords, body[:1200]]))


def second_brain_analysis(selected_notes: list[dict[str, Any]]) -> dict[str, Any]:
    topic_counter: Counter[str] = Counter()
    tag_counter: Counter[str] = Counter()
    path_groups: Counter[str] = Counter()
    note_tokens: dict[str, set[str]] = {}
    for note in selected_notes:
        path = str(note.get("path", ""))
        note_tokens[path] = set(note_topic_tokens(note))
        topic_counter.update(token for token in note_tokens[path] if len(token) >= 3)
        tag_counter.update(note.get("tags", []))
        top_folder = path.split("/", 1)[0] if "/" in path else path
        path_groups.update([top_folder])

    top_topics = [{"topic": topic, "count": count} for topic, count in topic_counter.most_common(12)]
    top_tags = [{"tag": tag, "count": count} for tag, count in tag_counter.most_common(12)]
    folder_distribution = [{"folder": folder, "count": count} for folder, count in path_groups.most_common()]

    relations: list[dict[str, Any]] = []
    duplicates: list[dict[str, Any]] = []
    for idx, left in enumerate(selected_notes):
        left_path = str(left.get("path", ""))
        left_tokens = note_tokens.get(left_path, set())
        left_tags = set(left.get("tags", []))
        left_links = set(left.get("links", []))
        for right in selected_notes[idx + 1:]:
            right_path = str(right.get("path", ""))
            right_tokens = note_tokens.get(right_path, set())
            right_tags = set(right.get("tags", []))
            right_links = set(right.get("links", []))
            shared_tokens = sorted((left_tokens & right_tokens) - STOP_WORDS)
            shared_tags = sorted(left_tags & right_tags)
            shared_links = sorted(left_links & right_links)
            if shared_tokens or shared_tags or shared_links:
                strength = len(shared_tokens[:6]) + len(shared_tags) * 2 + len(shared_links) * 2
                if strength > 0:
                    relations.append(
                        {
                            "left": left_path,
                            "right": right_path,
                            "strength": strength,
                            "sharedTopics": shared_tokens[:6],
                            "sharedTags": shared_tags[:6],
                            "sharedLinks": shared_links[:6],
                        }
                    )
            title_similarity = jaccard_similarity(set(tokenize(str(left.get("title", "")))), set(tokenize(str(right.get("title", "")))))
            preview_similarity = jaccard_similarity(set(shared_tokens[:10]), set(note_tokens.get(right_path, set())))
            if title_similarity >= 0.5 or (title_similarity >= 0.25 and preview_similarity >= 0.2):
                duplicates.append(
                    {
                        "left": left_path,
                        "right": right_path,
                        "titleSimilarity": round(title_similarity, 3),
                        "sharedTopics": shared_tokens[:8],
                    }
                )

    relations.sort(key=lambda item: (-item["strength"], item["left"], item["right"]))
    duplicates.sort(key=lambda item: (-item["titleSimilarity"], item["left"], item["right"]))
    hold_candidates = []
    for note in selected_notes:
        path = str(note.get("path", ""))
        token_count = len(note_tokens.get(path, set()))
        if token_count < 8 or len(str(note.get("preview", ""))) < 60:
            hold_candidates.append(
                {
                    "path": path,
                    "title": note.get("title"),
                    "reason": "low_information_density",
                }
            )

    return {
        "topTopics": top_topics,
        "topTags": top_tags,
        "folderDistribution": folder_distribution,
        "relations": relations[:40],
        "duplicateCandidates": duplicates[:20],
        "holdCandidates": hold_candidates[:20],
    }


def markdown_section_list(items: list[str], fallback: str = "- none") -> list[str]:
    if not items:
        return [fallback]
    return [f"- {item}" for item in items]


def build_second_brain_report_markdown(batch_id: str, selected_notes: list[dict[str, Any]], analysis: dict[str, Any], query: str | None, include_paths: list[str]) -> str:
    lines = [
        f"# Second Brain Batch Report: {batch_id}",
        "",
        f"- Generated: {now_jst_text()}",
        f"- Source Vault: {VAULT_ROOT}",
        f"- Query: {query or '-'}",
        f"- Include Paths: {', '.join(include_paths) if include_paths else 'all eligible notes'}",
        f"- Note Count: {len(selected_notes)}",
        "",
        "## Top Topics",
        "",
    ]
    for row in analysis.get("topTopics", []):
        lines.append(f"- {row['topic']}: {row['count']}")
    lines.extend(["", "## Folder Distribution", ""])
    for row in analysis.get("folderDistribution", []):
        lines.append(f"- {row['folder']}: {row['count']}")
    lines.extend(["", "## Candidate Notes", ""])
    for note in selected_notes:
        lines.extend(
            [
                f"### {note.get('title')}",
                "",
                f"- Path: {note.get('path')}",
                f"- Modified: {note.get('modifiedAt')}",
                f"- Tags: {', '.join(note.get('tags', [])) or '-'}",
                f"- Selection Reasons: {', '.join(note.get('_selectionReasons', [])) or '-'}",
                "",
                note.get("preview", "-"),
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def build_second_brain_relations_markdown(batch_id: str, analysis: dict[str, Any]) -> str:
    lines = [
        f"# Relation Map: {batch_id}",
        "",
        f"- Generated: {now_jst_text()}",
        "",
        "## Strongest Relations",
        "",
    ]
    relations = analysis.get("relations", [])
    if not relations:
        lines.append("- No strong relations found.")
    for row in relations:
        lines.extend(
            [
                f"### {row['left']} <-> {row['right']}",
                "",
                f"- Strength: {row['strength']}",
                f"- Shared Topics: {', '.join(row.get('sharedTopics', [])) or '-'}",
                f"- Shared Tags: {', '.join(row.get('sharedTags', [])) or '-'}",
                f"- Shared Links: {', '.join(row.get('sharedLinks', [])) or '-'}",
                "",
            ]
        )
    lines.extend(["## Duplicate Candidates", ""])
    duplicates = analysis.get("duplicateCandidates", [])
    if not duplicates:
        lines.append("- No duplicate candidates found.")
    for row in duplicates:
        lines.append(f"- {row['left']} <-> {row['right']} (titleSimilarity={row['titleSimilarity']}, sharedTopics={', '.join(row.get('sharedTopics', [])) or '-'})")
    lines.extend(["", "## Hold Candidates", ""])
    hold = analysis.get("holdCandidates", [])
    if not hold:
        lines.append("- None")
    for row in hold:
        lines.append(f"- {row['path']}: {row['reason']}")
    return "\n".join(lines).strip() + "\n"


def build_second_brain_hub_markdown(topic: str, batch_id: str, selected_notes: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    related_notes = []
    for note in selected_notes:
        tokens = set(note_topic_tokens(note))
        if topic in tokens:
            related_notes.append(note)
    related_notes = related_notes[:12]
    lines = [
        f"# {topic} Hub",
        "",
        f"- Generated: {now_jst_text()}",
        f"- Batch: {batch_id}",
        "- Source: second_brain_batch",
        "",
        "## Why This Hub Exists",
        "",
        f"- `{topic}` appeared repeatedly across the selected note batch and is a candidate organizing concept.",
        "",
        "## Related Notes",
        "",
    ]
    if not related_notes:
        lines.append("- None")
    for note in related_notes:
        lines.append(f"- [[{note['title']}]] ({note['path']})")
    lines.extend(
        [
            "",
            "## Reuse Questions",
            "",
            f"- Which existing notes under this topic should remain source-of-truth?",
            f"- Which notes under `{topic}` look duplicate or overlapping?",
            f"- Which follow-up insight note should be promoted from `_ai/` into a durable human-maintained note later?",
            "",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def build_second_brain_insight_markdown(batch_id: str, selected_notes: list[dict[str, Any]], analysis: dict[str, Any]) -> str:
    topic_lines = [f"- {row['topic']}: {row['count']}" for row in analysis.get("topTopics", [])[:8]]
    relation_lines = []
    for row in analysis.get("relations", [])[:8]:
        relation_lines.append(f"- {row['left']} <-> {row['right']} | shared: {', '.join(row.get('sharedTopics', [])[:4]) or '-'}")
    lines = [
        f"# Batch Insight: {batch_id}",
        "",
        f"- Generated: {now_jst_text()}",
        f"- Note Count: {len(selected_notes)}",
        "",
        "## High-Signal Topics",
        "",
        *(topic_lines or ["- None"]),
        "",
        "## Strong Relations",
        "",
        *(relation_lines or ["- None"]),
        "",
        "## Review Guidance",
        "",
        "- Review hub drafts first, then decide which human-maintained notes deserve promotion.",
        "- Treat `_ai/` outputs as suggestions, not source-of-truth replacements.",
        "- Expand the next batch only if relation links look meaningful and low-noise.",
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def second_brain_batch(query: str | None, include_paths: list[str], limit: int, batch_name: str | None, exclude_patterns_path: str | None, dry_run: bool) -> dict[str, Any]:
    index = load_index()
    exclude_patterns = load_exclude_patterns(Path(exclude_patterns_path) if exclude_patterns_path else None)
    selected_notes, skipped = select_second_brain_notes(
        notes=index.get("notes", []),
        include_paths=include_paths,
        limit=limit,
        query=query,
        exclude_patterns=exclude_patterns,
    )
    batch_seed = batch_name or query or ("_".join(include_paths) if include_paths else "vault")
    batch_id = f"{datetime.now(JST).strftime('%Y-%m-%d')}_{safe_batch_slug(batch_seed)}"
    analysis = second_brain_analysis(selected_notes)
    result: dict[str, Any] = {
        "ok": True,
        "mode": "dry_run" if dry_run else "write",
        "batchId": batch_id,
        "query": query,
        "includePaths": include_paths,
        "limit": limit,
        "selectedCount": len(selected_notes),
        "selectedNotes": [
            {
                "path": note.get("path"),
                "title": note.get("title"),
                "modifiedAt": note.get("modifiedAt"),
                "selectionReasons": note.get("_selectionReasons", []),
            }
            for note in selected_notes
        ],
        "excludedPatternCount": len(exclude_patterns),
        "skippedByPatternSample": skipped[:20],
        "analysis": analysis,
    }
    if dry_run:
        return result

    ensure_second_brain_dirs()
    report_path = AI_REPORTS_DIR / f"{batch_id}_report.md"
    relations_path = AI_RELATIONS_DIR / f"{batch_id}_relation_map.md"
    insights_path = AI_INSIGHTS_DIR / f"{batch_id}_insight.md"
    manifest_path = AI_BATCHES_DIR / f"{batch_id}.json"
    report_path.write_text(build_second_brain_report_markdown(batch_id, selected_notes, analysis, query, include_paths), encoding="utf-8")
    relations_path.write_text(build_second_brain_relations_markdown(batch_id, analysis), encoding="utf-8")
    insights_path.write_text(build_second_brain_insight_markdown(batch_id, selected_notes, analysis), encoding="utf-8")
    hub_paths: list[str] = []
    for topic_row in analysis.get("topTopics", [])[:3]:
        topic = str(topic_row.get("topic", "")).strip()
        if not topic:
            continue
        hub_path = AI_HUBS_DIR / f"{safe_batch_slug(topic)}_hub.md"
        hub_path.write_text(build_second_brain_hub_markdown(topic, batch_id, selected_notes, analysis), encoding="utf-8")
        hub_paths.append(relative_note_path(hub_path))
    manifest_payload = {
        **result,
        "reportPath": relative_note_path(report_path),
        "relationsPath": relative_note_path(relations_path),
        "insightPath": relative_note_path(insights_path),
        "hubPaths": hub_paths,
        "generatedAt": now_jst_text(),
    }
    manifest_path.write_text(json.dumps(manifest_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    result.update(
        {
            "reportPath": relative_note_path(report_path),
            "relationsPath": relative_note_path(relations_path),
            "insightPath": relative_note_path(insights_path),
            "hubPaths": hub_paths,
            "manifestPath": relative_note_path(manifest_path),
            "generatedAt": now_jst_text(),
        }
    )
    return result


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

    second_brain = sub.add_parser("second-brain-batch")
    second_brain.add_argument("--query")
    second_brain.add_argument("--include-path", action="append", default=[])
    second_brain.add_argument("--limit", type=int, default=30)
    second_brain.add_argument("--batch-name")
    second_brain.add_argument("--exclude-patterns-path")
    second_brain.add_argument("--dry-run", action="store_true")
    second_brain.set_defaults(
        func=lambda args: second_brain_batch(
            query=args.query,
            include_paths=args.include_path,
            limit=args.limit,
            batch_name=args.batch_name,
            exclude_patterns_path=args.exclude_patterns_path,
            dry_run=args.dry_run,
        )
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.func(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
