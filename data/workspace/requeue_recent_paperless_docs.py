#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATE_PATH = WORKSPACE / "ingest_watchdog_state.json"
STATUS_PATH = WORKSPACE / "requeue_recent_paperless_docs_status.json"
PAPERLESS_CANDIDATES = [
    "http://paperless:8000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
]
PAPERLESS_TOKEN = "a451ceb5c13ac270faf3936405d207e4093ff580"
HEADERS = {"Authorization": f"Token {PAPERLESS_TOKEN}"}


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"processed": {}}


def save_state(state: dict) -> None:
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def fetch_recent_docs(limit: int) -> tuple[str, list[dict]]:
    last_error = None
    for base_url in PAPERLESS_CANDIDATES:
        try:
            resp = requests.get(
                f"{base_url}/api/documents/?page_size={max(1, limit)}&ordering=-id",
                headers=HEADERS,
                timeout=60,
            )
            resp.raise_for_status()
            return base_url, resp.json().get("results", [])
        except Exception as exc:
            last_error = exc
    raise RuntimeError(str(last_error))


def main() -> None:
    parser = argparse.ArgumentParser(description="Requeue recent Paperless docs for re-ingest.")
    parser.add_argument("--limit", type=int, default=20)
    args = parser.parse_args()

    state = load_state()
    processed = state.setdefault("processed", {})
    base_url, docs = fetch_recent_docs(args.limit)

    removed = []
    for doc in docs:
        doc_id = str(doc["id"])
        if doc_id in processed:
            removed.append({"id": doc_id, "title": processed[doc_id].get("title") or doc.get("title", "")})
            processed.pop(doc_id, None)

    save_state(state)
    payload = {
        "generatedAt": now_jst_text(),
        "paperlessBaseUrl": base_url,
        "limit": args.limit,
        "removedCount": len(removed),
        "removed": removed,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    main()
