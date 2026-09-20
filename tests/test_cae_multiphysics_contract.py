import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location("cae_multiphysics_contract", ROOT / "scripts/cae_multiphysics_contract.py")
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def field(path, dimensions, body):
    path.write_text(f"dimensions [{dimensions}];\ninternalField nonuniform List<{'vector' if dimensions == '0 1 0 0 0 0 0' else 'scalar'}> 2(\n{body}\n);\n", encoding="utf-8")


def make_snapshot(tmp_path):
    tmp_path = tmp_path / "0.5"
    tmp_path.mkdir()
    field(tmp_path / "T", "0 0 0 1 0 0 0", "400\n410")
    field(tmp_path / "p", "1 -1 -1 0 0 0 0", "100000\n90000")
    field(tmp_path / "alpha", "0 0 0 0 0 0 0", "0.2\n1")
    field(tmp_path / "rho", "1 -3 0 0 0 0 0", "900\n910")
    (tmp_path / "U").write_text("internalField nonuniform List<vector> 2((1 0 0) (0 1 0));\n", encoding="utf-8")
    return tmp_path


def make_case(tmp_path):
    case = tmp_path / "case"
    case.mkdir()
    for time in ("0", "0.5"):
        snap = make_snapshot(case)
        snap.rename(case / time)
    return case


def test_snapshot_reads_all_five_fields(tmp_path):
    snap_dir = make_snapshot(tmp_path)
    result = M.read_openfoam_snapshot(snap_dir)
    assert result["cell_count"] == 2 and set(result["fields"]) == {"T", "p", "alpha", "U", "rho"}


def test_snapshot_normalizes_alpha_polymer_and_records_actual_source(tmp_path):
    snap_dir = make_snapshot(tmp_path)
    (snap_dir / "alpha").rename(snap_dir / "alpha.polymer")
    result = M.read_openfoam_snapshot(snap_dir)
    assert np.allclose(result["fields"]["alpha"], [0.2, 1.0])
    assert result["source_fields"]["alpha"] == "alpha.polymer"
    assert "alpha.polymer" in result["source_sha256"]
    assert "alpha" not in result["source_sha256"]


def test_snapshot_prefers_alpha_when_both_aliases_exist(tmp_path):
    snap_dir = make_snapshot(tmp_path)
    field(snap_dir / "alpha.polymer", "0 0 0 0 0 0 0", "0.9\n0.9")
    result = M.read_openfoam_snapshot(snap_dir)
    assert np.allclose(result["fields"]["alpha"], [0.2, 1.0])
    assert result["source_fields"]["alpha"] == "alpha"


def test_history_reads_numeric_times_in_order(tmp_path):
    case = make_case(tmp_path)
    result = M.read_openfoam_history(case)
    assert result["schema"] == "clawstack.openfoam.history.v1"
    assert result["time_s"] == [0.0, 0.5]
    assert result["cell_count"] == 2
    assert "0.5/T" in result["source_sha256"]


def test_history_accepts_alpha_polymer_and_preserves_source_name(tmp_path):
    case = make_case(tmp_path)
    for time_name in ("0", "0.5"):
        (case / time_name / "alpha").rename(case / time_name / "alpha.polymer")
    result = M.read_openfoam_history(case)
    assert result["fields"] == ["T", "p", "alpha", "U", "rho"]
    assert result["source_fields"]["0.5/alpha"] == "alpha.polymer"
    assert "0.5/alpha.polymer" in result["source_sha256"]


def test_history_rejects_incomplete_time_directory(tmp_path):
    case = make_case(tmp_path)
    (case / "0.5" / "rho").unlink()
    with pytest.raises(FileNotFoundError, match="incomplete"):
        M.read_openfoam_history(case)


def test_snapshot_rejects_out_of_bounds_alpha(tmp_path):
    snap_dir = make_snapshot(tmp_path)
    (snap_dir / "alpha").write_text("internalField uniform 1.2;\n", encoding="utf-8")
    with pytest.raises(ValueError, match="alpha"):
        M.read_openfoam_snapshot(snap_dir)


