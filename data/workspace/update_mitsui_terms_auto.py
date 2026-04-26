#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sqlite3
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
if SCRIPT_PATH.as_posix().startswith("/workspace/"):
    WORKSPACE = SCRIPT_PATH.parent
elif SCRIPT_PATH.as_posix().startswith("/home/node/clawd/"):
    WORKSPACE = SCRIPT_PATH.parent
else:
    WORKSPACE = SCRIPT_PATH.parents[2] / "data" / "workspace"

DB_PATH = WORKSPACE / "email_search.db"
MANUAL_PATH = WORKSPACE / "mitsui_terms.md"
AUTO_PATH = WORKSPACE / "mitsui_terms_auto.md"
STATUS_PATH = WORKSPACE / "mitsui_terms_auto_status.json"

CODE_PATTERN = re.compile(r"\b[A-Z]{2,}[A-Z0-9/_-]{2,}\b")
COMMON_BLACKLIST = {
    "RE", "FW", "FWD", "PDF", "JST", "HTML", "EML", "GMAIL", "EMAIL", "RAG",
    "HTTP", "HTTPS", "STEP", "FCSTD", "JSON", "TASK", "TODO", "NETFLIX",
    "AUTODESK", "DOCUSIGN", "EPARK", "UDemy".upper(), "OLLAMA", "PINTEREST",
}
NOISE_PATTERNS = [
    re.compile(r"^UTM_"),
    re.compile(r"^(JP|COM)/"),
    re.compile(r"HTTP"),
    re.compile(r"^IMAGE\d+$"),
    re.compile(r"^MITSUI[-_]"),
    re.compile(r"^YASUHIRO[-_]SUZUKI$"),
    re.compile(r"^INFO[-_]"),
]


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except Exception:
        return ""


def load_known_terms() -> set[str]:
    text = f"{read_text(MANUAL_PATH)}\n{read_text(AUTO_PATH)}"
    return {term.upper() for term in CODE_PATTERN.findall(text)}


def fetch_recent_texts(days_back: int = 180) -> list[tuple[str, str]]:
    con = sqlite3.connect(DB_PATH)
    try:
        con.row_factory = sqlite3.Row
        cutoff = int((datetime.now(JST) - timedelta(days=days_back)).timestamp() * 1000)
        rows = con.execute(
            """
            SELECT subject, body_text
            FROM emails
            WHERE internal_ts IS NOT NULL AND internal_ts >= ?
            ORDER BY internal_ts DESC
            """,
            (cutoff,),
        ).fetchall()
        return [(row["subject"] or "", row["body_text"] or "") for row in rows]
    finally:
        con.close()


def extract_candidates(text: str) -> list[str]:
    out: list[str] = []
    for term in CODE_PATTERN.findall(text.upper()):
        if len(term) < 4:
            continue
        if term in COMMON_BLACKLIST:
            continue
        if any(pattern.search(term) for pattern in NOISE_PATTERNS):
            continue
        if not any(ch.isdigit() for ch in term) and "-" not in term and "/" not in term and "_" not in term:
            continue
        if term.count("/") >= 2:
            continue
        out.append(term)
    return out


def render_auto_terms(items: list[dict]) -> str:
    lines = [
        "# Mitsui Terms Auto",
        "",
        "このファイルはメールDBから自動検出した再出現語の記録です。",
        "",
        "- 条件: 同一語が複数回出現",
        "- 当面は安全のため、品番・社内コード・英大文字/数字/ハイフン系の語のみ自動追加",
        "- 手入力の正式単語集は `mitsui_terms.md`",
        "",
        "## Auto Terms",
        "",
    ]
    for item in items:
        lines.append(f"- {item['term']}  | count={item['count']} | last_seen={item['last_seen']}")
    if not items:
        lines.append("<!-- auto-generated -->")
    lines.append("")
    return "\n".join(lines)


def main() -> None:
    known = load_known_terms()
    texts = fetch_recent_texts()
    counts: Counter[str] = Counter()
    last_seen: dict[str, str] = {}

    for subject, body in texts:
        seen_in_row = set(extract_candidates(subject) + extract_candidates(body))
        for term in seen_in_row:
            counts[term] += 1
            last_seen[term] = now_jst_text()

    new_items = [
        {"term": term, "count": count, "last_seen": last_seen[term]}
        for term, count in counts.most_common()
        if count >= 3 and term not in known
    ]
    AUTO_PATH.write_text(render_auto_terms(new_items), encoding="utf-8")
    write_status(
        {
            "updatedAt": now_jst_text(),
            "dbPath": str(DB_PATH),
            "knownTerms": len(known),
            "autoTerms": len(new_items),
            "topTerms": new_items[:20],
        }
    )
    print(str(AUTO_PATH))


if __name__ == "__main__":
    main()
