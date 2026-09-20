import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import run_openfoam_production_history as M


def _scalar(values):
    body = "\n".join(str(v) for v in values)
    return f"internalField nonuniform List<scalar>\n{len(values)}\n(\n{body}\n)\n;\n"


def _vector(values):
    body = "\n".join(f"({x} {y} {z})" for x, y, z in values)
    return f"internalField nonuniform List<vector>\n{len(values)}\n(\n{body}\n)\n;\n"


def test_existing_history_manifest_passes(tmp_path):
    case = tmp_path / "case"
    t = case / "0.1"
    t.mkdir(parents=True)
    (t / "T").write_text(_scalar([500, 501]), encoding="utf-8")
    (t / "p").write_text(_scalar([101325, 101326]), encoding="utf-8")
    (t / "alpha").write_text(_scalar([0.0, 1.0]), encoding="utf-8")
    (t / "rho").write_text(_scalar([900, 901]), encoding="utf-8")
    (t / "U").write_text(_vector([(0, 0, 0), (1, 0, 0)]), encoding="utf-8")

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
        final_alpha_mean_min = 0.5
        min_end_time_s = 0.1
        min_time_count = 1
        copy_history = False

    Args.case = case
    report = M.run(Args)

    assert report["status"] == "COMPLETED"
    assert report["run_gate"]["status"] == "PASS"
    assert report["alpha_mean_final"] == 0.5


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
        mass_balance_error = 0.0
        mass_balance_tolerance = 1e-3
        energy_balance_error = 0.0
        energy_balance_tolerance = 1e-3
        final_alpha_mean_min = 0.99
        min_end_time_s = 1.0
        min_time_count = 2
        copy_history = False

    Args.case = case
    report = M.run(Args)

    assert report["status"] == "HOLD"
    assert report["run_gate"]["checks"]["minimum_end_time_s"] is False
    assert report["run_gate"]["checks"]["minimum_time_count"] is False
