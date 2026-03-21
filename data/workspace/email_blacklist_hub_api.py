#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DB_PATH = WORKSPACE / "email_search.db"
FILTER_PATH = WORKSPACE / "email_rag_sender_filters.json"
STATUS_PATH = WORKSPACE / "email_blacklist_hub_status.json"
PID_PATH = WORKSPACE / "email_blacklist_hub.pid"
HOST = "127.0.0.1"
PORT = 8791

EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-]+)@([A-Za-z0-9.-]+\.[A-Za-z]{2,})")
ASCII_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9.+_-]{2,}")
JP_TOKEN_RE = re.compile(r"[一-龥ぁ-んァ-ヶー]{2,}")
COMMON_DOMAIN_PARTS = {
    "www", "mail", "news", "info", "point", "members", "system", "support",
    "co", "com", "jp", "net", "org", "ne", "or", "go", "ac", "biz",
}
INTERNAL_ALLOW_PATTERNS = {
    "mitsui-s.com",
    "mitsui-mpt.com",
    "mektec.nokgrp.com",
    "nokgrp.com",
    "yijiu-china.com",
}


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_filters() -> dict:
    if FILTER_PATH.exists():
        return json.loads(FILTER_PATH.read_text(encoding="utf-8"))
    return {"newsletter_patterns": [], "blacklist_patterns": []}


def save_filters(payload: dict) -> None:
    FILTER_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_pattern(value: str) -> str:
    return re.sub(r"\s+", " ", (value or "").strip().lower())


def extract_sender_candidates(sender: str) -> list[str]:
    sender = sender or ""
    candidates: list[str] = []
    lowered = sender.lower()

    for local, domain in EMAIL_RE.findall(lowered):
        candidates.append(f"{local}@{domain}")
        candidates.append(domain)
        for part in domain.split("."):
            if len(part) >= 3 and part not in COMMON_DOMAIN_PARTS:
                candidates.append(part)

    display = EMAIL_RE.sub(" ", sender)
    display = re.sub(r"[\[\]\"'<>/()|]", " ", display)
    for token in ASCII_TOKEN_RE.findall(display):
        candidates.append(token.lower())
    for token in JP_TOKEN_RE.findall(display):
        candidates.append(token)

    return candidates


def candidate_allowed(token: str, blacklist_patterns: list[str]) -> bool:
    token = normalize_pattern(token)
    if len(token) < 2:
        return False
    if any(pattern in token or token in pattern for pattern in INTERNAL_ALLOW_PATTERNS):
        return False
    if any(pattern and (pattern in token or token in pattern) for pattern in blacklist_patterns):
        return False
    if token.isdigit():
        return False
    return True


def sender_is_internal(sender: str) -> bool:
    lowered = (sender or "").lower()
    return any(pattern in lowered for pattern in INTERNAL_ALLOW_PATTERNS)


def build_candidates(min_count: int = 10, limit: int = 120) -> dict:
    filters = load_filters()
    blacklist_patterns = [normalize_pattern(v) for v in filters.get("blacklist_patterns", [])]

    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT sender
            FROM emails
            WHERE source = 'gmail'
              AND COALESCE(sender, '') <> ''
            ORDER BY internal_ts DESC, indexed_at DESC
            """
        ).fetchall()
    finally:
        con.close()

    counts: Counter[str] = Counter()
    samples: dict[str, str] = {}
    token_sources: defaultdict[str, set[str]] = defaultdict(set)
    for row in rows:
        sender = row["sender"] or ""
        if sender_is_internal(sender):
            continue
        row_tokens = {normalize_pattern(token) for token in extract_sender_candidates(sender)}
        for token in row_tokens:
            if not candidate_allowed(token, blacklist_patterns):
                continue
            counts[token] += 1
            if token not in samples:
                samples[token] = sender
            token_sources[token].add(sender)

    candidates = []
    for token, count in counts.most_common():
        if count < min_count:
            continue
        candidates.append(
            {
                "pattern": token,
                "count": count,
                "sample_sender": samples.get(token, ""),
                "unique_senders": len(token_sources[token]),
            }
        )
        if len(candidates) >= limit:
            break

    return {
        "updatedAt": now_jst_text(),
        "gmailRowCount": len(rows),
        "minCount": min_count,
        "currentBlacklistCount": len(blacklist_patterns),
        "candidates": candidates,
    }


class Handler(BaseHTTPRequestHandler):
    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self) -> None:  # noqa: N802
        self._send(200, {"ok": True})

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/email-blacklist/candidates":
            payload = build_candidates()
            write_status({"updatedAt": now_jst_text(), "lastAction": "get_candidates", "candidateCount": len(payload["candidates"])})
            self._send(200, payload)
            return
        if path == "/api/email-blacklist/config":
            filters = load_filters()
            self._send(
                200,
                {
                    "updatedAt": now_jst_text(),
                    "blacklist_patterns": filters.get("blacklist_patterns", []),
                    "newsletter_patterns": filters.get("newsletter_patterns", []),
                },
            )
            return
        self._send(404, {"ok": False, "error": "not_found"})

    def do_POST(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path != "/api/email-blacklist/add":
            self._send(404, {"ok": False, "error": "not_found"})
            return
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length) if length > 0 else b"{}"
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"ok": False, "error": "invalid_json"})
            return

        patterns = payload.get("patterns") or []
        normalized = [normalize_pattern(v) for v in patterns if normalize_pattern(v)]
        if not normalized:
            self._send(400, {"ok": False, "error": "no_patterns"})
            return

        filters = load_filters()
        existing = [normalize_pattern(v) for v in filters.get("blacklist_patterns", [])]
        merged = list(dict.fromkeys(existing + normalized))
        filters["blacklist_patterns"] = merged
        save_filters(filters)

        write_status(
            {
                "updatedAt": now_jst_text(),
                "lastAction": "add_blacklist",
                "added": normalized,
                "blacklistCount": len(merged),
            }
        )
        self._send(200, {"ok": True, "added": normalized, "blacklistCount": len(merged)})


def main() -> None:
    PID_PATH.write_text(str(Path(__file__).resolve()), encoding="utf-8")
    write_status({"updatedAt": now_jst_text(), "lastAction": "startup", "listen": f"http://{HOST}:{PORT}"})
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        server.serve_forever()
    finally:
        try:
            PID_PATH.unlink(missing_ok=True)
        except Exception:
            pass


if __name__ == "__main__":
    main()
