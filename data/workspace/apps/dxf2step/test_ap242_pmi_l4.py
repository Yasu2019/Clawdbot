# -*- coding: utf-8 -*-
"""CETOL L4 (T-iy63) regression test: AP242 semantic PMI -> tolerance stack.

Run:  python data/workspace/apps/dxf2step/test_ap242_pmi_l4.py
Verifies:
  A. AP242 parse: +/- tolerances, GD&T magnitudes, datum labels
  B. Manifest enrich merges PMI dims into nominal_dims_mm
  C. to_tolerance_dims honours PMI (asymmetric -> mid-shifted symmetric)
  D. L10 assembly stack reports 'pmi' dimension sources
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
WORKSPACE = HERE.parents[1]  # data/workspace
for p in (HERE, WORKSPACE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import step_pmi_extract as spe  # noqa: E402
import part_geometry_contract as pgc  # noqa: E402
import tolerance_l10_assembly as tla  # noqa: E402

FIXTURE = HERE / "test_data" / "ap242_pmi_sample.step"


def main() -> int:
    pmi = spe.parse_step_pmi(FIXTURE)
    dims = {d["name"]: d for d in pmi["pmi_dims"]}
    assert "hole_pitch" in dims and "diameter" in dims, dims.keys()
    hp = dims["hole_pitch"]
    assert hp["nominal_mm"] == 45.0 and hp["plus_mm"] == 0.10 and hp["minus_mm"] == -0.05, hp
    dia = dims["diameter"]
    assert dia["nominal_mm"] == 10.0 and dia["plus_mm"] == 0.02 and dia["minus_mm"] == -0.02, dia
    gdt = {g["name"]: g for g in pmi["gdt_annotations"] if g.get("source") == "gdt_pmi_step_ap242"}
    assert gdt["hole_a_position"]["gdt_type"] == "position" and gdt["hole_a_position"]["tolerance_mm"] == 0.1
    assert gdt["base_flatness"]["gdt_type"] == "flatness" and gdt["base_flatness"]["tolerance_mm"] == 0.05
    datum_names = [d["name"] for d in pmi["datums"]]
    assert "A" in datum_names and "B" in datum_names, datum_names
    print("A. AP242 parse: PASS")

    manifest = {
        "schema": "clawstack.part_manifest.v1",
        "bbox_mm": {"Lx": 100.0, "Ly": 50.0, "Lz": 3.0},
        "sheet_thickness_mm": 3.0,
        "features": {"nominal_dims_mm": [{"name": "bbox_Lx", "nominal_mm": 100.0, "source": "step_bbox"}]},
    }
    enriched = spe.enrich_manifest_with_pmi(manifest, pmi)
    nd = {d["name"]: d for d in enriched["features"]["nominal_dims_mm"]}
    assert "hole_pitch" in nd and nd["hole_pitch"]["plus_mm"] == 0.10
    assert enriched["pmi_enrichment"]["pmi_dim_count"] == 2
    print("B. manifest enrich: PASS")

    td = {d["name"]: d for d in pgc.to_tolerance_dims(enriched)}
    hp_td = td["hole_pitch"]
    assert abs(hp_td["mean"] - 45.025) < 1e-9 and abs(hp_td["tolerance"] - 0.075) < 1e-9, hp_td
    assert hp_td["source"] == "pmi" and td["bbox_Lx"]["source"] == "measured"
    print("C. stack dims (asymmetric mid-shift): PASS")

    rep = tla.analyze_l10_assembly_from_manifest(enriched)
    srcs = rep.get("dimension_source_summary") or {}
    assert srcs.get("pmi", 0) >= 2, srcs
    assert rep.get("monte_carlo"), "MC must run"
    print(f"D. L10 stack: PASS  sources={srcs}")
    print("ALL_CETOL_L4_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
