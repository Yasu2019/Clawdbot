# -*- coding: utf-8 -*-
"""Pressure-unit and first-order power-law calibration gates for MF vs OF."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math


def pa_to_mpa(value_pa: float) -> float:
    value = float(value_pa)
    if not math.isfinite(value):
        raise ValueError("pressure must be finite")
    return value / 1.0e6


def first_order_power_law_k(
    *, current_k: float, of_pressure_pa: float, mf_pressure_mpa: float,
    min_k: float = 1.0e-6, max_k: float = 50.0,
) -> dict[str, float]:
    """Scale k by pressure ratio for one bounded verification trial.

    Fixed inlet velocity makes fill time weakly dependent on k, while viscous
    pressure is approximately linear in k. The result is a trial proposal, not
    a validated material law.
    """
    k = float(current_k)
    of_mpa = pa_to_mpa(of_pressure_pa)
    mf_mpa = float(mf_pressure_mpa)
    if not all(math.isfinite(v) and v > 0 for v in (k, of_mpa, mf_mpa)):
        raise ValueError("k and pressures must be positive finite values")
    ratio = mf_mpa / of_mpa
    proposed = k * ratio
    if not min_k <= proposed <= max_k:
        raise ValueError(f"proposed k outside gate: {proposed}")
    return {
        "current_k": k,
        "of_pressure_MPa": of_mpa,
        "mf_pressure_MPa": mf_mpa,
        "pressure_ratio": ratio,
        "proposed_k": proposed,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--current-k", type=float, required=True)
    parser.add_argument("--of-pressure-pa", type=float, required=True)
    parser.add_argument("--mf-pressure-mpa", type=float, required=True)
    args = parser.parse_args()
    print(json.dumps(first_order_power_law_k(
        current_k=args.current_k,
        of_pressure_pa=args.of_pressure_pa,
        mf_pressure_mpa=args.mf_pressure_mpa,
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

