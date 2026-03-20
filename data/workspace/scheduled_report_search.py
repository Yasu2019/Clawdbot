#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable


JST = timezone(timedelta(hours=9))
API_BASE = "http://127.0.0.1:5679/api/v1"
API_KEY = "n8n_api_clawstack_f39c126b684f59ab50cc3fdedd82891086bfc633601067c9"
WORKSPACE_ROOT = Path("/home/node/clawd")
DEFAULT_DB = WORKSPACE_ROOT / "email_search.db"
HOST_WORKSPACE_ROOT = Path(__file__).resolve().parent
STATUS_PATH = (WORKSPACE_ROOT if WORKSPACE_ROOT.exists() else HOST_WORKSPACE_ROOT) / "scheduled_report_search_status.json"
SYNC_STATE_PATH = (WORKSPACE_ROOT if WORKSPACE_ROOT.exists() else HOST_WORKSPACE_ROOT) / "scheduled_report_sync_state.json"

TARGET_WORKFLOWS = [
    "Daily AI Scout (新AI・ツール探索)",
    "Daily Trend Opportunity Report (20:30 JST)",
    "Daily Promises Report (23:00 JST)",
    "Daily System Health Check (09:00 JST)",
    "P016 Email Report (Daily 21:00 JST)",
    "Email RAG Ingest (Nightly 02:00 JST)",
]


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_status(payload: dict) -> None:
    save_json(STATUS_PATH, payload)


def detect_db_path(explicit: str | None) -> Path:
    if explicit:
        return Path(explicit)
    if DEFAULT_DB.exists():
        return DEFAULT_DB
    return HOST_WORKSPACE_ROOT / "email_search.db"


def connect_db(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path, timeout=30)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL")
    con.execute("PRAGMA synchronous=NORMAL")
    return con


def ensure_schema(con: sqlite3.Connection) -> None:
    con.executescript(
        """
        CREATE TABLE IF NOT EXISTS scheduled_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            workflow_id TEXT NOT NULL,
            workflow_name TEXT NOT NULL,
            execution_id TEXT NOT NULL,
            category TEXT NOT NULL,
            title TEXT NOT NULL,
            message_text TEXT NOT NULL,
            source_node TEXT NOT NULL,
            started_at TEXT NOT NULL,
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            UNIQUE(workflow_id, execution_id)
        );

        CREATE VIRTUAL TABLE IF NOT EXISTS scheduled_reports_fts USING fts5(
            workflow_name,
            category,
            title,
            message_text,
            content='scheduled_reports',
            content_rowid='id'
        );

        CREATE TRIGGER IF NOT EXISTS scheduled_reports_ai
        AFTER INSERT ON scheduled_reports BEGIN
            INSERT INTO scheduled_reports_fts(rowid, workflow_name, category, title, message_text)
            VALUES (new.id, new.workflow_name, new.category, new.title, new.message_text);
        END;

        CREATE TRIGGER IF NOT EXISTS scheduled_reports_ad
        AFTER DELETE ON scheduled_reports BEGIN
            INSERT INTO scheduled_reports_fts(scheduled_reports_fts, rowid, workflow_name, category, title, message_text)
            VALUES ('delete', old.id, old.workflow_name, old.category, old.title, old.message_text);
        END;

        CREATE TRIGGER IF NOT EXISTS scheduled_reports_au
        AFTER UPDATE ON scheduled_reports BEGIN
            INSERT INTO scheduled_reports_fts(scheduled_reports_fts, rowid, workflow_name, category, title, message_text)
            VALUES ('delete', old.id, old.workflow_name, old.category, old.title, old.message_text);
            INSERT INTO scheduled_reports_fts(rowid, workflow_name, category, title, message_text)
            VALUES (new.id, new.workflow_name, new.category, new.title, new.message_text);
        END;
        """
    )
    con.commit()


