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
        "within_spec_worst_case": within_wc,
        "within_spec_mc": bool(mc.get("yield_rate", 0) >= 0.997),
        "engine": "tolerance_stackup_engine.v1",
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
