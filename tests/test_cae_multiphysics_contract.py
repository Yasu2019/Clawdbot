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


def test_history_reads_numeric_times_in_order(tmp_path):
    case = make_case(tmp_path)
    result = M.read_openfoam_history(case)
    assert result["schema"] == "clawstack.openfoam.history.v1"
    assert result["time_s"] == [0.0, 0.5]
    assert result["cell_count"] == 2
    assert "0.5/T" in result["source_sha256"]


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


def test_calculix_history_package_requires_matching_conservative_histories(tmp_path):
    case = make_case(tmp_path)
    history = M.read_openfoam_history(case)
    temperature = M.conservative_transfer_history(history, "T", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    pressure = M.conservative_transfer_history(history, "p", [2.0, 1.0], np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    package = M.build_calculix_history_package(
        temperature=temperature,
        pressure=pressure,
        reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "eigenstrain_only"},
        constraints={"hold": ["gate"], "release_time_s": 0.5},
    )
    assert package["schema"] == "clawstack.calculix.history.package.v1"
    assert package["status"] == "INPUT_READY"
    assert package["checks"]["shrinkage_double_counting_guard"] == "eigenstrain_only"


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
            reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "eigenstrain_only"},
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
        reference_state={"stress_free_temperature_K": 350.0, "shrinkage_counting": "eigenstrain_only"},
    )


def test_openfoam_run_manifest_gate_requires_real_completion():
    result = M.validate_openfoam_run_manifest({
        "status": "COMPLETED",
        "nonisothermal": True,
        "compressible": True,
        "venting": True,
        "fields": ["T", "p", "alpha", "U", "rho"],
        "alpha_min": 0.0,
        "alpha_max": 1.0,
        "mass_balance_relative_error": 1e-5,
        "energy_balance_relative_error": 1e-5,
    })
    assert result["status"] == "PASS"
    hold = M.validate_openfoam_run_manifest({"status": "COMPLETED", "fields": ["alpha"]})
    assert hold["status"] == "HOLD"
    assert hold["checks"]["nonisothermal"] is False


def test_write_calculix_history_deck_outputs_includes(tmp_path):
    package = complete_package(tmp_path)
    manifest = M.write_calculix_history_deck(tmp_path / "ccx", package, [10, 20])
    assert manifest["status"] == "WRITTEN_NOT_SOLVED"
    assert (tmp_path / "ccx" / "temperature_0000.inc").read_text().startswith("** OpenFOAM")
    assert "10, 1.268500000000e+02" in (tmp_path / "ccx" / "temperature_0000.inc").read_text()
    assert "20,9.000000000000e+04" in (tmp_path / "ccx" / "pressure_0000.csv").read_text()
    with pytest.raises(FileExistsError):
        M.write_calculix_history_deck(tmp_path / "ccx", package, [10, 20])


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
