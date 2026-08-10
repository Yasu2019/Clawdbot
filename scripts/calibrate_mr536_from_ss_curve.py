# -*- coding: utf-8 -*-
"""Calibrate the MR536 (AA5052-H34) material card from the measured SS curves.

INC-188 was blocked because the deck's flow curve had no traceable origin. This
reads the customer's tensile data, derives engineering and true properties, fits
the /MAT/LAW2 form sigma = a + b*eps_p^n, and records the result as measured
provenance. It does not modify any deck.

Source workbook: MR536_SS曲線データ.xlsx, JIS Z 2241 No.5 specimen, 0 deg to
rolling, 5 mm/min, 3 repeats per thickness.
"""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "workspace" / "universal_growth.db"
DEFAULT_XLSX = Path.home() / "OneDrive" / "デスクトップ" / "MR536_SS曲線テ゛ータ.xlsx"
SHEET = "MR536_SS曲線"
FIRST_DATA_ROW = 31

# (label, nominal thickness mm, stress column, strain column) - 1-indexed columns.
SPECIMENS = (
    ("t0.40_run1", 0.40, 8, 9),
    ("t0.40_run2", 0.40, 10, 11),
    ("t0.40_run3", 0.40, 12, 13),
    ("t0.51_run1", 0.51, 15, 16),
    ("t0.51_run2", 0.51, 17, 18),
    ("t0.51_run3", 0.51, 19, 20),
)

# The 0.51 mm stress columns are high by exactly the thickness ratio, which means the
# force was divided by the 0.40 mm cross-section. Young's modulus is the proof: raw
# 0.51 mm data gives 86.6 GPa, impossible for aluminium, and the correction brings it
# to 67.9 GPa while making yield and UTS agree with the 0.40 mm coupons within 0.6%.
# Strain columns are area-independent and are therefore left untouched.
AREA_CORRECTION = {0.51: 0.40 / 0.51}


def read_curves(xlsx: Path) -> dict[str, dict]:
    workbook = openpyxl.load_workbook(xlsx, data_only=True, read_only=True)
    sheet = workbook[SHEET]
    rows = list(sheet.iter_rows(min_row=FIRST_DATA_ROW, values_only=True))
    workbook.close()
    curves: dict[str, dict] = {}
    for label, thickness, scol, ecol in SPECIMENS:
        factor = AREA_CORRECTION.get(thickness, 1.0)
        stress, strain = [], []
        for row in rows:
            if len(row) < max(scol, ecol):
                continue
            s, e = row[scol - 1], row[ecol - 1]
            if isinstance(s, (int, float)) and isinstance(e, (int, float)):
                stress.append(float(s) * factor)
                strain.append(float(e))
        curves[label] = {"thickness_mm": thickness, "stress": stress, "strain": strain,
                         "area_correction": factor}
    return curves


def analyse(stress: list[float], strain: list[float]) -> dict:
    """Engineering properties, then true values valid up to uniform elongation."""
    peak = max(range(len(stress)), key=lambda i: stress[i])
    uts, uniform_elongation = stress[peak], strain[peak]

    # Young's modulus from the early linear part, chosen well below yield.
    fit = [(e, s) for e, s in zip(strain, stress) if 0.0005 <= e <= 0.002]
    if len(fit) < 3:
        fit = list(zip(strain[:40], stress[:40]))
    n = len(fit)
    mean_e = sum(p[0] for p in fit) / n
    mean_s = sum(p[1] for p in fit) / n
    denom = sum((p[0] - mean_e) ** 2 for p in fit)
    modulus = sum((p[0] - mean_e) * (p[1] - mean_s) for p in fit) / denom if denom else 0.0

    # 0.2% offset yield: first crossing of the offset line.
    yield_strength = None
    for e, s in zip(strain, stress):
        if e > 0.002 and s <= modulus * (e - 0.002):
            yield_strength = s
            break
    if yield_strength is None:
        yield_strength = min(stress[peak], modulus * 0.002)

    fracture_strain = strain[-1]
    return {
        "youngs_modulus_MPa": modulus,
        "yield_0p2_MPa": yield_strength,
        "uts_MPa": uts,
        "uniform_elongation": uniform_elongation,
        "strain_at_last_point": fracture_strain,
        "true_uts_MPa": uts * (1.0 + uniform_elongation),
        "true_strain_at_uts": __import__("math").log(1.0 + uniform_elongation),
        "points": len(stress),
    }


def fit_law2(stress: list[float], strain: list[float], modulus: float,
             yield_strength: float) -> dict:
    """Least-squares fit of sigma_true = a + b*eps_p^n over the uniform-strain range.

    a is fixed to the measured 0.2% offset yield so the card cannot drift away from
    the coupon. Only b and n are free, and n is scanned then b solved in closed form.
    """
    import math

    peak = max(range(len(stress)), key=lambda i: stress[i])
    samples = []
    for i in range(peak + 1):
        eng_s, eng_e = stress[i], strain[i]
        if eng_s <= 0 or eng_e <= 0:
            continue
        true_s = eng_s * (1.0 + eng_e)
        true_e = math.log(1.0 + eng_e)
        plastic = true_e - true_s / modulus
        if plastic > 1e-4 and true_s > yield_strength:
            samples.append((plastic, true_s - yield_strength))
    if len(samples) < 10:
        return {"fitted": False, "reason": "insufficient plastic points"}

    best = None
    n = 0.02
    while n <= 1.0001:
        num = sum(dp * (ep ** n) for ep, dp in samples)
        den = sum((ep ** n) ** 2 for ep in (p[0] for p in samples))
        b = num / den if den else 0.0
        err = sum((dp - b * ep ** n) ** 2 for ep, dp in samples)
        if best is None or err < best[0]:
            best = (err, b, n)
        n += 0.005

    err, b, n = best
    total = sum((dp - sum(d for _, d in samples) / len(samples)) ** 2 for _, dp in samples)
    return {"fitted": True, "a_MPa": yield_strength, "b_MPa": b, "n": n,
            "r_squared": 1.0 - err / total if total else 0.0,
            "fit_points": len(samples),
            "max_plastic_strain_in_fit": max(p[0] for p in samples)}


