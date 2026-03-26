#!/usr/bin/env python3
from __future__ import annotations

import argparse
import io
import json
import re
import sqlite3
import sys
import urllib.request
import urllib.error
from datetime import date, timedelta
from pathlib import Path

# Windows環境でも絵文字・日本語を正しく出力する（fd再オープンは避ける）
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

OLLAMA_URL = "http://ollama:11434/api/generate"
OLLAMA_MODEL = "qwen2.5-coder:7b"
SUMMARY_MAX_BODY = 800  # 要約に渡す本文の最大文字数


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


def connect_db(db_path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    # マイグレーション: 不足カラムを追加
    existing = {r[1] for r in con.execute("PRAGMA table_info(tasks)").fetchall()}
    if "reply_date" not in existing:
        con.execute("ALTER TABLE tasks ADD COLUMN reply_date TEXT NOT NULL DEFAULT ''")
        con.commit()
    if "request_summary" not in existing:
        con.execute("ALTER TABLE tasks ADD COLUMN request_summary TEXT NOT NULL DEFAULT ''")
        con.commit()
    return con


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
    """'表示名 <email@example.com>' から表示名のみ抽出する"""
    if not requester:
        return "-"
    # "Name <email>" 形式
    m = re.match(r'^"?([^"<]+)"?\s*<[^>]+>', requester.strip())
    if m:
        return m.group(1).strip().strip('"')
    # メールアドレスのみの場合はそのまま
    return clean_text(requester, 40)


def call_ollama_summary(subject: str, body: str) -> str | None:
    """qwen3:8b で本文を要約する。失敗時は None を返す。"""
    body_trimmed = body[:SUMMARY_MAX_BODY]
    prompt = (
        "以下はメールの件名と本文です。依頼内容を日本語で2〜3文に要約してください。\n"
        "挨拶・署名・宣伝文句は除外し、何を・いつまでに・どうしてほしいかを中心にまとめてください。\n\n"
        f"【件名】{subject}\n【本文】{body_trimmed}\n\n【要約】"
    )
    payload = json.dumps({
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2, "num_predict": 120},
    }).encode("utf-8")
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
    except Exception as e:
        import sys
        print(f"[WARN] LLM summary failed: {e}", file=sys.stderr)
        return None


def get_or_generate_summary(
    con: sqlite3.Connection,
    source: str,
    source_id: str,
    subject: str,
    body: str,
    use_llm: bool,
) -> tuple[str, bool]:
    """
    DBキャッシュを確認し、なければLLMで生成してDBに保存する。
    戻り値: (要約テキスト, llmを呼び出したか)
    """
    cached = con.execute(
        "SELECT request_summary FROM tasks WHERE source=? AND source_id=?",
        (source, source_id),
    ).fetchone()
    if cached and cached["request_summary"]:
        return cached["request_summary"], False

    if not use_llm:
        return "", False

    summary = call_ollama_summary(subject, body or "")
    if summary:
        con.execute(
            "UPDATE tasks SET request_summary=? WHERE source=? AND source_id=?",
            (summary, source, source_id),
        )
        con.commit()
        return summary, True
    return "", True  # LLM呼び出し試みたが失敗


def check_ollama_available() -> bool:
    """Ollama が応答するか確認する"""
    try:
        req = urllib.request.Request(
            "http://ollama:11434/api/tags",
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=5):
            return True
    except Exception:
        return False


def due_label(due_date: str) -> str:
    """回答期日に残日数・期限切れラベルを付与する"""
    if not due_date:
        return "期日未設定"
    try:
        due = date.fromisoformat(due_date)
        delta = (due - date.today()).days
        if delta < 0:
            return f"{due_date} 🔴期限切れ({abs(delta)}日超過)"
        elif delta == 0:
            return f"{due_date} 🟠今日まで"
        elif delta <= 3:
            return f"{due_date} 🟡残{delta}日"
        else:
            return f"{due_date} 残{delta}日"
    except ValueError:
        return due_date


def build_report(rows: list[sqlite3.Row], from_date: str, to_date: str, limit: int) -> str:
    lines = [
        f"📋 アクション一覧（{from_date} ～ {to_date}）",
        f"未対応件数: {len(rows)}件 / 表示: {min(len(rows), limit)}件",
    ]
    if not rows:
        lines.append("直近期間では未対応案件はありませんでした。")
        lines.append("さらに古い案件を見たい場合は、months_back を増やして再生成します。")
        return "\n".join(lines)

    for idx, row in enumerate(rows[:limit], start=1):
        requester = extract_requester_name(row["requester"])
        req_date = row["request_date"] or "-"
        due_str = due_label(row["due_date"] or "")
        reply_date = row.get("reply_date") or "-"
        summary = row["request_summary"] or clean_text(row["request_body"], 120)

        lines.append("")
        lines.append(f"{'─' * 40}")
        lines.append(f"[{idx}]")
        lines.append(f"  依頼日　: {req_date}")
        lines.append(f"  依頼者　: {requester}")
        lines.append(f"  依頼内容: {summary if summary else '（要約なし）'}")
        lines.append(f"  回答期日: {due_str}")
        lines.append(f"  回答日　: {reply_date}")

    lines.append("")
    lines.append("─" * 40)
    lines.append("さらに過去へさかのぼりたい場合は、months_back を増やして再送できます。")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db")
    parser.add_argument("--months-back", type=int, default=6)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--no-llm", action="store_true", help="LLM要約を無効化（キャッシュのみ使用）")
    args = parser.parse_args()

    db_path = detect_db_path(args.db)
    to_date = date.today()
    from_date = to_date - timedelta(days=max(args.months_back, 1) * 31)

    blacklist = load_blacklist_patterns()

    # LLM利用可否チェック
    use_llm = (not args.no_llm) and check_ollama_available()

    con = connect_db(db_path)
    try:
        all_rows = con.execute(
            """
            SELECT
                source,
                source_id,
                request_date,
                due_date,
                requester,
                assignee,
                request_subject,
                request_body,
                status,
                reply_status,
                replier,
                reply_summary,
                reply_date,
                request_summary
            FROM tasks
            WHERE status = 'open'
              AND request_date <> ''
              AND request_date BETWEEN ? AND ?
            ORDER BY CASE WHEN due_date = '' THEN 1 ELSE 0 END, due_date ASC, request_date DESC
            """,
            (from_date.isoformat(), to_date.isoformat()),
        ).fetchall()

        rows = [r for r in all_rows if not is_blacklisted(r["request_subject"], r["requester"], blacklist)]
        rows = rows[: args.limit]

        # 要約生成（キャッシュ優先、LLM利用可能な場合のみ生成）
        enriched = []
        for row in rows:
            summary, _ = get_or_generate_summary(
                con,
                row["source"],
                row["source_id"],
                row["request_subject"] or "",
                row["request_body"] or "",
                use_llm=use_llm,
            )
            # rowはsqlite3.Rowなのでdictに変換してsummaryを上書き
            d = dict(row)
            if summary:
                d["request_summary"] = summary
            enriched.append(d)

        report_text = build_report(enriched, from_date.isoformat(), to_date.isoformat(), args.limit)

        payload = {
            "db_path": str(db_path),
            "months_back": args.months_back,
            "from_date": from_date.isoformat(),
            "to_date": to_date.isoformat(),
            "result_count": len(enriched),
            "llm_available": use_llm,
            "results": enriched,
            "summary": report_text,
            "rule": "定刻送信の既定範囲は直近6か月です。さらに過去を希望した場合は months_back を増やして再送します。",
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    finally:
        con.close()


if __name__ == "__main__":
    raise SystemExit(main())
