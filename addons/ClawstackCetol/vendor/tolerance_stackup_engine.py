# -*- coding: utf-8 -*-
"""CETOL-style 1D stack-up: worst-case, RSS, Monte Carlo (theory pack 03_tolerance_analysis)."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import itertools
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
        elif d.distribution == "weibull":
            k = 3.0
            c_9973 = ((-math.log(0.00135))**(1.0/k)) - ((-math.log(0.99865))**(1.0/k))
            lam = (2.0 * d.tolerance) / c_9973 if c_9973 > 0 else 1.0
            w = rng.weibull(k, n)
            x_shift = (d.mean - d.tolerance) - lam * ((-math.log(0.99865))**(1.0/k))
            x = x_shift + lam * w
        elif d.distribution == "beta":
            alpha, beta_val = 2.0, 5.0
            b = rng.beta(alpha, beta_val, n)
            x = (d.mean - d.tolerance) + 2.0 * d.tolerance * b
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
    if dist == "weibull":
        k = 3.0
        g1 = math.gamma(1.0 + 1.0 / k)
        g2 = math.gamma(1.0 + 2.0 / k)
        g3 = math.gamma(1.0 + 3.0 / k)
        g4 = math.gamma(1.0 + 4.0 / k)
        c_9973 = ((-math.log(0.00135))**(1.0/k)) - ((-math.log(0.99865))**(1.0/k))
        lam = (2.0 * t) / c_9973 if c_9973 > 0 else 1.0
        sigma = lam * math.sqrt(max(0.0, g2 - g1*g1))
        skew = (g3 - 3.0*g1*g2 + 2.0*(g1**3)) / max(1e-12, (g2 - g1*g1)**1.5)
        exkurt = (g4 - 4.0*g1*g3 + 6.0*(g1**2)*g2 - 3.0*(g1**4)) / max(1e-12, (g2 - g1*g1)**2) - 3.0
        return sigma, skew, exkurt
    if dist == "beta":
        alpha, beta_val = 2.0, 5.0
        ab = alpha + beta_val
        var_0 = (alpha * beta_val) / ((ab ** 2) * (ab + 1.0))
        sigma = 2.0 * t * math.sqrt(var_0)
        skew = (2.0 * (beta_val - alpha) * math.sqrt(ab + 1.0)) / ((ab + 2.0) * math.sqrt(alpha * beta_val))
        exkurt = (6.0 * (((alpha - beta_val)**2) * (ab + 1.0) - alpha * beta_val * (ab + 2.0))) / (alpha * beta_val * (ab + 2.0) * (ab + 3.0))
        return sigma, skew, exkurt
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

        gc_yield = round(_cdf(usl) - _cdf(lsl), 6)
        gld = gld_yield_from_moments(mu, sigma_y, skew, exkurt, lsl, usl)
        out.update(
            {
                "Cp": (usl - lsl) / (6.0 * sigma_y),
                "Cpk": min((usl - mu) / (3.0 * sigma_y), (mu - lsl) / (3.0 * sigma_y)),
                "yield_rate": gc_yield,
                "yield_rate_gld": gld.get("yield_rate"),
                "gld": gld,
                "lsl": lsl,
                "usl": usl,
            }
        )
    return out


def gld_fmkl_from_moments(
    mean: float,
    sigma: float,
    skew: float,
    exkurt: float,
) -> dict[str, Any]:
    """FMKL Generalized Lambda (Freimer et al. 1988) from four moments.

    Quantile: Q(u) = l1 + ((u^l3-1)/l3 - ((1-u)^l4-1)/l4) / l2
    l3/l4 are a bounded skew/kurtosis heuristic, then l1/l2 match mean/sigma.
    This is not the Sigmetrix CETOL SOTA GLD lookup table (Gao 1995).
    """
    if sigma <= 0:
        return {"status": "FALLBACK", "reason": "sigma<=0", "parameterization": "fmkl"}
    l3 = 0.1349 - 0.08 * max(-1.5, min(1.5, float(skew)))
    l4 = 0.1349 + 0.08 * max(-1.5, min(1.5, float(skew)))
    kadj = max(-0.35, min(0.35, float(exkurt) * 0.04))
    l3 = max(-0.45, min(0.75, l3 - kadj))
    l4 = max(-0.45, min(0.75, l4 - kadj))

    def _q_unit(u: float) -> float:
        t1 = math.log(u) if abs(l3) < 1e-9 else (u ** l3 - 1.0) / l3
        t2 = math.log(1.0 - u) if abs(l4) < 1e-9 else ((1.0 - u) ** l4 - 1.0) / l4
        return t1 - t2

    zs = [_q_unit(i / 2000.0) for i in range(1, 2000)]
    z_mean = sum(zs) / len(zs)
    z_var = sum((z - z_mean) ** 2 for z in zs) / len(zs)
    z_std = math.sqrt(z_var) if z_var > 0 else 0.0
    if z_std <= 1e-12:
        return {"status": "FALLBACK", "reason": "gld_scale", "parameterization": "fmkl"}
    l2 = z_std / sigma
    l1 = mean - z_mean / l2
    return {
        "status": "OK",
        "parameterization": "fmkl",
        "lambda": [l1, l2, l3, l4],
        "note": "FMKL moment approx; not Sigmetrix CETOL SOTA GLD table.",
    }


def gld_cdf(x: float, fit: dict[str, Any]) -> float:
    """Invert FMKL quantile by bisection. Returns 0/1 outside support."""
    if fit.get("status") != "OK":
        return float("nan")
    l1, l2, l3, l4 = fit["lambda"]

    def _q(u: float) -> float:
        uu = min(1.0 - 1e-12, max(1e-12, u))
        t1 = math.log(uu) if abs(l3) < 1e-9 else (uu ** l3 - 1.0) / l3
        t2 = math.log(1.0 - uu) if abs(l4) < 1e-9 else ((1.0 - uu) ** l4 - 1.0) / l4
        return l1 + (t1 - t2) / l2

    lo, hi = 1e-12, 1.0 - 1e-12
    q_lo, q_hi = _q(lo), _q(hi)
    if q_hi < q_lo:
        lo, hi, q_lo, q_hi = hi, lo, q_hi, q_lo
    if x <= q_lo:
        return 0.0
    if x >= q_hi:
        return 1.0
    a, b = lo, hi
    for _ in range(48):
        mid = 0.5 * (a + b)
        if _q(mid) < x:
            a = mid
        else:
            b = mid
    return 0.5 * (a + b)


def gram_charlier_yield(
    mean: float,
    sigma: float,
    skew: float,
    exkurt: float,
    lsl: float,
    usl: float,
) -> dict[str, Any]:
    """Edgeworth/Gram-Charlier yield. Independent of FMKL GLD."""
    if sigma <= 1e-18:
        return {"status": "FALLBACK", "reason": "sigma<=0", "yield_rate": None}

    def _cdf(x: float) -> float:
        z = (x - mean) / sigma
        phi = math.exp(-0.5 * z * z) / math.sqrt(2.0 * math.pi)
        cdf = 0.5 * math.erfc(-z / math.sqrt(2.0))
        cdf -= phi * ((skew / 6.0) * (z * z - 1.0) + (exkurt / 24.0) * (z ** 3 - 3.0 * z))
        return min(1.0, max(0.0, cdf))

    y = _cdf(usl) - _cdf(lsl)
    return {
        "status": "OK",
        "method": "gram_charlier",
        "yield_rate": round(min(1.0, max(0.0, y)), 6),
    }


def cornish_fisher_yield(
    mean: float,
    sigma: float,
    skew: float,
    exkurt: float,
    lsl: float,
    usl: float,
) -> dict[str, Any]:
    """Cornish-Fisher quantile mapped through standard normal CDF.

    Used as a third tail model beside FMKL and Gram-Charlier. Not Gao 1995 table.
    """
    if sigma <= 1e-18:
        return {"status": "FALLBACK", "reason": "sigma<=0", "yield_rate": None}

    def _z_to_cf(z: float) -> float:
        g1 = float(skew)
        g2 = float(exkurt)
        return (
            z
            + (g1 / 6.0) * (z * z - 1.0)
            + (g2 / 24.0) * (z ** 3 - 3.0 * z)
            - (g1 * g1 / 36.0) * (2.0 * z ** 3 - 5.0 * z)
        )

    def _cdf(x: float) -> float:
        z_raw = (x - mean) / sigma
        lo, hi = -12.0, 12.0
        for _ in range(48):
            mid = 0.5 * (lo + hi)
            if _z_to_cf(mid) < z_raw:
                lo = mid
            else:
                hi = mid
        z = 0.5 * (lo + hi)
        return min(1.0, max(0.0, 0.5 * math.erfc(-z / math.sqrt(2.0))))

    y = _cdf(usl) - _cdf(lsl)
    return {
        "status": "OK",
        "method": "cornish_fisher",
        "yield_rate": round(min(1.0, max(0.0, y)), 6),
    }


def tail_model_bundle(
    mean: float,
    sigma: float,
    skew: float,
    exkurt: float,
    lsl: float,
    usl: float,
) -> dict[str, Any]:
    """FMKL + Gram-Charlier + Cornish-Fisher. Flag disagreement. Not CETOL GLD table."""
    gld = gld_yield_from_moments(mean, sigma, skew, exkurt, lsl, usl)
    gc = gram_charlier_yield(mean, sigma, skew, exkurt, lsl, usl)
    cf = cornish_fisher_yield(mean, sigma, skew, exkurt, lsl, usl)
    rates = [
        float(x["yield_rate"])
        for x in (gld, gc, cf)
        if x.get("status") == "OK" and x.get("yield_rate") is not None
    ]
    spread = (max(rates) - min(rates)) if len(rates) >= 2 else 0.0
    return {
        "gld_fmkl": gld,
        "gram_charlier": gc,
        "cornish_fisher": cf,
        "yield_spread": round(spread, 6),
        "disagreement": bool(spread > 1.0e-3),
        "note": "Three independent tail models. Spread is not a CETOL 3D pass.",
    }


def joint_ctq_yield(
    measures: dict[str, Any],
    *,
    lsl: float,
    usl: float,
    n: int = 20_000,
    seed: int = 7,
) -> dict[str, Any]:
    """Simultaneous yield P(all linear CTQs in spec) via Gaussian copula MC.

    Documented CETOL 6-sigma reports one CTQ at a time. This is extra.
    """
    rows: list[tuple[str, dict[str, Any]]] = []
    for mid, res in (measures or {}).items():
        if not isinstance(res, dict):
            continue
        if str(res.get("kind") or "linear").lower() == "angular":
            continue
        if str(res.get("unit") or "mm") == "deg":
            continue
        rows.append((str(mid), res))
    if len(rows) < 2:
        return {"applied": False, "reason": "need_2_linear_ctq", "n_ctq": len(rows)}
    names: list[str] = []
    seen: set[str] = set()
    for _mid, res in rows:
        for nm, rec in (res.get("sensitivity") or {}).items():
            if (rec or {}).get("dlm_assembly_variable"):
                continue
            if nm not in seen:
                seen.add(nm)
                names.append(str(nm))
    if not names:
        return {"applied": False, "reason": "no_x_params"}
    a_mat = np.zeros((len(rows), len(names)), dtype=float)
    sig = np.zeros(len(names), dtype=float)
    means = np.zeros(len(rows), dtype=float)
    for i, (_mid, res) in enumerate(rows):
        sota = res.get("sota") or {}
        means[i] = float(sota.get("mean_shift") or 0.0)
        sens = res.get("sensitivity") or {}
        for j, nm in enumerate(names):
            rec = sens.get(nm) or {}
            ai = float(rec.get("sensitivity") or 0.0)
            a_mat[i, j] = ai
            sm = float(rec.get("sigma_mm") or 0.0)
            if abs(ai) > 1e-18 and sig[j] <= 0:
                sig[j] = sm / abs(ai)
    cov = a_mat @ np.diag(sig ** 2) @ a_mat.T
    cov = cov + np.eye(len(rows)) * 1e-18
    try:
        chol = np.linalg.cholesky(cov)
    except np.linalg.LinAlgError:
        w, v = np.linalg.eigh(cov)
        w = np.clip(w, 1e-18, None)
        chol = v @ np.diag(np.sqrt(w))
    rng = np.random.default_rng(seed)
    z = rng.normal(size=(len(rows), int(n)))
    y = (chol @ z) + means.reshape(-1, 1)
    inside = np.all((y >= lsl) & (y <= usl), axis=0)
    single = [float(np.mean((y[i] >= lsl) & (y[i] <= usl))) for i in range(len(rows))]
    return {
        "applied": True,
        "method": "gaussian_copula_mc",
        "n_ctq": len(rows),
        "n_samples": int(n),
        "measure_ids": [m for m, _ in rows],
        "yield_joint": round(float(np.mean(inside)), 6),
        "yield_single": {rows[i][0]: round(single[i], 6) for i in range(len(rows))},
        "note": "Joint P(all linear CTQs in spec). Not a Sigmetrix CETOL output.",
    }


def gld_yield_from_moments(
    mean: float,
    sigma: float,
    skew: float,
    exkurt: float,
    lsl: float,
    usl: float,
) -> dict[str, Any]:
    """Yield from FMKL GLD fit to four moments. FALLBACK copies Gram-Charlier caller."""
    fit = gld_fmkl_from_moments(mean, sigma, skew, exkurt)
    out: dict[str, Any] = dict(fit)
    if fit.get("status") != "OK":
        out["yield_rate"] = None
        return out
    y = gld_cdf(usl, fit) - gld_cdf(lsl, fit)
    if not math.isfinite(y):
        out["status"] = "FALLBACK"
        out["reason"] = "cdf_nonfinite"
        out["yield_rate"] = None
        return out
    out["yield_rate"] = round(min(1.0, max(0.0, y)), 6)
    out["lsl"] = lsl
    out["usl"] = usl
    return out


def sota_truncated_higher_moments(
    *,
    a: list[float],
    sig: list[float],
    bii: list[float],
    bij_pairs: list[tuple[int, int, float]],
    var_y: float,
) -> dict[str, float]:
    """Truncated MSM 3rd/4th moments (Glancy/Chase 1999 eqs 10-11 style).

    Independent normal inputs (mu3=0, mu4=3 sigma^4). Not the full Cox 1979
    expansion and not the Sigmetrix GLD lookup table.
    """
    n = len(a)
    mu3 = 0.0
    for i in range(n):
        mu3 += 3.0 * (a[i] ** 2) * bii[i] * (sig[i] ** 4)
    for i, j, bij in bij_pairs:
        mu3 += 6.0 * a[i] * a[j] * bij * (sig[i] ** 2) * (sig[j] ** 2)
    mu4 = 3.0 * (var_y ** 2) if var_y > 0 else 0.0
    for i in range(n):
        mu4 += 6.0 * (a[i] ** 2) * (bii[i] ** 2) * (sig[i] ** 6)
    sigma = math.sqrt(var_y) if var_y > 0 else 0.0
    skew = (mu3 / (sigma ** 3)) if sigma > 1e-18 else 0.0
    exkurt = (mu4 / (var_y ** 2) - 3.0) if var_y > 1e-18 else 0.0
    if not math.isfinite(skew):
        skew = 0.0
    if not math.isfinite(exkurt):
        exkurt = 0.0
    return {
        "mu3": mu3,
        "mu4": mu4,
        "skewness": max(-4.0, min(4.0, skew)),
        "excess_kurtosis": max(-1.2, min(8.0, exkurt)),
    }


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


class VectorLoop3D:
    """3D Vector Loop tolerance stackup analysis solver using kinematic chains.
    
    Models mechanical assembly loop as:
        T_total = T_1 * T_2 * ... * T_m = I
    where each joint/part coordinate frame transformation T_i is perturbed
    by independent 3D translational (Tx, Ty, Tz) and rotational (Rx, Ry, Rz)
    tolerances.
    """
    def __init__(self) -> None:
        self.frames: list[dict[str, Any]] = []

    def add_frame(
        self,
        name: str,
        nominal_translation: tuple[float, float, float],
        nominal_rotation_deg: tuple[float, float, float],
        translation_tolerance: tuple[float, float, float] = (0.0, 0.0, 0.0),
        rotation_tolerance_deg: tuple[float, float, float] = (0.0, 0.0, 0.0),
        source: str = "synthetic",
        role: str = "frame",
    ) -> None:
        """Add a perturbed coordinate transformation frame to the loop."""
        self.frames.append({
            "name": name,
            "t_nom": nominal_translation,
            "r_nom": nominal_rotation_deg,
            "t_tol": translation_tolerance,
            "r_tol": rotation_tolerance_deg,
            "source": source,
            "role": role,
        })

    def frame_index(self, token: str | None) -> int | None:
        """Match a feature/joint token to a frame index."""
        if not token:
            return None
        tok_l = str(token).strip().lower().replace("-", "_")
        if not tok_l:
            return None
        last = tok_l.split("_")[-1]
        for i, f in enumerate(self.frames):
            fn_l = str(f.get("name") or "").lower()
            if fn_l == tok_l or fn_l.endswith("_" + tok_l):
                return i
            if len(last) >= 2 and (fn_l.endswith("_" + last) or fn_l == last):
                return i
        return None

    def param_specs(self) -> list[dict[str, Any]]:
        specs: list[dict[str, Any]] = []
        k = 0
        for idx, f in enumerate(self.frames):
            t_tol = f["t_tol"]
            r_tol = f["r_tol"]
            for i, name_t in enumerate(["Tx", "Ty", "Tz"]):
                tol = t_tol[i]
                if tol <= 0:
                    continue
                specs.append({
                    "k": k, "idx": idx, "kind": "t", "axis": i,
                    "name": f"{f['name']}_{name_t}",
                    "sigma": tol / 6.0,
                    "tol_wc": float(tol),
                    "tol_report": float(tol),
                    "mean": f["t_nom"][i],
                    "source": f["source"],
                })
                k += 1
            for i, name_r in enumerate(["Rx", "Ry", "Rz"]):
                tol_deg = r_tol[i]
                if tol_deg <= 0:
                    continue
                tol_rad = float(np.radians(tol_deg))
                specs.append({
                    "k": k, "idx": idx, "kind": "r", "axis": i,
                    "name": f"{f['name']}_{name_r}",
                    "sigma": tol_rad / 6.0,
                    "tol_wc": tol_rad,
                    "tol_report": float(tol_deg),
                    "mean": f["r_nom"][i],
                    "source": f["source"],
                })
                k += 1
        return specs

    def _poses_with_deltas(
        self,
        deltas: dict[int, tuple[list[float], list[float]]],
    ) -> list[np.ndarray]:
        poses: list[np.ndarray] = []
        t_acc = np.eye(4)
        for idx, f in enumerate(self.frames):
            t = list(f["t_nom"])
            r = list(f["r_nom"])
            if idx in deltas:
                dt, dr = deltas[idx]
                t = [t[i] + dt[i] for i in range(3)]
                r = [r[i] + dr[i] for i in range(3)]
            t_acc = t_acc @ self._make_t(tuple(t), tuple(r))
            poses.append(t_acc.copy())
        return poses

    def relative_dof(
        self,
        from_idx: int,
        to_idx: int,
        dof: str,
        deltas: dict[int, tuple[list[float], list[float]]] | None = None,
    ) -> float:
        """Joint-local relative pose component (mm or deg)."""
        poses = self._poses_with_deltas(deltas or {})
        t_rel = np.linalg.inv(poses[int(from_idx)]) @ poses[int(to_idx)]
        r = t_rel[:3, :3]
        t = t_rel[:3, 3]
        d = str(dof or "")
        if d == "Tx":
            return float(t[0])
        if d == "Ty":
            return float(t[1])
        if d == "Tz":
            return float(t[2])
        rx = math.atan2(float(r[2, 1]), float(r[2, 2]))
        ry = math.atan2(-float(r[2, 0]), math.sqrt(max(0.0, r[2, 1] ** 2 + r[2, 2] ** 2)))
        rz = math.atan2(float(r[1, 0]), float(r[0, 0]))
        if d == "Rx":
            return math.degrees(rx)
        if d == "Ry":
            return math.degrees(ry)
        if d == "Rz":
            return math.degrees(rz)
        return 0.0

    def solve(
        self,
        gap_direction: tuple[float, float, float] = (0.0, 0.0, 1.0),
        *,
        second_order: bool = True,
        cross_top_n: int = 32,
        quantity: str = "linear",
        from_frame: str | None = None,
        to_frame: str | None = None,
    ) -> dict[str, Any]:
        """Solves the 3D loop for the specified gap direction vector.
        
        Computes 3D gap mean, RSS 3-sigma, Worst Case limits, and 
        individual dimension sensitivity contributions.
        SOTA-class 2nd order: central first+diagonal Hessian (Glancy/Chase
        reuse of +/- eps) plus cross-partials up to cross_top_n (full n^2
        when n <= cap). Truncated MSM 4 moments. Not Sigmetrix GLD table.
        """
        ax = np.array(gap_direction, dtype=float)
        nrm = float(np.linalg.norm(ax))
        if nrm <= 0:
            ax = np.array([0.0, 0.0, 1.0])
        else:
            ax = ax / nrm
        qty = "angular" if str(quantity).lower() == "angular" else "linear"
        from_idx = self.frame_index(from_frame)
        to_idx = self.frame_index(to_frame)
        use_rel = from_idx is not None and to_idx is not None
        if use_rel:
            poses0 = self._poses_with_deltas({})
            t_rel0 = np.linalg.inv(poses0[from_idx]) @ poses0[to_idx]
            R0 = t_rel0[:3, :3].copy()
            if qty == "angular":
                gap_val = 0.0
            else:
                gap_val = float(np.dot(t_rel0[:3, 3], ax))
        else:
            t_total = np.eye(4)
            for f in self.frames:
                t_total = t_total @ self._make_t(f["t_nom"], f["r_nom"])
            R0 = t_total[:3, :3].copy()
            if qty == "angular":
                gap_val = 0.0
            else:
                gap_val = float(np.dot(t_total[:3, 3], ax))

        def _g(deltas: dict[int, tuple[list[float], list[float]]]) -> float:
            return self._gap_with_deltas(
                (float(ax[0]), float(ax[1]), float(ax[2])),
                deltas,
                quantity=qty,
                R0=R0,
                ax=ax,
                from_idx=from_idx if use_rel else None,
                to_idx=to_idx if use_rel else None,
            )

        # Central first-order + diagonal Hessian share +/- eps (Glancy/Chase).
        eps = 1e-5
        sensitivities: dict[str, dict[str, float]] = {}
        total_rss_var = 0.0
        wc_sum = 0.0

        dim_details: list[dict[str, Any]] = []
        param_specs: list[dict[str, Any]] = self.param_specs()

        mean_shift = 0.0
        var_extra = 0.0
        hessian_diag: dict[str, float] = {}
        bij_pairs: list[tuple[int, int, float]] = []
        cross_pairs = 0
        full_cross = False
        for p in param_specs:
            g_p = _g(self._param_delta(p, 1.0, eps))
            g_m = _g(self._param_delta(p, -1.0, eps))
            sens = (g_p - g_m) / (2.0 * eps)
            b_ii = 0.0
            if second_order:
                b_ii = (g_p - 2.0 * gap_val + g_m) / (eps * eps)
                sig = float(p["sigma"])
                mean_shift += 0.5 * b_ii * (sig ** 2)
                var_extra += 0.5 * (b_ii * (sig ** 2)) ** 2
                hessian_diag[str(p["name"])] = b_ii
            p["a"] = sens
            p["bii"] = b_ii
            var = (sens * float(p["sigma"])) ** 2
            total_rss_var += var
            wc_sum += abs(sens) * float(p["tol_wc"])
            sensitivities[str(p["name"])] = {
                "sensitivity": sens,
                "tolerance": float(p["tol_report"]),
                "var": var,
            }
            dim_details.append({
                "name": p["name"],
                "mean": p["mean"],
                "tolerance": float(p["tol_report"]),
                "coef": sens,
                "source": p["source"],
            })
        if second_order and param_specs:
            cap = max(0, int(cross_top_n))
            ranked = sorted(
                param_specs,
                key=lambda q: abs(float(q["a"])) * float(q["sigma"]),
                reverse=True,
            )
            chosen = ranked if len(param_specs) <= cap else ranked[:cap]
            full_cross = len(chosen) == len(param_specs) and len(chosen) >= 2
            for pa, pb in itertools.combinations(chosen, 2):
                dpp = self._merge_frame_deltas(
                    self._param_delta(pa, 1.0, eps), self._param_delta(pb, 1.0, eps)
                )
                dpm = self._merge_frame_deltas(
                    self._param_delta(pa, 1.0, eps), self._param_delta(pb, -1.0, eps)
                )
                dmp = self._merge_frame_deltas(
                    self._param_delta(pa, -1.0, eps), self._param_delta(pb, 1.0, eps)
                )
                dmm = self._merge_frame_deltas(
                    self._param_delta(pa, -1.0, eps), self._param_delta(pb, -1.0, eps)
                )
                gpp = _g(dpp)
                gpm = _g(dpm)
                gmp = _g(dmp)
                gmm = _g(dmm)
                b_ij = (gpp - gpm - gmp + gmm) / (4.0 * eps * eps)
                var_extra += (b_ij * float(pa["sigma"]) * float(pb["sigma"])) ** 2
                bij_pairs.append((int(pa["k"]), int(pb["k"]), b_ij))
                cross_pairs += 1

        denom = total_rss_var if total_rss_var > 0 else 1.0
        sensitivity_contrib = {}
        for name, data in sensitivities.items():
            sensitivity_contrib[name] = {
                "sigma_mm": round(math.sqrt(data["var"]), 6),
                "contribution": round(data["var"] / denom, 4),
                "sensitivity": data["sensitivity"],
            }
        max_c = max((float(v["contribution"]) for v in sensitivity_contrib.values()), default=0.0)
        coupling = "uncoupled" if (total_rss_var <= 1e-18 or max_c <= 1e-6) else "coupled"
        sota_var = max(0.0, total_rss_var + var_extra)
        hm = sota_truncated_higher_moments(
            a=[float(p["a"]) for p in param_specs],
            sig=[float(p["sigma"]) for p in param_specs],
            bii=[float(p["bii"]) for p in param_specs],
            bij_pairs=bij_pairs,
            var_y=sota_var,
        ) if (second_order and param_specs) else {
            "skewness": 0.0, "excess_kurtosis": 0.0, "mu3": 0.0, "mu4": 0.0,
        }
        method = "sota_full_cross_msm" if full_cross else (
            "sota_diag_plus_topn_cross" if cross_pairs else "diagonal_hessian_msm"
        )
        return {
            "gap_nominal": gap_val,
            "worst_case_stack_mm": wc_sum,
            "rss_3sigma_mm": 3.0 * math.sqrt(total_rss_var),
            "sensitivity": sensitivity_contrib,
            "dimensions": dim_details,
            "coupling": coupling,
            "unit": "deg" if qty == "angular" else "mm",
            "sota": {
                "method": method,
                "mean": gap_val + mean_shift,
                "sigma": math.sqrt(sota_var),
                "mean_shift": mean_shift,
                "var_extra": var_extra,
                "skewness": hm["skewness"],
                "excess_kurtosis": hm["excess_kurtosis"],
                "cross_derivatives": bool(cross_pairs > 0),
                "cross_pairs": cross_pairs,
                "cross_top_n": int(cross_top_n) if second_order else 0,
                "full_cross": bool(full_cross),
                "n_dof": len(param_specs),
                "second_order": bool(second_order),
                "quantity": qty,
                "note": (
                    "Glancy/Chase-class central 1st+2nd MSM (truncated 4 moments). "
                    "Not Sigmetrix CETOL SOTA/GLD table"
                    + ("." if full_cross else " (cross Hessian capped at top-N).")
                ),
            },
        }

    def solve_measures(
        self,
        measures: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Solve multiple CTQ measures on the same kinematic chain.

        Each measure: {id, kind=linear|angular, direction=(dx,dy,dz)}.
        Returns per-measure stacks plus an Analyzer cross-table
        (contributor x measure tolerance-contribution).
        """
        if not measures:
            measures = [{
                "id": "gap_z",
                "kind": "linear",
                "direction": (0.0, 0.0, 1.0),
            }]
        per: dict[str, Any] = {}
        contrib_names: list[str] = []
        seen: set[str] = set()
        for m in measures:
            mid = str(m.get("id") or "measure")
            kind = str(m.get("kind") or "linear").lower()
            from_f = m.get("from_feature") or m.get("from")
            to_f = m.get("to_feature") or m.get("to")
            if kind == "angular":
                direction = tuple(m.get("axis") or m.get("direction") or (0.0, 0.0, 1.0))
                per[mid] = self.solve(
                    gap_direction=direction, quantity="angular",
                    from_frame=from_f, to_frame=to_f,
                )
            else:
                direction = tuple(m.get("direction") or (0.0, 0.0, 1.0))
                per[mid] = self.solve(
                    gap_direction=direction,
                    from_frame=from_f, to_frame=to_f,
                )
            per[mid]["measure_id"] = mid
            per[mid]["kind"] = kind
            per[mid]["direction"] = [float(x) for x in direction]
            per[mid]["from_frame"] = from_f
            per[mid]["to_frame"] = to_f
            for d in per[mid].get("dimensions") or []:
                n = str(d.get("name") or "")
                if n and n not in seen:
                    seen.add(n)
                    contrib_names.append(n)
        cross: dict[str, dict[str, float]] = {}
        for name in contrib_names:
            row: dict[str, float] = {}
            for mid, res in per.items():
                sens = (res.get("sensitivity") or {}).get(name) or {}
                row[mid] = float(sens.get("contribution") or 0.0)
            cross[name] = row
        coupling: dict[str, Any] = {}
        for mid, res in per.items():
            status = str(res.get("coupling") or "")
            sens = res.get("sensitivity") or {}
            mx = max((float((v or {}).get("contribution") or 0.0) for v in sens.values()), default=0.0)
            if not status:
                rss = float(res.get("rss_3sigma_mm") or 0.0)
                status = "uncoupled" if (rss <= 1e-12 or mx <= 1e-6) else "coupled"
            coupling[mid] = {
                "status": status,
                "max_contribution": mx,
                "note": (
                    "no kinematic coupling in this direction"
                    if status == "uncoupled"
                    else "loop DOF projects onto this CTQ"
                ),
            }
        return {
            "schema": "clawstack.cetol_vector_loop_measures.v2",
            "frame_names": [str(f.get("name") or "") for f in self.frames],
            "measures": per,
            "cross_table": cross,
            "measure_ids": [str(m.get("id") or "") for m in measures],
            "measure_coupling": coupling,
        }

    def _solve_angular(self, axis: tuple[float, float, float]) -> dict[str, Any]:
        """Angular CTQ: rotation of the closing frame about `axis` (degrees)."""
        ax = np.array(axis, dtype=float)
        nrm = float(np.linalg.norm(ax))
        if nrm <= 0:
            ax = np.array([0.0, 0.0, 1.0])
        else:
            ax = ax / nrm
        T_total = np.eye(4)
        for f in self.frames:
            T_total = T_total @ self._make_t(f["t_nom"], f["r_nom"])
        R0 = T_total[:3, :3]
        # Nominal closing angle vs identity about axis (small-angle proxy: 0)
        gap_val = 0.0
        eps = 1e-5
        sensitivities: dict[str, dict[str, float]] = {}
        total_rss_var = 0.0
        wc_sum = 0.0
        dim_details: list[dict[str, Any]] = []

        def _angle_deg(R: np.ndarray) -> float:
            rel = R @ R0.T
            # axis-angle: theta = acos((tr-1)/2), signed by axis
            tr = float(np.trace(rel))
            c = max(-1.0, min(1.0, (tr - 1.0) * 0.5))
            theta = math.acos(c)
            skew = np.array([
                rel[2, 1] - rel[1, 2],
                rel[0, 2] - rel[2, 0],
                rel[1, 0] - rel[0, 1],
            ])
            sign = 1.0 if float(np.dot(skew, ax)) >= 0 else -1.0
            return sign * math.degrees(theta)

        for idx, f in enumerate(self.frames):
            t_nom = list(f["t_nom"])
            r_nom = list(f["r_nom"])
            t_tol = f["t_tol"]
            r_tol = f["r_tol"]
            for i, name_t in enumerate(["Tx", "Ty", "Tz"]):
                tol = t_tol[i]
                if tol <= 0:
                    continue
                t_nom[i] += eps
                T_p = self._eval_chain(idx, t_nom, r_nom)
                val_p = _angle_deg(T_p[:3, :3])
                sens = (val_p - gap_val) / eps
                t_nom[i] -= eps
                var = (sens * (tol / 6.0)) ** 2
                total_rss_var += var
                wc_sum += abs(sens) * tol
                dim_name = f"{f['name']}_{name_t}"
                sensitivities[dim_name] = {"sensitivity": sens, "tolerance": tol, "var": var}
                dim_details.append({
                    "name": dim_name, "mean": f["t_nom"][i], "tolerance": tol,
                    "coef": sens, "source": f["source"],
                })
            for i, name_r in enumerate(["Rx", "Ry", "Rz"]):
                tol_deg = r_tol[i]
                if tol_deg <= 0:
                    continue
                tol_rad = np.radians(tol_deg)
                r_nom[i] += np.degrees(eps)
                T_p = self._eval_chain(idx, t_nom, r_nom)
                val_p = _angle_deg(T_p[:3, :3])
                sens = (val_p - gap_val) / eps
                r_nom[i] -= np.degrees(eps)
                var = (sens * (tol_rad / 6.0)) ** 2
                total_rss_var += var
                wc_sum += abs(sens) * tol_rad
                dim_name = f"{f['name']}_{name_r}"
                sensitivities[dim_name] = {"sensitivity": sens, "tolerance": tol_deg, "var": var}
                dim_details.append({
                    "name": dim_name, "mean": f["r_nom"][i], "tolerance": tol_deg,
                    "coef": sens, "source": f["source"],
                })
        denom = total_rss_var if total_rss_var > 0 else 1.0
        sensitivity_contrib = {
            name: {
                "sigma_mm": round(math.sqrt(data["var"]), 6),
                "contribution": round(data["var"] / denom, 4),
                "sensitivity": data["sensitivity"],
            }
            for name, data in sensitivities.items()
        }
        max_c = max((float(v["contribution"]) for v in sensitivity_contrib.values()), default=0.0)
        coupling = "uncoupled" if (total_rss_var <= 1e-18 or max_c <= 1e-6) else "coupled"
        return {
            "gap_nominal": gap_val,
            "worst_case_stack_mm": wc_sum,
            "rss_3sigma_mm": 3.0 * math.sqrt(total_rss_var),
            "sensitivity": sensitivity_contrib,
            "dimensions": dim_details,
            "unit": "deg",
            "coupling": coupling,
        }

    def _param_delta(
        self, spec: dict[str, Any], sign: float, eps: float
    ) -> dict[int, tuple[list[float], list[float]]]:
        dt = [0.0, 0.0, 0.0]
        dr = [0.0, 0.0, 0.0]
        axis = int(spec["axis"])
        if spec.get("kind") == "t":
            dt[axis] = sign * eps
        else:
            dr[axis] = sign * float(np.degrees(eps))
        return {int(spec["idx"]): (dt, dr)}

    @staticmethod
    def _merge_frame_deltas(
        a: dict[int, tuple[list[float], list[float]]],
        b: dict[int, tuple[list[float], list[float]]],
    ) -> dict[int, tuple[list[float], list[float]]]:
        out: dict[int, tuple[list[float], list[float]]] = {}
        for k in set(a) | set(b):
            dta, dra = a.get(k, ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))
            dtb, drb = b.get(k, ([0.0, 0.0, 0.0], [0.0, 0.0, 0.0]))
            out[k] = (
                [dta[i] + dtb[i] for i in range(3)],
                [dra[i] + drb[i] for i in range(3)],
            )
        return out

    def _angle_deg(self, R: np.ndarray, R0: np.ndarray, ax: np.ndarray) -> float:
        rel = R @ R0.T
        tr = float(np.trace(rel))
        c = max(-1.0, min(1.0, (tr - 1.0) * 0.5))
        theta = math.acos(c)
        skew = np.array([
            rel[2, 1] - rel[1, 2],
            rel[0, 2] - rel[2, 0],
            rel[1, 0] - rel[0, 1],
        ])
        sign = 1.0 if float(np.dot(skew, ax)) >= 0 else -1.0
        return sign * math.degrees(theta)

    def _gap_with_deltas(
        self,
        gap_direction: tuple[float, float, float],
        deltas: dict[int, tuple[list[float], list[float]]],
        *,
        quantity: str = "linear",
        R0: np.ndarray | None = None,
        ax: np.ndarray | None = None,
        from_idx: int | None = None,
        to_idx: int | None = None,
    ) -> float:
        if from_idx is not None and to_idx is not None:
            poses = self._poses_with_deltas(deltas)
            t_rel = np.linalg.inv(poses[int(from_idx)]) @ poses[int(to_idx)]
            if str(quantity).lower() == "angular":
                if R0 is None:
                    R0 = np.eye(3)
                if ax is None:
                    ax = np.array(gap_direction, dtype=float)
                return self._angle_deg(t_rel[:3, :3], R0, ax)
            return float(np.dot(t_rel[:3, 3], gap_direction))
        t_acc = np.eye(4)
        for idx, f in enumerate(self.frames):
            t = list(f["t_nom"])
            r = list(f["r_nom"])
            if idx in deltas:
                dt, dr = deltas[idx]
                t = [t[i] + dt[i] for i in range(3)]
                r = [r[i] + dr[i] for i in range(3)]
            t_acc = t_acc @ self._make_t(tuple(t), tuple(r))
        if str(quantity).lower() == "angular":
            if R0 is None:
                R0 = np.eye(3)
            if ax is None:
                ax = np.array(gap_direction, dtype=float)
            return self._angle_deg(t_acc[:3, :3], R0, ax)
        return float(np.dot(t_acc[:3, 3], gap_direction))

    def _eval_chain(self, perturbed_idx: int, t_pert: list[float], r_pert: list[float]) -> np.ndarray:
        T = np.eye(4)
        for idx, f in enumerate(self.frames):
            if idx == perturbed_idx:
                T = T @ self._make_t(tuple(t_pert), tuple(r_pert))
            else:
                T = T @ self._make_t(f["t_nom"], f["r_nom"])
        return T

    def _make_t(self, translation: tuple[float, float, float], rotation_deg: tuple[float, float, float]) -> np.ndarray:
        tx, ty, tz = translation
        rx, ry, rz = np.radians(rotation_deg)
        Rx = np.array([[1.0, 0.0, 0.0],
                       [0.0, math.cos(rx), -math.sin(rx)],
                       [0.0, math.sin(rx), math.cos(rx)]])
        Ry = np.array([[math.cos(ry), 0.0, math.sin(ry)],
                       [0.0, 1.0, 0.0],
                       [-math.sin(ry), 0.0, math.cos(ry)]])
        Rz = np.array([[math.cos(rz), -math.sin(rz), 0.0],
                       [math.sin(rz), math.cos(rz), 0.0],
                       [0.0, 0.0, 1.0]])
        R = Rz @ Ry @ Rx
        T = np.eye(4)
        T[:3, :3] = R
        T[:3, 3] = [tx, ty, tz]
        return T
