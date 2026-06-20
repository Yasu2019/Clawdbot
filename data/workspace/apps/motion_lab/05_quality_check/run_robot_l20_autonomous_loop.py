import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_robot_l20_motion_trials import DASHBOARD, run_trials, write_html, write_report, OUT_JSON


ROOT = Path(__file__).resolve().parents[5]
STATUS_PATH = DASHBOARD / "robot_l20_autonomous_status.json"
HISTORY_PATH = DASHBOARD / "robot_l20_autonomous_history.jsonl"
BEST_PATH = DASHBOARD / "robot_l20_autonomous_best.json"


def load_best() -> dict[str, Any] | None:
    if not BEST_PATH.exists():
        return None
    try:
        return json.loads(BEST_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None


def task_floor(payload: dict[str, Any]) -> float:
    scores = payload["best_trial"]["metrics"].get("task_scores") or {}
    if not scores:
        return 0.0
    return min(float(v) for v in scores.values())


def is_improvement(payload: dict[str, Any], previous: dict[str, Any] | None) -> bool:
    if previous is None:
        return True
    current_key = (
        int(payload.get("best_score", 0)),
        float(task_floor(payload)),
        int(payload.get("l20_candidate_count", 0)),
    )
    prev_key = (
        int(previous.get("best_score", 0)),
        float(task_floor(previous)),
        int(previous.get("l20_candidate_count", 0)),
    )
    return current_key > prev_key


def write_status(status: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")


def append_history(record: dict[str, Any]) -> None:
    with HISTORY_PATH.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def notify_improvement(payload: dict[str, Any], cycle: int) -> bool:
    try:
        sys.path.insert(0, str((ROOT / "data" / "workspace").resolve()))
        from notify_image import send_telegram_text
    except Exception:
        return False

    scores = payload["best_trial"]["metrics"].get("task_scores") or {}
    text = (
        f"Robot L20 autonomous cycle {cycle}: improvement recorded. "
        f"best={payload['best_score']} {payload['best_verdict']}, "
        f"candidates={payload['l20_candidate_count']}, task_floor={task_floor(payload):.1f}, "
        f"scores={scores}. Real L20 still requires visual render review."
    )
    return bool(send_telegram_text(text))


def run_loop(cycles: int, sleep_sec: float, count: int, refine_top: int, seed_base: int, notify: bool) -> dict[str, Any]:
    best = load_best()
    final_status: dict[str, Any] = {}
    for cycle in range(1, cycles + 1):
        cycle_seed = seed_base + cycle * 1009
        started_at = datetime.now(timezone.utc).isoformat()
        payload = run_trials(count=count, seed_base=cycle_seed, refine_top=refine_top)
        improved = is_improvement(payload, best)

        if improved:
            best = payload
            BEST_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            OUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            write_report(payload)
            write_html(payload)

        record = {
            "cycle": cycle,
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "seed_base": cycle_seed,
            "best_score": payload["best_score"],
            "best_verdict": payload["best_verdict"],
            "l20_candidate_count": payload["l20_candidate_count"],
            "task_floor": task_floor(payload),
            "improved": improved,
        }
        append_history(record)
        notified = notify_improvement(payload, cycle) if notify and improved else False
        final_status = {
            "schema": "clawstack.robot_l20_autonomous_loop.v1",
            "state": "running" if cycle < cycles else "completed",
            "updated_at": record["finished_at"],
            "cycles_requested": cycles,
            "cycles_completed": cycle,
            "sleep_sec": sleep_sec,
            "count": count,
            "refine_top": refine_top,
            "last_cycle": record,
            "best_summary": {
                "best_score": best["best_score"] if best else None,
                "best_verdict": best["best_verdict"] if best else None,
                "l20_candidate_count": best["l20_candidate_count"] if best else None,
                "task_floor": task_floor(best) if best else None,
                "seed_base": best.get("seed_base") if best else None,
            },
            "telegram_notified": notified,
            "outputs": {
                "status": str(STATUS_PATH),
                "history": str(HISTORY_PATH),
                "best": str(BEST_PATH),
                "trial_status": str(OUT_JSON),
                "trial_html": str(DASHBOARD / "robot_l20_motion_trials.html"),
            },
            "safety_note": "Bounded proxy loop only. It does not edit robot model geometry or deploy to real hardware.",
        }
        write_status(final_status)
        if cycle < cycles and sleep_sec > 0:
            time.sleep(sleep_sec)
    return final_status


def main() -> int:
    parser = argparse.ArgumentParser(description="Bounded autonomous Robot L20 proxy development loop.")
    parser.add_argument("--cycles", type=int, default=5)
    parser.add_argument("--sleep-sec", type=float, default=2.0)
    parser.add_argument("--count", type=int, default=96)
    parser.add_argument("--refine-top", type=int, default=12)
    parser.add_argument("--seed-base", type=int, default=20260620)
    parser.add_argument("--notify", action="store_true")
    args = parser.parse_args()

    cycles = max(1, min(args.cycles, 200))
    count = max(16, min(args.count, 500))
    refine_top = max(1, min(args.refine_top, count))
    status = run_loop(
        cycles=cycles,
        sleep_sec=max(0.0, args.sleep_sec),
        count=count,
        refine_top=refine_top,
        seed_base=args.seed_base,
        notify=args.notify,
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
