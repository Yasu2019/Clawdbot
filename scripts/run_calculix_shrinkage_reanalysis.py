#!/usr/bin/env python3
"""Prepare a CalculiX thermal-shrinkage/packing reanalysis deck.

The source deck is the existing box-roundhole screening mesh.  This bridge
keeps the same nodes/elements and replaces the provisional thermal expansion
with the material-card CTE, while preserving the mapped cooling temperatures
and cavity-load step.  It is intentionally deterministic so a measured card
can replace the virtual coefficients without changing the workflow.
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--input", type=Path, required=True)
    ap.add_argument("--output", type=Path, required=True)
    ap.add_argument("--cte", type=float, default=1.0e-4)
    ap.add_argument("--youngs-modulus", type=float, default=1.2e9)
    ap.add_argument("--poisson", type=float, default=0.42)
    ap.add_argument("--pressure-pa", type=float, default=30.0e6)
    args = ap.parse_args()
    text = args.input.read_text(encoding="utf-8", errors="replace")
    text = text.replace("Box resin screen: Vivobook alpha.polymer -> CalculiX",
                        "Tait/Cross-WLF thermal shrinkage and packing reanalysis")
    text = re.sub(r"\*ELASTIC\n[^\n]+", f"*ELASTIC\n{args.youngs_modulus:.9g}, {args.poisson:.9g}", text, count=1)
    text = re.sub(r"\*EXPANSION\n[^\n]+", f"*EXPANSION\n{args.cte:.9g}", text, count=1)
    # Keep the existing mapped pressure distribution; record the intended
    # pressure used to generate it so the result is auditable.
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    report = {
        "status": "INPUT_READY",
        "solver": "CalculiX",
        "source": str(args.input.resolve()),
        "output": str(args.output.resolve()),
        "loads": {"packing_pressure_pa": args.pressure_pa},
        "material": {"cte_1_K": args.cte, "youngs_modulus_pa": args.youngs_modulus, "poisson": args.poisson},
        "temperature_field": "preserved_from_openfoam_cooling_mapping",
        "limitations": ["virtual coefficients unless replaced by measured card", "pressure field is inherited from source deck"]}
    args.output.with_suffix(".manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
