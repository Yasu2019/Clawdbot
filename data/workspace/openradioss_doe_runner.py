"""openradioss_doe_runner.py — Automated DOE execution for shear blanking.

Reads doe_analysis/doe_design_next.csv and runs each point sequentially:
  1. Patch starter/engine .rad files via rad_model
  2. Start engine in container via start_engine.sh
  3. Poll log until NORMAL/ABNORMAL TERMINATION or timeout
  4. Parse result and log to sim_trial DB

Run numbers are assigned sequentially starting from START_RUN_ID.
All runs use Inacti=6, TSTOP=0.025s (fixed per DOE design).

Usage:
    python openradioss_doe_runner.py [--dry-run] [--start-run N]

    --dry-run   : patch files and verify, do not execute engine
    --start-run : override starting run number (default: auto-detect from DB)
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
WORK_DIR = ROOT / "clawstack_v2/data/work"
CONTAINER = "clawstack-unified-openradioss-1"
STARTER_BASE = "4mmx4mm_ASSY_20260105_0000.rad"
ENGINE_BASE  = "4mmx4mm_ASSY_20260105_0001.rad"
DOE_CSV = ROOT / "data/workspace/doe_analysis/doe_design_next.csv"
GATE_T_S = 0.01813
POLL_INTERVAL = 60   # seconds between log checks
TIMEOUT_S = 14400    # 4 hours per run

sys.path.insert(0, str(ROOT / "data/workspace"))
import rad_model as rm
import sim_trial_logger as db


# ─────────────────────────────────────────────────────────────
# Container helpers
# ─────────────────────────────────────────────────────────────

def docker_exec(cmd: str) -> str:
    r = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-lc", cmd],
        text=True, encoding="utf-8", errors="replace",
        capture_output=True, check=False,
    )
    return r.stdout


def start_engine(run_id: int) -> None:
    result = subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-c",
         f"bash /work/start_engine.sh {run_id}"],
        text=True, encoding="utf-8", capture_output=True,
    )
    print(f"  [engine] start: {result.stdout.strip() or result.stderr.strip()}", flush=True)


def kill_engine() -> None:
    subprocess.run(
        ["docker", "exec", CONTAINER, "bash", "-c", "bash /work/kill_engine.sh"],
        capture_output=True,
    )


# ─────────────────────────────────────────────────────────────
# Result parsing
# ─────────────────────────────────────────────────────────────

def parse_log(run_id: int) -> dict:
    log = f"/work/engine_run{run_id}.log"
    last_nc  = docker_exec(f"grep 'NC=' {log} 2>/dev/null | tail -1").strip()
    term     = docker_exec(f"grep -E 'NORMAL TERMINATION|ABNORMAL TERMINATION' {log} 2>/dev/null | tail -1").strip()
    vel_err  = docker_exec(f"grep -E 'NODAL VELOCITY.*TOO HIGH|ERROR.*VELOCITY' {log} 2>/dev/null | tail -1").strip()

    result: dict = {}
    m = re.search(r'NC=\s*(\d+)\s+T=\s*([\d.E+\-]+)\s+DT=.*ERR=\s*([\d.\-]+)%', last_nc)
    if m:
        result["nc_final"]      = int(m.group(1))
        result["t_final_s"]     = float(m.group(2))
        result["t_final_ms"]    = float(m.group(2)) * 1000
        result["err_final_pct"] = float(m.group(3))

    if "NORMAL TERMINATION" in term:
        result["termination_type"] = "NORMAL_VELOCITY" if vel_err else "NORMAL_TSTOP"
        if vel_err:
            result["failure_mode"] = "NODAL VELOCITY TOO HIGH (Inacti=6)"
    elif "ABNORMAL" in term:
        result["termination_type"] = "ABNORMAL"
        result["failure_mode"] = "ABNORMAL TERMINATION (ERR=-100%)"
    else:
        result["termination_type"] = "UNKNOWN_OR_RUNNING"

    return result


def wait_for_completion(run_id: int) -> dict:
    log = f"/work/engine_run{run_id}.log"
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > TIMEOUT_S:
            print(f"  [timeout] Run{run_id} exceeded {TIMEOUT_S}s", flush=True)
            kill_engine()
            break
        out = docker_exec(f"grep -E 'NORMAL TERMINATION|ABNORMAL TERMINATION' {log} 2>/dev/null | tail -1")
        if "TERMINATION" in out:
            break
        last = docker_exec(f"grep 'NC=' {log} 2>/dev/null | tail -1").strip()
        if last:
            m = re.search(r'T=\s*([\d.E+\-]+)', last)
            t_ms = float(m.group(1)) * 1000 if m else 0
            print(f"  [poll] Run{run_id} {last.strip()} ({elapsed/60:.1f}min)", flush=True)
        time.sleep(POLL_INTERVAL)
    return parse_log(run_id)


# ─────────────────────────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────────────────────────

def next_run_id() -> int:
    try:
        rows = db.query_similar("openradioss", "shear_blanking_4mmx4mm", top_n=300)
        existing = {r[1] for r in rows}
        n = 48
        while n in existing:
            n += 1
        return n
    except Exception:
        return 48


# ─────────────────────────────────────────────────────────────
# Main loop
# ─────────────────────────────────────────────────────────────

def run_doe(dry_run: bool = False, start_run: int | None = None) -> None:
    rows = list(csv.DictReader(DOE_CSV.open(encoding="utf-8")))
    print(f"DOE points: {len(rows)}", flush=True)

    run_id = start_run if start_run else next_run_id()

    for row in sorted(rows, key=lambda r: int(r["run_priority"])):
        eps_eff = float(row["Eps_eff"])
        vc      = float(row["VC"])
        inacti  = int(row["Inacti"])
        tstop   = float(row["TSTOP"])

        print(f"\n{'='*60}", flush=True)
        print(f"Run{run_id}: Eps_eff={eps_eff} VC={vc} Inacti={inacti} TSTOP={tstop}", flush=True)

        # --- Patch files (always from orig backup to avoid accumulation) ---
        starter_path = WORK_DIR / STARTER_BASE
        engine_path  = WORK_DIR / ENGINE_BASE
        orig_starter = WORK_DIR / (STARTER_BASE.replace(".rad", "_orig.rad"))
        orig_engine  = WORK_DIR / (ENGINE_BASE.replace(".rad", "_orig.rad"))

        if not orig_starter.exists():
            shutil.copy2(starter_path, orig_starter)
            print(f"  [backup] created {orig_starter.name}", flush=True)
        if not orig_engine.exists():
            shutil.copy2(engine_path, orig_engine)
            print(f"  [backup] created {orig_engine.name}", flush=True)

        shutil.copy2(orig_starter, starter_path)
        shutil.copy2(orig_engine,  engine_path)

        model = rm.RadModel(starter_path)
        model.set_fail_gene1(eps_eff=eps_eff).set_inter_type25_all(inacti=inacti, vc=vc)
        model.write(starter_path)
        rm.set_engine_tstop(engine_path, tstop)

        actual = rm.RadModel(starter_path).verify()
        print(f"  [verify] {actual}", flush=True)
        assert abs(actual.get("Eps_eff", 0) - eps_eff) < 1e-5, f"Eps_eff mismatch: {actual.get('Eps_eff')} != {eps_eff}"
        assert abs(actual.get("VC",      0) - vc)      < 1e-5, f"VC mismatch: {actual.get('VC')} != {vc}"
        assert actual.get("Inacti") == inacti,                  f"Inacti mismatch: {actual.get('Inacti')} != {inacti}"

        if dry_run:
            print(f"  [dry-run] skipping engine execution", flush=True)
            run_id += 1
            continue

        # --- DB: register before start ---
        params = {"Eps_eff": eps_eff, "VC": vc, "Inacti": inacti,
                  "TSTOP": tstop, "EPS_p_max": float(row["EPS_p_max"]),
                  "DT": row["DT"], "FAIL_model": row["FAIL_model"]}
        trial_id = db.log_trial(
            solver="openradioss", analysis_type="shear_blanking_4mmx4mm",
            run_number=run_id, model_file=STARTER_BASE,
            parameters=params, status="running",
            log_file=f"/work/engine_run{run_id}.log",
        )
        print(f"  [db] trial_id={trial_id} registered", flush=True)

        # --- Execute ---
        start_engine(run_id)
        result = wait_for_completion(run_id)
        print(f"  [result] {result}", flush=True)

        # --- DB: update result ---
        term = result.get("termination_type", "UNKNOWN")
        t_ms = result.get("t_final_ms")
        status = "success" if (term == "NORMAL_TSTOP" and t_ms and t_ms >= GATE_T_S * 1000) else "failed"
        if term == "NORMAL_TSTOP" and t_ms:
            status = "success"

        db.update_trial(
            trial_id=trial_id,
            status=status,
            results={
                "nc_final":           result.get("nc_final"),
                "err_final_pct":      result.get("err_final_pct"),
                "termination_type":   term,
            },
            max_time_reached=result.get("t_final_s"),
            failure_mode=result.get("failure_mode"),
        )
        print(f"  [db] updated: status={status} T={t_ms}ms term={term}", flush=True)

        run_id += 1

    print(f"\nDOE complete. {len(rows)} runs executed.", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--start-run", type=int, default=None)
    args = parser.parse_args()
    run_doe(dry_run=args.dry_run, start_run=args.start_run)
