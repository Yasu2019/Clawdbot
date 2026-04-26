#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import sys
import tempfile
import urllib.request
from datetime import date, timedelta
from pathlib import Path


if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"
SUMMARY_MAX_BODY = 800


def detect_db_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    candidates = [
        Path(__file__).resolve().parent / "email_search.db",
        Path("/home/node/clawd/email_search.db"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def load_blacklist_patterns() -> list[str]:
    candidates = [
        Path(__file__).resolve().parent / "email_rag_sender_filters.json",
        Path("/home/node/clawd/email_rag_sender_filters.json"),
    ]
    for path in candidates:
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return [p.lower() for p in data.get("blacklist_patterns", []) if p]
            except Exception:
                pass
    return []


def is_blacklisted(subject: str | None, requester: str | None, blacklist: list[str]) -> bool:
    if not blacklist:
        return False
    target = ((subject or "") + " " + (requester or "")).lower()
    return any(pat in target for pat in blacklist)


def stage_db_copy(db_path: Path) -> tuple[Path, Path | None]:
    try:
        temp_dir = Path(tempfile.mkdtemp(prefix="todo_report_db_"))
        staged_path = temp_dir / db_path.name
        shutil.copy2(db_path, staged_path)
        return staged_path, temp_dir
    except Exception:
        return db_path, None


def connect_db(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def available_task_columns(con: sqlite3.Connection) -> set[str]:
    return {str(row[1]) for row in con.execute("PRAGMA table_info(tasks)").fetchall()}


def task_select_expr(columns: set[str], column: str) -> str:
    return column if column in columns else f"'' AS {column}"


def clean_text(value: str | None, max_len: int = 80) -> str:
    text = (value or "").replace("\r", " ").replace("\n", " ").strip()
    if not text:
        return "-"
    if "\x1b" in text:
        return "[文字化けのため省略]"
    if len(text) > max_len:
        return text[: max_len - 3] + "..."
    return text


def extract_requester_name(requester: str | None) -> str:
    if not requester:
        return "-"
    match = re.match(r'^"?([^"<]+)"?\s*<[^>]+>', requester.strip())
    if match:
        return match.group(1).strip().strip('"')
    return clean_text(requester, 40)


def call_ollama_summary(subject: str, body: str) -> str | None:
    body_trimmed = body[:SUMMARY_MAX_BODY]
    prompt = (
        "以下のメールの依頼内容を日本語で2文以内に要約してください。\n"
        "固有名詞・型番・対策依頼は残し、挨拶や定型文は落としてください。\n\n"
        f"件名: {subject}\n本文: {body_trimmed}\n\n要約:"
    )
    payload = json.dumps(
        {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.2, "num_predict": 120},
        }
    ).encode("utf-8")
    try:
        req = urllib.request.Request(
            OLLAMA_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=25) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            text = result.get("response", "").strip()
            return text if text else None
    except Exception as exc:
        print(f"[WARN] LLM summary failed: {exc}", file=sys.stderr)
        return None


def get_or_generate_summary(
    con: sqlite3.Connection,
    available_columns: set[str],
    source: str,
    source_id: str,
    subject: str,
    body: str,
    use_llm: bool,
) -> tuple[str, bool]:
    if "request_summary" in available_columns:
        cached = con.execute(
            "SELECT request_summary FROM tasks WHERE source=? AND source_id=?",
            (source, source_id),
        ).fetchone()
        if cached and cached["request_summary"]:
            return cached["request_summary"], False

    if not use_llm:
        return "", False

    summary = call_ollama_summary(subject, body or "")
    return (summary or "", bool(summary))


def check_ollama_available() -> bool:
    try:
        req = urllib.request.Request("http://ollama:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def due_label(due_date: str) -> str:
    if not due_date:
        return "期日未設定"
    try:
        due = date.fromisoformat(due_date)
        delta = (due - date.today()).days
        if delta < 0:
            return f"{due_date} 期限切れ({abs(delta)}日超過)"
        if delta == 0:
            return f"{due_date} 今日まで"
        if delta <= 3:
            return f"{due_date} あと{delta}日"
        return f"{due_date} 残り{delta}日"
    except ValueError:
        return due_date


def classify_rows(rows: list[dict], today: date) -> tuple[list[dict], list[dict]]:
    urgent, no_due = [], []
    cutoff = (today - timedelta(days=30)).isoformat()
    for row in rows:
        due = row.get("due_date") or ""
        if due and due >= cutoff:
            urgent.append(row)
        else:
            no_due.append(row)
    urgent.sort(key=lambda item: item.get("due_date") or "")
    return urgent, no_due


def format_row(idx: int, row: dict) -> list[str]:
    requester = extract_requester_name(row.get("requester"))
    req_date = row.get("request_date") or "-"
    due_str = due_label(row.get("due_date") or "")
    reply_date = row.get("reply_date") or "-"
    summary = row.get("request_summary") or clean_text(row.get("request_body"), 120)
    return [
        "",
        "-" * 60,
        f"[{idx}]",
        f"  依頼日: {req_date}",
        f"  依頼者: {requester}",
        f"  要点  : {summary if summary else '要約なし'}",
        f"  期日  : {due_str}",
        f"  回答日: {reply_date}",
    ]


def build_report(rows: list[dict], from_date: str, to_date: str, limit: int) -> str:
    today = date.today()
    urgent, no_due = classify_rows(rows, today)

    lines = [
        f"依頼事項一覧 ({from_date} 〜 {to_date})",
        f"対象件数: {len(rows)}件 (期日あり: {len(urgent)}件 / 期日未設定・古い期限切れ: {len(no_due)}件)",
    ]
    if not rows:
        lines.append("対象期間に未回答の依頼事項は見つかりませんでした。")
        lines.append("さらに過去を見たい場合は months_back を増やして再実行してください。")
        return "\n".join(lines)

    urgent_show = urgent[:limit]
    if urgent_show:
        lines.append("")
        lines.append("【優先: 期日あり】")
        for idx, row in enumerate(urgent_show, start=1):
            lines.extend(format_row(idx, row))

    no_due_show = no_due[: max(limit - len(urgent_show), 5)]
    if no_due_show:
        lines.append("")
        lines.append("【参考: 期日未設定 / 古い期限切れ】")
        for idx, row in enumerate(no_due_show, start=1):
            lines.extend(format_row(idx, row))

    lines.append("")
    lines.append("さらに過去を見たい場合は months_back を増やして再実行してください。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--months-back", type=int, default=6)
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--no-llm", action="store_true", help="LLM要約を無効化（キャッシュのみ使用）")
    args = parser.parse_args()

    db_path = detect_db_path(args.db)
    today = date.today()
    to_date = today
    from_date = to_date - timedelta(days=max(args.months_back, 1) * 31)
    due_cutoff = (today - timedelta(days=30)).isoformat()
    req_from = from_date.isoformat()
    blacklist = load_blacklist_patterns()
    use_llm = (not args.no_llm) and check_ollama_available()

    staged_db_path, temp_dir = stage_db_copy(db_path)
    con = connect_db(staged_db_path)
    try:
        columns = available_task_columns(con)
        reply_date_expr = task_select_expr(columns, "reply_date")
        request_summary_expr = task_select_expr(columns, "request_summary")

        urgent_rows = con.execute(
            f"""
            SELECT
                source, source_id, request_date, due_date,
                requester, assignee, request_subject, request_body,
                status, reply_status, replier, reply_summary, {reply_date_expr}, {request_summary_expr}
            FROM tasks
            WHERE status = 'open'
              AND due_date >= ?
            ORDER BY due_date ASC
            LIMIT 200
            """,
            (due_cutoff,),
        ).fetchall()

        other_rows = con.execute(
            f"""
            SELECT
                source, source_id, request_date, due_date,
                requester, assignee, request_subject, request_body,
                status, reply_status, replier, reply_summary, {reply_date_expr}, {request_summary_expr}
            FROM tasks
            WHERE status = 'open'
              AND request_date <> ''
              AND request_date BETWEEN ? AND ?
              AND (due_date = '' OR due_date < ?)
            ORDER BY request_date DESC
            LIMIT 200
            """,
            (req_from, to_date.isoformat(), due_cutoff),
        ).fetchall()

        urgent_rows = [row for row in urgent_rows if not is_blacklisted(row["request_subject"], row["requester"], blacklist)]
        other_rows = [row for row in other_rows if not is_blacklisted(row["request_subject"], row["requester"], blacklist)]

        seen = set()
        all_rows: list[dict] = []
        for row in list(urgent_rows) + list(other_rows):
            key = (row["source"], row["source_id"])
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(dict(row))

        rows = all_rows[: args.limit * 3]
        enriched: list[dict] = []
        for row in rows:
            summary, _ = get_or_generate_summary(
                con,
                columns,
                row["source"],
                row["source_id"],
                row.get("request_subject") or "",
                row.get("request_body") or "",
                use_llm=use_llm,
            )
            if summary:
                row["request_summary"] = summary
            enriched.append(row)

        report_text = build_report(enriched, from_date.isoformat(), to_date.isoformat(), args.limit)
        payload = {
            "db_path": str(db_path),
            "staged_db_path": str(staged_db_path),
            "months_back": args.months_back,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "result_count": len(enriched),
            "llm_available": use_llm,
            "results": enriched,
            "summary": report_text,
            "rule": "①納期あり（直近30日超過〜未来）を優先表示し、②期日なし/古い期限切れは直近request_date順で補完します。",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
