# -*- coding: utf-8 -*-
"""Compare Dynabook Moldflow Fill KPIs vs Lavie OpenFOAM proxy run."""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HANDOFF = (
    ROOT
    / "data"
    / "workspace"
    / "moldflow_bridge"
    / "mf_to_of_handoff_box_xplus_d2_20260720.json"
)


def _rel(a: float, b: float) -> float | None:
    if b == 0:
        return None
    return (a - b) / abs(b)


def scorecard(mf: dict[str, Any], of: dict[str, Any], band: dict[str, Any]) -> dict[str, Any]:
    fill_tol = float(band.get("fill_time_rel_tol", 0.25))
    fill_min = float(band.get("fill_fraction_min_pct", 99.0))
    rows = []

    def add(name: str, mf_v: float | None, of_v: float | None, ok: bool | None, note: str = "") -> None:
        rows.append(
            {
                "kpi": name,
                "moldflow": mf_v,
                "openfoam": of_v,
                "rel_err": _rel(of_v, mf_v) if (mf_v is not None and of_v is not None) else None,
                "pass": ok,
                "note": note,
            }
        )

    mf_ft = mf.get("fill_time_s")
    of_ft = of.get("fill_time_s")
    if mf_ft and of_ft:
        rel = abs(_rel(float(of_ft), float(mf_ft)) or 99)
        add("fill_time_s", float(mf_ft), float(of_ft), rel <= fill_tol, f"tol=+/-{fill_tol:.0%}")
    else:
        add("fill_time_s", mf_ft, of_ft, False, "missing")

    mf_ff = mf.get("fill_fraction_pct")
    of_ff = of.get("fill_fraction_pct")
    if of_ff is not None:
        add(
            "fill_fraction_pct",
            float(mf_ff) if mf_ff is not None else None,
            float(of_ff),
            float(of_ff) >= fill_min,
            f"min={fill_min}",
        )

    pressure_kpi = (
        "pressure_end_of_fill_MPa"
        if mf.get("pressure_end_of_fill_MPa") is not None
        else "peak_pressure_MPa"
    )
    mf_p = mf.get("pressure_end_of_fill_MPa", mf.get("peak_injection_pressure_MPa"))
    of_p = of.get("peak_pressure_MPa")
    if mf_p is not None and of_p is not None:
        # pressure band looser until Cross-WLF calibrated
        p_tol = float(band.get("pressure_rel_tol", 0.5))
        rel = abs(_rel(float(of_p), float(mf_p)) or 99)
        add(pressure_kpi, float(mf_p), float(of_p), rel <= p_tol, f"tol=+/-{p_tol:.0%}")
    else:
        add(pressure_kpi, mf_p, of_p, None, "OF pressure not yet extracted")

    add(
        "mesh_elements",
        float(mf.get("mesh_triangles") or 0) or None,
        float(of.get("cells") or 0) or None,
        None,
        "MF midplane tris vs OF 3D cells (not apples-to-apples)",
    )

    mf_w = mf.get("weldline_count")
    of_w = of.get("weldline_count")
    if mf_w is not None or of_w is not None:
        add(
            "weldline_count",
            float(mf_w) if mf_w is not None else None,
            float(of_w) if of_w is not None else None,
            None,
            "location PROXY via mf_of_weldline_proxy.py (not MF weld quality)",
        )

    mandatory = {"fill_time_s", "fill_fraction_pct", pressure_kpi}
    mandatory_rows = [row for row in rows if row["kpi"] in mandatory]
    # Never promote on fill alone. Every mandatory KPI must be present and pass.
    label = (
        "PROXY_OK"
        if len(mandatory_rows) == len(mandatory)
        and all(row["pass"] is True for row in mandatory_rows)
        else "PROXY_GAP"
    )
    return {
        "label": label,
        "rows": rows,
        "never_claim": "MOLDFLOW_EQUIVALENT",
    }


