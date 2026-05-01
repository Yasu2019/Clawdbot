#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "ai_strategy_scout_watchdog_status.json"
STATE_PATH = WORKSPACE / "ai_strategy_scout_watchdog_state.json"
HARNESS_PATH = ROOT / "data" / "state" / "ai_strategy_scout_watchdog" / "harness_status.json"
RUNNER = WORKSPACE / "run_ai_strategy_scout_local.py"
RUNNER_STATUS = WORKSPACE / "ai_strategy_scout_local_status.json"
RUNNER_MARKDOWN = WORKSPACE / "ai_strategy_scout_local_digest.md"
OPENCLAW_CONFIG = ROOT / "data" / "state" / "openclaw.json"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_telegram_config() -> tuple[str, str]:
    cfg = load_json(OPENCLAW_CONFIG, {})
    telegram = ((cfg.get("channels") or {}).get("telegram") or {})
    bot_token = str(telegram.get("botToken") or os.environ.get("TELEGRAM_BOT_TOKEN") or "").strip()
    chat_ids = telegram.get("allowFrom") or []
    chat_id = str(os.environ.get("TELEGRAM_CHAT_ID") or (chat_ids[0] if chat_ids else "")).strip()
    return bot_token, chat_id


def send_telegram(text: str) -> dict[str, Any]:
    bot_token, chat_id = load_telegram_config()
    if not bot_token or not chat_id:
        return {"sent": False, "reason": "telegram config missing"}
    body = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:3900]}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.telegram.org/bot{bot_token}/sendMessage",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    return {"sent": bool(payload.get("ok")), "messageId": ((payload.get("result") or {}).get("message_id"))}


def build_scout_telegram_message() -> str:
    header = f"AI Strategy Scout 定時レポート\n生成: {now_jst_text()}\n"
    if not RUNNER_MARKDOWN.exists():
        return header + "\nローカルダイジェストは生成されましたが、Markdownが見つかりません。"
    text = RUNNER_MARKDOWN.read_text(encoding="utf-8", errors="replace")
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("# "):
            continue
        if line.startswith("## ") or line.startswith("### ") or line.startswith("- "):
            lines.append(line.replace("### ", "").replace("## ", ""))
        if len("\n".join(lines)) > 3200:
            break
    return header + "\n" + "\n".join(lines[:60])


def parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    return None


def run_command(command: list[str], timeout_seconds: int = 900) -> dict[str, Any]:
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
        return {
            "command": " ".join(command),
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
            "timedOut": False,
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "command": " ".join(command),
            "returncode": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "timedOut": True,
        }


def write_status(status: dict[str, Any]) -> None:
    save_json(STATUS_PATH, status)
    save_json(
        HARNESS_PATH,
        {
            "service": "ai_strategy_scout_watchdog",
            "updatedAt": now_jst().isoformat(),
            "pid": os.getpid(),
            "state": status.get("stage"),
            "reason": status.get("reason"),
            "lastAction": status.get("lastAction"),
        },
    )


def should_run(status: dict[str, Any], stale_hours: int) -> tuple[bool, str]:
    finished = parse_dt(str(status.get("finishedAt") or status.get("generatedAt") or ""))
    if finished is None:
        return True, "no successful local scout run found"
    age = now_jst().astimezone(finished.tzinfo) - finished
    if age >= timedelta(hours=stale_hours):
        return True, f"last scout run is stale ({round(age.total_seconds() / 3600, 1)}h old)"
    return False, "local scout output is fresh"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the local AI strategy scout on a freshness schedule")
    parser.add_argument("--poll-seconds", type=int, default=1800)
    parser.add_argument("--stale-hours", type=int, default=20)
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()

    cycle = 0
    while True:
        cycle += 1
        runner_status = load_json(RUNNER_STATUS, {})
        should_execute, reason = should_run(runner_status, args.stale_hours)
        status: dict[str, Any] = {
            "startedAt": load_json(STATE_PATH, {}).get("startedAt") or now_jst_text(),
            "updatedAt": now_jst_text(),
            "cycle": cycle,
            "pid": os.getpid(),
            "stage": "healthy",
            "lastAction": "none",
            "reason": reason,
        }
        if should_execute:
            status["stage"] = "running"
            status["lastAction"] = "run_local_scout"
            write_status(status)
            run_result = run_command(["python", str(RUNNER)], 1200)
            status["runResult"] = run_result
            status["updatedAt"] = now_jst_text()
            status["stage"] = "completed" if run_result.get("returncode") == 0 else "error"
            status["reason"] = "local scout refresh completed" if run_result.get("returncode") == 0 else "local scout refresh failed"
            if run_result.get("returncode") == 0:
                runner_status_after = load_json(RUNNER_STATUS, {})
                state = load_json(STATE_PATH, {})
                generated_at = str(runner_status_after.get("finishedAt") or runner_status_after.get("generatedAt") or "")
                if generated_at and state.get("lastTelegramGeneratedAt") != generated_at:
                    try:
                        status["telegram"] = send_telegram(build_scout_telegram_message())
                        state["lastTelegramGeneratedAt"] = generated_at
                    except Exception as exc:
                        status["telegram"] = {"sent": False, "reason": str(exc)}
                save_json(STATE_PATH, {**state, "startedAt": status["startedAt"], "cycle": cycle})
        write_status(status)
        state = load_json(STATE_PATH, {})
        save_json(STATE_PATH, {**state, "startedAt": status["startedAt"], "cycle": cycle})
        if args.once:
            return
        time.sleep(max(args.poll_seconds, 60))


if __name__ == "__main__":
    main()
