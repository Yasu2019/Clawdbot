#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
HELPER_WIN = WORKSPACE / "wsl_http_request_helper.py"
HELPER_WSL = "/mnt/d/Clawdbot_Docker_20260125/data/workspace/wsl_http_request_helper.py"
STATUS_PATH: Path | None = None
TARGET_BASE = "http://127.0.0.1:3003"
REQUEST_COUNT = 0


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    if STATUS_PATH is None:
        return
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class ReverseProxyHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def _handle(self) -> None:
        global REQUEST_COUNT
        REQUEST_COUNT += 1

        length = int(self.headers.get("Content-Length", "0") or "0")
        body = self.rfile.read(length) if length else b""
        headers = {}
        for key, value in self.headers.items():
            if key.lower() == "host":
                continue
            headers[key] = value

        target_url = f"{TARGET_BASE}{self.path}"
        command = [
            "wsl",
            "-d",
            "Ubuntu",
            "--",
            "python3",
            HELPER_WSL,
            "--method",
            self.command,
            "--url",
            target_url,
            "--headers-json",
            json.dumps(headers, ensure_ascii=False),
            "--body-base64",
            base64.b64encode(body).decode("ascii"),
            "--timeout",
            "30",
        ]

        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=60,
                check=True,
            )
            payload = json.loads(completed.stdout)
            raw_body = base64.b64decode(payload.get("body_base64", ""))
            self.send_response(payload["status"], payload.get("reason"))
            content_length_sent = False
            for key, value in payload.get("headers", []):
                key_lower = key.lower()
                if key_lower == "content-length":
                    content_length_sent = True
                if key_lower == "location" and value.startswith("http://127.0.0.1:3003"):
                    value = value.replace("http://127.0.0.1:3003", "http://127.0.0.1:3003")
                self.send_header(key, value)
            if not content_length_sent:
                self.send_header("Content-Length", str(len(raw_body)))
            self.end_headers()
            if raw_body:
                self.wfile.write(raw_body)
            write_status(
                {
                    "startedAt": getattr(self.server, "started_at", now_jst_text()),
                    "updatedAt": now_jst_text(),
                    "state": "running",
                    "pid": os.getpid(),
                    "listen": f"{self.server.server_address[0]}:{self.server.server_address[1]}",
                    "target": TARGET_BASE,
                    "acceptedRequests": REQUEST_COUNT,
                    "lastPath": self.path,
                    "lastStatus": payload["status"],
                }
            )
        except Exception as exc:
            error_text = str(exc)
            self.send_response(502, "Bad Gateway")
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(error_text.encode("utf-8", errors="replace"))
            write_status(
                {
                    "startedAt": getattr(self.server, "started_at", now_jst_text()),
                    "updatedAt": now_jst_text(),
                    "state": "error",
                    "pid": os.getpid(),
                    "listen": f"{self.server.server_address[0]}:{self.server.server_address[1]}",
                    "target": TARGET_BASE,
                    "acceptedRequests": REQUEST_COUNT,
                    "lastPath": self.path,
                    "lastError": error_text,
                }
            )

    def do_GET(self) -> None:
        self._handle()

    def do_POST(self) -> None:
        self._handle()

    def do_PUT(self) -> None:
        self._handle()

    def do_PATCH(self) -> None:
        self._handle()

    def do_DELETE(self) -> None:
        self._handle()

    def do_HEAD(self) -> None:
        self._handle()

    def log_message(self, _format: str, *_args: object) -> None:
        return


def main() -> int:
    parser = argparse.ArgumentParser(description="Windows reverse proxy into WSL HTTP service")
    parser.add_argument("--listen-host", default="127.0.0.1")
    parser.add_argument("--listen-port", type=int, required=True)
    parser.add_argument("--target-base", default="http://127.0.0.1:3003")
    parser.add_argument("--status-path", required=True)
    args = parser.parse_args()

    global STATUS_PATH, TARGET_BASE
    STATUS_PATH = Path(args.status_path)
    TARGET_BASE = args.target_base.rstrip("/")

    if not HELPER_WIN.exists():
        raise SystemExit(f"Missing helper script: {HELPER_WIN}")

    httpd = ThreadingHTTPServer((args.listen_host, args.listen_port), ReverseProxyHandler)
    httpd.started_at = now_jst_text()
    write_status(
        {
            "startedAt": httpd.started_at,
            "updatedAt": now_jst_text(),
            "state": "starting",
            "pid": os.getpid(),
            "listen": f"{args.listen_host}:{args.listen_port}",
            "target": TARGET_BASE,
            "acceptedRequests": 0,
        }
    )
    write_status(
        {
            "startedAt": httpd.started_at,
            "updatedAt": now_jst_text(),
            "state": "running",
            "pid": os.getpid(),
            "listen": f"{args.listen_host}:{args.listen_port}",
            "target": TARGET_BASE,
            "acceptedRequests": 0,
        }
    )
    httpd.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
