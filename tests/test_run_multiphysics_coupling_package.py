import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import importlib.util
import json
from argparse import Namespace
from pathlib import Path

import numpy as np
import pytest


ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("run_multiphysics_coupling_package", ROOT / "scripts/run_multiphysics_coupling_package.py")
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


def field(path, dimensions, body):
    path.write_text(f"dimensions [{dimensions}];\ninternalField nonuniform List<{'vector' if dimensions == '0 1 0 0 0 0 0' else 'scalar'}> 2(\n{body}\n);\n", encoding="utf-8")


def make_case(root):
    case = root / "of_case"
    case.mkdir()
    for name in ("0", "0.5"):
        time = case / name
        time.mkdir()
        field(time / "T", "0 0 0 1 0 0 0", "400\n410")
        field(time / "p", "1 -1 -1 0 0 0 0", "100000\n90000")
        field(time / "alpha", "0 0 0 0 0 0 0", "1\n1")
        field(time / "rho", "1 -3 0 0 0 0 0", "900\n910")
        (time / "U").write_text("internalField nonuniform List<vector> 2((1 0 0) (0 1 0));\n", encoding="utf-8")
    return case


def write_json(path, payload):
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def args(tmp_path, manifest):
    case = make_case(tmp_path)
    np.save(tmp_path / "volumes.npy", np.asarray([2.0, 1.0]))
    np.save(tmp_path / "weights.npy", np.asarray([[2.0, 0.0], [0.0, 1.0]]))
    (tmp_path / "ids.txt").write_text("10\n20\n", encoding="ascii")
    (tmp_path / "job_source.inp").write_text("*HEADING\n", encoding="ascii")
    return Namespace(
        openfoam_case=case,
        openfoam_manifest=write_json(tmp_path / "manifest.json", manifest),
        source_volumes=tmp_path / "volumes.npy",
        overlap_weights=tmp_path / "weights.npy",
        overlap_coo_npz=None,
        target_ids=tmp_path / "ids.txt",
        reference_state=write_json(tmp_path / "reference.json", {"stress_free_temperature_K": 350.0, "shrinkage_counting": "cte_only"}),
        constraints=None,
        calibration=write_json(tmp_path / "calibration.json", {
            "metadata": {"measured": True},
            "pvt": {"density_kg_m3": [[950.0, 900.0], [980.0, 930.0]]},
            "cross_wlf": {"n": 0.35, "tau_star_pa": 5e4, "d1_pa_s": 1e10, "d2_k": 378.15, "d3_k_pa": 0.0, "a1": 17.44, "a2_k": 51.6},
            "cte": {"solid_per_k": 8e-5},
        }),
        void_population=write_json(tmp_path / "void.json", {
            "data_status": "VIRTUAL",
            "time_s": [0.0, 0.5],
            "nucleation": {},
            "growth": {},
            "coalescence": {},
            "transport": {},
            "stress_feedback": {},
        }),
        stress_history=write_json(tmp_path / "stress.json", {"source": "ccx"}),
        eigenstrain_field=None,
        calculix_input_deck=tmp_path / "job_source.inp",
        same_mesh_transfer=False,
        output=tmp_path / "out",
    )


def complete_manifest():
    history_sources = {
        f"{time_name}/{field_name}": hashlib.sha256(f"{time_name}/{field_name}".encode("ascii")).hexdigest()
        for time_name in ("0", "0.5")
        for field_name in ("T", "p", "alpha", "U", "rho")
    }
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
        "alpha_min": 1.0,
        "alpha_max": 1.0,
        "alpha_mean_final": 1.0,
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
            "returncode": 0,
            "end_marker": True,
            "fatal_markers": [],
            "completed": True,
        },
        "balance_audit": {
            "source": "solver_function_object",
            "source_path": "balance.json",
            "source_sha256": "b" * 64,
            "mass_balance_relative_error": 1e-5,
            "energy_balance_relative_error": 2e-5,
        },
        "mesh_fingerprint_sha256": "c" * 64,
        "mesh_fingerprint_files": ["points", "faces", "owner", "neighbour", "boundary"],
        "history_source_sha256": history_sources,
        "history_fingerprint_sha256": hashlib.sha256(
            json.dumps(history_sources, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    }


def test_package_runner_writes_downstream_contracts(tmp_path):
    result = M.run(args(tmp_path, complete_manifest()))
    assert result["status"] == "PACKAGED_NOT_SOLVED"
    assert result["openfoam_run_gate"]["status"] == "PASS"
    assert result["calibration"]["status"] == "CALIBRATED_INPUT"
    assert result["void_feedback"]["status"] == "INPUT_READY_NOT_SOLVED"
    assert result["calculix_package"]["input_deck"] == "calculix/job.inp"
    assert (tmp_path / "out" / "calculix" / "temperature_0000.inc").is_file()
    assert (tmp_path / "out" / "calculix" / "job.inp").is_file()
    assert (tmp_path / "out" / "coupling_package_manifest.json").is_file()


def test_package_runner_supports_same_mesh_transfer_without_dense_mapping(tmp_path):
    a = args(tmp_path, complete_manifest())
    a.same_mesh_transfer = True
    a.source_volumes = None
    a.overlap_weights = None
    result = M.run(a)
    assert result["status"] == "PACKAGED_NOT_SOLVED"
    assert result["calculix_package"]["transfer_mode"] == "same_mesh_identity"
    assert result["calculix_package"]["target_count"] == 2


def test_package_runner_supports_sparse_overlap_npz(tmp_path):
    a = args(tmp_path, complete_manifest())
    sparse = tmp_path / "overlap_sparse.npz"
    np.savez(
        sparse,
        target_indices=np.asarray([0, 1]),
        source_indices=np.asarray([0, 1]),
        overlap_volumes=np.asarray([2.0, 1.0]),
        source_volumes=np.asarray([2.0, 1.0]),
        target_count=np.asarray(2),
    )
    a.overlap_coo_npz = sparse
    a.source_volumes = None
    a.overlap_weights = None
    result = M.run(a)
    assert result["status"] == "PACKAGED_NOT_SOLVED"
    assert result["calculix_package"]["transfer_mode"] == "sparse_overlap"


def test_package_runner_rejects_incomplete_openfoam_manifest(tmp_path):
    bad = complete_manifest()
    bad["compressible"] = False
    with pytest.raises(ValueError, match="OpenFOAM run gate is HOLD"):
        M.run(args(tmp_path, bad))
