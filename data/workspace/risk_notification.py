#!/usr/bin/env python3
from __future__ import annotations

import base64
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
SCRIPT_PATH = Path(__file__).resolve()
WORKSPACE = SCRIPT_PATH.parent

STATUS_PATH = WORKSPACE / "risk_notification_status.json"
STATE_PATH = WORKSPACE / "risk_notification_state.json"
EMAIL_RUNTIME = WORKSPACE / "email_rag_ingest_runtime_status.json"
IDLE_STATUS = WORKSPACE / "idle_ingest_maintenance_status.json"
AUTO_REPAIR_STATUS = WORKSPACE / "auto_repair_allowed_status.json"
NODE_GMAIL_SCRIPT = WORKSPACE / "scripts" / "send_allowed_gmail_from_b64.js"

TELEGRAM_BOT = "8085717200:AAHzacN6Q3xSunrLyvUTuHnKEf7Cd5YFdt4"
TELEGRAM_CHAT_ID = "8173025084"
GMAIL_RECIPIENT = "y.suzuki.hk@gmail.com"
NOTIFICATION_COOLDOWN_HOURS = 6
HEALTH_URLS = [
    "http://localhost:8110/health",
    "http://127.0.0.1:8110/health",
    "http://host.docker.internal:8110/health",
]


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = value.strip()
    parsers = [
        lambda x: datetime.strptime(x, "%Y-%m-%d %H:%M:%S JST").replace(tzinfo=JST),
        lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S.%f%z"),
        lambda x: datetime.strptime(x, "%Y-%m-%dT%H:%M:%S%z"),
        lambda x: datetime.fromisoformat(x.replace("Z", "+00:00")) if x.endswith("Z") else datetime.fromisoformat(x),
    ]
    for parser in parsers:
        try:
            return parser(raw)
        except Exception:
            continue
    return None


def age_minutes(dt: datetime | None) -> float | None:
    if dt is None:
        return None
    return round((now_jst().astimezone(dt.tzinfo) - dt).total_seconds() / 60.0, 1)


def health_check() -> dict[str, Any]:
    attempts = []
    for url in HEALTH_URLS:
        try:
            response = requests.get(url, timeout=10)
            attempts.append({"url": url, "status": response.status_code})
            if response.ok:
                data = response.json()
                return {
                    "ok": True,
                    "url": url,
                    "status": response.status_code,
                    "qdrant": data.get("qdrant"),
                    "collections": len(data.get("collections") or []),
                    "raw": data,
                    "attempts": attempts,
                }
        except Exception as exc:
            attempts.append({"url": url, "error": str(exc)})
    return {"ok": False, "attempts": attempts}


def encode_b64url(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode("utf-8")).decode("ascii").rstrip("=")


def send_telegram(text: str) -> dict[str, Any]:
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT}/sendMessage",
        data={"chat_id": TELEGRAM_CHAT_ID, "text": text},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def send_gmail(subject: str, body: str) -> dict[str, Any]:
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


def make_finding(key: str, severity: str, title: str, detail: str) -> dict[str, str]:
    return {"key": key, "severity": severity, "title": title, "detail": detail}


def has_bad_result(result: dict[str, Any] | None) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("timedOut"):
        return True
    return result.get("returncode") not in (None, 0)


