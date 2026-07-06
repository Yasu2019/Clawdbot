# -*- coding: utf-8 -*-
"""CETOL-style 1D stack-up: worst-case, RSS, Monte Carlo (theory pack 03_tolerance_analysis)."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

_APPS_DXF2STEP = Path(__file__).resolve().parent / "apps" / "dxf2step"
if str(_APPS_DXF2STEP) not in sys.path:
    sys.path.insert(0, str(_APPS_DXF2STEP))


@dataclass(frozen=True)
class StackDimension:
    name: str
    mean: float
    tolerance: float
    coef: float = 1.0
    distribution: str = "normal"
    source: str = "synthetic"


def worst_case_stack(dims: list[StackDimension]) -> float:
    return sum(abs(d.coef) * d.tolerance for d in dims)


def rss_stack(dims: list[StackDimension], sigma_fraction: float = 1.0 / 6.0) -> float:
    parts = [(abs(d.coef) * d.tolerance * sigma_fraction) ** 2 for d in dims]
    return math.sqrt(sum(parts))


def monte_carlo_stack(
    dims: list[StackDimension],
    *,
    n: int = 100_000,
    seed: int = 42,
    lsl: float | None = None,
    usl: float | None = None,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    y = np.zeros(n)
    contributions: dict[str, np.ndarray] = {}
    for d in dims:
        sigma = d.tolerance / 6.0 if d.tolerance > 0 else 0.0
        if d.distribution == "uniform":
            half = d.tolerance
            x = rng.uniform(d.mean - half, d.mean + half, n)
        elif d.distribution == "triangular":
            # T-iy63/L5: symmetric triangular, half-width = tolerance
            x = rng.triangular(d.mean - d.tolerance, d.mean, d.mean + d.tolerance, n)
        else:
            x = rng.normal(d.mean, sigma, n)
        contributions[d.name] = x
        y += d.coef * x

    mu = float(np.mean(y))
    sigma_y = float(np.std(y, ddof=1))
    result: dict[str, Any] = {
        "mean": mu,
        "sigma": sigma_y,
        "n": n,
        "worst_case_tol": worst_case_stack(dims),
        "rss_3sigma": rss_stack(dims) * 3.0,
    }
    if lsl is not None and usl is not None and sigma_y > 0:
        cp = (usl - lsl) / (6 * sigma_y)
        cpk = min((usl - mu) / (3 * sigma_y), (mu - lsl) / (3 * sigma_y))
        yield_rate = float(np.mean((y >= lsl) & (y <= usl)))
        result.update({"Cp": cp, "Cpk": cpk, "yield_rate": yield_rate, "lsl": lsl, "usl": usl})
        var_parts = []
        for d in dims:
            x = contributions[d.name]
            var_parts.append((d.coef * float(np.std(x, ddof=1))) ** 2)
        total_var = sum(var_parts) or 1.0
        result["contributions"] = {
            d.name: round(var_parts[i] / total_var, 4) for i, d in enumerate(dims)
        }
    return result


# --- T-iy63/L5 (2026-07-07): Method of System Moments + tolerance allocation ---
# CETOL 6σの中核=解析的な感度/寄与度と歩留まり推定(MC不要)、および目標Cpkへの
# 公差再配分推奨。ギャップ#2「MSM未移植」(cetol_progressive_die_freecad_mapping)を解消。


def _norm_pdf(z: float) -> float:
    return math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def _dist_sigma_skew_exkurt(d: StackDimension) -> tuple[float, float, float]:
    """(sigma, skewness, excess kurtosis) matching monte_carlo_stack semantics."""
    t = max(d.tolerance, 0.0)
    dist = str(d.distribution or "normal").lower()
    if dist == "uniform":
        return t / math.sqrt(3.0), 0.0, -1.2
    if dist == "triangular":
        return t / math.sqrt(6.0), 0.0, -0.6
    return t / 6.0, 0.0, 0.0


def msm_stack(
    dims: list[StackDimension],
    *,
    lsl: float | None = None,
    usl: float | None = None,
) -> dict[str, Any]:
    """Method of System Moments: analytic moments of Y = sum(ai*Xi), CETOL-style.

    Propagates mean/variance/skewness/excess-kurtosis for independent Xi and
    estimates yield with a Gram-Charlier corrected CDF - no Monte Carlo noise.
    Sensitivity output: contribution_i = (ai*sigma_i)^2 / sigma_Y^2 (theory pack E).
    """
    mu = sum(d.coef * d.mean for d in dims)
    var = 0.0
    m3 = 0.0
    exk_num = 0.0
    per_dim: list[tuple[str, float, float]] = []
    for d in dims:
        s, g1, g2 = _dist_sigma_skew_exkurt(d)
        a = d.coef
        var += (a * s) ** 2
        m3 += (a ** 3) * g1 * (s ** 3)
        exk_num += (a ** 4) * g2 * (s ** 4)
        per_dim.append((d.name, s, (a * s) ** 2))
    sigma_y = math.sqrt(var) if var > 0 else 0.0
    skew = (m3 / sigma_y ** 3) if sigma_y > 0 else 0.0
    exkurt = (exk_num / sigma_y ** 4) if sigma_y > 0 else 0.0
    total = var or 1.0
    out: dict[str, Any] = {
        "method": "system_moments_gram_charlier",
        "mean": mu,
        "sigma": sigma_y,
        "skewness": round(skew, 6),
        "excess_kurtosis": round(exkurt, 6),
        "sensitivity": {
            name: {"sigma_mm": round(s, 6), "contribution": round(v / total, 4)}
            for name, s, v in per_dim
        },
    }
    if lsl is not None and usl is not None and sigma_y > 0:

        def _cdf(x: float) -> float:
            z = (x - mu) / sigma_y
            corr = _norm_pdf(z) * (
                skew / 6.0 * (z * z - 1.0)
                + exkurt / 24.0 * z * (z * z - 3.0)
                + (skew ** 2) / 72.0 * z * (z ** 4 - 10.0 * z * z + 15.0)
            )
            return min(1.0, max(0.0, _norm_cdf(z) - corr))

        out.update(
            {
                "Cp": (usl - lsl) / (6.0 * sigma_y),
                "Cpk": min((usl - mu) / (3.0 * sigma_y), (mu - lsl) / (3.0 * sigma_y)),
                "yield_rate": round(_cdf(usl) - _cdf(lsl), 6),
                "lsl": lsl,
                "usl": usl,
            }
        )
    return out


def tolerance_allocation(
    dims: list[StackDimension],
    *,
    lsl: float,
    usl: float,
    target_cpk: float = 1.33,
    loosen_threshold: float = 0.02,
    fixed_sources: tuple[str, ...] = ("assembly_l10",),
) -> dict[str, Any]:
    """CETOL-style allocation: tolerance changes needed to reach target Cpk.

    Proportional model: adjustable dims (source not in fixed_sources) are scaled
    by a common factor k so that sigma_Y meets the target; die-set terms stay
    fixed. Low-contribution dims are reported as loosen candidates with the
    Cpk they would leave after widening x2 (cost-down insight).
    """
    mu = sum(d.coef * d.mean for d in dims)
    fixed_var = 0.0
    adj_var = 0.0
    rows: list[tuple[StackDimension, float, float]] = []
    for d in dims:
        s, _, _ = _dist_sigma_skew_exkurt(d)
        v = (d.coef * s) ** 2
        if d.source in fixed_sources:
            fixed_var += v
        else:
            adj_var += v
        rows.append((d, s, v))
    total_var = fixed_var + adj_var
    if total_var <= 0:
        return {"feasible": False, "reason": "zero_variance"}
    sigma_now = math.sqrt(total_var)
    half_window = min(usl - mu, mu - lsl)
    cpk_now = half_window / (3.0 * sigma_now) if sigma_now > 0 else float("inf")
    sigma_req = half_window / (3.0 * target_cpk) if target_cpk > 0 else sigma_now
    need = sigma_req ** 2 - fixed_var

    k: float | None = None
    feasible = True
    reason = ""
    if cpk_now >= target_cpk:
        reason = "already_capable"
    elif need <= 0 or adj_var <= 0:
        feasible = False
        reason = "fixed_die_set_variance_exceeds_budget"  # 金型側(assembly_l10)の改善が必要
    else:
        k = math.sqrt(need / adj_var)
        reason = "tighten_by_common_scale"

    recommendations: list[dict[str, Any]] = []
    for d, s, v in rows:
        contribution = v / total_var
        if d.source in fixed_sources:
            action, new_tol, cpk_after = "fixed", d.tolerance, None
        elif k is not None:
            action, new_tol, cpk_after = "tighten", round(d.tolerance * k, 6), None
        elif contribution < loosen_threshold and cpk_now >= target_cpk:
            sigma_after = math.sqrt(total_var - v + v * 4.0)  # tol x2 -> var x4
            cpk_after = round(half_window / (3.0 * sigma_after), 4)
            action = "loosen_candidate" if cpk_after >= target_cpk else "keep"
            new_tol = round(d.tolerance * 2.0, 6) if action == "loosen_candidate" else d.tolerance
        else:
            action, new_tol, cpk_after = "keep", d.tolerance, None
        rec = {
            "name": d.name,
            "source": d.source,
            "tolerance_mm": d.tolerance,
            "recommended_tolerance_mm": new_tol,
            "contribution": round(contribution, 4),
            "action": action,
        }
        if cpk_after is not None:
            rec["cpk_if_loosened_x2"] = cpk_after
        recommendations.append(rec)

    return {
        "schema": "clawstack.tolerance_allocation.v1",
        "feasible": feasible,
        "reason": reason,
        "target_cpk": target_cpk,
        "current_cpk": round(cpk_now, 4),
        "common_tighten_scale": round(k, 4) if k is not None else None,
        "recommendations": recommendations,
    }


def default_progressive_die_gap_case() -> list[StackDimension]:
    """Example chain for press-part gap (editable per user STEP)."""
    return [
        StackDimension("strip_thickness", 1.000, 0.020, 1.0),
        StackDimension("punch_set", 0.050, 0.015, 1.0),
        StackDimension("die_clearance", 0.030, 0.010, -1.0),
        StackDimension("guide_play", 0.020, 0.008, 1.0),
    ]


def analyze_stack(
    dims: list[StackDimension],
    *,
    nominal_target: float,
    lsl: float,
    usl: float,
    n: int = 80_000,
) -> dict[str, Any]:
    mc = monte_carlo_stack(dims, n=n, lsl=lsl, usl=usl)
    wc = worst_case_stack(dims)
    rss3 = rss_stack(dims) * 3.0
    within_wc = nominal_target + wc <= usl and nominal_target - wc >= lsl
    return {
        "nominal_target": nominal_target,
        "worst_case_stack_mm": wc,
        "rss_3sigma_mm": rss3,
        "monte_carlo": mc,
        # T-iy63/L5: analytic MSM + allocation (CETOL core outputs)
        "msm": msm_stack(dims, lsl=lsl, usl=usl),
        "tolerance_allocation": tolerance_allocation(dims, lsl=lsl, usl=usl),
        "within_spec_worst_case": within_wc,
        "within_spec_mc": bool(mc.get("yield_rate", 0) >= 0.997),
        "engine": "tolerance_stackup_engine.v2_l5_msm",
        "dimensions": [
            {
                "name": d.name,
                "mean": d.mean,
                "tolerance": d.tolerance,
                "coef": d.coef,
                "source": d.source,
            }
            for d in dims
        ],
        "dimension_source_summary": {
            "measured": sum(1 for d in dims if d.source == "measured"),
            "synthetic": sum(1 for d in dims if d.source != "measured"),
            "gdt": sum(1 for d in dims if str(d.source).startswith("gdt")),
            # T-iy63/L4: drawing-driven dims from AP242 PMI (+/- tolerances)
            "pmi": sum(
                1
                for d in dims
                if str(d.source) == "pmi" or str(d.source).startswith("gdt_pmi")
            ),
        },
    }


def analyze_stack_from_manifest_dict(
    manifest: dict[str, Any],
    *,
    nominal_target: float = 0.0,
    lsl: float = -0.05,
    usl: float = 0.05,
    n: int = 80_000,
    include_gdt: bool = True,
) -> dict[str, Any]:
    """Build stack from part_manifest nominal + GD&T dims (L2 Cetol proxy)."""
    import part_geometry_contract as pgc  # type: ignore

    rows = pgc.merged_tolerance_dims(manifest, include_gdt=include_gdt)
    dims = [
        StackDimension(
            name=str(r["name"]),
            mean=float(r.get("mean") or 0.0),
            tolerance=float(r.get("tolerance") or 0.05),
            coef=float(r.get("coef") or 1.0),
            distribution=str(r.get("distribution") or "normal"),
            source=str(r.get("source") or "synthetic"),
        )
        for r in rows
    ]
    out = analyze_stack(dims, nominal_target=nominal_target, lsl=lsl, usl=usl, n=n)
    out["gdt_included"] = include_gdt
    out["gdt_dims"] = [r for r in rows if str(r.get("source", "")).startswith("gdt")]
    out["maturity_level"] = pgc.detect_maturity_level(manifest, include_gdt=include_gdt)
    return out
