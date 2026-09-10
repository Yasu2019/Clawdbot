#!/usr/bin/env python3
"""Run and parse OpenFOAM checkMesh for a case."""
from __future__ import annotations
import argparse, json, re, subprocess
from pathlib import Path

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--case", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--log", type=Path, help="Parse an existing checkMesh log instead of running Docker")
    args = ap.parse_args()
    cmd = ["docker", "run", "--rm", "-v", f"{args.case.resolve()}:/case",
           "opencfd/openfoam-dev:latest", "bash", "-lc",
           "source /usr/lib/openfoam/openfoam2512/etc/bashrc >/dev/null 2>&1; checkMesh -case /case -constant"]
    if args.log:
        proc = subprocess.CompletedProcess(cmd, 0)
        text = args.log.read_text(errors="replace")
    else:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=300)
        text = proc.stdout + proc.stderr
    def num(pattern):
        m = re.search(pattern, text, re.I)
        return float(m.group(1).rstrip(".")) if m else None
    report = {
        "status": "PASS" if proc.returncode == 0 and "Failed" not in text else "FAIL",
        "returncode": proc.returncode,
        "cells": num(r"cells:\s+(\d+)"),
        "faces": num(r"faces:\s+(\d+)"),
        "points": num(r"points:\s+(\d+)"),
        "max_non_orthogonality_deg": num(r"non-orthogonality Max:\s*([0-9.eE+-]+)"),
        "max_skewness": num(r"Max skewness\s*=\s*([0-9.eE+-]+)"),
        "negative_volume_cells": num(r"negative volume cells:\s*(\d+)") if "negative volume cells" in text.lower() else (0 if "Cell volumes OK" in text else None),
        "total_volume": num(r"Total volume =\s*([0-9.eE+-]+)"),
        "closed_boundary": "boundary openness" in text.lower() and "open cells" not in text.lower(),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
