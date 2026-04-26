#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATE_PATH = WORKSPACE / "ingest_watchdog_state.json"
JSON_OUTPUT_PATH = WORKSPACE / "paperless_pdf_review_report.json"
MD_OUTPUT_PATH = WORKSPACE / "paperless_pdf_review_report.md"
CACHE_PATH = WORKSPACE / "paperless_pdf_review_cache.json"
CACHE_VERSION = 2

QDRANT_URL = os.getenv("QDRANT_URL", "http://qdrant:6333")
COLLECTION = os.getenv("PAPERLESS_COLLECTION", "universal_knowledge")
MOJIBAKE_REPLACEMENTS = {
    "蟷ｴ": "年",
    "譛亥ｺｦ": "月度",
    "譛・": "月",
    "譛": "月",
    "縲": " ",
    "\u3000": " ",
    "謌先棡蝣ｱ蜻頑嶌": "成果報告書",
    "蝣ｱ蜻頑嶌": "報告書",
    "騾｣": "",
    "謨ｴ": "",
}


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def mojibake_score(text: str) -> int:
    value = text or ""
    return sum(value.count(token) for token in ("縲", "繝", "蜻", "蟷", "譛", "蝣", "讒", "�"))


def normalize_display_text(text: str) -> str:
    value = (text or "").strip()
    if not value:
        return ""
    if "IATF16949" in value:
        ym = re.search(r"(20\d{2}).*?(\d{1,2})", value)
        if ym:
            year, month = ym.groups()
            return f"{year}年{int(month)}月度 IATF16949 成果報告書"
    cleaned = value
    for old, new in MOJIBAKE_REPLACEMENTS.items():
        cleaned = cleaned.replace(old, new)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if "IATF16949" in cleaned and "成果報告書" in cleaned:
        cleaned = re.sub(r"(\d{4})年(\d{1,2})月(?:度)?", r"\1年\2月度", cleaned)
    if mojibake_score(cleaned) > mojibake_score(value):
        return value
    return cleaned


def normalize_caption_display(text: str) -> str:
    value = normalize_display_text(text)
    if not value:
        return ""
    trimmed = re.sub(r"^[・●\-\s]+", "", value).strip()
    if len(trimmed) <= 2:
        return ""
    if trimmed in {"整", "表", "図", "グラフ"}:
        return ""
    if ("JQA" in trimmed or "IATF" in trimmed) and len(trimmed) <= 120:
        trimmed = trimmed.replace(" 、", "、").replace(" 。", "。")
        trimmed = re.sub(r"\s+", " ", trimmed).strip()
    return trimmed


def qdrant_candidates() -> list[str]:
    seen: list[str] = []
    for item in (
        QDRANT_URL,
        "http://qdrant:6333",
        "http://host.docker.internal:6333",
        "http://127.0.0.1:6333",
        "http://localhost:6333",
    ):
        value = (item or "").strip()
        if value and value not in seen:
            seen.append(value)
    return seen


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"processed": {}}


def load_cache() -> dict:
    try:
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"items": {}}


def save_cache(cache: dict) -> None:
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")


def iter_recent_docs(limit: int) -> list[tuple[str, dict]]:
    state = load_state()
    processed = list((state.get("processed") or {}).items())
    processed.sort(key=lambda item: item[1].get("ts") or "", reverse=True)
    return processed[: max(1, limit)]


