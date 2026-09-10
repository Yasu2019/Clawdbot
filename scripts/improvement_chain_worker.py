#!/usr/bin/env python3
"""Bounded background evidence worker for the 50-step improvement chain.

This worker only invokes auditable local checks and updates its own ledger.
It never stops, deletes, or overwrites legacy jobs/cases.
"""
from __future__ import annotations
import argparse
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    ap.add_argument("--iterations", type=int, default=50)
    ap.add_argument("--interval-sec", type=int, default=60)
    args = ap.parse_args()
    root = args.root.resolve()
    out = root / "artifacts/box_roundhole_v5/improvement_chain_20260910.json"
    state_path = root / "artifacts/box_roundhole_v5/improvement_chain_worker_state.json"
    state = {"started_utc": datetime.now(timezone.utc).isoformat(), "iterations": 0,
             "policy": "no legacy task stop/delete/overwrite"}
    for n in range(1, args.iterations + 1):
        cmd = [sys.executable, str(root / "scripts/run_improvement_chain.py"),
               "--output", str(out), "--count", "50"]
        result = subprocess.run(cmd, cwd=root, capture_output=True, text=True)
        state.update({"iterations": n, "last_utc": datetime.now(timezone.utc).isoformat(),
                      "last_returncode": result.returncode})
        if result.returncode != 0:
            state["last_error"] = result.stderr[-2000:]
            state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
            return result.returncode
        state_path.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        if n < args.iterations:
            time.sleep(max(1, args.interval_sec))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
