import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import run_openfoam_production_history as M


def _scalar(values):
    body = "\n".join(str(v) for v in values)
    return f"internalField nonuniform List<scalar>\n{len(values)}\n(\n{body}\n)\n;\n"


def _vector(values):
    body = "\n".join(f"({x} {y} {z})" for x, y, z in values)
    return f"internalField nonuniform List<vector>\n{len(values)}\n(\n{body}\n)\n;\n"


def _write_snapshot(case: Path, time_name: str, alpha_values) -> None:
    time_dir = case / time_name
    time_dir.mkdir(parents=True)
    (time_dir / "T").write_text(_scalar([500, 501]), encoding="utf-8")
    (time_dir / "p").write_text(_scalar([101325, 101326]), encoding="utf-8")
    (time_dir / "alpha").write_text(_scalar(alpha_values), encoding="utf-8")
    (time_dir / "rho").write_text(_scalar([900, 901]), encoding="utf-8")
    (time_dir / "U").write_text(_vector([(0, 0, 0), (1, 0, 0)]), encoding="utf-8")


def _write_mesh(case: Path) -> None:
    mesh = case / "constant" / "polyMesh"
    mesh.mkdir(parents=True)
    for name in ("points", "faces", "owner", "neighbour", "boundary"):
        (mesh / name).write_text(f"synthetic test {name}\n", encoding="ascii")


def test_existing_history_manifest_passes(tmp_path):
    case = tmp_path / "case"
    _write_snapshot(case, "0.05", [0.995, 1.0])
    _write_snapshot(case, "0.1", [1.0, 1.0])
    _write_mesh(case)
    solver_log = tmp_path / "log.compressibleVoF"
    solver_log.write_text("Time = 0.1\nExecutionTime = 1 s\nEnd\n", encoding="utf-8")
    audit = tmp_path / "balance.json"
    audit.write_text(json.dumps({
        "source": "postprocess_integral",
        "mass_balance_relative_error": 1e-5,
        "energy_balance_relative_error": 2e-5,
    }), encoding="utf-8")

    class Args:
        output = tmp_path / "out"
        execute = False
        command = None
        timeout = 1
        solver = "testSolver"
        mass_balance_error = 0.0
        mass_balance_tolerance = 1e-3
        energy_balance_error = 0.0
        energy_balance_tolerance = 1e-3
        final_alpha_mean_min = 0.99
        filled_cell_alpha_min = 0.99
        filled_cell_fraction_min = 0.99
        min_end_time_s = 0.1
        min_time_count = 2
        copy_history = False

    Args.case = case
    Args.solver_log = solver_log
    Args.audit_json = audit
    report = M.run(Args)

    assert report["status"] == "COMPLETED"
    assert report["run_gate"]["status"] == "PASS"
    assert report["alpha_mean_final"] == 1.0
    assert report["filled_cell_fraction_final"] == 1.0
    assert report["solver_execution_evidence"]["completed"] is True
    assert report["balance_audit"]["source"] == "postprocess_integral"
    assert report["mesh_fingerprint_sha256"]


def test_existing_history_manifest_holds_when_too_short(tmp_path):
    case = tmp_path / "case"
    t = case / "0.001"
    t.mkdir(parents=True)
    (t / "T").write_text(_scalar([500, 501]), encoding="utf-8")
    (t / "p").write_text(_scalar([101325, 101326]), encoding="utf-8")
    (t / "alpha").write_text(_scalar([1.0, 1.0]), encoding="utf-8")
    (t / "rho").write_text(_scalar([900, 901]), encoding="utf-8")
    (t / "U").write_text(_vector([(0, 0, 0), (1, 0, 0)]), encoding="utf-8")

    class Args:
        output = tmp_path / "out"
        execute = False
        command = None
        timeout = 1
        solver = "testSolver"
        solver_log = None
        audit_json = None
        mass_balance_error = 0.0
        mass_balance_tolerance = 1e-3
        energy_balance_error = 0.0
        energy_balance_tolerance = 1e-3
        final_alpha_mean_min = 0.99
        filled_cell_alpha_min = 0.99
        filled_cell_fraction_min = 0.99
        min_end_time_s = 1.0
        min_time_count = 2
        copy_history = False

    Args.case = case
    report = M.run(Args)

    assert report["status"] == "HOLD"
    assert report["run_gate"]["checks"]["minimum_end_time_s"] is False
    assert report["run_gate"]["checks"]["minimum_time_count"] is False


def test_existing_full_history_without_execution_and_balance_evidence_holds(tmp_path):
    case = tmp_path / "case"
    _write_snapshot(case, "0.05", [1.0, 1.0])
    _write_snapshot(case, "0.1", [1.0, 1.0])
    _write_mesh(case)

    class Args:
        output = tmp_path / "out"
        execute = False
        command = None
        timeout = 1
        solver = "testSolver"
        solver_log = None
        audit_json = None
        mass_balance_error = 0.0
        mass_balance_tolerance = 1e-3
        energy_balance_error = 0.0
        energy_balance_tolerance = 1e-3
        final_alpha_mean_min = 0.99
        filled_cell_alpha_min = 0.99
        filled_cell_fraction_min = 0.99
        min_end_time_s = 0.1
        min_time_count = 2
        copy_history = False

    Args.case = case
    report = M.run(Args)

    assert report["status"] == "HOLD"
    assert report["solver_execution_evidence"]["completed"] is False
    assert report["balance_audit"]["source"] == "declared_cli_unverified"
