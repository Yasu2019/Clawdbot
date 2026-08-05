#!/usr/bin/env python3
"""Watch CAE trial/monitor terminal states and alert immediately via Telegram.

Prevents agent-turn gaps: IF ledger/monitor reaches a terminal state THEN notify
within one poll interval, even when no chat session is active.
"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import ctypes
import json
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

LEDGER = ROOT / "data" / "workspace" / "satellite_cae_log.jsonl"
STATE_DIR = ROOT / "data" / "state" / "lavie_mf_pipeline_monitor"
HEARTBEAT = STATE_DIR / "inc187_watchdog_heartbeat.json"
ALERT_LOG = STATE_DIR / "inc187_watchdog_alerts.jsonl"
TERMINAL_VERDICTS = {
    "SUCCESS",
    "FAILED",
    "TIMEOUT",
    "ERROR",
    "PREGATE_FAIL",
    "STOPPED_MEANING_GATE",
    "DRY_RUN",
}
TERMINAL_MONITOR_PREFIXES = (
    "r14_failed",
    "r16_failed",
    "r12_failed",
    "r12_rca",
    "monitor_timeout",
    "r15_full_fill_",
    "r17_",
    "r18_",
    "blocked_",
)
ES_CONTINUOUS = 0x80000000
ES_SYSTEM_REQUIRED = 0x00000001


def _now() -> str:
    return datetime.now().astimezone().isoformat()


def latest_trial(trial_id: str) -> dict | None:
    if not LEDGER.exists():
        return None
    found = None
    for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        if trial_id not in line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        trial = row.get("trial_entry") or {}
        if trial.get("id") == trial_id:
            found = trial
    return found


def read_json(path: Path) -> dict:
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def write_heartbeat(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    temporary = HEARTBEAT.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(HEARTBEAT)


def append_alert(payload: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    with ALERT_LOG.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def send_telegram(text: str) -> tuple[bool, str]:
    try:
        import cae_telegram_video_notify as tg

        ok = tg.send_telegram_message(text)
        return bool(ok), "ok" if ok else "send_returned_false"
    except Exception as exc:
        return False, str(exc)[:300]


def monitor_is_terminal(state: str) -> bool:
    if not state:
        return False
    if state.endswith("_complete") or state.endswith("_failed") or state.endswith("_failed_or_not_promotable"):
        return True
    return any(state.startswith(prefix) for prefix in TERMINAL_MONITOR_PREFIXES)


def main() -> int:
    parser = argparse.ArgumentParser(description="INC-187 terminal-state Telegram watchdog")
    parser.add_argument("--trial-id", action="append", default=[], help="Trial IDs to watch (repeatable)")
    parser.add_argument(
        "--status-file",
        action="append",
        default=[],
        help="Monitor status JSON paths (repeatable)",
    )
    parser.add_argument("--interval-seconds", type=int, default=30)
    parser.add_argument("--max-checks", type=int, default=2880)
    parser.add_argument("--no-sleep-inhibit", action="store_true")
    parser.add_argument("--label", default="INC-187")
    args = parser.parse_args()

    trial_ids = list(dict.fromkeys(args.trial_id))
    status_files = [Path(p) for p in args.status_file]
    if not trial_ids and not status_files:
        print("Need --trial-id and/or --status-file", file=sys.stderr)
        return 2

    alerted: set[str] = set()
    if sys.platform == "win32" and not args.no_sleep_inhibit:
        ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)

    try:
        for check in range(1, args.max_checks + 1):
            events: list[dict] = []

            for trial_id in trial_ids:
                trial = latest_trial(trial_id)
                if not trial:
                    continue
                verdict = str(trial.get("verdict") or "")
                key = f"trial:{trial_id}:{verdict}"
                if verdict in TERMINAL_VERDICTS and key not in alerted:
                    tags = trial.get("failure_tags") or []
                    defects = trial.get("defects_detected") or {}
                    events.append(
                        {
                            "kind": "trial_terminal",
                            "trial_id": trial_id,
                            "verdict": verdict,
                            "failure_tags": tags,
                            "fill_time_s": defects.get("fill_time_s"),
                            "duration_sec": trial.get("duration_sec"),
                            "key": key,
                        }
                    )

            for status_path in status_files:
                status = read_json(status_path)
                state = str(status.get("state") or "")
                key = f"status:{status_path.name}:{state}:{status.get('check')}"
                # Deduplicate by state only for terminal monitor states
                state_key = f"status:{status_path.name}:{state}"
                if monitor_is_terminal(state) and state_key not in alerted:
                    events.append(
                        {
                            "kind": "monitor_terminal",
                            "status_file": str(status_path),
                            "state": state,
                            "check": status.get("check"),
                            "details": status.get("details") or {},
                            "key": state_key,
                        }
                    )

            for event in events:
                key = str(event["key"])
                if event["kind"] == "trial_terminal":
                    text = (
                        f"[{args.label}] CAE terminal\n"
                        f"trial: {event['trial_id']}\n"
                        f"verdict: {event['verdict']}\n"
                        f"tags: {event.get('failure_tags')}\n"
                        f"fill_time_s: {event.get('fill_time_s')}\n"
                        f"duration_sec: {event.get('duration_sec')}\n"
                        f"accuracy: PROXY_GAP\n"
                        f"next: RCA / fresh ID if FAILED; promote only on SUCCESS gates"
                    )
                else:
                    text = (
                        f"[{args.label}] Monitor terminal\n"
                        f"state: {event['state']}\n"
                        f"file: {event['status_file']}\n"
                        f"check: {event.get('check')}\n"
                        f"details: {json.dumps(event.get('details') or {}, ensure_ascii=False)[:500]}\n"
                        f"accuracy: PROXY_GAP"
                    )
                ok, detail = send_telegram(text)
                alert_row = {
                    "at": _now(),
                    "telegram_ok": ok,
                    "telegram_detail": detail,
                    "event": event,
                }
                append_alert(alert_row)
                alerted.add(key)
                print(f"[watchdog] ALERT key={key} telegram_ok={ok} detail={detail}", flush=True)

            write_heartbeat(
                {
                    "schema": "clawstack.inc187.watchdog.v1",
                    "updated_at": _now(),
                    "check": check,
                    "max_checks": args.max_checks,
                    "interval_seconds": args.interval_seconds,
                    "trial_ids": trial_ids,
                    "status_files": [str(p) for p in status_files],
                    "alerted_count": len(alerted),
                    "last_events": events,
                }
            )

            # Exit when every watched trial has a terminal alert, if trials were requested.
            if trial_ids:
                pending = []
                for trial_id in trial_ids:
                    trial = latest_trial(trial_id)
                    verdict = str((trial or {}).get("verdict") or "")
                    if verdict not in TERMINAL_VERDICTS:
                        pending.append(trial_id)
                if not pending and all(
                    any(k.startswith(f"trial:{tid}:") for k in alerted) for tid in trial_ids
                ):
                    print("[watchdog] all watched trials terminal; exiting", flush=True)
                    return 0

            time.sleep(max(5, int(args.interval_seconds)))

        send_telegram(f"[{args.label}] Watchdog reached max_checks without full terminal coverage")
        return 1
    finally:
        if sys.platform == "win32" and not args.no_sleep_inhibit:
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)


if __name__ == "__main__":
    raise SystemExit(main())