def collect_findings() -> tuple[list[dict[str, str]], dict[str, Any]]:
    findings: list[dict[str, str]] = []
    email = read_json(EMAIL_RUNTIME)
    idle = read_json(IDLE_STATUS)
    auto_repair = read_json(AUTO_REPAIR_STATUS)
    health = health_check()

    if not health.get("ok"):
        findings.append(
            make_finding(
                "learning_engine_offline",
                "high",
                "learning_engine is offline",
                "All health endpoints failed. Learning Memory and compare features may be unavailable.",
            )
        )

    email_started = parse_dt(email.get("startedAt"))
    if any(has_bad_result(v) for v in (email.get("results") or {}).values()):
        findings.append(
            make_finding(
                "email_nightly_failed",
                "medium",
                "Email nightly reported a failed phase",
                f"step={email.get('step')} currentPhase={email.get('currentPhase')}",
            )
        )
    elif email.get("step") != "completed" and email_started and age_minutes(email_started) and age_minutes(email_started) >= 120:
        findings.append(
            make_finding(
                "email_nightly_stuck",
                "medium",
                "Email nightly appears stuck",
                f"step={email.get('step')} currentPhase={email.get('currentPhase')} age={age_minutes(email_started)} minutes",
            )
        )

    idle_results = idle.get("results") or {}
    for name in [
        "scheduled_reports_sync",
        "cae_learning_sync",
        "cmux_status_refresh",
        "mitsui_terms_refresh",
        "auto_repair_allowed",
    ]:
        result = idle_results.get(name)
        if has_bad_result(result):
            findings.append(
                make_finding(
                    f"idle_{name}_failed",
                    "medium",
                    f"{name} failed in idle maintenance",
                    f"returncode={result.get('returncode')} timedOut={result.get('timedOut', False)}",
                )
            )

    for name, result in (auto_repair.get("results") or {}).items():
        if has_bad_result(result):
            findings.append(
                make_finding(
                    f"auto_repair_{name}_failed",
                    "medium",
                    f"Auto repair action failed: {name}",
                    f"returncode={result.get('returncode')} timedOut={result.get('timedOut', False)}",
                )
            )

    return findings, {"health": health, "email": email, "idle": idle, "autoRepair": auto_repair}


def should_send(findings: list[dict[str, str]], state: dict[str, Any]) -> tuple[bool, list[str]]:
    if not findings:
        return False, []
    sent = state.get("sent", {})
    keys_to_send: list[str] = []
    for finding in findings:
        key = finding["key"]
        sent_at = parse_dt((sent.get(key) or {}).get("sentAt"))
        if sent_at is None or (now_jst().astimezone(sent_at.tzinfo) - sent_at) >= timedelta(hours=NOTIFICATION_COOLDOWN_HOURS):
            keys_to_send.append(key)
    return bool(keys_to_send), keys_to_send


def build_message(findings: list[dict[str, str]], keys_to_send: list[str], context: dict[str, Any]) -> tuple[str, str]:
    active = [f for f in findings if f["key"] in keys_to_send]
    highest = "HIGH" if any(f["severity"] == "high" for f in active) else "MEDIUM"
    lines = [f"Risk Notification [{highest}]", f"Updated: {now_jst_text()}"]
    for finding in active:
        lines.append(f"- {finding['severity'].upper()}: {finding['title']} | {finding['detail']}")
    health = context.get("health") or {}
    if health.get("ok"):
        lines.append(f"learning_engine: online via {health.get('url')}")
    else:
        lines.append("learning_engine: offline")
    body = "\n".join(lines)
    subject = f"Clawdbot Risk Notification [{highest}]"
    return subject, body


def main() -> None:
    state = read_json(STATE_PATH)
    findings, context = collect_findings()
    should_notify, keys_to_send = should_send(findings, state)

    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "step": "evaluate",
        "findings": findings,
        "sent": False,
        "channels": {},
        "health": context.get("health") or {},
    }
    write_json(STATUS_PATH, status)

    if should_notify:
        subject, body = build_message(findings, keys_to_send, context)
        status["step"] = "notify"
        status["message"] = {"subject": subject, "body": body}
        write_json(STATUS_PATH, status)

        try:
            status["channels"]["telegram"] = send_telegram(body)
        except Exception as exc:
            status["channels"]["telegram"] = {"error": str(exc)}
        write_json(STATUS_PATH, status)

        try:
            status["channels"]["gmail"] = send_gmail(subject, body)
        except Exception as exc:
            status["channels"]["gmail"] = {"error": str(exc)}
        write_json(STATUS_PATH, status)

        sent = state.get("sent", {})
        stamp = now_jst_text()
        for key in keys_to_send:
            sent[key] = {"sentAt": stamp}
        state["sent"] = sent
        write_json(STATE_PATH, state)
        status["sent"] = True
        status["sentKeys"] = keys_to_send

    status["step"] = "completed"
    status["finishedAt"] = now_jst_text()
    write_json(STATUS_PATH, status)


if __name__ == "__main__":
    main()
