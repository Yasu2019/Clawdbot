# -*- coding: utf-8 -*-
"""Process physics CETOL 6-sigma cannot implement (rigid CAD assembly only).

Progressive-die station transfer, compliant sheet influence, Moldflow shrink
handoff. Missing CAE stays INSUFFICIENT -- never faked.

Truth Gate: UNVALIDATED vs hardware. Not a Sigmetrix comparison pass.
"""
from __future__ import annotations

import math
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tolerance_stackup_engine as tse


def _f(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _handoff(manifest: dict[str, Any], key: str) -> dict[str, Any]:
    raw = (manifest.get("physics_handoff") or {}).get(key) or {}
    return raw if isinstance(raw, dict) else {}


def progressive_die_transfer(
    manifest: dict[str, Any],
    *,
    or_contrib: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """BL pierce -> PI pilot -> BE bend+springback. Ordered process, not a mate.

    Commercial CETOL 6-sigma has no progressive-die station clock.
    """
    or_contrib = or_contrib or {}
    sheet = max(_f(manifest.get("sheet_thickness_mm"), 1.0), 0.1)
    feats = manifest.get("features") or {}
    holes = [h for h in (feats.get("holes") or []) if isinstance(h, dict)]
    bl = 0.012
    if holes:
        bl = max(_f(holes[0].get("position_tol_mm"), 0.012), 0.001)
    hd = _f(holes[0].get("diameter_mm"), 0.0) if holes else 0.0
    pd = _f(holes[0].get("pin_diameter_mm"), 0.0) if holes else 0.0
    clearance = ((hd - pd) * 0.5) if (hd > pd > 0) else max(hd * 0.02, 0.02)
    k_pilot = 0.70 if holes else 0.0
    after_pi = math.sqrt((bl * (1.0 - k_pilot)) ** 2 + (clearance / 6.0) ** 2)
    be_set = 0.015
    sb = 0.0
    sb_status = "INSUFFICIENT"
    if or_contrib.get("present") and or_contrib.get("field") in (
        "springback_mm", "kpi_springback_mm",
    ):
        sb = abs(_f(or_contrib.get("value")))
        sb_status = "USED"
    elif or_contrib.get("present") and or_contrib.get("field") == "springback_angle_deg":
        sb = abs(_f(or_contrib.get("value"))) * math.pi / 180.0 * max(sheet, 1.0)
        sb_status = "USED"
    be = math.sqrt(be_set ** 2 + sb ** 2)
    feed = 0.008
    rss = math.sqrt(after_pi ** 2 + be ** 2 + feed ** 2)
    return {
        "schema": "clawstack.cetol_cannot.progressive_die.v1",
        "cetol_can_implement": False,
        "reason": "CETOL 6-sigma is rigid assembly joints, not a station clock.",
        "sequence": ["BL", "PI", "BE", "FEED"],
        "bl_pierce_mm": round(bl, 6),
        "pilot_absorb": k_pilot,
        "clearance_mm": round(clearance, 6),
        "after_pilot_mm": round(after_pi, 6),
        "bend_set_mm": be_set,
        "springback_mm": round(sb, 6),
        "springback_status": sb_status,
        "after_bend_mm": round(be, 6),
        "feed_mm": feed,
        "rss_process_mm": round(rss, 6),
        "note": "Sequential BL-PI-BE transfer. Not a CAD mate stack.",
    }


def compliant_sheet_influence(
    *,
    sheet_mm: float,
    lx_mm: float,
    ly_mm: float,
    e_gpa: float = 200.0,
    load_n: float = 80.0,
) -> dict[str, Any]:
    """Liu-Hu-style thickness influence on deflection. CETOL parts are rigid."""
    t = max(float(sheet_mm), 0.05)
    a = max(float(lx_mm), float(ly_mm), 1.0) * 0.5
    e = max(float(e_gpa), 1.0) * 1000.0
    k = 0.0116
    delta = k * float(load_n) * (a ** 2) / max(e * (t ** 3), 1e-9)
    d_delta_dt = -3.0 * delta / t
    sheet_tol = min(0.05, max(0.01, t * 0.005))
    sigma = abs(d_delta_dt) * (sheet_tol / 6.0)
    return {
        "schema": "clawstack.cetol_cannot.compliant.v1",
        "cetol_can_implement": False,
        "reason": "CETOL 6-sigma treats parts as rigid bodies.",
        "method": "plate_influence_dt",
        "delta_nom_mm": round(delta, 6),
        "d_delta_d_thickness": round(d_delta_dt, 6),
        "sheet_tol_mm": round(sheet_tol, 6),
        "sigma_mm": round(sigma, 6),
        "e_gpa": e_gpa,
        "load_n": load_n,
        "note": "Analog of influence coefficients, not a full FEM compliant assembly.",
        "source": "Liu and Hu 1997 J. Manuf. Sci. Eng. 119(3) MIC analog (plate d-delta/dt, not full FEM MIC).",
    }


def moldflow_shrink_contributor(
    manifest: dict[str, Any],
    *,
    lx_mm: float,
) -> dict[str, Any]:
    """Resin shrink/warp as a length change. CETOL has no fill solver.

    Fail-closed: no number invented as a Moldflow result.
    """
    mf = _handoff(manifest, "moldflow")
    lx = max(float(lx_mm), 1.0)
    for key in ("shrink_mm", "linear_shrink_mm", "warp_mm"):
        if mf.get(key) is not None:
            val = _f(mf.get(key))
            return {
                "schema": "clawstack.cetol_cannot.moldflow.v1",
                "cetol_can_implement": False,
                "status": "USED",
                "field": key,
                "shrink_mm": abs(val),
                "source": "physics_handoff.moldflow",
                "note": "Handoff value. Not Autodesk Moldflow validation.",
            }
    if mf.get("shrink_pct") is not None or mf.get("volumetric_shrinkage") is not None:
        pct = _f(mf.get("shrink_pct"), _f(mf.get("volumetric_shrinkage")))
        return {
            "schema": "clawstack.cetol_cannot.moldflow.v1",
            "cetol_can_implement": False,
            "status": "USED",
            "field": "shrink_pct",
            "shrink_mm": abs(pct) * 0.01 * lx,
            "source": "physics_handoff.moldflow",
            "note": "percent * Lx. Not Autodesk Moldflow validation.",
        }
    if mf.get("melt_temp_c") is not None:
        import north_star_cae_models as nsm

        sheet = max(_f(manifest.get("sheet_thickness_mm"), 1.0), 0.1)
        screen = nsm.quick_fill_screen(
            thickness_mm=sheet,
            flow_length_mm=lx,
            melt_temp_c=_f(mf.get("melt_temp_c"), 240.0),
            mold_temp_c=_f(mf.get("mold_temp_c"), 60.0),
            packing_pressure_mpa=_f(mf.get("packing_pressure_mpa"), 50.0),
        )
        shrink = abs(float(screen.get("shrinkage_indicator") or 0.0)) * lx * 0.01
        return {
            "schema": "clawstack.cetol_cannot.moldflow.v1",
            "cetol_can_implement": False,
            "status": "THEORY_PROXY",
            "field": "shrinkage_indicator",
            "shrink_mm": shrink,
            "source": "north_star_cae_models.quick_fill_screen",
            "warp_risk": screen.get("warp_risk"),
            "note": "Theory-pack proxy from melt temp. Not a Moldflow run. Not faked as solver output.",
        }
    return {
        "schema": "clawstack.cetol_cannot.moldflow.v1",
        "cetol_can_implement": False,
        "status": "INSUFFICIENT",
        "shrink_mm": 0.0,
        "reason": "no moldflow shrink artifact",
        "truth_gate": "fail_closed",
        "note": "CETOL cannot do cavity fill. Missing handoff is not invented.",
    }


def build_cetol_cannot_bundle(
    manifest: dict[str, Any],
    *,
    or_contrib: dict[str, Any] | None = None,
    lx_mm: float = 40.0,
    ly_mm: float = 20.0,
    lsl: float = -0.05,
    usl: float = 0.05,
    rigid_sigma_mm: float = 0.0,
) -> dict[str, Any]:
    """Bundle of process effects commercial CETOL 6-sigma cannot compute."""
    sheet = max(_f(manifest.get("sheet_thickness_mm"), 1.0), 0.05)
    die = progressive_die_transfer(manifest, or_contrib=or_contrib)
    comp = compliant_sheet_influence(sheet_mm=sheet, lx_mm=lx_mm, ly_mm=ly_mm)
    mf = moldflow_shrink_contributor(manifest, lx_mm=lx_mm)
    dims = [
        tse.StackDimension("proc_bl_pi", 0.0, max(die["after_pilot_mm"] * 6.0, 0.001), 1.0, source="process_die"),
        tse.StackDimension("proc_be_springback", 0.0, max(die["after_bend_mm"] * 6.0, 0.001), 1.0, source="process_die"),
        tse.StackDimension("proc_compliant", 0.0, max(comp["sigma_mm"] * 6.0, 0.001), 1.0, source="process_compliant"),
    ]
    if mf.get("status") in ("USED", "THEORY_PROXY") and _f(mf.get("shrink_mm")) > 0:
        dims.append(tse.StackDimension(
            "proc_moldflow_shrink", 0.0, max(_f(mf.get("shrink_mm")), 0.001), 1.0,
            source="process_moldflow",
        ))
    msm = tse.msm_stack(dims, lsl=lsl, usl=usl) if dims else {}
    proc_sig = float(msm.get("sigma") or 0.0)
    rigid = max(float(rigid_sigma_mm), 0.0)
    denom = proc_sig ** 2 + rigid ** 2
    split = {
        "process_sigma_mm": round(proc_sig, 6),
        "rigid_gdt_sigma_mm": round(rigid, 6),
        "process_variance_fraction": round((proc_sig ** 2) / denom, 4) if denom > 1e-18 else 0.0,
        "note": "Split CETOL-class rigid GDT vs process physics CETOL cannot run.",
    }
    flags: list[dict[str, Any]] = []
    if die.get("springback_status") == "INSUFFICIENT":
        flags.append({
            "code": "process_springback_absent",
            "severity": "info",
            "text": "OpenRadioss springback absent -- BE station uses bend-set only (fail-closed)",
        })
    if mf.get("status") == "INSUFFICIENT":
        flags.append({
            "code": "moldflow_shrink_absent",
            "severity": "info",
            "text": "Moldflow shrink missing (fail-closed). CETOL cannot fill a cavity either.",
        })
    elif mf.get("status") == "THEORY_PROXY":
        flags.append({
            "code": "moldflow_theory_proxy",
            "severity": "info",
            "text": "Shrink from theory-pack indicator, not a Moldflow solver run",
        })
    return {
        "schema": "clawstack.cetol_cannot.v1",
        "commercial_cetol_equivalent": False,
        "cetol_can_implement": False,
        "truth_gate": "UNVALIDATED",
        "note": (
            "Process physics commercial CETOL 6-sigma cannot implement "
            "(no station clock, no compliant sheet, no cavity fill)."
        ),
        "progressive_die": die,
        "compliant": comp,
        "moldflow": mf,
        "msm_process": {
            "sigma": msm.get("sigma"),
            "Cpk": msm.get("Cpk"),
            "yield_rate": msm.get("yield_rate"),
        },
        "variance_split": split,
        "advisor": flags,
    }
