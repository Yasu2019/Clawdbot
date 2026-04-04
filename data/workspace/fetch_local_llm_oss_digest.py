#!/usr/bin/env python3
from __future__ import annotations

import email.utils
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from html import unescape
from pathlib import Path
from typing import Iterable


JST = timezone(timedelta(hours=9))
UTC = timezone.utc
USER_AGENT = "Mozilla/5.0 (compatible; ClawdbotScout/1.0; +https://example.invalid)"
WORKSPACE = Path(__file__).absolute().parent
STATUS_PATH = WORKSPACE / "local_llm_oss_scout_status.json"
JSON_PATH = WORKSPACE / "local_llm_oss_digest.json"
MD_PATH = WORKSPACE / "local_llm_oss_digest.md"


@dataclass(frozen=True)
class SourceConfig:
    category: str
    source: str
    kind: str
    url: str
    include_pattern: str | None = None
    limit: int = 5


SOURCES: list[SourceConfig] = [
    SourceConfig("Local LLM", "Ollama Blog", "html_links", "https://ollama.com/blog", include_pattern=r"/blog/"),
    SourceConfig("Local LLM", "LM Studio Blog", "html_links", "https://lmstudio.ai/blog", include_pattern=r"/blog/"),
    SourceConfig("Local LLM", "Hugging Face Blog", "rss", "https://huggingface.co/blog/feed.xml"),
    SourceConfig("Local LLM", "llama.cpp Releases", "atom", "https://github.com/ggml-org/llama.cpp/releases.atom"),
    SourceConfig("Local LLM", "vLLM Releases", "atom", "https://github.com/vllm-project/vllm/releases.atom"),
    SourceConfig("Productivity OSS", "n8n Releases", "atom", "https://github.com/n8n-io/n8n/releases.atom"),
    SourceConfig("Productivity OSS", "AppFlowy Releases", "atom", "https://github.com/AppFlowy-IO/AppFlowy/releases.atom"),
    SourceConfig("Productivity OSS", "Plane Releases", "atom", "https://github.com/makeplane/plane/releases.atom"),
    SourceConfig("Productivity OSS", "Twenty Releases", "atom", "https://github.com/twentyhq/twenty/releases.atom"),
    SourceConfig("Productivity OSS", "Docmost Releases", "atom", "https://github.com/docmost/docmost/releases.atom"),
]


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def parse_datetime(raw: str | None) -> str | None:
    if not raw:
        return None
    raw = raw.strip()
    if not raw:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(raw)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(JST).isoformat()
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d"):
        try:
            dt = datetime.strptime(raw, fmt)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            return dt.astimezone(JST).isoformat()
        except Exception:
            continue
    return None


def extract_rss_items(url: str, limit: int) -> list[dict]:
    raw = fetch_text(url)
    root = ET.fromstring(raw)
    items: list[dict] = []
    for item in root.findall(".//item")[:limit]:
        title = clean_text(item.findtext("title", default=""))
        link = clean_text(item.findtext("link", default=""))
        published = parse_datetime(item.findtext("pubDate", default="") or item.findtext("published", default=""))
        if title and link:
            items.append({"title": title, "url": link, "published": published})
    return items


def extract_atom_items(url: str, limit: int) -> list[dict]:
    raw = fetch_text(url)
    root = ET.fromstring(raw)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    items: list[dict] = []
    for entry in root.findall("atom:entry", ns)[:limit]:
        title = clean_text(entry.findtext("atom:title", default="", namespaces=ns))
        link = ""
        for link_node in entry.findall("atom:link", ns):
            href = link_node.attrib.get("href", "").strip()
            if href:
                link = href
                break
        published = parse_datetime(
            entry.findtext("atom:updated", default="", namespaces=ns)
            or entry.findtext("atom:published", default="", namespaces=ns)
        )
        if title and link:
            items.append({"title": title, "url": link, "published": published})
    return items


def extract_homepage_links(url: str, include_pattern: str | None, limit: int) -> list[dict]:
    html = fetch_text(url)
    title_map: dict[str, str] = {}
    for match in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", html, flags=re.I | re.S):
        href = match.group(1).strip()
        label = clean_text(match.group(2))
        if href.startswith("/"):
            href = urllib.request.urljoin(url, href)
        if not href.startswith("http"):
            continue
        if include_pattern and not re.search(include_pattern, href, flags=re.I):
            continue
        if any(block in href for block in (".png", ".jpg", ".svg", "/cdn-cgi/", "mailto:", "#")):
            continue
        if href not in title_map and label:
            title_map[href] = label
        if len(title_map) >= limit:
            break
    return [{"title": title, "url": href, "published": None} for href, title in title_map.items()]


def fetch_source(source: SourceConfig) -> dict:
    if source.kind == "rss":
        items = extract_rss_items(source.url, source.limit)
    elif source.kind == "atom":
        items = extract_atom_items(source.url, source.limit)
    elif source.kind == "html_links":
        items = extract_homepage_links(source.url, source.include_pattern, source.limit)
    else:
        raise ValueError(f"Unsupported source kind: {source.kind}")
    return {
        "category": source.category,
        "source": source.source,
        "kind": source.kind,
        "url": source.url,
        "status": "ok",
        "items": [item for item in items if keep_item(source, item)],
    }


