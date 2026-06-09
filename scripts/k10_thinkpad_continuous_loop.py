# -*- coding: utf-8 -*-
"""Run guarded 24x7 SSH work allocation from K10 to the Ubuntu ThinkPad."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import k10_thinkpad_ssh_dispatch
import thinkpad_ssh_metrics

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
REGISTRY = WORKSPACE / "thinkpad_node_registry.json"
STATUS_PATH = WORKSPACE / "thinkpad_continuous_loop_status.json"
LOG_PATH = WORKSPACE / "thinkpad_continuous_loop_log.jsonl"
PID_PATH = WORKSPACE / "thinkpad_continuous_loop.pid"
JST = timezone(timedelta(hours=9))

DEFAULT_SEQUENCE = [
    "qms_iatf_probe",
    "document_parse_probe",
    "rag_index_probe",
    "dataset_download_probe",
    "cae_pregate_probe",
    "health_snapshot",
]

DEFAULT_THRESHOLDS = {
    "max_cpu_percent": 80.0,
    "max_ram_percent": 75.0,
    "max_temp_c": 75.0,
}


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
    finally:
        if tmp.exists():
            try:
                tmp.unlink()
            except OSError:
                pass


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_thresholds() -> dict[str, float]:
    registry = read_json(REGISTRY)
    thresholds = dict(DEFAULT_THRESHOLDS)
    for key in thresholds:
        value = registry.get(key)
        if isinstance(value, (int, float)):
            thresholds[key] = float(value)
    return thresholds


def guard_decision(metrics: dict[str, Any], thresholds: dict[str, float]) -> tuple[bool, list[str]]:
    reasons: list[str] = []
    if not metrics.get("ok"):
        reasons.append(f"metrics_unavailable: {metrics.get('error') or 'unknown'}")
        return False, reasons

    cpu = float(metrics.get("cpu_usage_percent") or 0.0)
    ram = float(metrics.get("ram_usage_percent") or 0.0)
    temp_value = metrics.get("thermal_control_temp_c")
    temp = float(temp_value) if isinstance(temp_value, (int, float)) else None

    if cpu >= thresholds["max_cpu_percent"]:
        reasons.append(f"cpu_high {cpu:.1f}>={thresholds['max_cpu_percent']:.1f}")
    if ram >= thresholds["max_ram_percent"]:
        reasons.append(f"ram_high {ram:.1f}>={thresholds['max_ram_percent']:.1f}")
    if temp is not None and temp >= thresholds["max_temp_c"]:
        reasons.append(f"temp_high {temp:.1f}>={thresholds['max_temp_c']:.1f}")

    return not reasons, reasons


def choose_job(sequence: list[str], cycle_count: int) -> str:
    if not sequence:
        return "health_snapshot"
    return sequence[cycle_count % len(sequence)]


def status_payload(
    *,
    running: bool,
    cycle_count: int,
    poll_seconds: int,
    thresholds: dict[str, float],
    metrics: dict[str, Any] | None,
    decision: str,
    reasons: list[str],
    last_job: dict[str, Any] | None,
    fail_streak: int,
    next_run_after: str | None,
) -> dict[str, Any]:
    return {
        "running": running,
        "updated_at": now_iso(),
        "node": "thinkpad",
        "mode": "guarded_24x7_ssh_loop",
        "poll_seconds": poll_seconds,
        "thresholds": thresholds,
        "cycle_count": cycle_count,
        "decision": decision,
        "guard_reasons": reasons,
        "fail_streak": fail_streak,
        "next_run_after": next_run_after,
        "last_metrics": metrics,
        "last_job": last_job,
        "allowed_sequence": DEFAULT_SEQUENCE,
        "blocked_workloads": [
            "openradioss_real_solver",
            "openfoam_real_solver",
            "long_video_render",
            "unbounded_download_loop",
        ],
    }


def run_cycle(sequence: list[str], cycle_count: int, poll_seconds: int, fail_streak: int, timeout: int) -> tuple[int, int]:
    thresholds = load_thresholds()
    metrics = thinkpad_ssh_metrics.collect_metrics()
    thinkpad_ssh_metrics.write_outputs(metrics)
    allowed, reasons = guard_decision(metrics, thresholds)
    last_job: dict[str, Any] | None = None
    decision = "guard_hold"

    if allowed:
        job_type = choose_job(sequence, cycle_count)
        try:
            last_job = k10_thinkpad_ssh_dispatch.run_job(job_type, timeout=timeout)
            decision = "job_dispatched"
            fail_streak = 0 if last_job.get("status") == "ok" else fail_streak + 1
        except Exception as exc:
            fail_streak += 1
            decision = "dispatch_error"
            reasons = [str(exc)[:300]]
            last_job = {
                "job_type": job_type,
                "status": "failed",
                "error": str(exc)[:300],
                "finished_at": now_iso(),
            }
    else:
        fail_streak += 1

    next_delay = poll_seconds
    if fail_streak >= 3:
        next_delay = max(poll_seconds, 1800)
    next_run_after = (datetime.now(JST) + timedelta(seconds=next_delay)).isoformat(timespec="seconds")
    payload = status_payload(
        running=True,
        cycle_count=cycle_count + 1,
        poll_seconds=poll_seconds,
        thresholds=thresholds,
        metrics=metrics,
        decision=decision,
        reasons=reasons,
        last_job=last_job,
        fail_streak=fail_streak,
        next_run_after=next_run_after,
    )
    atomic_write_json(STATUS_PATH, payload)
    append_log(payload)
    return cycle_count + 1, fail_streak


def parse_sequence(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_SEQUENCE)
    sequence = [item.strip() for item in raw.split(",") if item.strip()]
    allowed = set(k10_thinkpad_ssh_dispatch.JOB_COMMANDS)
    bad = [item for item in sequence if item not in allowed]
    if bad:
        raise ValueError(f"unsupported job sequence items: {', '.join(bad)}")
    return sequence or list(DEFAULT_SEQUENCE)


def main() -> int:
    parser = argparse.ArgumentParser(description="Guarded 24x7 ThinkPad SSH job allocation loop")
    parser.add_argument("--once", action="store_true", help="run one guarded cycle and exit")
    parser.add_argument("--poll-seconds", type=int, default=900)
    parser.add_argument("--max-cycles", type=int, default=0, help="0 means run forever")
    parser.add_argument("--job-sequence", default=None, help="comma-separated dispatch job types")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    sequence = parse_sequence(args.job_sequence)
    PID_PATH.write_text(str(__import__("os").getpid()), encoding="ascii")
    cycle_count = 0
    fail_streak = 0

    try:
        while True:
            cycle_count, fail_streak = run_cycle(sequence, cycle_count, args.poll_seconds, fail_streak, args.timeout)
            if args.once or (args.max_cycles and cycle_count >= args.max_cycles):
                break
            sleep_seconds = args.poll_seconds if fail_streak < 3 else max(args.poll_seconds, 1800)
            time.sleep(sleep_seconds)
    finally:
        current = read_json(STATUS_PATH)
        current["running"] = False if args.once or (args.max_cycles and cycle_count >= args.max_cycles) else current.get("running", True)
        current["updated_at"] = now_iso()
        atomic_write_json(STATUS_PATH, current)

    print(f"[OK] thinkpad continuous loop cycles={cycle_count} status={STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