def scroll_doc_payloads(doc_id: str) -> tuple[list[dict], str | None]:
    body = {
        "limit": 256,
        "with_payload": True,
        "with_vector": False,
        "filter": {
            "must": [
                {
                    "key": "paperless_id",
                    "match": {"value": int(doc_id)},
                }
            ]
        },
    }
    errors: list[str] = []
    for base in qdrant_candidates():
        try:
            response = requests.post(
                f"{base}/collections/{COLLECTION}/points/scroll",
                json=body,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json().get("result", {})
            points = data.get("points") or []
            payloads = []
            for point in points:
                payload = point.get("payload") or {}
                if payload.get("paperless_id") == int(doc_id):
                    payloads.append(payload)
            return payloads, base
        except Exception as exc:
            errors.append(f"{base}: {exc}")
    raise RuntimeError(" | ".join(errors))


def summarize_doc(doc_id: str, meta: dict) -> dict:
    payloads, qdrant_base = scroll_doc_payloads(doc_id)
    item_counts = Counter()
    page_item_counts: dict[int, list[str]] = defaultdict(list)
    captions: list[dict] = []
    assets = 0
    caption_confidence = Counter()
    table_pages: list[dict] = []

    for payload in payloads:
        item_type = payload.get("item_type") or "unknown"
        item_counts[item_type] += 1
        page_no = int(payload.get("page") or 0)
        if page_no:
            page_item_counts[page_no].append(item_type)
        if payload.get("source_asset_path"):
            assets += 1
        caption = (payload.get("nearby_caption") or "").strip()
        caption = normalize_caption_display(caption)
        if caption:
            captions.append(
                {
                    "page": page_no,
                    "caption": caption,
                    "raw_caption": (payload.get("nearby_caption") or "").strip(),
                    "confidence": payload.get("caption_confidence") or "",
                }
            )
            caption_confidence[payload.get("caption_confidence") or "unknown"] += 1
        if payload.get("table_like"):
            table_pages.append(
                {
                    "page": page_no,
                    "table_score": payload.get("table_score"),
                    "numeric_heavy_lines": payload.get("numeric_heavy_lines"),
                }
            )

    prioritized_pages = []
    for page_no in sorted(page_item_counts):
        page_types = sorted(set(page_item_counts[page_no]))
        if "figure_rich_page" in page_types or "table_rich_page" in page_types:
            prioritized_pages.append({"page": page_no, "item_types": page_types})

    return {
        "paperless_id": doc_id,
        "title": normalize_display_text(meta.get("title", "")),
        "raw_title": meta.get("title", ""),
        "processed_at": meta.get("ts"),
        "pdf_type": meta.get("pdf_type", "unknown"),
        "pages": meta.get("pages"),
        "chunks": meta.get("chunks"),
        "qdrant_endpoint": qdrant_base,
        "item_type_counts": dict(item_counts),
        "asset_count": assets,
        "caption_confidence_counts": dict(caption_confidence),
        "captions": captions[:8],
        "table_pages": table_pages[:8],
        "priority_pages": prioritized_pages[:12],
    }


def render_markdown(items: list[dict], qdrant_endpoint: str | None) -> str:
    lines = [
        "# Paperless PDF Review Report",
        "",
        f"- Generated: {now_jst_text()}",
        f"- Collection: `{COLLECTION}`",
        f"- Qdrant endpoint: `{qdrant_endpoint or 'unresolved'}`",
        "",
    ]
    for item in items:
        lines.append(f"## {item['paperless_id']} - {item['title']}")
        lines.append("")
        if item.get("raw_title") and item.get("raw_title") != item.get("title"):
            lines.append(f"- Raw title: `{item.get('raw_title')}`")
        lines.append(f"- PDF type: `{item.get('pdf_type')}`")
        lines.append(f"- Pages / chunks: `{item.get('pages')}` / `{item.get('chunks')}`")
        lines.append(f"- Processed at: `{item.get('processed_at')}`")
        lines.append(f"- Asset count: `{item.get('asset_count')}`")
        lines.append(f"- Item types: `{json.dumps(item.get('item_type_counts', {}), ensure_ascii=False)}`")
        lines.append(f"- Caption confidence: `{json.dumps(item.get('caption_confidence_counts', {}), ensure_ascii=False)}`")
        if item.get("priority_pages"):
            lines.append("- Priority pages:")
            for page in item["priority_pages"][:5]:
                lines.append(f"  - page {page['page']}: {', '.join(page['item_types'])}")
        if item.get("captions"):
            lines.append("- Sample captions:")
            for cap in item["captions"][:3]:
                lines.append(f"  - p{cap['page']} [{cap['confidence']}]: {cap['caption'][:140]}")
                if cap.get("raw_caption") and cap.get("raw_caption") != cap.get("caption"):
                    lines.append(f"    raw: {cap['raw_caption'][:140]}")
        if item.get("table_pages"):
            lines.append("- Table-like pages:")
            for page in item["table_pages"][:3]:
                lines.append(
                    f"  - p{page['page']}: table_score={page.get('table_score')} numeric_heavy_lines={page.get('numeric_heavy_lines')}"
                )
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a review report for recently ingested Paperless PDFs.")
    parser.add_argument("--limit", type=int, default=12)
    args = parser.parse_args()

    docs = iter_recent_docs(args.limit)
    cache = load_cache()
    cache_items = cache.get("items") or {}
    items = []
    qdrant_endpoint = None
    errors = []
    for doc_id, meta in docs:
        try:
            cache_entry = cache_items.get(str(doc_id)) or {}
            cache_key = {
                "processed_at": meta.get("ts"),
                "title": meta.get("title", ""),
                "pdf_type": meta.get("pdf_type", "unknown"),
                "pages": meta.get("pages"),
                "chunks": meta.get("chunks"),
            }
            if (
                cache_entry.get("cache_version") == CACHE_VERSION
                and cache_entry.get("cache_key") == cache_key
                and cache_entry.get("item")
            ):
                item = cache_entry["item"]
            else:
                item = summarize_doc(doc_id, meta)
                cache_items[str(doc_id)] = {
                    "cache_version": CACHE_VERSION,
                    "cache_key": cache_key,
                    "item": item,
                }
            qdrant_endpoint = qdrant_endpoint or item.get("qdrant_endpoint")
            items.append(item)
        except Exception as exc:
            errors.append({"paperless_id": doc_id, "title": meta.get("title", ""), "error": str(exc)})

    payload = {
        "generatedAt": now_jst_text(),
        "collection": COLLECTION,
        "qdrantEndpoint": qdrant_endpoint,
        "count": len(items),
        "items": items,
        "errors": errors,
    }
    JSON_OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    MD_OUTPUT_PATH.write_text(render_markdown(items, qdrant_endpoint), encoding="utf-8")
    cache["items"] = cache_items
    cache["cacheVersion"] = CACHE_VERSION
    cache["updatedAt"] = now_jst_text()
    save_cache(cache)
    print(json.dumps({"json": str(JSON_OUTPUT_PATH), "markdown": str(MD_OUTPUT_PATH), "count": len(items), "errors": len(errors)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
