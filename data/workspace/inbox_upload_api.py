#!/usr/bin/env python3
"""
inbox_upload_api.py — Inbox ファイルアップロード API サーバー
=============================================================
Port 8099 で起動。Portal の inbox_uploader アプリから呼び出される。

Endpoints:
  POST /upload      — multipart/form-data でファイルをinboxへ保存
  GET  /status      — inbox の現在のファイル一覧 + 処理済み件数
  GET  /health      — ヘルスチェック
  DELETE /file/:name — inboxからファイルを削除
"""

import cgi
import json
import os
import shutil
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse, unquote

JST       = timezone(timedelta(hours=9))
INBOX_DIR = Path("/home/node/clawd/inbox")
PROC_DIR  = INBOX_DIR / "processed"
RAG_DIR   = Path("/home/node/clawd/rag_queue")
PORT      = 8099

# アップロード許可拡張子
ALLOWED_EXT = {
    ".pdf", ".xlsx", ".xls", ".csv", ".docx", ".doc",
    ".txt", ".md", ".json", ".yaml", ".yml", ".xml",
    ".png", ".jpg", ".jpeg", ".zip",
}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100 MB


def now_str() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

def log(msg: str):
    print(f"[{now_str()}] {msg}", flush=True)

def cors_headers() -> dict:
    return {
        "Access-Control-Allow-Origin":  "*",
        "Access-Control-Allow-Methods": "GET, POST, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }

def inbox_status() -> dict:
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    inbox_files = []
    for f in sorted(INBOX_DIR.iterdir()):
        if f.is_file() and not f.name.startswith("."):
            stat = f.stat()
            inbox_files.append({
                "name":      f.name,
                "size":      stat.st_size,
                "size_kb":   round(stat.st_size / 1024, 1),
                "modified":  datetime.fromtimestamp(stat.st_mtime, JST).strftime("%Y-%m-%d %H:%M"),
                "ext":       f.suffix.lower(),
            })

    proc_count = sum(
        1 for f in PROC_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ) if PROC_DIR.exists() else 0

    rag_count = sum(
        1 for f in RAG_DIR.iterdir()
        if f.is_file() and not f.name.startswith(".")
    ) if RAG_DIR.exists() else 0

    return {
        "inbox":          inbox_files,
        "inbox_count":    len(inbox_files),
        "processed_count": proc_count,
        "rag_queue_count": rag_count,
        "timestamp":      now_str(),
    }


class InboxHandler(BaseHTTPRequestHandler):

    def log_message(self, fmt, *args):
        log(fmt % args)

    def send_json(self, code: int, data: dict):
        body = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def do_GET(self):
        path = urlparse(self.path).path

        if path == "/health":
            self.send_json(200, {"status": "ok", "timestamp": now_str()})

        elif path == "/status":
            self.send_json(200, inbox_status())

        else:
            self.send_json(404, {"error": "Not found"})

    def do_DELETE(self):
        path = urlparse(self.path).path
        if path.startswith("/file/"):
            fname = unquote(path[len("/file/"):])
            # セキュリティ: パストラバーサル防止
            fname = Path(fname).name
            target = INBOX_DIR / fname
            if target.exists() and target.is_file():
                target.unlink()
                log(f"Deleted: {fname}")
                self.send_json(200, {"deleted": fname})
            else:
                self.send_json(404, {"error": f"{fname} not found in inbox"})
        else:
            self.send_json(404, {"error": "Not found"})

    def do_POST(self):
        path = urlparse(self.path).path

        if path != "/upload":
            self.send_json(404, {"error": "Not found"})
            return

        # Content-Length チェック
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length > MAX_FILE_SIZE:
            self.send_json(413, {"error": f"File too large (max {MAX_FILE_SIZE // 1024 // 1024}MB)"})
            return

        # multipart/form-data パース
        content_type = self.headers.get("Content-Type", "")
        if "multipart/form-data" not in content_type:
            self.send_json(400, {"error": "multipart/form-data required"})
            return

        try:
            form = cgi.FieldStorage(
                fp=self.rfile,
                headers=self.headers,
                environ={
                    "REQUEST_METHOD": "POST",
                    "CONTENT_TYPE":   content_type,
                    "CONTENT_LENGTH": str(content_length),
                },
            )
        except Exception as e:
            self.send_json(400, {"error": f"Form parse error: {e}"})
            return

        saved = []
        errors = []

        files_field = form["files"] if "files" in form else None
        if files_field is None:
            self.send_json(400, {"error": "No 'files' field in form"})
            return

        # 単一ファイルもリスト化
        items = files_field if isinstance(files_field, list) else [files_field]

        INBOX_DIR.mkdir(parents=True, exist_ok=True)

        for item in items:
            if not item.filename:
                continue

            fname = Path(item.filename).name  # パストラバーサル防止
            ext   = Path(fname).suffix.lower()

            if ext not in ALLOWED_EXT:
                errors.append({"file": fname, "error": f"Extension {ext} not allowed"})
                continue

            # 重複回避
            dest = INBOX_DIR / fname
            if dest.exists():
                stem = Path(fname).stem
                dest = INBOX_DIR / f"{stem}_{int(time.time())}{ext}"

            try:
                data = item.file.read()
                if len(data) > MAX_FILE_SIZE:
                    errors.append({"file": fname, "error": "File too large"})
                    continue
                with open(dest, "wb") as f:
                    f.write(data)
                size_kb = round(len(data) / 1024, 1)
                log(f"Saved to inbox: {dest.name} ({size_kb} KB)")
                saved.append({"name": dest.name, "size_kb": size_kb})
            except Exception as e:
                errors.append({"file": fname, "error": str(e)})

        if saved:
            self.send_json(200, {
                "saved":  saved,
                "errors": errors,
                "message": f"{len(saved)} file(s) saved to inbox. OpenClaw will process shortly.",
            })
        else:
            self.send_json(400, {"saved": [], "errors": errors, "message": "No files saved."})


def main():
    INBOX_DIR.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", PORT), InboxHandler)
    log(f"Inbox Upload API listening on port {PORT}")
    log(f"Inbox dir: {INBOX_DIR}")
    server.serve_forever()


if __name__ == "__main__":
    main()
