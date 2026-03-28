#!/usr/bin/env python3
import json
import subprocess
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
START_DATE = date(2026, 1, 1)
MAX_MESSAGES_PER_CHUNK = 5000
TIMEOUT_SECONDS = 3600
CONTAINER_NAME = "clawstack-unified-clawdbot-gateway-1"

SCRIPT_PATH = Path(__file__).resolve()
STATUS_PATH = SCRIPT_PATH.parent / "gmail_priority_backfill_status.json"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def month_chunks(start_date: date, end_date_inclusive: date) -> list[dict]:
    chunks: list[dict] = []
    cursor = start_date
    while cursor <= end_date_inclusive:
        if cursor.month == 12:
            next_month = date(cursor.year + 1, 1, 1)
        else:
            next_month = date(cursor.year, cursor.month + 1, 1)
        chunk_end = min(end_date_inclusive, next_month - timedelta(days=1))
        start_anchor = cursor - timedelta(days=1)
        chunks.append(
            {
                "startDate": cursor.isoformat(),
                "endDateInclusive": chunk_end.isoformat(),
                "query": f"in:anywhere after:{start_anchor.strftime('%Y/%m/%d')} before:{(chunk_end + timedelta(days=1)).strftime('%Y/%m/%d')}",
            }
        )
        cursor = chunk_end + timedelta(days=1)
    return chunks


def container_script(chunks: list[dict]) -> str:
    payload = json.dumps(chunks, ensure_ascii=False)
    return f"""
import importlib.util, json, shutil, sys, traceback
from pathlib import Path

spec = importlib.util.spec_from_file_location("email_search_index", "/home/node/clawd/email_search_index.py")
mod = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = mod
spec.loader.exec_module(mod)

chunks = json.loads({payload!r})
host_db = Path("/home/node/clawd/email_search.db")
host_state = Path("/home/node/clawd/email_search_state.json")
backup_db = Path("/home/node/clawd/email_search.before_priority_backfill.db")
temp_db = Path("/tmp/email_search_priority_backfill.db")
temp_state = Path("/tmp/email_search_priority_backfill_state.json")

if not backup_db.exists():
    shutil.copy2(host_db, backup_db)
shutil.copy2(host_db, temp_db)
if host_state.exists():
    shutil.copy2(host_state, temp_state)

mod.DB_PATH = temp_db
mod.STATE_PATH = temp_state
state = mod.load_json(mod.STATE_PATH)
results = []
con = None

try:
    con = mod.connect_db()
    for chunk in chunks:
        gmail_result = mod.index_gmail(con, state, {MAX_MESSAGES_PER_CHUNK}, 30, chunk["query"])
        con.commit()
        rebuilt = mod.rebuild_tasks(con)
        con.commit()
        results.append({{
            "startDate": chunk["startDate"],
            "endDateInclusive": chunk["endDateInclusive"],
            "query": chunk["query"],
            "gmail": gmail_result,
            "rebuiltTasks": rebuilt,
        }})
    state["updatedAt"] = mod.now_iso()
    mod.save_json(mod.STATE_PATH, state)
    shutil.copy2(temp_db, host_db)
    if temp_state.exists():
        shutil.copy2(temp_state, host_state)
    summary = {{"ok": True, "chunks": results}}
    print(json.dumps(summary, ensure_ascii=False))
except Exception as exc:
    print(json.dumps({{
        "ok": False,
        "error": str(exc),
        "traceback": traceback.format_exc(),
        "chunks": results,
    }}, ensure_ascii=False))
    raise
finally:
    if con is not None:
        con.close()
"""


def run_backfill(chunks: list[dict]) -> dict:
    proc = subprocess.run(
        ["docker", "exec", "-i", CONTAINER_NAME, "python3", "-"],
        input=container_script(chunks),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
    )
    result = {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "timedOut": False,
    }
    lines = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
    for line in reversed(lines):
        try:
            result["summary"] = json.loads(line)
            break
        except Exception:
            continue
    return result


def main() -> None:
    yesterday = datetime.now(JST).date() - timedelta(days=1)
    chunks = month_chunks(START_DATE, yesterday)
    status = {
        "startedAt": now_jst(),
        "stage": "running",
        "startDate": START_DATE.isoformat(),
        "endDateInclusive": yesterday.isoformat(),
        "maxMessagesPerChunk": MAX_MESSAGES_PER_CHUNK,
        "chunks": chunks,
    }
    write_status(status)
    try:
        result = run_backfill(chunks)
        status["result"] = result
        status["ok"] = bool(result.get("returncode") == 0 and result.get("summary", {}).get("ok"))
    except subprocess.TimeoutExpired as exc:
        status["result"] = {
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": TIMEOUT_SECONDS,
        }
        status["ok"] = False
    status["stage"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
