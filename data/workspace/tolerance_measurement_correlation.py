# -*- coding: utf-8 -*-
"""Measured lot vs simulated stack correlation (Cetol measurement correlation path)."""
from __future__ import annotations

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

import numpy as np


def load_measured_lot(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema") != "clawstack.measured_lot.v1":
        raise ValueError(f"schema!=clawstack.measured_lot.v1: {path}")
    return data


def _cpk_from_samples(samples: np.ndarray, lsl: float, usl: float) -> tuple[float, float, float]:
    mu = float(np.mean(samples))
    sigma = float(np.std(samples, ddof=1)) if len(samples) > 1 else 0.0
    if sigma <= 0:
        return mu, sigma, 0.0
    cp = (usl - lsl) / (6.0 * sigma)
    cpk = min((usl - mu) / (3.0 * sigma), (mu - lsl) / (3.0 * sigma))
    return mu, sigma, float(cpk)


def correlate_measured_lot(
    *,
    l10_report: dict[str, Any],
    measured_lot: dict[str, Any],
    lsl: float | None = None,
    usl: float | None = None,
    nominal_target: float = 0.0,
) -> dict[str, Any]:
    """Compare Monte Carlo prediction to measured lot (gap or KPI samples)."""
    mc = l10_report.get("monte_carlo") or {}
    pred_mean = float(mc.get("mean") or 0.0) + float(nominal_target)
    pred_sigma = float(mc.get("sigma") or 0.0)
    pred_cpk = float(mc.get("Cpk") or 0.0)

    lsl_v = float(lsl if lsl is not None else mc.get("lsl") or -0.05)
    usl_v = float(usl if usl is not None else mc.get("usl") or 0.05)

    samples_raw = measured_lot.get("gap_samples_mm") or measured_lot.get("samples_mm") or []
    samples = np.asarray([float(x) for x in samples_raw], dtype=float)
    if samples.size == 0:
        return {
            "schema": "clawstack.tolerance_measurement_correlation.v1",
            "ok": False,
            "reason": "no_samples",
        }

    mu_m, sigma_m, cpk_m = _cpk_from_samples(samples, lsl_v, usl_v)
    bias_mm = mu_m - pred_mean
    sigma_ratio = (sigma_m / pred_sigma) if pred_sigma > 0 else None

    within = float(np.mean((samples >= lsl_v) & (samples <= usl_v)))
    yield_delta = within - float(mc.get("yield_rate") or 0.0)

    checks = {
        "bias_within_2sigma": abs(bias_mm) <= max(2.0 * pred_sigma, 0.02),
        "cpk_measured_ge_1": cpk_m >= 1.0,
        "yield_delta_abs_le_0.10": abs(yield_delta) <= 0.10,
    }
    verdict = "PASS" if all(checks.values()) else "FAIL"

    return {
        "schema": "clawstack.tolerance_measurement_correlation.v1",
        "ok": True,
        "verdict": verdict,
        "lot_id": measured_lot.get("lot_id"),
        "n_samples": int(samples.size),
        "predicted": {"mean_mm": pred_mean, "sigma_mm": pred_sigma, "Cpk": pred_cpk},
        "measured": {"mean_mm": round(mu_m, 6), "sigma_mm": round(sigma_m, 6), "Cpk": round(cpk_m, 4)},
        "bias_mm": round(bias_mm, 6),
        "sigma_ratio": round(sigma_ratio, 4) if sigma_ratio is not None else None,
        "yield_measured": round(within, 6),
        "yield_delta": round(yield_delta, 6),
        "checks": checks,
        "lsl": lsl_v,
        "usl": usl_v,
    }
