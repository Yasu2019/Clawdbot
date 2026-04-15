#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests
from docker_runtime import docker_command


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "paperless_ingest_audit_status.json"
MARKDOWN_PATH = WORKSPACE / "paperless_ingest_audit_summary.md"
CONFIG_PATH = WORKSPACE / "paperless_ingest_config.json"
GATEWAY_CONTAINER = "clawstack-unified-clawdbot-gateway-1"
GATEWAY_STATE_PATH = "/home/node/clawd/ingest_watchdog_state.json"
DEFAULT_PAPERLESS_URL = "http://paperless:8000"
DEFAULT_PAPERLESS_TOKEN = "a451ceb5c13ac270faf3936405d207e4093ff580"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run(command: list[str], timeout_seconds: int = 60) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def parse_ingest_watchdog_config() -> tuple[str, str]:
    try:
        payload = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        url = str(payload.get("paperlessUrl") or DEFAULT_PAPERLESS_URL).strip()
        token = str(payload.get("paperlessToken") or DEFAULT_PAPERLESS_TOKEN).strip()
        if url and token:
            return url, token
    except Exception:
        pass
    return DEFAULT_PAPERLESS_URL, DEFAULT_PAPERLESS_TOKEN


def candidate_urls(base_url: str) -> list[str]:
    urls = [base_url.rstrip("/")]
    if "://paperless:" in base_url:
        urls.extend(
            [
                base_url.replace("://paperless:", "://127.0.0.1:").rstrip("/"),
                base_url.replace("://paperless:", "://localhost:").rstrip("/"),
                base_url.replace("://paperless:", "://host.docker.internal:").rstrip("/"),
            ]
        )
    if "://host.docker.internal:" in base_url:
        urls.extend(
            [
                base_url.replace("://host.docker.internal:", "://127.0.0.1:").rstrip("/"),
                base_url.replace("://host.docker.internal:", "://localhost:").rstrip("/"),
            ]
        )
    deduped: list[str] = []
    for item in urls:
        if item not in deduped:
            deduped.append(item)
    return deduped


def fetch_paperless_recent(base_url: str, token: str, limit: int) -> dict[str, Any]:
    headers = {"Authorization": f"Token {token}"}
    errors: list[str] = []
    for candidate in candidate_urls(base_url):
        url = f"{candidate}/api/documents/?page_size={limit}&ordering=-modified"
        try:
            resp = requests.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            payload = resp.json()
            recent = []
            for item in payload.get("results", []):
                recent.append(
                    {
                        "id": item.get("id"),
                        "title": item.get("title"),
                        "modified": item.get("modified"),
                        "created": item.get("created"),
                        "added": item.get("added"),
                    }
                )
            return {"count": payload.get("count"), "recent": recent, "apiBaseUrl": candidate}
        except Exception as exc:
            errors.append(f"{candidate}: {exc}")
    raise RuntimeError(" ; ".join(errors))


def fetch_gateway_processed_state() -> dict[str, Any]:
    script = (
        "python3 - <<'PY'\n"
        "import json\n"
        "from pathlib import Path\n"
        f"p=Path('{GATEWAY_STATE_PATH}')\n"
        "if not p.exists():\n"
        "    print(json.dumps({'exists': False}))\n"
        "    raise SystemExit(0)\n"
        "data=json.loads(p.read_text(encoding='utf-8'))\n"
        "processed=data.get('processed', {}) if isinstance(data, dict) else {}\n"
        "keys=sorted((int(k) for k in processed.keys()), reverse=True)\n"
        "tail=[]\n"
        "for key in keys[:20]:\n"
        "    item=processed.get(str(key), {})\n"
        "    tail.append({'id': key, 'title': item.get('title'), 'ts': item.get('ts'), 'chunks': item.get('chunks'), 'pdf_type': item.get('pdf_type')})\n"
        "print(json.dumps({'exists': True, 'processedCount': len(processed), 'processedIds': keys, 'maxProcessedId': (keys[0] if keys else None), 'recentProcessed': tail}, ensure_ascii=False))\n"
        "PY"
    )
    result = run(docker_command("exec", GATEWAY_CONTAINER, "sh", "-lc", script), timeout_seconds=120)
    if result.get("returncode") != 0:
        raise RuntimeError(result.get("stderr") or "failed to fetch gateway processed state")
    return json.loads(result.get("stdout") or "{}")


def write_markdown(payload: dict[str, Any]) -> None:
    recent_missing = payload.get("recentMissing") or []
    recent = payload.get("paperlessRecent", {}).get("recent") or []
    processed_recent = payload.get("gatewayProcessedState", {}).get("recentProcessed") or []
    lines = [
        "# Paperless Ingest Audit",
        "",
        f"Updated: {payload.get('updatedAt')}",
        "",
        f"- Status: `{payload.get('status')}`",
        f"- Paperless count: `{payload.get('paperlessRecent', {}).get('count')}`",
        f"- Processed count: `{payload.get('gatewayProcessedState', {}).get('processedCount')}`",
        f"- Max processed id: `{payload.get('gatewayProcessedState', {}).get('maxProcessedId')}`",
        f"- Recent missing ids: `{len(recent_missing)}`",
        "",
        "## Recent Missing",
    ]
    if recent_missing:
        for item in recent_missing:
            lines.append(f"- `{item.get('id')}` {item.get('title')}")
    else:
        lines.append("- none")
    lines.extend(["", "## Recent Paperless Docs"])
    if recent:
        for item in recent:
            lines.append(f"- `{item.get('id')}` {item.get('title')} ({item.get('modified') or item.get('created') or item.get('added')})")
    else:
        lines.append("- none")
    lines.extend(["", "## Recent Processed Docs"])
    if processed_recent:
        for item in processed_recent[:10]:
            lines.append(f"- `{item.get('id')}` {item.get('title')} ({item.get('ts')})")
    else:
        lines.append("- none")
    MARKDOWN_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Paperless document count vs ingest state.")
    parser.add_argument("--recent-limit", type=int, default=10)
    args = parser.parse_args()

    base_url, token = parse_ingest_watchdog_config()
    paperless_recent = fetch_paperless_recent(base_url, token, args.recent_limit)
    gateway_state = fetch_gateway_processed_state()
    processed_ids = {int(item) for item in gateway_state.get("processedIds") or []}

    recent_missing = [
        item
        for item in paperless_recent.get("recent", [])
        if item.get("id") is not None and int(item["id"]) not in processed_ids
    ]

    status = "healthy" if not recent_missing else "lagging"
    payload = {
        "updatedAt": now_jst_text(),
        "service": "paperless_ingest_audit",
        "status": status,
        "paperlessRecent": paperless_recent,
        "gatewayProcessedState": {
            "exists": gateway_state.get("exists"),
            "processedCount": gateway_state.get("processedCount"),
            "maxProcessedId": gateway_state.get("maxProcessedId"),
            "recentProcessed": gateway_state.get("recentProcessed"),
        },
        "recentMissing": recent_missing,
        "recentLimit": args.recent_limit,
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown(payload)
    print(json.dumps(payload, ensure_ascii=False))
    raise SystemExit(0 if status == "healthy" else 1)


if __name__ == "__main__":
    main()
