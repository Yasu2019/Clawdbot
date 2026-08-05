#!/usr/bin/env python3
"""Periodic INC-187 supervisor: check status, alert gaps, stop on terminal without next step.

Does not blind-retry. On terminal failure it Telegram-notifies and exits so a human/agent
session can apply a fresh-ID countermeasure. On running states it heartbeats.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor"
APPROVAL = ROOT / "data" / "workspace" / "user_approval_batch_60_20260805.json"
HEARTBEAT = STATE_DIR / "inc187_supervisor_heartbeat.json"


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def load_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def save_heartbeat(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = HEARTBEAT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(HEARTBEAT)


def consume_approval(task: str, units: int = 1) -> int:
    data = load_json(APPROVAL)
    if not data:
        return -1
    remaining = int(data.get("remaining", 0)) - units
    data["remaining"] = max(0, remaining)
    consumed = list(data.get("consumed") or [])
    consumed.append({"at": _now(), "task": task, "units": units, "agent": "inc187_supervisor"})
    data["consumed"] = consumed
    temporary = APPROVAL.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(APPROVAL)
    return data["remaining"]


def notify(text: str) -> None:
    try:
        sys.path.insert(0, str(ROOT / "scripts"))
        import cae_telegram_video_notify as tg

        tg.send_telegram_message(text)
    except Exception as exc:
        print(f"[supervisor-notify] {exc}", flush=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--status-file", required=True)
    parser.add_argument("--interval-seconds", type=int, default=120)
    parser.add_argument("--max-checks", type=int, default=60)
    parser.add_argument("--label", default="INC-187")
    args = parser.parse_args()
    status_path = Path(args.status_file)
    last_state = ""
    for check in range(1, args.max_checks + 1):
        status = load_json(status_path)
        state = str(status.get("state") or "missing")
        remaining = int(load_json(APPROVAL).get("remaining", -1))
        save_heartbeat(
            {
                "schema": "clawstack.inc187.supervisor.v1",
                "updated_at": _now(),
                "check": check,
                "max_checks": args.max_checks,
                "status_file": str(status_path),
                "state": state,
                "approval_remaining": remaining,
            }
        )
        print(f"[supervisor] check={check} state={state} approval_remaining={remaining}", flush=True)
        if state != last_state and state:
            if any(
                state.endswith(suf)
                for suf in (
                    "_failed_or_not_promotable",
                    "_failed",
                    "monitor_timeout",
                    "_complete",
                )
            ):
                consume_approval(f"terminal_observe:{state}", 1)
                notify(
                    f"[{args.label}] Supervisor sees terminal state={state}\n"
                    f"details={json.dumps(status.get('details') or {}, ensure_ascii=False)[:700]}\n"
                    f"approval_remaining={remaining}\nPROXY_GAP"
                )
                if state.endswith("_complete"):
                    return 0
                # Failure: exit so next agent iteration applies fresh countermeasure
                return 1
            last_state = state
        if remaining == 0:
            notify(f"[{args.label}] Approval budget exhausted")
            return 2
        time.sleep(max(30, int(args.interval_seconds)))
    notify(f"[{args.label}] Supervisor reached max_checks={args.max_checks} still running")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
