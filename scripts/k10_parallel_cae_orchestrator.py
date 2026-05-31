# -*- coding: utf-8 -*-
"""Run OpenRadioss on K10 and OpenFOAM trials on LAVIE in parallel (SJP-2).

Optional SJP-3: add K10 gap jobs (Cetol proxy + DXF2STEP check) in a third thread.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
JST = timezone(timedelta(hours=9))
LOG_PATH = ROOT / "data" / "workspace" / "parallel_cae_log.jsonl"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_gap_job_runner as gap_jobs
import k10_satellite_cae_dispatch as cae_dispatch


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["logged_at"] = datetime.now(JST).isoformat()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_openradioss_k10(
    category: str,
    max_trials: int,
    dry_run: bool,
    timeout: int,
    results: dict[str, Any],
) -> None:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "cae_te_engine.py"),
        "--category",
        category,
        "--max-trials",
        str(max_trials),
        "--timeout",
        str(timeout),
    ]
    if dry_run:
        cmd.append("--dry-run")
    print(f"[parallel-or] K10 OpenRadioss start category={category} max={max_trials}")
    proc = subprocess.run(
        cmd,
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    results["openradioss"] = {
        "exit_code": proc.returncode,
        "stdout_tail": (proc.stdout or "")[-3000:],
        "stderr_tail": (proc.stderr or "")[-2000:],
    }
    print(f"[parallel-or] K10 OpenRadioss done exit={proc.returncode}")


def run_openfoam_lavie_loop(
    category: str,
    max_trials: int,
    dry_run: bool,
    timeout: int,
    node: str,
    results: dict[str, Any],
) -> None:
    trials: list[dict[str, Any]] = []
    print(f"[parallel-of] LAVIE OpenFOAM start category={category} max={max_trials}")
    for idx in range(max_trials):
        trial_id = f"parallel-{category}-{uuid.uuid4().hex[:8]}"
        decision = router.pick_host(category, router.load_config())
        host = "lavie" if decision.get("host") == "lavie" else "lavie"
        print(f"[parallel-of] trial {idx + 1}/{max_trials} -> {host} ({decision.get('reason')})")
        try:
            if host == "lavie":
                token = cae_dispatch.sjp.load_token()
                bundle = cae_dispatch.run_lavie_trial(
                    node=node,
                    category=category,
                    params=None,
                    trial_id=trial_id,
                    dry_run=dry_run,
                    timeout=timeout,
                    token=token,
                    cfg=router.load_config(),
                )
                trial_entry = bundle["trial_entry"]
                cae_dispatch.merge_trial_into_log(trial_entry)
            else:
                trial_entry = cae_dispatch.run_local_trial(
                    category=category,
                    params=None,
                    trial_id=trial_id,
                    dry_run=dry_run,
                    timeout=timeout,
                )
                cae_dispatch.merge_trial_into_log(trial_entry)
            trials.append({"trial_id": trial_id, "verdict": trial_entry.get("verdict"), "host": trial_entry.get("host")})
            print(f"[parallel-of] verdict={trial_entry.get('verdict')}")
        except Exception as exc:
            trials.append({"trial_id": trial_id, "verdict": "ERROR", "error": str(exc)})
            print(f"[parallel-of] ERROR {exc}")
        if not dry_run:
            time.sleep(3)
    results["openfoam"] = {"trials": trials}
    print(f"[parallel-of] LAVIE OpenFOAM loop done count={len(trials)}")


def run_sjp3_gap_jobs(jobs_csv: str, difficulty: int, results: dict[str, Any]) -> None:
    job_list = [j.strip() for j in jobs_csv.split(",") if j.strip()]
    print(f"[parallel-sjp3] K10 gap jobs start: {job_list}")
    summary = gap_jobs.run_gap_jobs(job_list, difficulty)
    results["sjp3_gap"] = summary
    print(f"[parallel-sjp3] done all_ok={summary.get('all_ok')}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Parallel CAE: OpenRadioss@K10 + OpenFOAM@LAVIE")
    parser.add_argument("--or-category", default="press_blanking", help="OpenRadioss category on K10")
    parser.add_argument("--of-category", default="resin_flow", help="OpenFOAM category on LAVIE")
    parser.add_argument("--or-max-trials", type=int, default=3)
    parser.add_argument("--of-max-trials", type=int, default=3)
    parser.add_argument("--node", default="lavie")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--or-only", action="store_true")
    parser.add_argument("--of-only", action="store_true")
    parser.add_argument(
        "--sjp3",
        action="store_true",
        help="Run SJP-3 gap jobs on K10 (tolerance + dxf2step) in parallel",
    )
    parser.add_argument(
        "--gap-jobs",
        default="tolerance,dxf2step",
        help="Comma list for --sjp3 (tolerance,cetol,dxf2step)",
    )
    parser.add_argument("--gap-difficulty", type=int, default=1)
    args = parser.parse_args()

    cfg = router.load_config()
    ok, reason = router.probe_lavie_job_worker(cfg)
    if not args.or_only and not ok:
        print(f"[NG] LAVIE worker offline: {reason}", file=sys.stderr)
        return 1

    results: dict[str, Any] = {}
    threads: list[threading.Thread] = []

    if not args.of_only:
        t_or = threading.Thread(
            target=run_openradioss_k10,
            args=(args.or_category, args.or_max_trials, args.dry_run, args.timeout, results),
            daemon=True,
        )
        threads.append(t_or)

    if not args.or_only:
        t_of = threading.Thread(
            target=run_openfoam_lavie_loop,
            args=(args.of_category, args.of_max_trials, args.dry_run, args.timeout, args.node, results),
            daemon=True,
        )
        threads.append(t_of)

    if args.sjp3:
        t_gap = threading.Thread(
            target=run_sjp3_gap_jobs,
            args=(args.gap_jobs, args.gap_difficulty, results),
            daemon=True,
        )
        threads.append(t_gap)

    print("[parallel-orchestrator] starting parallel CAE sessions...")
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    entry = {
        "or_category": args.or_category,
        "of_category": args.of_category,
        "dry_run": args.dry_run,
        "sjp3": bool(args.sjp3),
        "gap_jobs": args.gap_jobs if args.sjp3 else None,
        "results": results,
    }
    append_log(entry)
    print(json.dumps(entry, ensure_ascii=False, indent=2))
    print(f"\nlog: {LOG_PATH}")
    print(f"te_log: {cae_dispatch.TE_LOG}")

    or_ok = args.of_only or results.get("openradioss", {}).get("exit_code") == 0
    of_trials = results.get("openfoam", {}).get("trials", [])
    of_ok = args.or_only or (len(of_trials) > 0 and all(t.get("verdict") != "ERROR" for t in of_trials))
    gap_ok = (not args.sjp3) or results.get("sjp3_gap", {}).get("all_ok", False)
    ok_all = or_ok and of_ok and gap_ok
    print(f"\nRESULT: {'PASS' if ok_all else 'FAIL'}")
    return 0 if ok_all else 1


if __name__ == "__main__":
    raise SystemExit(main())
