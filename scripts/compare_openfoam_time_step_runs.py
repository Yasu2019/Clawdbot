#!/usr/bin/env python3
"""Compare final integral diagnostics from two OpenFOAM runs."""
from __future__ import annotations
import argparse, json, re
from pathlib import Path

def last(pattern: str, text: str) -> float:
    values = re.findall(pattern, text)
    if not values:
        raise ValueError(f"missing diagnostic: {pattern}")
    return float(values[-1])

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reference", type=Path, required=True)
    ap.add_argument("--candidate", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    r, c = a.reference.read_text(errors="replace"), a.candidate.read_text(errors="replace")
    names = {"mass": r"volIntegrate\(region0\) of rho = ([0-9.eE+-]+)",
             "polymer_volume": r"volIntegrate\(region0\) of alpha\.polymer = ([0-9.eE+-]+)",
             "thermal_integral": r"volIntegrate\(region0\) of T = ([0-9.eE+-]+)"}
    ref = {k: last(p, r) for k, p in names.items()}
    cand = {k: last(p, c) for k, p in names.items()}
    rel = {k: abs(cand[k] - ref[k]) / max(abs(ref[k]), 1e-30) for k in names}
    report = {"status": "PASS" if max(rel.values()) < 1e-3 else "REVIEW",
              "reference": ref, "candidate": cand, "relative_difference": rel,
              "criterion": "max relative difference < 1e-3"}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1

if __name__ == "__main__":
    raise SystemExit(main())