def request_json(path: str) -> dict:
    req = urllib.request.Request(
        f"{API_BASE}{path}",
        headers={"X-N8N-API-KEY": API_KEY, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def list_workflows() -> list[dict]:
    return request_json("/workflows?limit=100").get("data", [])


def category_for_workflow(name: str) -> str:
    lowered = name.lower()
    if "trend opportunity" in lowered:
        return "trend_opportunity"
    if "ai scout" in lowered:
        return "ai_scout"
    if "promises" in lowered:
        return "promises"
    if "health check" in lowered:
        return "health_check"
    if "email report" in lowered:
        return "email_report"
    if "email rag ingest" in lowered:
        return "email_ingest"
    return "scheduled_report"


def extract_message_from_execution(execution: dict) -> tuple[str, str, dict]:
    run_data = (((execution.get("data") or {}).get("resultData") or {}).get("runData")) or {}
    if not isinstance(run_data, dict):
        return "", "", {}

    preferred_nodes = ["Telegram Notify", "Format Trend Report", "Extract AI Report", "メッセージ整形"]

    def candidate_from_node(node_name: str, node_runs: list) -> tuple[str, str, dict]:
        first = (node_runs or [{}])[0]
        data = (first.get("data") or {}).get("main") or []
        if not data or not data[0] or not data[0][0]:
            return "", "", {}
        json_item = data[0][0].get("json") or {}
        if "result" in json_item and isinstance(json_item["result"], dict) and json_item["result"].get("text"):
            return str(json_item["result"]["text"]), node_name, json_item
        if json_item.get("message"):
            return str(json_item["message"]), node_name, json_item
        if json_item.get("text"):
            return str(json_item["text"]), node_name, json_item
        return "", "", {}

    for node_name in preferred_nodes:
        if node_name in run_data:
            text, source, meta = candidate_from_node(node_name, run_data[node_name])
            if text:
                return text, source, meta

    for node_name, node_runs in reversed(list(run_data.items())):
        text, source, meta = candidate_from_node(node_name, node_runs)
        if text:
            return text, source, meta
    return "", "", {}


def sync_reports(con: sqlite3.Connection, limit_per_workflow: int) -> dict:
    ensure_schema(con)
    workflows = [w for w in list_workflows() if w.get("name") in TARGET_WORKFLOWS]
    synced = 0
    scanned = 0
    details: list[dict] = []

    for wf in workflows:
        workflow_id = wf["id"]
        workflow_name = wf["name"]
        executions = request_json(f"/executions?workflowId={workflow_id}&limit={limit_per_workflow}").get("data", [])
        for execution_summary in executions:
            if execution_summary.get("status") != "success":
                continue
            scanned += 1
            execution_id = str(execution_summary["id"])
            exists = con.execute(
                "SELECT 1 FROM scheduled_reports WHERE workflow_id = ? AND execution_id = ?",
                (workflow_id, execution_id),
            ).fetchone()
            if exists:
                continue

            detail = request_json(f"/executions/{execution_id}?includeData=true")
            message_text, source_node, metadata = extract_message_from_execution(detail)
            if not message_text.strip():
                continue

            started_at = execution_summary.get("startedAt") or execution_summary.get("stoppedAt") or ""
            con.execute(
                """
                INSERT OR IGNORE INTO scheduled_reports (
                    workflow_id, workflow_name, execution_id, category, title,
                    message_text, source_node, started_at, created_at, metadata_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    workflow_id,
                    workflow_name,
                    execution_id,
                    category_for_workflow(workflow_name),
                    workflow_name,
                    message_text,
                    source_node or "unknown",
                    started_at,
                    now_jst(),
                    json.dumps(metadata, ensure_ascii=False),
                ),
            )
            synced += 1
            details.append({"workflow": workflow_name, "execution_id": execution_id, "source_node": source_node})

    con.commit()
    result = {"scanned": scanned, "synced": synced, "workflows": len(workflows), "details": details}
    save_json(SYNC_STATE_PATH, result)
    return result


def tokenize_query(query: str) -> list[str]:
    return [token for token in re.split(r"\s+", query or "") if token.strip()]


def relative_requested(query: str) -> bool:
    compact = re.sub(r"\s+", "", (query or "").lower())
    return any(token in compact for token in ("today", "yesterday", "latest", "recent", "今日", "昨日", "最新", "直近"))


def extract_category_filter(query: str) -> str:
    compact = re.sub(r"\s+", "", query or "").lower()
    if any(token in compact for token in ("ai日報", "ai scout", "モデルランキング", "モデル日報", "aiランキング")):
        return "ai_scout"
    if any(token in compact for token in ("トレンド", "人気コンテンツ", "稼げるチャンス", "trend")):
        return "trend_opportunity"
    if any(token in compact for token in ("約束", "promises", "promise")):
        return "promises"
    if any(token in compact for token in ("health", "ヘルス", "systemhealth", "システムヘルス")):
        return "health_check"
    if any(token in compact for token in ("todo", "p016", "emailreport", "メールtodo", "未対応案件")):
        return "email_report"
    if any(token in compact for token in ("rag", "ingest")):
        return "email_ingest"
    return ""


def search_rows(con: sqlite3.Connection, query: str, limit: int) -> list[sqlite3.Row]:
    category_filter = extract_category_filter(query)
    try:
        sql = """
            SELECT
                sr.workflow_name,
                sr.execution_id,
                sr.category,
                sr.title,
                sr.message_text,
                sr.source_node,
                sr.started_at,
                bm25(scheduled_reports_fts) AS score
            FROM scheduled_reports_fts
            JOIN scheduled_reports sr ON sr.id = scheduled_reports_fts.rowid
            WHERE scheduled_reports_fts MATCH ?
        """
        params: list[object] = [query]
        if category_filter:
            sql += " AND sr.category = ?"
            params.append(category_filter)
        sql += " ORDER BY score, sr.started_at DESC LIMIT ?"
        params.append(limit)
        rows = con.execute(sql, params).fetchall()
        if rows:
            return rows
    except sqlite3.OperationalError:
        pass

    terms = tokenize_query(query)
    if not terms:
        return []

    clauses = []
    params: list[object] = []
    for term in terms:
        clauses.append("(workflow_name LIKE ? OR category LIKE ? OR title LIKE ? OR message_text LIKE ?)")
        needle = f"%{term}%"
        params.extend([needle, needle, needle, needle])
    if category_filter:
        clauses.append("category = ?")
        params.append(category_filter)
    params.append(limit)
    return con.execute(
        f"""
        SELECT
            workflow_name,
            execution_id,
            category,
            title,
            message_text,
            source_node,
            started_at,
            0.0 AS score
        FROM scheduled_reports
        WHERE {' AND '.join(clauses)}
        ORDER BY started_at DESC
        LIMIT ?
        """,
        params,
    ).fetchall()


def recent_rows(con: sqlite3.Connection, limit: int) -> list[sqlite3.Row]:
    return con.execute(
        """
        SELECT
            workflow_name,
            execution_id,
            category,
            title,
            message_text,
            source_node,
            started_at,
            0.0 AS score
        FROM scheduled_reports
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()


def recent_rows_filtered(con: sqlite3.Connection, limit: int, category_filter: str) -> list[sqlite3.Row]:
    if not category_filter:
        return recent_rows(con, limit)
    return con.execute(
        """
        SELECT
            workflow_name,
            execution_id,
            category,
            title,
            message_text,
            source_node,
            started_at,
            0.0 AS score
        FROM scheduled_reports
        WHERE category = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (category_filter, limit),
    ).fetchall()


def rows_to_dicts(rows: Iterable[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


def build_summary(query: str, rows: list[dict], fallback_kind: str) -> str:
    if not rows:
        return "該当する定刻レポートは見つかりませんでした。"
    head = f"定刻レポートを {len(rows)} 件見つけました。"
    if fallback_kind == "recent":
        head = f"直近の定刻レポートを {len(rows)} 件見つけました。"
    lines = [head]
    for idx, row in enumerate(rows[:5], start=1):
        started_at = row.get("started_at") or "-"
        workflow = row.get("workflow_name") or "-"
        text = re.sub(r"\s+", " ", row.get("message_text") or "").strip()
        if len(text) > 120:
            text = text[:117] + "..."
        lines.append(f"{idx}. {started_at} / {workflow} / {text}")
    return "\n".join(lines)


def build_context(query: str, rows: list[dict], fallback_kind: str) -> str:
    if not rows:
        return ""
    heading = "Relevant scheduled reports"
    if fallback_kind == "recent":
        heading = "Recent scheduled reports"
    lines = [
        f"{heading} for: {query}",
        "Use only if relevant. If the record is insufficient, say so.",
    ]
    for idx, row in enumerate(rows, start=1):
        text = re.sub(r"\s+", " ", row.get("message_text") or "").strip()
        if len(text) > 320:
            text = text[:317] + "..."
        lines.append(
            f"[{idx}] {row.get('started_at') or '-'} | {row.get('workflow_name') or '-'} | {row.get('category') or '-'}\n{text}"
        )
    return "\n\n".join(lines)


def cmd_sync(args: argparse.Namespace) -> int:
    db_path = detect_db_path(args.db)
    con = connect_db(db_path)
    try:
        result = sync_reports(con, args.limit_executions)
        payload = {"db_path": str(db_path), **result}
        write_status({"updatedAt": now_jst(), "stage": "sync", **payload})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def cmd_context(args: argparse.Namespace) -> int:
    db_path = detect_db_path(args.db)
    con = connect_db(db_path)
    try:
        ensure_schema(con)
        primary = rows_to_dicts(search_rows(con, args.query, args.limit))
        fallback_kind = "search"
        category_filter = extract_category_filter(args.query)
        if (not primary and relative_requested(args.query)) or args.recent_only:
            primary = rows_to_dicts(recent_rows_filtered(con, args.limit, category_filter))
            fallback_kind = "recent"
        payload = {
            "query": args.query,
            "db_path": str(db_path),
            "result_count": len(primary),
            "fallback_kind": fallback_kind,
            "results": primary,
            "summary": build_summary(args.query, primary, fallback_kind),
            "context": build_context(args.query, primary, fallback_kind),
            "category_filter": category_filter,
        }
        write_status({"updatedAt": now_jst(), "stage": "query", "query": args.query, "result_count": len(primary)})
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    sub = parser.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync")
    sync.add_argument("--limit-executions", type=int, default=30)
    sync.set_defaults(func=cmd_sync)

    context = sub.add_parser("context")
    context.add_argument("query")
    context.add_argument("--limit", type=int, default=5)
    context.add_argument("--recent-only", action="store_true")
    context.set_defaults(func=cmd_context)
    return parser


def main() -> int:
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8")
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
