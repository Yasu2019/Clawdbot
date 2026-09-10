#!/usr/bin/env python3
"""Run deterministic constitutive sanity checks and emit a JSON report."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from material_chain import CrossWLF, PVTTable, TaitTwoDomain


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--card", type=Path, default=Path("config/virtual_material_pp_screening.json"))
    ap.add_argument("--output", type=Path, required=True)
    a = ap.parse_args()
    card = json.loads(a.card.read_text(encoding="utf-8"))
    tait_cfg = card["tait_two_domain"]
    tait = TaitTwoDomain(
        rho_ref=1.0 / float(tait_cfg["A0"]), t_ref=float(tait_cfg["Tref_K"]),
        alpha_melt=2.0e-4, alpha_solid=7.0e-5, transition_k=393.15,
        width_k=5.0, B_melt=float(tait_cfg["B0"]), B_solid=float(tait_cfg["B0"]),
        C=float(tait_cfg["C"]), p_ref=101325.0)
    w = card["cross_wlf"]
    cross = CrossWLF(float(w["n"]), float(w["tauStar_Pa"]), float(w["D1"]),
                     float(w["D2_C"]) + 273.15, float(w["D3_C_MPa"]) / 1.0e6,
                     float(w["A1"]), float(w["A2_C"]))
    pvt = PVTTable((313.15, 503.15), (101325.0, 30.0e6),
                   ((917.0, 900.0), (1037.0, 1018.0)))
    samples = [(101325.0, 503.15), (30.0e6, 503.15), (30.0e6, 313.15)]
    densities = [tait.density(p, t) for p, t in samples]
    report = {
        "status": "PASS" if pvt.validate()["valid"] and all(x > 0 for x in densities) else "FAIL",
        "data_status": card["identity"]["data_status"],
        "tait": {"density_kg_m3": densities,
                  "compressibility_1_Pa": [tait.compressibility_pa_inv(p, t) for p, t in samples],
                  "sound_speed_m_s": [tait.sound_speed_m_s(p, t) for p, t in samples]},
        "cross_wlf": {"viscosity_1_per_s_Pa_s": cross.viscosity(1.0, 503.15, 101325.0),
                      "viscosity_1000_per_s_Pa_s": cross.viscosity(1000.0, 503.15, 101325.0)},
        "pvt": pvt.validate(),
        "limitations": ["virtual coefficients", "not a measured material calibration", "custom OpenFOAM Cross-WLF plug-in still required for direct momentum coupling"]}
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
