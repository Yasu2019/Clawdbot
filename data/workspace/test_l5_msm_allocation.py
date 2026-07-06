# -*- coding: utf-8 -*-
"""CETOL L5 (T-iy63) regression test: MSM (Method of System Moments) + allocation.

Run:  python data/workspace/test_l5_msm_allocation.py
  V1. MSM analytic sigma/yield matches Monte Carlo (<1% / <0.005) on mixed
      normal+uniform+triangular stack; sensitivity ranking correct
  V2. tolerance_allocation common-scale k reaches target Cpk (re-verified by MSM)
  V3. infeasible when fixed die-set (assembly_l10) variance exceeds budget
  V4. loosen candidates quantified (cpk_if_loosened_x2) when already capable
  V5. analyze_stack embeds msm + tolerance_allocation (engine v2_l5_msm)
"""
from __future__ import annotations

import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parent
for p in (WORKSPACE, WORKSPACE / "apps" / "dxf2step"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import tolerance_stackup_engine as tse  # noqa: E402

SD = tse.StackDimension


def main() -> int:
    dims = [
        SD("a_norm", 10.0, 0.30, 1.0, "normal"),
        SD("b_unif", 5.0, 0.10, -1.0, "uniform"),
        SD("c_tri", 2.0, 0.15, 1.0, "triangular"),
        SD("d_norm", 1.0, 0.06, 1.0, "normal"),
    ]
    lsl, usl = 8.0 - 0.25, 8.0 + 0.25
    mc = tse.monte_carlo_stack(dims, n=400_000, lsl=lsl, usl=usl)
    msm = tse.msm_stack(dims, lsl=lsl, usl=usl)
    assert abs(msm["sigma"] - mc["sigma"]) / mc["sigma"] < 0.01
    assert abs(msm["yield_rate"] - mc["yield_rate"]) < 0.005
    top = max(msm["sensitivity"].items(), key=lambda kv: kv[1]["contribution"])
    assert top[0] == "c_tri"  # 0.15/sqrt(6)=0.0612 dominates 0.30/6=0.05
    print("V1 MSM vs MC + sensitivity: PASS")

    loose = [
        SD("p1", 0.0, 0.30, 1.0, "normal", "pmi"),
        SD("p2", 0.0, 0.20, -1.0, "normal", "pmi"),
        SD("die", 0.0, 0.05, 1.0, "normal", "assembly_l10"),
    ]
    alloc = tse.tolerance_allocation(loose, lsl=-0.15, usl=0.15, target_cpk=1.33)
    assert alloc["reason"] == "tighten_by_common_scale"
    k = alloc["common_tighten_scale"]
    new_dims = [
        SD(d.name, d.mean, d.tolerance * (k if d.source != "assembly_l10" else 1.0),
           d.coef, d.distribution, d.source)
        for d in loose
    ]
    chk = tse.msm_stack(new_dims, lsl=-0.15, usl=0.15)
    assert abs(chk["Cpk"] - 1.33) < 0.01, chk["Cpk"]
    print(f"V2 allocation tighten: PASS (k={k} -> Cpk {chk['Cpk']:.4f})")

    imp = tse.tolerance_allocation(
        [SD("p", 0.0, 0.02, 1.0, "normal", "pmi"),
         SD("die", 0.0, 0.5, 1.0, "normal", "assembly_l10")],
        lsl=-0.1, usl=0.1, target_cpk=1.33)
    assert not imp["feasible"] and imp["reason"] == "fixed_die_set_variance_exceeds_budget"
    print("V3 infeasible (die-set budget): PASS")

    cap = tse.tolerance_allocation(
        [SD("big", 0.0, 0.06, 1.0, "normal", "pmi"),
         SD("tiny", 0.0, 0.005, 1.0, "normal", "pmi")],
        lsl=-0.1, usl=0.1, target_cpk=1.33)
    recs = {r["name"]: r for r in cap["recommendations"]}
    assert cap["reason"] == "already_capable"
    assert recs["tiny"]["action"] == "loosen_candidate" and recs["tiny"]["cpk_if_loosened_x2"] >= 1.33
    print("V4 loosen candidates: PASS")

    rep = tse.analyze_stack(dims, nominal_target=8.0, lsl=lsl, usl=usl, n=20_000)
    assert rep.get("msm") and rep.get("tolerance_allocation")
    assert rep.get("engine") == "tolerance_stackup_engine.v2_l5_msm"
    print("V5 analyze_stack embeds msm+allocation: PASS")
    print("ALL_L5_MSM_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
