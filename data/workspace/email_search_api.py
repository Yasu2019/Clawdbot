#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
email_search_api.py

メール全文検索 API サーバー（ポート 8792）
email_search.db の FTS テーブルを使って高速検索する。

起動:
  python3 data/workspace/email_search_api.py
"""
from __future__ import annotations

import json
import re
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DB_CANDIDATES = [
    WORKSPACE / "email_search.db",
    Path("/home/node/clawd/email_search.db"),
]
PID_PATH = WORKSPACE / "email_search_api.pid"
HOST = "127.0.0.1"
PORT = 8792
DEFAULT_LIMIT = 20


def find_db() -> Path:
    for p in DB_CANDIDATES:
        if p.exists():
            return p
    raise FileNotFoundError(f"email_search.db not found in {DB_CANDIDATES}")


DB_PATH = find_db()


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=15)
    con.row_factory = sqlite3.Row
    return con


# ── ヘルパー ──────────────────────────────────────────────────

GARBLED = ("\x1b", "縺", "繧", "荳", "譛", "�")


def is_garbled(text: str) -> bool:
    return any(c in text for c in GARBLED)


def clean(text: str | None, max_len: int = 100) -> str:
    t = re.sub(r"\s+", " ", text or "").strip()
    if not t:
        return ""
    if is_garbled(t):
        return "[文字化け]"
    return t[:max_len]


def due_label(due_date: str) -> str:
    if not due_date:
        return ""
    try:
        due = date.fromisoformat(due_date)
        delta = (due - date.today()).days
        if delta < 0:
            return f"🔴 期限切れ({abs(delta)}日)"
        if delta == 0:
            return "🟠 今日"
        if delta <= 3:
            return f"🟡 残{delta}日"
        return f"残{delta}日"
    except ValueError:
        return ""


# ── 検索ロジック ──────────────────────────────────────────────

def search_emails(query: str, limit: int = DEFAULT_LIMIT) -> list[dict]:
    con = connect()
    try:
        # FTS 検索
        try:
            rows = con.execute(
                """
                SELECT e.source, e.source_id, e.subject, e.sender,
                       e.email_date, e.category, e.person, e.snippet,
                       bm25(emails_fts) AS score
                FROM emails_fts
                JOIN emails e ON e.rowid = emails_fts.rowid
                WHERE emails_fts MATCH ?
                ORDER BY score
                LIMIT ?
                """,
                (query, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            rows = []

        # フォールバック: LIKE 検索
        if not rows:
            needle = f"%{query}%"
            rows = con.execute(
                """
                SELECT source, source_id, subject, sender,
                       email_date, category, person, snippet,
                       0.0 AS score
                FROM emails
                WHERE subject LIKE ? OR sender LIKE ? OR body_text LIKE ?
                ORDER BY internal_ts DESC
                LIMIT ?
                """,
                (needle, needle, needle, limit),
            ).fetchall()

        result = []
        for r in rows:
            result.append({
                "source": r["source"],
                "source_id": r["source_id"],
                "subject": clean(r["subject"], 120),
                "sender": clean(r["sender"], 60),
                "email_date": r["email_date"] or "",
                "category": r["category"] or "",
                "person": r["person"] or "",
                "snippet": clean(r["snippet"], 200),
            })
        return result
    finally:
        con.close()


def search_tasks(
    query: str,
    status: str = "",
    overdue: bool = False,
    limit: int = DEFAULT_LIMIT,
) -> list[dict]:
    con = connect()
    try:
        clauses: list[str] = []
        params: list = []

        if status in ("open", "replied"):
            clauses.append("status = ?")
            params.append(status)

        if overdue:
            clauses.append("due_date <> '' AND due_date < date('now','localtime')")

        if query.strip():
            needle = f"%{query}%"
            clauses.append(
                "(request_subject LIKE ? OR request_body LIKE ? OR requester LIKE ? OR request_summary LIKE ?)"
            )
            params.extend([needle, needle, needle, needle])

        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        params.append(limit)

        rows = con.execute(
            f"""
            SELECT source, source_id, request_date, due_date,
                   requester, assignee, request_subject,
                   request_body, request_summary, status,
                   reply_status, replier, reply_summary
            FROM tasks
            {where}
            ORDER BY
                CASE WHEN due_date='' THEN 1 ELSE 0 END,
                due_date ASC,
                request_date DESC
            LIMIT ?
            """,
            params,
        ).fetchall()

        result = []
        for r in rows:
            summary = r["request_summary"] or clean(r["request_body"], 160)
            result.append({
                "source": r["source"],
                "source_id": r["source_id"],
                "request_date": r["request_date"] or "",
                "due_date": r["due_date"] or "",
                "due_label": due_label(r["due_date"] or ""),
                "requester": clean(r["requester"], 50),
                "assignee": r["assignee"] or "",
                "subject": clean(r["request_subject"], 120),
                "summary": summary,
                "status": r["status"] or "",
                "reply_status": r["reply_status"] or "",
                "replier": clean(r["replier"], 40),
                "reply_summary": clean(r["reply_summary"], 160),
            })
        return result
    finally:
        con.close()


def get_stats() -> dict:
    con = connect()
    try:
        total_emails = con.execute("SELECT COUNT(*) FROM emails").fetchone()[0]
        total_tasks = con.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        cached = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE request_summary != ''"
        ).fetchone()[0]
        open_tasks = con.execute(
            "SELECT COUNT(*) FROM tasks WHERE status='open'"
        ).fetchone()[0]
        min_date = con.execute("SELECT MIN(request_date) FROM tasks").fetchone()[0]
        max_date = con.execute("SELECT MAX(request_date) FROM tasks").fetchone()[0]
        return {
            "total_emails": total_emails,
            "total_tasks": total_tasks,
            "open_tasks": open_tasks,
            "cached_summaries": cached,
            "date_range": {"min": min_date or "", "max": max_date or ""},
            "db_path": str(DB_PATH),
        }
    finally:
        con.close()


# ── HTTP サーバー ─────────────────────────────────────────────

class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # アクセスログ抑制

    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        qs = parse_qs(parsed.query)

        def qstr(key: str, default: str = "") -> str:
            return qs.get(key, [default])[0]

        def qint(key: str, default: int = DEFAULT_LIMIT) -> int:
            try:
                return int(qstr(key, str(default)))
            except ValueError:
                return default

        try:
            if parsed.path == "/api/stats":
                data = get_stats()

            elif parsed.path == "/api/search":
                q = qstr("q")
                limit = qint("limit")
                data = {"query": q, "results": search_emails(q, limit)}

            elif parsed.path == "/api/tasks":
                q = qstr("q")
                status = qstr("status")
                overdue = qstr("overdue") == "1"
                limit = qint("limit")
                results = search_tasks(q, status=status, overdue=overdue, limit=limit)
                data = {
                    "query": q,
                    "status_filter": status,
                    "overdue_filter": overdue,
                    "result_count": len(results),
                    "results": results,
                }

            else:
                self.send_response(404)
                self._cors()
                self.end_headers()
                self.wfile.write(b'{"error":"not found"}')
                return

            body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._cors()
            self.end_headers()
            self.wfile.write(body)

        except Exception as e:
            err = json.dumps({"error": str(e)}, ensure_ascii=False).encode("utf-8")
            self.send_response(500)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._cors()
            self.end_headers()
            self.wfile.write(err)


def main() -> None:
    import os
    import signal
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    # 多重起動防止
    if PID_PATH.exists():
        try:
            existing = int(PID_PATH.read_text().strip())
            if Path(f"/proc/{existing}").exists():
                print(f"Already running (PID {existing})", flush=True)
                sys.exit(0)
        except Exception:
            pass
    PID_PATH.write_text(str(os.getpid()))

    def _stop(sig, frame):
        PID_PATH.unlink(missing_ok=True)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    server = ThreadingHTTPServer((HOST, PORT), Handler)
    ts = datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")
    print(f"[{ts}] Email Search API started: http://{HOST}:{PORT}  DB: {DB_PATH}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