def keep_item(source: SourceConfig, item: dict) -> bool:
    title = (item.get("title") or "").strip().lower()
    url = (item.get("url") or "").strip().lower()
    if not title or not url:
        return False
    if source.source == "n8n Releases" and (title in {"v1", "beta", "stable"} or "/tag/v1" in url):
        return False
    if "/tag/beta" in url or "/tag/stable" in url:
        return False
    return True


def iter_all_items(source_results: Iterable[dict]) -> Iterable[dict]:
    for result in source_results:
        for item in result.get("items", []):
            merged = dict(item)
            merged["source"] = result.get("source")
            merged["category"] = result.get("category")
            yield merged


def dt_from_iso(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except Exception:
        return None


def build_digest(source_results: list[dict], days: int, limit: int) -> dict:
    window_start = now_jst() - timedelta(days=days)
    category_rows: dict[str, list[dict]] = {}
    for category in sorted({source.category for source in SOURCES}):
        rows: list[dict] = []
        for item in iter_all_items(result for result in source_results if result.get("category") == category):
            published_dt = dt_from_iso(item.get("published"))
            freshness = "fresh" if published_dt and published_dt >= window_start else "reference"
            rows.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "published": item.get("published"),
                    "freshness": freshness,
                    "source": item.get("source"),
                }
            )
        rows.sort(key=lambda row: row.get("published") or "", reverse=True)
        fresh_rows = [row for row in rows if row.get("freshness") == "fresh"]
        candidate_rows = fresh_rows or rows
        picked: list[dict] = []
        used_sources: set[str] = set()
        for row in candidate_rows:
            source = row.get("source") or ""
            if source in used_sources:
                continue
            picked.append(row)
            used_sources.add(source)
            if len(picked) >= limit:
                break
        if len(picked) < limit:
            for row in rows:
                source = row.get("source") or ""
                if source in used_sources:
                    continue
                marker = (row.get("source"), row.get("title"), row.get("url"))
                if any((item.get("source"), item.get("title"), item.get("url")) == marker for item in picked):
                    continue
                picked.append(row)
                used_sources.add(source)
                if len(picked) >= limit:
                    break
        if len(picked) < limit:
            for row in rows:
                marker = (row.get("source"), row.get("title"), row.get("url"))
                if any((item.get("source"), item.get("title"), item.get("url")) == marker for item in picked):
                    continue
                picked.append(row)
                if len(picked) >= limit:
                    break
        category_rows[category] = picked[:limit]
    return {
        "generatedAt": now_jst_text(),
        "windowDays": days,
        "sourcesChecked": len(source_results),
        "categories": category_rows,
        "sourceResults": source_results,
        "policy": {
            "paidApiUsed": False,
            "summaryMode": "deterministic_public_sources_only",
            "allowedInputs": ["public_rss", "public_homepages", "public_github_release_atom"],
        },
    }


def render_markdown(payload: dict) -> str:
    lines = [
        f"# Local LLM / OSS Scout ({payload['generatedAt']})",
        "",
        f"- Window: last {payload['windowDays']} day(s)",
        "- Policy: no paid API, no cloud LLM, public RSS/homepage/release feeds only",
        "",
    ]
    for category, rows in payload.get("categories", {}).items():
        lines.append(f"## {category}")
        if not rows:
            lines.append("- No items found")
            lines.append("")
            continue
        for row in rows:
            prefix = row["published"][:10] if row.get("published") else "reference"
            lines.append(f"- [{prefix}] {row['title']}")
            lines.append(f"  {row['source']}")
            lines.append(f"  {row['url']}")
        lines.append("")
    lines.append("## Source Health")
    for result in payload.get("sourceResults", []):
        lines.append(f"- {result['source']}: {result['status']} ({len(result.get('items', []))} items)")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def main() -> int:
    status = {"startedAt": now_jst_text(), "stage": "collecting"}
    write_status(status)
    source_results: list[dict] = []
    for source in SOURCES:
        try:
            source_results.append(fetch_source(source))
        except Exception as exc:
            source_results.append(
                {
                    "category": source.category,
                    "source": source.source,
                    "kind": source.kind,
                    "url": source.url,
                    "status": f"error: {exc}",
                    "items": [],
                }
            )
    payload = build_digest(source_results, days=7, limit=5)
    JSON_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_PATH.write_text(render_markdown(payload), encoding="utf-8")
    status.update(
        {
            "finishedAt": now_jst_text(),
            "stage": "completed",
            "jsonPath": str(JSON_PATH),
            "markdownPath": str(MD_PATH),
            "sourcesChecked": payload["sourcesChecked"],
            "categoryCounts": {key: len(value) for key, value in payload["categories"].items()},
            "errorSources": [result["source"] for result in source_results if str(result.get("status", "")).startswith("error:")],
        }
    )
    write_status(status)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="ignore")
    except Exception:
        pass
    raise SystemExit(main())