def test_conservative_transfer_preserves_integral():
    mapped, audit = M.conservative_transfer([1.0, 3.0], [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    assert np.isclose(audit["source_integral"], audit["target_integral"])
    assert audit["relative_error"] < 1e-14
    assert mapped.shape == (2,)


def test_conservative_transfer_rejects_bad_overlap():
    with pytest.raises(ValueError):
        M.conservative_transfer([1.0], [1.0], np.asarray([[0.0]]))


def test_conservative_transfer_history_preserves_each_time(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    package = M.conservative_transfer_history(history, "T", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    assert package["schema"] == "clawstack.conservative.transfer.history.v1"
    assert package["time_s"] == [0.0, 0.5]
    assert package["conservative"] is True
    assert len(package["frames"]) == 2
    assert max(frame["audit"]["relative_error"] for frame in package["frames"]) < 1e-14


def test_sparse_conservative_transfer_matches_dense_integral():
    mapped, audit = M.conservative_transfer_sparse(
        [1.0, 3.0],
        [2.0, 1.0],
        target_indices=[0, 1],
        source_indices=[0, 1],
        overlap_volumes=[2.0, 1.0],
        target_count=2,
    )
    assert np.isclose(audit["source_integral"], audit["target_integral"])
    assert audit["method"] == "sparse_overlap_volume_corrected"
    assert mapped.shape == (2,)


def test_sparse_conservative_transfer_history(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    package = M.conservative_transfer_sparse_history(
        history, "T", [2.0, 1.0], [0, 1], [0, 1], [2.0, 1.0], target_count=2
    )
    assert package["mapping"] == "sparse_overlap_volume_corrected"
    assert package["conservative"] is True
    assert package["target_count"] == 2


def test_direct_same_mesh_history_preserves_values_without_dense_weights(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    package = M.direct_same_mesh_history(history, "T")
    assert package["schema"] == "clawstack.conservative.transfer.history.v1"
    assert package["mapping"] == "same_mesh_identity"
    assert package["target_count"] == 2
    assert package["conservative"] is True
    assert package["frames"][0]["audit"]["relative_error"] == 0.0
    assert np.allclose(package["frames"][1]["values"], [400.0, 410.0])


def eigenstrain_history(history):
    result = M.direct_same_mesh_history(history, "alpha")
    result["field"] = "eigenstrain"
    for index, frame in enumerate(result["frames"], start=1):
        frame["values"] = np.asarray([-1e-3 * index, -2e-3 * index])
    return result


def eigen_reference_state():
    return {
        "stress_free_temperature_K": 350.0,
        "shrinkage_counting": "eigenstrain_only",
        "eigenstrain_frame_semantics": "total_from_stress_free",
        "strain_measure": "green_lagrange",
        "reference_configuration": "stress_free_geometry",
        "eigenstrain_value_kind": "isotropic_normal_component",
    }


def test_calculix_history_package_requires_matching_conservative_histories(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.conservative_transfer_history(history, "T", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    pressure = M.conservative_transfer_history(history, "p", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    eigenstrain = eigenstrain_history(history)
    package = M.build_calculix_history_package(
        temperature=temperature,
        pressure=pressure,
        eigenstrain=eigenstrain,
        reference_state=eigen_reference_state(),
        constraints={"hold": ["gate"], "release_time_s": 0.5},
    )
    assert package["schema"] == "clawstack.calculix.history.package.v1"
    assert package["status"] == "INPUT_READY"
    assert package["checks"]["shrinkage_double_counting_guard"] == "eigenstrain_only"


def test_calculix_history_package_requires_eigenstrain_for_eigenstrain_only(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.direct_same_mesh_history(history, "T")
    pressure = M.direct_same_mesh_history(history, "p")
    with pytest.raises(ValueError, match="eigenstrain history is required"):
        M.build_calculix_history_package(
            temperature=temperature,
            pressure=pressure,
            reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "eigenstrain_only"},
        )


def test_calculix_history_package_rejects_eigenstrain_for_cte_only(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    with pytest.raises(ValueError, match="eigenstrain history is forbidden"):
        M.build_calculix_history_package(
            temperature=M.direct_same_mesh_history(history, "T"),
            pressure=M.direct_same_mesh_history(history, "p"),
            eigenstrain=eigenstrain_history(history),
            reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "cte_only"},
        )


@pytest.mark.parametrize("metadata_key", ["time_s", "target_count"])
def test_calculix_history_package_rejects_mismatched_eigenstrain_metadata(tmp_path, metadata_key):
    history = M.read_openfoam_history(make_case(tmp_path))
    eigenstrain = eigenstrain_history(history)
    eigenstrain[metadata_key] = [0.0] if metadata_key == "time_s" else 1
    with pytest.raises(ValueError, match="share nonempty times|share positive target_count"):
        M.build_calculix_history_package(
            temperature=M.direct_same_mesh_history(history, "T"),
            pressure=M.direct_same_mesh_history(history, "p"),
            eigenstrain=eigenstrain,
            reference_state=eigen_reference_state(),
        )


def test_calculix_history_package_rejects_time_mismatch(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.conservative_transfer_history(history, "T", [1.0, 1.0], np.eye(2))
    pressure = M.conservative_transfer_history(history, "p", [1.0, 1.0], np.eye(2))
    pressure["time_s"] = [0.0]
    with pytest.raises(ValueError, match="share nonempty times"):
        M.build_calculix_history_package(
            temperature=temperature,
            pressure=pressure,
            reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "cte_only"},
        )


def test_calculix_history_package_requires_reference_state(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.conservative_transfer_history(history, "T", [1.0, 1.0], np.eye(2))
    pressure = M.conservative_transfer_history(history, "p", [1.0, 1.0], np.eye(2))
    with pytest.raises(ValueError, match="stress_free_temperature"):
        M.build_calculix_history_package(temperature=temperature, pressure=pressure, reference_state={})


def complete_package(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.conservative_transfer_history(history, "T", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    pressure = M.conservative_transfer_history(history, "p", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    return M.build_calculix_history_package(
        temperature=temperature,
        pressure=pressure,
        eigenstrain=eigenstrain_history(history),
        reference_state=eigen_reference_state(),
    )


def complete_openfoam_manifest():
    source_sha256 = {
        f"{time_name}/{field_name}": hashlib.sha256(f"{time_name}/{field_name}".encode("ascii")).hexdigest()
        for time_name in ("0", "0.5")
        for field_name in ("T", "p", "alpha.polymer", "U", "rho")
    }
    history_fingerprint = hashlib.sha256(
        json.dumps(source_sha256, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return {
        "schema": "clawstack.openfoam.production.history.v1",
        "status": "COMPLETED",
        "solver": "compressibleVoF",
        "case_dir": "case",
        "nonisothermal": True,
        "compressible": True,
        "venting": True,
        "source_kind": "raw_openfoam_solver_history",
        "synthetic": False,
        "proxy": False,
        "fields": ["T", "p", "alpha", "U", "rho"],
        "time_s": [0.0, 0.5],
        "history_time_count": 2,
        "alpha_min": 0.99,
        "alpha_max": 1.0,
        "alpha_mean_final": 0.995,
        "final_alpha_mean_min": 0.99,
        "filled_cell_alpha_min": 0.99,
        "filled_cell_fraction_final": 1.0,
        "filled_cell_fraction_min": 0.99,
        "mass_balance_relative_error": 1e-5,
        "mass_balance_tolerance": 1e-3,
        "energy_balance_relative_error": 2e-5,
        "energy_balance_tolerance": 1e-3,
        "solver_execution_evidence": {
            "path": "log.compressibleVoF",
            "sha256": "a" * 64,
            "returncode": None,
            "end_marker": True,
            "fatal_markers": [],
            "completed": True,
        },
        "balance_audit": {
            "source": "postprocess_integral",
            "source_path": "balance.json",
            "source_sha256": "b" * 64,
            "mass_balance_relative_error": 1e-5,
            "energy_balance_relative_error": 2e-5,
        },
        "mesh_fingerprint_sha256": "c" * 64,
        "mesh_fingerprint_files": ["points", "faces", "owner", "neighbour", "boundary"],
        "history_fingerprint_sha256": history_fingerprint,
        "history_source_sha256": source_sha256,
    }


def test_openfoam_run_manifest_gate_requires_real_completion():
    result = M.validate_openfoam_run_manifest(complete_openfoam_manifest())
    assert result["status"] == "PASS"
    hold = M.validate_openfoam_run_manifest({"status": "COMPLETED", "fields": ["alpha"]})
    assert hold["status"] == "HOLD"
    assert hold["checks"]["nonisothermal"] is False


@pytest.mark.parametrize(
    ("field_name", "bad_value", "failed_check"),
    [
        ("synthetic", True, "not_synthetic"),
        ("proxy", True, "not_proxy"),
        ("time_s", [0.5], "raw_multi_time_history"),
        ("alpha_mean_final", 0.98, "full_fill_alpha_mean"),
        ("filled_cell_fraction_final", 0.98, "filled_cell_fraction"),
        ("history_fingerprint_sha256", "d" * 64, "history_fingerprint"),
        ("mesh_fingerprint_sha256", None, "mesh_fingerprint"),
    ],
)
def test_openfoam_run_manifest_gate_fails_closed_on_missing_authenticity(field_name, bad_value, failed_check):
    manifest = complete_openfoam_manifest()
    manifest[field_name] = bad_value
    result = M.validate_openfoam_run_manifest(manifest)
    assert result["status"] == "HOLD"
    assert result["checks"][failed_check] is False


def test_openfoam_run_manifest_gate_requires_solver_log_and_solver_balance_source():
    manifest = complete_openfoam_manifest()
    manifest["solver_execution_evidence"]["end_marker"] = False
    manifest["balance_audit"]["source"] = "declared_cli_unverified"
    result = M.validate_openfoam_run_manifest(manifest)
    assert result["status"] == "HOLD"
    assert result["checks"]["solver_log_completion"] is False
    assert result["checks"]["balance_audit_source"] is False


def test_write_calculix_history_deck_outputs_includes(tmp_path):
    package = complete_package(tmp_path)
    manifest = M.write_calculix_history_deck(
        tmp_path / "ccx",
        package,
        element_ids=[10, 20],
        element_integration_points={10: 1, 20: 1},
    )
    assert manifest["status"] == "WRITTEN_NOT_SOLVED"
    assert "10,4.000000000000e+02" in (tmp_path / "ccx" / "temperature_element_0000.csv").read_text()
    assert "20,9.000000000000e+04" in (tmp_path / "ccx" / "pressure_0000.csv").read_text()
    assert "20,-2.000000000000e-03" in (tmp_path / "ccx" / "eigenstrain_0000.csv").read_text()
    assert manifest["target_entity"] == "element"
    assert manifest["element_integration_points"] == {"10": 1, "20": 1}
    with pytest.raises(FileExistsError):
        M.write_calculix_history_deck(
            tmp_path / "ccx",
            package,
            element_ids=[10, 20],
            element_integration_points={10: 1, 20: 1},
        )


def test_write_calculix_history_deck_rejects_ambiguous_eigenstrain_targets(tmp_path):
    package = complete_package(tmp_path)
    with pytest.raises(ValueError, match="explicit element_ids"):
        M.write_calculix_history_deck(tmp_path / "ambiguous", package, [10, 20])
    with pytest.raises(ValueError, match="element_integration_points"):
        M.write_calculix_history_deck(tmp_path / "no_ip_map", package, element_ids=[10, 20])


def test_elmer_comparison_package_uses_same_history(tmp_path):
    package = complete_package(tmp_path)
    result = M.build_elmer_comparison_package(package)
    assert result["schema"] == "clawstack.elmer.comparison.package.v1"
    assert result["status"] == "INPUT_READY_NOT_SOLVED"
    assert result["time_s"] == [0.0, 0.5]


def test_void_feedback_contract_requires_all_mechanisms(tmp_path):
    package = complete_package(tmp_path)
    ready = M.build_void_feedback_contract(
        history_package=package,
        population_model={
            "data_status": "VIRTUAL",
            "time_s": [0.0, 0.5],
            "nucleation": {},
            "growth": {},
            "coalescence": {},
            "transport": {},
            "stress_feedback": {},
        },
        stress_history={"source": "ccx"},
    )
    assert ready["status"] == "INPUT_READY_NOT_SOLVED"
    hold = M.build_void_feedback_contract(history_package=package, population_model={"data_status": "VIRTUAL"})
    assert hold["status"] == "HOLD"
    assert hold["checks"]["nucleation"] is False


def test_convergence_report():
    result = M.convergence_report([1.0, 2.0], [1.0, 2.000001], tolerance=1e-5)
    assert result["pass"] is True


def test_calibration_requires_measured_metadata():
    result = M.validate_calibration({"pvt": {}, "cross_wlf": {}, "cte": {}, "metadata": {"measured": False}})
    assert result["status"] == "VIRTUAL_OR_INCOMPLETE"


def test_calibration_accepts_measured_complete_card():
    result = M.validate_calibration({
        "metadata": {"measured": True},
        "pvt": {"density_kg_m3": [[950.0, 900.0], [980.0, 930.0]]},
        "cross_wlf": {"n": 0.35, "tau_star_pa": 5e4, "d1_pa_s": 1e10, "d2_k": 378.15, "d3_k_pa": 0.0, "a1": 17.44, "a2_k": 51.6},
        "cte": {"solid_per_k": 8e-5, "melt_per_k": 2e-4},
    })
    assert result["status"] == "CALIBRATED_INPUT"


def test_contract_exposes_all_eight_stages(tmp_path):
    snap_dir = make_snapshot(tmp_path)
    snap = M.read_openfoam_snapshot(snap_dir)
    _, mapping = M.conservative_transfer([1.0, 1.0], [1.0, 1.0], np.eye(2))
    result = M.build_contract(snapshot=snap, mapping=mapping, calibration={"pvt": {}, "cross_wlf": {}, "cte": {}}, convergence={"pass": True})
    assert len(result["stages"]) == 8
    assert result["stages"]["same_mesh_time_T_p_alpha_U_rho"] == "PASS"
    assert result["stages"]["openfoam_to_calculix_conservative_transfer"] == "PASS"
