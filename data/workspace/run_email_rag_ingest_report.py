#!/usr/bin/env python3
import base64
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
if SCRIPT_PATH.parent.name == "workspace":
    STATUS_PATH = SCRIPT_PATH.parent / "email_rag_ingest_runtime_status.json"
    NODE_GMAIL_SCRIPT = SCRIPT_PATH.parent / "scripts" / "send_allowed_gmail_from_b64.js"
    SHARED_REPORT_PATH = SCRIPT_PATH.parent / "email_rag_message.txt"
    EMAIL_LEARNING_SYNC_SCRIPT = SCRIPT_PATH.parent / "sync_email_learning_memory.py"
    EMAIL_LEARNING_SYNC_STATUS_PATH = SCRIPT_PATH.parent / "email_learning_memory_sync_status.json"
    PRIORITY_GMAIL_BACKFILL_SCRIPT = SCRIPT_PATH.parent / "run_priority_gmail_backfill.py"
else:
    STATUS_PATH = SCRIPT_PATH.parents[2] / "data" / "workspace" / "email_rag_ingest_runtime_status.json"
    NODE_GMAIL_SCRIPT = SCRIPT_PATH.parents[2] / "data" / "workspace" / "scripts" / "send_allowed_gmail_from_b64.js"
    SHARED_REPORT_PATH = SCRIPT_PATH.parents[2] / "data" / "workspace" / "email_rag_message.txt"
    EMAIL_LEARNING_SYNC_SCRIPT = SCRIPT_PATH.parents[2] / "data" / "workspace" / "sync_email_learning_memory.py"
    EMAIL_LEARNING_SYNC_STATUS_PATH = SCRIPT_PATH.parents[2] / "data" / "workspace" / "email_learning_memory_sync_status.json"
    PRIORITY_GMAIL_BACKFILL_SCRIPT = SCRIPT_PATH.parents[2] / "data" / "workspace" / "run_priority_gmail_backfill.py"

TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"
GMAIL_RECIPIENT = "y.suzuki.hk@gmail.com"
GMAIL_PRIORITY_START_DATE = datetime(2026, 1, 1, tzinfo=JST).date()
GMAIL_PRIORITY_BACKFILL_TIMEOUT = 5400
EMAIL_LEARNING_SYNC_TIMEOUT = 1800
def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(data: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_command(command: str, timeout_seconds: int) -> dict:
    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": command,
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
            "timeoutSeconds": timeout_seconds,
        }


def parse_latest_json_line(value: str) -> dict:
    text = (value or "").strip()
    if not text:
        return {}
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except json.JSONDecodeError:
            continue
    return {}


def read_json_file(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def phase_issue(name: str, result: dict) -> str | None:
    if not result:
        return None
    if result.get("timedOut"):
        return f"{name}: timed out after {result.get('timeoutSeconds', '?')}s"
    returncode = result.get("returncode")
    if returncode not in (None, 0):
        return f"{name}: exit code {returncode}"
    return None


def summarize_overall_status(results: dict) -> tuple[str, list[str]]:
    issues = []
    for name, result in results.items():
        issue = phase_issue(name, result)
        if issue:
            issues.append(issue)
    if not issues:
        return "ok", []
    timed_out_only = all("timed out" in issue for issue in issues)
    return ("warning" if timed_out_only else "error"), issues


def build_report(results: dict) -> str:
    overall, issues = summarize_overall_status(results)
    result = run_command(
        'docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/generate_email_rag_message.py >/home/node/clawd/email_rag_message.txt"',
        60,
    )
    if result.get("returncode") == 0 and SHARED_REPORT_PATH.exists():
        text = SHARED_REPORT_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            if issues:
                text += "\n\nRun status: " + overall.upper()
                text += "\nIssues:\n- " + "\n- ".join(issues)
            sync_status = read_json_file(EMAIL_LEARNING_SYNC_STATUS_PATH)
            if sync_status:
                sync_line = (
                    "\n\nLearning memory sync: "
                    f"{sync_status.get('stage', 'unknown')}, "
                    f"messages={sync_status.get('postedMessages', 0)}, "
                    f"threads={sync_status.get('postedThreads', 0)}, "
                    f"errors={len(sync_status.get('errors', []))}"
                )
                return text + sync_line
            return text
    latest = parse_latest_json_line(results["phase4_sqlite_search"]["stdout"])
    message = f"Email ingest {overall}\nUpdated: {latest.get('updatedAt', '(unknown)')}"
    if issues:
        message += "\nIssues:\n- " + "\n- ".join(issues)
    return message


def send_telegram(text: str) -> dict:
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def encode_b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def send_gmail(subject: str, body: str) -> dict:
    proc = subprocess.run(
        [
            "node",
            str(NODE_GMAIL_SCRIPT),
            GMAIL_RECIPIENT,
            encode_b64url(subject),
            encode_b64url(body),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def main() -> None:
    status = {"startedAt": now_jst(), "step": "run", "results": {}}
    status["gmailPriorityWindow"] = {
        "startDate": GMAIL_PRIORITY_START_DATE.isoformat(),
        "endDateInclusive": (datetime.now(JST).date() - timedelta(days=1)).isoformat(),
        "strategy": "monthly_chunk_backfill",
        "script": str(PRIORITY_GMAIL_BACKFILL_SCRIPT),
    }
    write_status(status)

    commands = [
        (
            "phase4_sqlite_search",
            f'python3 "{PRIORITY_GMAIL_BACKFILL_SCRIPT}"',
            GMAIL_PRIORITY_BACKFILL_TIMEOUT,
        ),
        (
            "phase5_learning_memory_sync",
            f'python3 "{EMAIL_LEARNING_SYNC_SCRIPT}" --base-url "http://localhost:8110" --source-org "Mitsui"',
            EMAIL_LEARNING_SYNC_TIMEOUT,
        ),
    ]

    for name, command, timeout_seconds in commands:
        status["currentPhase"] = name
        write_status(status)
        status["results"][name] = run_command(command, timeout_seconds)
        write_status(status)

    status["results"]["phase12_qdrant"] = {
        "skipped": True,
        "reason": "nightly stable mode uses SQLite/Gmail ingest only; learning_engine sync is handled separately",
        "stdout": "",
        "stderr": "",
    }
    status["results"]["phase3_meilisearch"] = {
        "skipped": True,
        "reason": "nightly stable mode uses SQLite/Gmail ingest only",
        "stdout": "",
        "stderr": "",
    }

    report = build_report(status["results"])
    status["reportText"] = report
    status["overall"], status["issues"] = summarize_overall_status(status["results"])
    status["step"] = "notify"
    write_status(status)

    try:
        status["telegram"] = send_telegram(report)
    except Exception as exc:
        status["telegram"] = {"error": str(exc)}
    write_status(status)

    try:
        subject = "Email RAG Ingest" if status.get("overall") == "ok" else f"Email RAG Ingest [{status.get('overall', 'warning').upper()}]"
        status["gmail"] = send_gmail(subject, report)
    except Exception as exc:
        status["gmail"] = {"error": str(exc)}
    write_status(status)

    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
