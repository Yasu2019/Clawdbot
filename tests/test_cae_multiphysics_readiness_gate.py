import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("cae_multiphysics_readiness_gate", ROOT / "scripts/cae_multiphysics_readiness_gate.py")
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def write_field(path: Path, value: str = "1") -> None:
    path.write_text(
        "dimensions [0 0 0 0 0 0 0];\n"
        "internalField nonuniform List<scalar> 1(\n"
        f"{value}\n"
        ");\n",
        encoding="utf-8",
    )


def make_case(tmp_path: Path) -> Path:
    case = tmp_path / "case"
    (case / "system").mkdir(parents=True)
    (case / "constant/polyMesh").mkdir(parents=True)
    (case / "constant").mkdir(exist_ok=True)
    (case / "0").mkdir()
    (case / "system/controlDict").write_text(
        "runTimeModifiable true;\nadjustTimeStep yes;\nmaxCo 0.01;\nmaxAlphaCo 0.003;\nmaxDeltaT 1e-7;\n",
        encoding="utf-8",
    )
    (case / "system/fvSolution").write_text("solvers {}\n", encoding="utf-8")
    (case / "system/fvSchemes").write_text("divSchemes {}\n", encoding="utf-8")
    (case / "constant/polyMesh/boundary").write_text("gate { nFaces 1; }\nvent { nFaces 1; }\nwall { nFaces 1; }\n", encoding="utf-8")
    (case / "constant/transportProperties").write_text("polymer { nu [0 2 -1 0 0 0 0] 1e-6; }\n", encoding="utf-8")
    (case / "constant/thermophysicalProperties.polymer").write_text("equationOfState rPolynomial;\n", encoding="utf-8")
    for name in ("T", "alpha.polymer"):
        write_field(case / "0" / name, "1")
    (case / "0/U").write_text("internalField nonuniform List<vector> 1((0 0 0));\n", encoding="utf-8")
    t = case / "0.1"
    t.mkdir()
    for name in ("T", "p", "alpha", "rho"):
        write_field(t / name, "1")
    (t / "U").write_text("internalField nonuniform List<vector> 1((0 0 0));\n", encoding="utf-8")
    return case


def test_readiness_gate_reports_all_eight_stages(tmp_path):
    case = make_case(tmp_path)
    report = M.build_report(
        type(
            "Args",
            (),
            {
                "case": case,
                "openfoam_manifest": None,
                "cross_plan": None,
                "calibration": None,
                "monitor_report": None,
                "coupling_package": None,
                "video_manifest": None,
                "boundary_config": None,
            },
        )()
    )

    assert report["schema"] == "clawstack.cae.multiphysics.readiness.v1"
    assert len(report["stages"]) == 8
    assert report["stages"]["openfoam_case_generation_hardened"]["status"] == "PASS"
    assert report["stages"]["tait_pvt_density_viscosity_unit_verified"]["status"] == "PASS"
    assert "bounded_cross_wlf_reconnection_ready" in report["next_actions"]


