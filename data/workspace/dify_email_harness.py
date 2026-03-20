#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
STATE_DIR = REPO_ROOT / "data" / "state" / "dify_email_harness"
STATUS_FILE = STATE_DIR / "harness_status.json"
SCRIPT_PATH = REPO_ROOT / "data" / "workspace" / "email_search_query.py"
DB_PATH = REPO_ROOT / "data" / "workspace" / "email_search.db"
HOST = "127.0.0.1"
PORT = 8787


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def write_status(state: str, **extra: object) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "service": "dify_email_harness",
        "updatedAt": now_iso(),
        "pid": os.getpid(),
        "state": state,
        "host": HOST,
        "port": PORT,
        **extra,
    }
    STATUS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def query_email_context(query: str, limit: int = 3) -> dict:
    cmd = [
        sys.executable,
        str(SCRIPT_PATH),
        "--db",
        str(DB_PATH),
        "context",
        query,
        "--limit",
        str(limit),
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
        check=True,
    )
    return json.loads(completed.stdout or "{}")


def build_summary(payload: dict) -> str:
    results = payload.get("results") or []
    query = str(payload.get("query") or "").strip()
    if not results:
        return f"メール検索結果は見つかりませんでした。対象条件を具体化してください。\n問い合わせ: {query}"

    lines = ["ローカルメール検索の要約です。"]
    for index, row in enumerate(results[:3], start=1):
        date_text = str(row.get("email_date") or "日付不明")
        sender = str(row.get("sender") or "送信者不明").replace("\n", " ").strip()
        subject = str(row.get("subject") or "(件名なし)").replace("\n", " ").strip()
        snippet = " ".join(str(row.get("snippet") or "").split())
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        lines.append(f"{index}. {date_text} | {sender} | {subject}")
        if snippet:
            lines.append(f"   {snippet}")

    if payload.get("fallback_kind") == "recent":
        lines.append("条件一致が弱かったため、直近メールから候補を提示しました。")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    server_version = "DifyEmailHarness/1.0"

    def _json(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._json(200, {"status": "ok", "service": "dify_email_harness"})
            return
        self._json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if self.path != "/summarize_email":
            self._json(404, {"error": "not_found"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length) if length > 0 else b"{}"
            data = json.loads(raw.decode("utf-8"))
            query = str(data.get("query") or "").strip()
            limit = max(1, min(5, int(data.get("limit") or 3)))
            if not query:
                self._json(400, {"error": "query_required"})
                return

            write_status("processing", lastQuery=query)
            payload = query_email_context(query, limit=limit)
            summary = build_summary(payload)
            response = {
                "query": query,
                "result_count": int(payload.get("result_count") or 0),
                "fallback_kind": payload.get("fallback_kind") or "search",
                "summary": summary,
                "results": payload.get("results") or [],
            }
            write_status("idle", lastQuery=query, lastResultCount=response["result_count"])
            self._json(200, response)
        except subprocess.TimeoutExpired:
            write_status("timeout")
            self._json(504, {"error": "timeout"})
        except Exception as exc:
            write_status("error", lastError=str(exc))
            self._json(500, {"error": str(exc)})

    def log_message(self, format: str, *args) -> None:
        return


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    write_status("starting")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    write_status("idle")
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