def propose_next_params(
    mf: dict[str, Any], of: dict[str, Any], current_u: float, power_law_k: float
) -> dict[str, Any]:
    """Calibrate forced-velocity fill time; raise rheology toward MF Cross n~0.275."""
    mf_ft = float(mf.get("fill_time_s") or 1.077)
    of_ft = float(of.get("fill_time_s") or 0.0)
    u = float(current_u)
    if of_ft > 0 and mf_ft > 0:
        # IF OF fills faster THEN reduce U proportionally BECAUSE velocity BC dominates fill time
        u_cal = u * (of_ft / mf_ft)
    else:
        u_cal = u
    return {
        "inlet_velocity": round(u_cal, 4),
        "analysis_end_time_s": round(mf_ft * 1.15, 3),
        "mf_fill_time_s": mf_ft,
        "polymer_rho_kg_m3": 900.0,
        "transportModel": "powerLaw",
        "power_law_n": 0.275,
        "power_law_k": float(power_law_k),
        "power_law_nuMax": 50.0,
        "power_law_nuMin": 1.0e-4,
        "polymer_nu_newtonian_fallback": 0.05,
        "T_melt": 513.15,
        "T_mold": 313.15,
        "max_global_cells": 120000,
        "mesh_note": "keep ~25k coarse family; refine only if gate under-resolved",
        "rationale": {
            "u_from": u,
            "u_to": round(u_cal, 4),
            "of_fill_time_observed": of_ft,
            "mf_fill_time": mf_ft,
            "rheology": "powerLaw n=0.275 from MF Cross block; raise effective viscosity for pressure",
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--handoff", default=str(DEFAULT_HANDOFF))
    ap.add_argument("--of-json", default="", help="OF result JSON override")
    ap.add_argument(
        "--of-fill-time",
        type=float,
        default=0.804,
        help="Observed OF fill time (when alpha~1)",
    )
    ap.add_argument("--of-fill-fraction", type=float, default=99.95)
    ap.add_argument("--of-cells", type=int, default=24928)
    ap.add_argument("--of-peak-p-mpa", type=float, default=-1.0)
    ap.add_argument("--current-u", type=float, default=14.21)
    ap.add_argument("--power-law-k", type=float, default=-1.0)
    ap.add_argument("--write", default="", help="Write scorecard JSON path")
    args = ap.parse_args()

    handoff = json.loads(Path(args.handoff).read_text(encoding="utf-8-sig"))
    mf = dict(handoff.get("mf_kpis") or {})
    target = dict(handoff.get("of_target") or {})
    if target.get("pressure_end_of_fill_MPa") is not None:
        mf["pressure_end_of_fill_MPa"] = float(target["pressure_end_of_fill_MPa"])
    band = dict(handoff.get("accuracy_band") or {})
    if args.of_json:
        of = json.loads(Path(args.of_json).read_text(encoding="utf-8-sig"))
    else:
        of = {
            "fill_time_s": args.of_fill_time,
            "fill_fraction_pct": args.of_fill_fraction,
            "fill_complete": args.of_fill_fraction >= 99.0,
            "cells": args.of_cells,
            "peak_pressure_MPa": None if args.of_peak_p_mpa < 0 else args.of_peak_p_mpa,
            "inlet_velocity": args.current_u,
            "transport": "Newtonian nu=0.01 rho=1200",
        }

    sc = scorecard(mf, of, band)
    next_k = (
        args.power_law_k
        if args.power_law_k > 0
        else float(target.get("power_law_k") or 0.05)
    )
    nxt = propose_next_params(mf, of, args.current_u, next_k)
    out = {
        "comparison_id": "box_phi2_mfalign_coarse_v1",
        "moldflow": mf,
        "openfoam": of,
        "scorecard": sc,
        "next_of_params": nxt,
        "gaps_ranked": [
            "1 Rheology: Newtonian nu=0.01 too thin vs MF Cross n~0.275 (pressure under-predicted)",
            "2 Density: OF rho=1200 vs PP melt ~900",
            "3 Fill time: OF faster with U=14.21 -> calibrate U down",
            "4 Thermal: OF isothermal; MF melt/mold 240/40 C",
            "5 Mesh family: OF 3D ~25k vs MF midplane 3552 (acceptable for PROXY)",
        ],
    }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    if args.write:
        Path(args.write).write_text(text + "\n", encoding="utf-8")
    print(text)
    print(
        f"[OK] label={sc['label']} next_U={nxt['inlet_velocity']} "
        f"powerLaw_n={nxt['power_law_n']}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
