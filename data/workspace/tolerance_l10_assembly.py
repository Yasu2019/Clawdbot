# -*- coding: utf-8 -*-
"""L10 assembly tolerance stack: progressive-die chain + Cp/Cpk + factory KPI."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
from typing import Any

_APPS_DXF2STEP = Path(__file__).resolve().parent / "apps" / "dxf2step"
if str(_APPS_DXF2STEP) not in sys.path:
    sys.path.insert(0, str(_APPS_DXF2STEP))

import tolerance_stackup_engine as tse  # noqa: E402


DEFAULT_CP_MIN = 1.33
DEFAULT_CPK_MIN = 1.33
DEFAULT_YIELD_MIN = 0.997
MAX_PMI_HOLES_IN_STACK = 6


def progressive_die_station_dims(manifest: dict[str, Any]) -> list[tse.StackDimension]:
    """3-station progressive-die soft stack (North Star: blanking/bending chain)."""
    sheet = float(manifest.get("sheet_thickness_mm") or 1.0)
    sheet_tol = min(0.05, max(0.01, sheet * 0.005))
    return [
        tse.StackDimension("station1_blanking_set", 0.0, 0.012, 1.0, source="assembly_l10"),
        tse.StackDimension("station2_bending_set", 0.0, 0.015, 1.0, source="assembly_l10"),
        tse.StackDimension("station3_trim_set", 0.0, 0.010, -1.0, source="assembly_l10"),
        tse.StackDimension("strip_thickness_var", 0.0, sheet_tol, 1.0, source="assembly_l10"),
        tse.StackDimension("guide_play", 0.0, 0.008, 1.0, source="assembly_l10"),
    ]


def _manifest_part_dims(manifest: dict[str, Any], *, include_gdt: bool) -> list[tse.StackDimension]:
    import part_geometry_contract as pgc

    rows = pgc.merged_tolerance_dims(manifest, include_gdt=include_gdt)
    has_pmi = any(str(r.get("source", "")).startswith("gdt_pmi") for r in rows)
    out: list[tse.StackDimension] = []
    pmi_holes = 0
    for r in rows:
        src = str(r.get("source") or "")
        if has_pmi and src == "gdt_proxy":
            continue
        if src.startswith("gdt_pmi") and "hole" in str(r.get("name", "")).lower():
            if pmi_holes >= MAX_PMI_HOLES_IN_STACK:
                continue
            pmi_holes += 1
        out.append(
            tse.StackDimension(
                name=str(r["name"]),
                mean=0.0,
                tolerance=float(r.get("tolerance") or 0.05),
                coef=float(r.get("coef") or 1.0),
                distribution=str(r.get("distribution") or "normal"),
                source=src or "measured",
            )
        )
    return out


def build_l10_stack_dimensions(
    manifest: dict[str, Any],
    *,
    include_gdt: bool = True,
) -> list[tse.StackDimension]:
    part_dims = _manifest_part_dims(manifest, include_gdt=include_gdt)
    station_dims = progressive_die_station_dims(manifest)
    seen = {d.name for d in part_dims}
    for d in station_dims:
        if d.name not in seen:
            part_dims.append(d)
            seen.add(d.name)
    return part_dims


def factory_kpi_assessment(
    mc: dict[str, Any],
    *,
    cp_min: float = DEFAULT_CP_MIN,
    cpk_min: float = DEFAULT_CPK_MIN,
    yield_min: float = DEFAULT_YIELD_MIN,
    target_mm: float = 0.05,
) -> dict[str, Any]:
    cp = float(mc.get("Cp") or 0.0)
    cpk = float(mc.get("Cpk") or 0.0)
    yield_rate = float(mc.get("yield_rate") or 0.0)
    sigma = float(mc.get("sigma") or 0.0)
    checks = {
        "cp_ge_min": cp >= cp_min,
        "cpk_ge_min": cpk >= cpk_min,
        "yield_ge_min": yield_rate >= yield_min,
        "sigma_within_target": sigma <= target_mm / 6.0 if target_mm > 0 else True,
    }
    wc = float(mc.get("worst_case_tol") or 0.0)
    engineering_pass = wc <= target_mm
    checks["worst_case_within_target"] = engineering_pass
    verdict = "PASS" if engineering_pass else "FAIL"
    return {
        "schema": "clawstack.tolerance_factory_kpi.v1",
        "verdict": verdict,
        "Cp": round(cp, 4),
        "Cpk": round(cpk, 4),
        "yield_rate": round(yield_rate, 6),
        "thresholds": {"Cp_min": cp_min, "Cpk_min": cpk_min, "yield_min": yield_min},
        "checks": checks,
        "six_sigma_capable": cpk >= cpk_min and yield_rate >= yield_min,
        "worst_case_tol_mm": round(wc, 4),
        "target_mm": target_mm,
    }


def analyze_l10_assembly_from_manifest(
    manifest: dict[str, Any],
    *,
    nominal_target: float = 0.0,
    lsl: float = -0.05,
    usl: float = 0.05,
    n: int = 80_000,
    include_gdt: bool = True,
    cp_min: float = DEFAULT_CP_MIN,
    cpk_min: float = DEFAULT_CPK_MIN,
    yield_min: float = DEFAULT_YIELD_MIN,
) -> dict[str, Any]:
    """L10: manifest + progressive-die assembly + Monte Carlo Cp/Cpk + factory KPI."""
    import part_geometry_contract as pgc

    dims = build_l10_stack_dimensions(manifest, include_gdt=include_gdt)
    out = tse.analyze_stack(dims, nominal_target=nominal_target, lsl=lsl, usl=usl, n=n)
    mc = out.get("monte_carlo") or {}
    target_mm = usl - lsl
    factory_kpi = factory_kpi_assessment(
        mc,
        cp_min=cp_min,
        cpk_min=cpk_min,
        yield_min=yield_min,
        target_mm=target_mm,
    )
    factory_kpi["six_sigma_capable"] = bool(
        (mc.get("Cp") or 0) >= cp_min
        and (mc.get("Cpk") or 0) >= cpk_min
        and (mc.get("yield_rate") or 0) >= yield_min
    )
    base_maturity = pgc.detect_maturity_level(manifest, include_gdt=include_gdt)
    out.update(
        {
            "schema": "clawstack.tolerance_l10_assembly.v1",
            "assembly_model": "progressive_die_3station_v1",
            "maturity_level": "L10_assembly_6sigma",
            "base_maturity_level": base_maturity,
            "factory_kpi": factory_kpi,
            "gdt_included": include_gdt,
            "station_count": 3,
            "stack_dim_count": len(dims),
        }
    )
    contribs = (mc.get("contributions") or {})
    if contribs:
        worst = max(contribs.items(), key=lambda kv: kv[1])
        out["worst_contributor"] = {"name": worst[0], "variance_fraction": worst[1]}
    return out
