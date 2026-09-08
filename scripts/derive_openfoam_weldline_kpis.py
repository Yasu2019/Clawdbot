#!/usr/bin/env python3
"""Derive an auditable OpenFOAM flow-front meeting (weld-line) proxy.

This never labels the result as a commercial Moldflow weld quality result.
It uses first arrival of alpha.polymer >= threshold and late-fill spatial ridges.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from mf_of_weldline_proxy import of_weld_from_alpha_fill_arrival


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--case", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--alpha-threshold", type=float, default=0.5)
    p.add_argument("--late-percentile", type=float, default=0.85)
    args = p.parse_args()
    result = of_weld_from_alpha_fill_arrival(
        args.case,
        alpha_thresh=args.alpha_threshold,
        late_percentile=args.late_percentile,
    )
    result["schema"] = "clawstack.openfoam_weldline_proxy.v1"
    result["case"] = str(args.case)
    result["formal_status"] = "PROXY_ONLY"
    result["visual_qc_required"] = True
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({
        "output": str(args.output),
        "weldline_count": result.get("weldline_count", 0),
        "accuracy_band": result.get("accuracy_band"),
        "formal_status": result["formal_status"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
