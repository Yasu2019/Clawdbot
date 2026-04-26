#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATE_PATH = WORKSPACE / "ingest_watchdog_state.json"
OUTPUT_PATH = WORKSPACE / "paperless_pdf_benchmark.json"
MOJIBAKE_REPLACEMENTS = {
    "蟷ｴ": "年",
    "譛亥ｺｦ": "月度",
    "譛・": "月",
    "譛": "月",
    "縲": " ",
    "\u3000": " ",
    "謌先棡蝣ｱ蜻頑嶌": "成果報告書",
    "蝣ｱ蜻頑嶌": "報告書",
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


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"processed": {}}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build manual benchmark sheet for Paperless PDF ingestion.")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    state = load_state()
    processed = state.get("processed", {})
    rows = []
    for doc_id, meta in processed.items():
        rows.append(
            {
                "paperless_id": doc_id,
                "title": normalize_display_text(meta.get("title", "")),
                "raw_title": meta.get("title", ""),
                "pdf_type": meta.get("pdf_type", "unknown"),
                "pages": meta.get("pages"),
                "chunks": meta.get("chunks"),
                "processed_at": meta.get("ts"),
                "text_acceptable": None,
                "figure_summary_useful": None,
                "figure_asset_present": None,
                "caption_acceptable": None,
                "table_detection_acceptable": None,
                "review_notes": "",
            }
        )

    rows.sort(key=lambda item: item.get("processed_at") or "", reverse=True)
    payload = {
        "generatedAt": now_jst_text(),
        "service": "paperless_pdf_benchmark",
        "limit": args.limit,
        "items": rows[: max(1, args.limit)],
        "reviewFields": [
            "text_acceptable",
            "figure_summary_useful",
            "figure_asset_present",
            "caption_acceptable",
            "table_detection_acceptable",
            "review_notes",
        ],
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"output": str(OUTPUT_PATH), "count": len(payload["items"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