def test_readiness_gate_accepts_ready_contract_inputs(tmp_path):
    case = make_case(tmp_path)
    cross_plan = tmp_path / "cross.json"
    cross_plan.write_text(
        json.dumps(
            {
                "status": "DESIGN_CARD_READY_CUSTOM_LIBRARY_REQUIRED",
                "guards": {"nu_min": 1e-9, "nu_max": 1.0, "shear_rate_min": 1e-6, "shear_rate_max": 1e6},
            }
        ),
        encoding="utf-8",
    )
    coupling = tmp_path / "coupling.json"
    coupling.write_text(
        json.dumps(
            {
                "calculix_package": {"status": "PACKAGED_NOT_SOLVED", "transfer_mode": "same_mesh_identity"},
                "elmer_package": {"status": "INPUT_READY_NOT_SOLVED"},
            }
        ),
        encoding="utf-8",
    )
    video = tmp_path / "video.json"
    video.write_text(
        json.dumps(
            {
                "videos": {
                    k: {
                        "path": f"{k}.mp4",
                        "moving_frames_verified": True,
                        "frame_delta_fraction": 0.1,
                        "interpretation_label": f"How to read {k}",
                    }
                    for k in ("resin_fill", "warpage", "shrinkage", "sink", "void", "airtrap", "weldline")
                },
                "visual_qc": {"moving_frames_verified": True, "contour_interpretation_labels": True},
            }
        ),
        encoding="utf-8",
    )
    boundary = tmp_path / "boundary.json"
    boundary.write_text(
        json.dumps(
            {
                "schema": "clawstack.arbitrary.boundary.groups.v1",
                "status": "PASS",
                "model": {"sha256": "model-digest"},
                "spec": {"sha256": "spec-digest"},
                "surface_topology": {
                    "checks": {
                        "watertight": True,
                        "manifold": True,
                        "orientation_consistent": True,
                        "nonzero_enclosed_volume": True,
                    }
                },
                "groups": {"gate_main": [1], "vent_main": [2], "outer_wall": [3, 4]},
                "roles": {"gate": ["gate_main"], "vent": ["vent_main"], "hole": [], "wall": ["outer_wall"]},
                "openfoam_artifacts": {
                    "status": "PASS",
                    "patches": {
                        "gate_main": {"surface_file": "gate_main.stl"},
                        "vent_main": {"surface_file": "vent_main.stl"},
                        "outer_wall": {"surface_file": "outer_wall.stl"},
                    },
                },
            }
        ),
        encoding="utf-8",
    )

    report = M.build_report(
        type(
            "Args",
            (),
            {
                "case": case,
                "openfoam_manifest": None,
                "cross_plan": cross_plan,
                "calibration": None,
                "monitor_report": None,
                "coupling_package": coupling,
                "video_manifest": video,
                "boundary_config": boundary,
            },
        )()
    )

    assert report["stages"]["bounded_cross_wlf_reconnection_ready"]["status"] == "READY_TO_RECONNECT"
    assert report["stages"]["openfoam_to_calculix_elmer_conservative_transfer"]["status"] == "TRANSFER_INPUT_READY"
    assert report["stages"]["calculix_elmer_wait_and_smoke_inputs"]["status"] == "DOWNSTREAM_INPUT_READY"
    assert report["stages"]["video_visual_qa_report_pipeline"]["status"] == "VIDEO_QA_READY"
    assert report["stages"]["arbitrary_3d_boundary_generalization"]["status"] == "BOUNDARY_CONTRACT_READY"


def test_boundary_gate_rejects_declarative_patch_names_without_geometry_evidence():
    result = M.check_boundary_generalization({
        "selection_mode": "mesh_groups",
        "roles": {
            "gate": {"face_groups": ["gateA"]},
            "vent": {"face_groups": ["ventA"]},
            "wall": {"face_groups": ["wall"]},
        },
    })
    assert result["status"] == "HOLD"
    assert "not geometry evidence" in result["note"]


def test_video_gate_rejects_global_flags_when_individual_video_is_static():
    videos = {
        k: {
            "path": f"{k}.mp4",
            "moving_frames_verified": True,
            "frame_delta_fraction": 0.1,
            "interpretation_label": f"How to read {k}",
        }
        for k in ("resin_fill", "warpage", "shrinkage", "sink", "void", "airtrap", "weldline")
    }
    videos["sink"]["frame_delta_fraction"] = 0.0
    result = M.check_video_pipeline({
        "videos": videos,
        "visual_qc": {"moving_frames_verified": True, "contour_interpretation_labels": True},
    })

    assert result["status"] == "HOLD"
    assert result["per_video_motion"]["sink"] is False


def test_downstream_gate_accepts_solved_packages():
    result = M.check_downstream_solvers(
        {
            "calculix_package": {"status": "SOLVED", "frd": "job.frd", "dat": "job.dat"},
            "elmer_package": {"status": "SOLVED", "result": "case.result"},
        }
    )

    assert result["status"] == "DOWNSTREAM_INPUT_READY"
    assert all(result["checks"].values())


def test_resume_gate_exports_dashboard_progress(tmp_path):
    case = make_case(tmp_path)
    result = M.check_resume_and_checkpoint(case, {
        "status": "RUNNING",
        "running_process_detected": True,
        "latest_complete_checkpoint": "parallel:0.1",
        "progress": {
            "last_time_s": 0.11,
            "target_time_s": 1.3,
            "last_alpha_mean": 0.2,
            "last_delta_t_s": 1e-7,
            "last_courant_max": 0.01,
            "last_interface_courant_max": 0.002,
            "estimated_remaining_wall_seconds": 8 * 86400,
            "active_error_markers": [],
        },
    })
    assert result["status"] == "CHECKPOINT_READY"
    assert result["progress"]["time_s"] == 0.11
    assert result["progress"]["alpha_mean"] == 0.2
    assert result["runtime_classification"] == "RUNNING_IMPRACTICAL_ETA"


def test_resume_gate_accepts_restart_grace_with_checkpoint(tmp_path):
    case = make_case(tmp_path)
    result = M.check_resume_and_checkpoint(case, {
        "status": "RESTART_GRACE",
        "running_process_detected": False,
        "latest_complete_checkpoint": "parallel:0.1",
        "progress": {"active_error_markers": []},
    })
    assert result["status"] == "CHECKPOINT_READY"