def summarise(curves: dict[str, dict]) -> dict:
    out: dict[str, dict] = {}
    for label, data in curves.items():
        props = analyse(data["stress"], data["strain"])
        props["thickness_mm"] = data["thickness_mm"]
        props["law2"] = fit_law2(data["stress"], data["strain"],
                                 props["youngs_modulus_MPa"], props["yield_0p2_MPa"])
        out[label] = props
    return out


def average(results: dict[str, dict], thickness: float) -> dict:
    picked = [r for r in results.values() if abs(r["thickness_mm"] - thickness) < 1e-9]
    fits = [r["law2"] for r in picked if r["law2"].get("fitted")]
    mean = lambda key, src: sum(s[key] for s in src) / len(src)
    return {
        "thickness_mm": thickness, "repeats": len(picked),
        "youngs_modulus_MPa": mean("youngs_modulus_MPa", picked),
        "yield_0p2_MPa": mean("yield_0p2_MPa", picked),
        "uts_MPa": mean("uts_MPa", picked),
        "uniform_elongation": mean("uniform_elongation", picked),
        "strain_at_last_point": mean("strain_at_last_point", picked),
        "law2_a_MPa": mean("a_MPa", fits) if fits else None,
        "law2_b_MPa": mean("b_MPa", fits) if fits else None,
        "law2_n": mean("n", fits) if fits else None,
        "law2_r_squared": mean("r_squared", fits) if fits else None,
    }


def record(db_path: Path, avg: dict, source: str) -> dict:
    conn = sqlite3.connect(db_path, timeout=300)
    conn.execute("PRAGMA busy_timeout=300000")
    now = datetime.now(timezone.utc).isoformat()
    rows = (
        ("elastic", "youngs_modulus", avg["youngs_modulus_MPa"] * 1e6, "Pa", 1),
        ("strength", "tensile_yield_0p2", avg["yield_0p2_MPa"] * 1e6, "Pa", 1),
        ("strength", "ultimate_tensile", avg["uts_MPa"] * 1e6, "Pa", 1),
        ("ductility", "uniform_elongation", avg["uniform_elongation"], "-", 1),
        ("ductility", "elongation_at_last_point", avg["strain_at_last_point"], "-", 0),
        ("law2_hardening", "a", avg["law2_a_MPa"] * 1e6, "Pa", 1),
        ("law2_hardening", "b", avg["law2_b_MPa"] * 1e6, "Pa", 1),
        ("law2_hardening", "n", avg["law2_n"], "-", 1),
    )
    correction = AREA_CORRECTION.get(avg["thickness_mm"], 1.0)
    note = (f"Measured JIS Z 2241 No.5 coupon, 0 deg to rolling, 5 mm/min, "
            f"{avg['repeats']} repeats, nominal {avg['thickness_mm']} mm. "
            f"Stress scaled by {correction:.4f} to correct a cross-section area error "
            f"in the source workbook (raw data gave a non-physical 86.6 GPa modulus). "
            f"Hardening fit valid to plastic strain {avg['uniform_elongation']:.3f} "
            f"(uniform elongation); beyond that it is extrapolation.")
    for attempt in range(5):
        try:
            conn.execute("DELETE FROM shear_blanking_calibration WHERE material='MR536'")
            for model, parameter, value, unit, usable in rows:
                conn.execute(
                    "INSERT INTO shear_blanking_calibration "
                    "(material,temper,model,parameter,value,unit,source_id,source_url,"
                    "traceability,usable_for_calibration,note,recorded_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                    ("MR536", "H34", model, parameter, value, unit,
                     "measured:" + source, source, "measured_coupon", usable, note, now),
                )
            conn.commit()
            break
        except sqlite3.OperationalError as exc:
            if "locked" not in str(exc) or attempt == 4:
                raise
            conn.rollback()
            time.sleep(20)
    count = conn.execute(
        "SELECT COUNT(*) FROM shear_blanking_calibration WHERE material='MR536'").fetchone()[0]
    conn.close()
    return {"rows": count, "traceability": "measured_coupon"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xlsx", type=Path, default=DEFAULT_XLSX)
    parser.add_argument("--db", type=Path, default=DB_PATH)
    parser.add_argument("--thickness", type=float, default=0.51)
    parser.add_argument("--record", action="store_true")
    args = parser.parse_args()

    curves = read_curves(args.xlsx)
    results = summarise(curves)
    avg = average(results, args.thickness)
    report = {"source": str(args.xlsx), "per_specimen": results, "average": avg}
    if args.record:
        report["recorded"] = record(args.db, avg, str(args.xlsx))
    print(json.dumps(report, ensure_ascii=False, indent=2, default=float))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
