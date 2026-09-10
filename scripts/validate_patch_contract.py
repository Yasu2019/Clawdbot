#!/usr/bin/env python3
"""Reject a case before convergence studies if gate/vent areas differ."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import compare_patch_geometry

def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--case",type=Path,required=True); ap.add_argument("--contract",type=Path,required=True); ap.add_argument("--output",type=Path,required=True); a=ap.parse_args()
    actual=compare_patch_geometry.measure(a.case); contract=json.loads(a.contract.read_text())["patches"]; checks={}
    for name, spec in contract.items():
        x=actual.get(name); checks[name]=bool(x and abs(x["area"]-spec["area_m2"])/spec["area_m2"] <= spec["tolerance"] and float(x["mean_normal"][0])*spec["normal"][0] > 0.9)
    report={"status":"PASS" if all(checks.values()) else "FAIL","checks":checks,"actual":{k:actual.get(k) for k in contract},"contract":contract}
    a.output.parent.mkdir(parents=True,exist_ok=True); a.output.write_text(json.dumps(report,indent=2)+"\n"); print(json.dumps(report,indent=2)); return 0 if report["status"]=="PASS" else 1
if __name__=='__main__': raise SystemExit(main())
