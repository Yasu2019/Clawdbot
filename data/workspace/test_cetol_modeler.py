# -*- coding: utf-8 -*-
"""CETOL Modeler/Analyzer tests: geometry-derived 3D loop, dual contrib, what-if.

Run:  python data/workspace/test_cetol_modeler.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
sys.path.insert(0, str(WORKSPACE))
sys.path.insert(0, str(WORKSPACE / "apps" / "dxf2step"))

import cetol_modeler as ctm  # noqa: E402
import cetol_process_physics as cpp  # noqa: E402
import tolerance_stackup_engine as tse  # noqa: E402


FORBIDDEN = ctm.FORBIDDEN_GENERIC_FRAMES


def _pump_manifest() -> dict:
    return {
        "schema": "clawstack.part_manifest.v1",
        "job_id": "PROSTATIC_MINIATURE_PUMP_DEMO_09",
        "source_dxf": "medical_piezo_micropump_v4.dxf",
        "bbox_mm": {"Lx": 28.0, "Ly": 28.0, "Lz": 8.5},
        "sheet_thickness_mm": 0.8,
        "features": {
            "holes": [
                {"name": "valve_port", "diameter_mm": 2.2, "position_tol_mm": 0.04,
                 "xyz_mm": [8.0, 14.0, 8.5], "source": "gdt_pmi_step_cylinder"},
                {"name": "outlet_port", "diameter_mm": 2.2, "position_tol_mm": 0.04,
                 "xyz_mm": [20.0, 14.0, 8.5], "source": "gdt_pmi_step_cylinder"},
            ],
            "datums": [],
            "nominal_dims_mm": [
                {"name": "bbox_Lx", "nominal_mm": 28.0, "source": "step_bbox"},
            ],
        },
        "physics_handoff": {"openradioss": {"ready": True, "thickness_mm": 0.8}},
        "units": "mm",
    }


def _bracket_manifest() -> dict:
    return {
        "schema": "clawstack.part_manifest.v1",
        "job_id": "sheet_strip_bracket_job",
        "source_dxf": "L_bracket.dxf",
        "bbox_mm": {"Lx": 180.0, "Ly": 15.0, "Lz": 120.0},
        "sheet_thickness_mm": 2.0,
        "features": {
            "holes": [
                {"name": "mount_a", "diameter_mm": 6.0, "position_tol_mm": 0.05,
                 "xyz_mm": [20.0, 7.5, 2.0]},
            ],
            "datums": [{"name": "datum_A", "letter": "A", "flatness_tol_mm": 0.02}],
            "nominal_dims_mm": [],
        },
        "physics_handoff": {"openradioss": {"ready": True, "thickness_mm": 2.0}},
        "units": "mm",
    }


def main() -> int:
    pump = _pump_manifest()
    brk = _bracket_manifest()
    m_pump = ctm.build_cetol_model(pump, job_id=pump["job_id"])
    m_brk = ctm.build_cetol_model(brk, job_id=brk["job_id"])

    p_names = [f["name"] for f in m_pump["frames"]]
    b_names = [f["name"] for f in m_brk["frames"]]
    for banned in FORBIDDEN:
        assert banned not in p_names, p_names
        assert banned not in b_names, b_names
        assert not any(n.startswith(banned + "_") and n.split("_")[0] == banned for n in p_names)
    assert any("PUMP" in n or "PROSTATIC" in n for n in p_names), p_names
    assert any("sheet_strip_bracket_job" in n or "bracket_job" in n for n in b_names), b_names
    assert p_names != b_names
    p_bbox = m_pump["bbox_mm"]
    b_bbox = m_brk["bbox_mm"]
    assert abs(p_bbox["Lx"] - 28.0) < 1e-9
    assert abs(b_bbox["Lx"] - 180.0) < 1e-9
    print("V1 geometry-derived frames (pump vs bracket, no hardcoded BasePlate/Bracket): PASS")

    loop = ctm.loop_from_frames(m_pump["frames"])
    multi = loop.solve_measures(m_pump["measures"])
    assert len(multi["measure_ids"]) >= 2
    assert "gap_z" in multi["measures"] and "pitch_x" in multi["measures"]
    assert multi["cross_table"], multi
    print("V2 multi-measure VectorLoop3D + cross-table: PASS")

    dual = m_pump["dual_contribution"]
    assert dual.get("rows")
    row0 = dual["rows"][0]
    assert "dimension_contribution" in row0 and "tolerance_contribution" in row0
    print("V3 dimension vs tolerance contribution: PASS")

    flags = {f["code"] for f in m_pump["advisor"]}
    assert "missing_datums" in flags
    assert m_pump["openradioss"]["present"] is False
    assert m_pump["openradioss"]["status"] == "INSUFFICIENT"
    print("V4 Advisor missing datums + OpenRadioss fail-closed: PASS")

    stations = {s["station"] for s in m_pump["station_contributors"]}
    assert "BL" in stations and "BE" in stations and "PI" in stations
    print("V5 progressive-die BL/PI/BE station contributors: PASS")

    dims = [
        tse.StackDimension("a", 0.0, 0.30, 1.0, "normal", "pmi"),
        tse.StackDimension("b", 0.0, 0.10, -1.0, "normal", "pmi"),
    ]
    base = tse.msm_stack(dims, lsl=-0.2, usl=0.2)
    tight = ctm.msm_what_if(dims, {"a": 0.10}, lsl=-0.2, usl=0.2)
    assert tight["Cpk"] > base["Cpk"]
    print(f"V6 MSM what-if without MC (Cpk {base['Cpk']:.3f} -> {tight['Cpk']:.3f}): PASS")

    # report builder path must not inject generic frames
    pump_frames = ctm.frames_from_manifest(pump, job_id="PROSTATIC_MINIATURE_PUMP_DEMO_09")
    assert all(f["name"] not in FORBIDDEN for f in pump_frames)
    src = (ROOT / "scripts" / "cetol_app_report_builder.py").read_text(encoding="utf-8")
    assert "import cetol_modeler" in src
    assert "loop.add_frame(\"BasePlate\"" not in src
    assert "loop.add_frame(\"Bracket\"" not in src
    print("V7 report builder uses cetol_modeler (no hardcoded 4-frame): PASS")

    gdt = m_brk["gdt"]
    assert any(x["type"] == "position" for x in gdt)
    assert any(x["type"] == "flatness" for x in gdt)
    print("V8 GD&T FCF labels from PMI/features: PASS")

    topo_src = (ROOT / "data" / "workspace" / "apps" / "dxf2step" / "step_pmi_extract.py").read_text(encoding="utf-8")
    assert "def extract_step_topology" in topo_src
    bracket = ROOT / "data" / "workspace" / "apps" / "cetol6sigma" / "models" / "C_bracket.STEP"
    if bracket.is_file():
        import step_pmi_extract as spe
        topo = spe.extract_step_topology(bracket)
        assert topo["hole_count"] >= 1, topo
        assert any(h.get("xyz_mm") for h in topo["holes"]), topo["holes"][:2]
        print(f"V9 STEP topology XYZ on C_bracket ({topo['hole_count']} holes): PASS")
    else:
        print("V9 SKIP no C_bracket.STEP")

    seq = m_pump.get("assembly_sequence") or []
    assert seq and seq[0].get("seq") == 1, seq
    assert any(s.get("kind") == "planar_contact" for s in seq), seq
    mids = {m["id"] for m in m_pump["measures"]}
    assert "gap_z" in mids and "pitch_x" in mids
    print(f"V10 assembly sequence ({len(seq)}) + measures {sorted(mids)}: PASS")

    px_max = max((float((row or {}).get("pitch_x") or 0) for row in (m_pump.get("cross_table") or {}).values()), default=0)
    assert px_max > 0.1, px_max
    coup = (m_pump.get("measure_coupling") or {}).get("pitch_x") or {}
    assert coup.get("status") == "coupled", coup
    print(f"V11 Analyzer pitch_x column coupled (max {px_max:.3f}): PASS")

    mmc_man = _pump_manifest()
    mmc_man["features"]["holes"][0]["material_condition"] = "MMC"
    mmc_man["features"]["holes"][0]["diameter_tol_mm"] = 0.10
    mmc_man["features"]["holes"][0]["pin_diameter_mm"] = 2.0
    mmc_man["features"]["holes"][0]["pin_tol_mm"] = 0.04
    mmc_man["features"]["holes"][0]["pin_material_condition"] = "MMC"
    m_mmc = ctm.build_cetol_model(mmc_man, job_id=mmc_man["job_id"])
    recs = [f.get("mmc_bonus") for f in m_mmc["frames"] if f.get("mmc_bonus")]
    assert recs and recs[0]["status"] == "APPLIED", recs
    assert recs[0]["bonus_mm"] > 0.05, recs[0]
    assert m_mmc["tim"]["mmc_applied_count"] >= 1
    flags_mmc = {f["code"] for f in m_mmc["advisor"]}
    assert "mmc_lmc_absent" not in flags_mmc
    print(f"V12 MMC bonus APPLIED ({recs[0]['bonus_mm']:.3f} mm) + TIM: PASS")

    no_bonus = ctm.mmc_lmc_bonus(material_condition=None, position_tol_mm=0.05, hole_diameter_mm=6.0)
    assert no_bonus["status"] == "INSUFFICIENT"
    print("V13 MMC INSUFFICIENT without modifier: PASS")

    assert m_pump["tim"]["schema"] == "clawstack.cetol_tim.v1"
    assert "not Creo" in (m_pump["tim"].get("note") or "").lower() or "Not Creo" in (m_pump["tim"].get("note") or "")
    assert m_pump["msm_sota"]["commercial_cetol_equivalent"] is False
    assert m_pump["msm"].get("yield_rate_gld") is not None or (m_pump["msm"].get("gld") or {}).get("status")
    sota = (m_pump["msm_sota"].get("loop_sota") or {})
    assert sota.get("cross_derivatives") is True
    assert int(sota.get("cross_pairs") or 0) >= 1
    print("V14 TIM + MSM/SOTA+GLD + cross-partials present (UNVALIDATED vs CETOL): PASS")

    gld_n = tse.msm_stack(
        [tse.StackDimension("a", 0.0, 0.30, 1.0, "normal"),
         tse.StackDimension("b", 0.0, 0.10, 1.0, "normal")],
        lsl=-0.2, usl=0.2,
    )
    assert gld_n.get("yield_rate_gld") is not None
    assert abs(gld_n["yield_rate_gld"] - gld_n["yield_rate"]) < 0.05, gld_n
    print(f"V15 GLD vs Gram-Charlier near-normal ({gld_n['yield_rate_gld']:.4f} vs {gld_n['yield_rate']:.4f}): PASS")

    man_j = _pump_manifest()
    strip_before = next(f for f in ctm.frames_from_manifest(man_j, job_id=man_j["job_id"]) if str(f["name"]).endswith("_Strip"))
    m_j = ctm.build_cetol_model(man_j, job_id=man_j["job_id"])
    strip = next(f for f in m_j["frames"] if str(f["name"]).endswith("_Strip"))
    assert float(strip["t_tol"][2]) <= 0.003, strip["t_tol"]
    assert float(strip["t_tol"][2]) < float(strip_before["t_tol"][2]), (strip["t_tol"], strip_before["t_tol"])
    assert float(strip["t_tol"][0]) > 0.005, strip["t_tol"]
    assert strip.get("joint_driven") is True
    print(f"V16 joint-driven Strip Tz locked ({strip['t_tol'][2]} mm residual): PASS")

    loop_x = tse.VectorLoop3D()
    loop_x.add_frame("A", (0.0, 0.0, 0.0), (8.0, 0.0, 0.0), (0.10, 0.10, 0.10), (0.5, 0.5, 0.5))
    loop_x.add_frame("B", (10.0, 0.0, 2.0), (0.0, 6.0, 0.0), (0.08, 0.08, 0.08), (0.4, 0.4, 0.4))
    sota_x = loop_x.solve((0.0, 0.0, 1.0), second_order=True, cross_top_n=6)["sota"]
    assert sota_x["cross_derivatives"] is True
    assert int(sota_x["cross_pairs"]) >= 1
    print(f"V17 VectorLoop3D cross-partials ({sota_x['cross_pairs']} pairs): PASS")

    hm = tse.sota_truncated_higher_moments(
        a=[1.0], sig=[0.1], bii=[2.0], bij_pairs=[], var_y=0.01,
    )
    assert abs(hm["skewness"] - 0.6) < 1e-9, hm  # 3*a^2*bii*s^4 / sY^3 = 3*1*2*1e-4 / 0.001 = 0.6
    assert "skewness" in (m_pump["msm_sota"]["loop_sota"] or {})
    assert (m_pump["msm_sota"]["loop_sota"] or {}).get("yield_rate_gld") is not None
    print(f"V18 loop MSM 4-moments + GLD yield ({m_pump['msm_sota']['loop_sota'].get('yield_rate_gld')}): PASS")

    man_over = _pump_manifest()
    man_over["freecad_assembly_joints"] = [
        {"kind": "planar_contact", "from": "DieBase", "to": "Strip",
         "constrained_dof": ["Tz", "Rx", "Ry"], "id": "j1"},
        {"kind": "planar_contact", "from": "DieBase", "to": "Strip",
         "constrained_dof": ["Tz", "Rx", "Ry"], "id": "j2"},
    ]
    m_over = ctm.build_cetol_model(man_over, job_id=man_over["job_id"])
    assert (m_over.get("constraint_state") or {}).get("status") == "OVERCONSTRAINED", m_over.get("constraint_state")
    assert any(a.get("code") == "overconstrained_joint" for a in m_over["advisor"])
    print("V19 overconstrained TIM analog: PASS")

    assert abs(ctm.pin_hole_clearance_mm(6.2, 5.7) - 0.25) < 1e-9
    man_clr = _pump_manifest()
    man_clr["features"]["holes"][0]["pin_diameter_mm"] = 2.0
    man_clr["features"]["holes"][0]["diameter_mm"] = 2.2
    feats = ctm.build_features(man_clr, ctm.part_slug(man_clr), 28.0, 28.0, 8.5)
    js = ctm.build_joints(man_clr, ctm.part_slug(man_clr), feats)
    pins = [j for j in js if j.get("kind") == "pin_hole_float"]
    assert pins and abs(float(pins[0]["clearance_mm"]) - 0.1) < 1e-9, pins
    print("V20 pin-hole radial clearance from diameters: PASS")

    kin = ctm.kinematic_loop_golden()
    assert kin["verdict"] == "PASS", kin
    assert kin["cetol_3d_equivalent"] is False
    print(f"V21 kinematic loop golden (max_err {kin['max_err_pct']}% -- not CETOL 3D): PASS")

    cl = m_pump.get("closed_loop") or {}
    assert cl.get("applied") is True, cl
    assert str(cl.get("method") or "").startswith("joint_local"), cl
    gz = (m_pump.get("vector_loop_measures") or {}).get("measures") or {}
    gz = gz.get("gap_z") or m_pump.get("vector_loop_3d") or {}
    strip_tz = next((n for n in (gz.get("sensitivity") or {}) if n.endswith("_Strip_Tz")), None)
    if strip_tz:
        assert float((gz["sensitivity"][strip_tz] or {}).get("contribution") or 0) <= 0.02, gz["sensitivity"][strip_tz]
    ang = ((m_pump.get("vector_loop_measures") or {}).get("measures") or {}).get("angular_rz") or {}
    assert (ang.get("sota") or {}).get("second_order") is True, ang.get("sota")
    assert ang.get("unit") == "deg"
    assert (ang.get("closed_loop") or {}).get("applied") is True, ang.get("closed_loop")
    print("V22 joint-local DLM + angular CTQ reduced: PASS")

    js_tim = (ROOT / "data" / "workspace" / "apps" / "cetol6sigma" / "cetol_model.js").read_text(encoding="utf-8")
    assert "constraint=" in js_tim and "DLM=" in js_tim
    assert "jointY=" in js_tim
    print("V23 web TIM shows constraint + DLM + joint yield: PASS")

    cap = m_pump.get("capability_beyond_cetol") or {}
    assert cap.get("commercial_claim") is False
    assert cap.get("joint_local_dlm") is True
    assert cap.get("relative_feature_measures") is True
    assert cap.get("cad_addin") == "skipped_by_user"
    jy = m_pump.get("joint_ctq_yield") or {}
    assert jy.get("applied") is True, jy
    tails = ((m_pump.get("msm_sota") or {}).get("loop_sota") or {}).get("tails") or {}
    assert "gld_fmkl" in tails and "cornish_fisher" in tails, tails
    assert any(isinstance(f.get("geometric_form"), dict) for f in m_pump["frames"])
    print("V24 beyond-CETOL methods (joint yield, 3 tails, form, no CAD add-in): PASS")

    cannot = m_pump.get("cetol_cannot") or {}
    assert cannot.get("cetol_can_implement") is False
    assert cannot.get("commercial_cetol_equivalent") is False
    assert cannot.get("truth_gate") == "UNVALIDATED"
    die = cannot.get("progressive_die") or {}
    assert die.get("sequence") == ["BL", "PI", "BE", "FEED"]
    assert die.get("cetol_can_implement") is False
    assert float(die.get("rss_process_mm") or 0) > 0
    assert die.get("springback_status") == "INSUFFICIENT"
    print(f"V25 progressive-die transfer CETOL cannot implement (RSS {die.get('rss_process_mm')} mm): PASS")

    comp = cannot.get("compliant") or {}
    assert comp.get("cetol_can_implement") is False
    assert float(comp.get("sigma_mm") or 0) > 0
    print(f"V26 compliant-sheet influence CETOL cannot implement (sigma {comp.get('sigma_mm')} mm): PASS")

    mf0 = cpp.moldflow_shrink_contributor(pump, lx_mm=28.0)
    assert mf0.get("status") == "INSUFFICIENT"
    assert (cannot.get("moldflow") or {}).get("status") == "INSUFFICIENT"
    man_used = _pump_manifest()
    man_used["physics_handoff"]["moldflow"] = {"shrink_mm": 0.04}
    mf_used = cpp.moldflow_shrink_contributor(man_used, lx_mm=28.0)
    assert mf_used.get("status") == "USED"
    assert abs(float(mf_used.get("shrink_mm")) - 0.04) < 1e-9
    man_proxy = _pump_manifest()
    man_proxy["physics_handoff"]["moldflow"] = {"melt_temp_c": 240.0}
    mf_proxy = cpp.moldflow_shrink_contributor(man_proxy, lx_mm=28.0)
    assert mf_proxy.get("status") == "THEORY_PROXY"
    print("V27 moldflow shrink USED / THEORY_PROXY / INSUFFICIENT (fail-closed): PASS")

    js_cannot = (ROOT / "data" / "workspace" / "apps" / "cetol6sigma" / "cetol_model.js").read_text(encoding="utf-8")
    html_cannot = (ROOT / "data" / "workspace" / "apps" / "cetol6sigma" / "index.html").read_text(encoding="utf-8")
    assert "function renderCetolCannot" in js_cannot
    assert "商用 CETOL 6σ は剛体ジョイントのみ" in js_cannot
    assert "商用 CETOL が実装できない工程物理" in html_cannot
    assert "cetolCannotBox" in html_cannot
    assert "20260829j" in html_cannot
    print("V28 web cetol-cannot section + renderCetolCannot: PASS")

    assert (m_pump.get("capability_beyond_cetol") or {}).get("process_physics_cetol_cannot") is True
    assert any(a.get("code") == "moldflow_shrink_absent" for a in m_pump["advisor"])
    print("V29 capability flag + moldflow_shrink_absent advisor: PASS")

    print("ALL_CETOL_MODELER_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
