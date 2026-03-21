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
else:
    STATUS_PATH = SCRIPT_PATH.parents[2] / "data" / "workspace" / "email_rag_ingest_runtime_status.json"
    NODE_GMAIL_SCRIPT = SCRIPT_PATH.parents[2] / "data" / "workspace" / "scripts" / "send_allowed_gmail_from_b64.js"
    SHARED_REPORT_PATH = SCRIPT_PATH.parents[2] / "data" / "workspace" / "email_rag_message.txt"

TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"
GMAIL_RECIPIENT = "y.suzuki.hk@gmail.com"


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


def build_report(results: dict) -> str:
    result = run_command(
        'docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/generate_email_rag_message.py >/home/node/clawd/email_rag_message.txt"',
        60,
    )
    if result.get("returncode") == 0 and SHARED_REPORT_PATH.exists():
        text = SHARED_REPORT_PATH.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return text
    latest = parse_latest_json_line(results["phase4_sqlite_search"]["stdout"])
    return f"Email ingest completed\nUpdated: {latest.get('updatedAt', '(unknown)')}"


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
    write_status(status)

    commands = [
        (
            "phase4_sqlite_search",
            'docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/email_search_index.py --gmail-force-query \'in:anywhere newer_than:7d\' --gmail-max-messages 500 >>/home/node/clawd/email_search_index.log 2>&1; tail -5 /home/node/clawd/email_search_index.log" || true',
            180,
        ),
    ]

    for name, command, timeout_seconds in commands:
        status["currentPhase"] = name
        write_status(status)
        status["results"][name] = run_command(command, timeout_seconds)
        write_status(status)

    status["results"]["phase12_qdrant"] = {
        "skipped": True,
        "reason": "nightly stable mode uses SQLite/Gmail ingest only",
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
    status["step"] = "notify"
    write_status(status)

    try:
        status["telegram"] = send_telegram(report)
    except Exception as exc:
        status["telegram"] = {"error": str(exc)}
    write_status(status)

    try:
        status["gmail"] = send_gmail("Email RAG Ingest", report)
    except Exception as exc:
        status["gmail"] = {"error": str(exc)}
    write_status(status)

    status["step"] = "completed"
    status["finishedAt"] = now_jst()
    write_status(status)


if __name__ == "__main__":
    main()
