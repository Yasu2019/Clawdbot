import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import verify_ccx_eigenstrain_smoke as M


def test_generation_uses_continuous_builder_and_stays_hold_without_solve(tmp_path):
    output = tmp_path / "smoke"
    result = M.run(output, solve=False)

    assert result["status"] == "HOLD"
    assert result["stage"] == "GENERATED_NOT_SOLVED"
    assert result["generation"]["builder_schema"] == "clawstack.ccx.continuous.reanalysis.deck.v1"
    assert result["generation"]["builder_status"] == "WRITTEN_NOT_SOLVED"
    assert result["generation"]["step_count"] == 2

    deck = Path(result["generation"]["deck"]).read_text(encoding="utf-8")
    assert deck.count("*STEP") == 2
    assert deck.count("*NODE FILE") == 2
    assert deck.count("*EL FILE") == 2
    assert "*INCLUDE, INPUT=eigenstrain_initial.inc" in deck
    assert "1, 1, -5.000000000000e-03, -5.000000000000e-03, -5.000000000000e-03" in (
        output / "generated" / "eigenstrain_increment_0000.inc"
    ).read_text(encoding="ascii")
    assert "1, 1, -5.000000000000e-03, -5.000000000000e-03, -5.000000000000e-03" in (
        output / "generated" / "eigenstrain_increment_0001.inc"
    ).read_text(encoding="ascii")
    persisted = json.loads((output / "ccx_eigenstrain_smoke_report.json").read_text(encoding="utf-8"))
    assert persisted["hold_reason"].startswith("docker_solve_not_requested")


def test_solve_is_explicit_hold_when_docker_is_unavailable(monkeypatch, tmp_path):
    monkeypatch.setattr(
        M,
        "probe_docker",
        lambda image, pull, timeout_s: {
            "available": False,
            "image_available": False,
            "reason": "docker_daemon_unavailable",
        },
    )

    result = M.run(tmp_path / "smoke", solve=True)

    assert result["status"] == "HOLD"
    assert result["stage"] == "DOCKER_UNAVAILABLE"
    assert result["hold_reason"] == "docker_daemon_unavailable"
    assert "execution" not in result


def test_windows_mount_source_uses_absolute_forward_slash_path(tmp_path):
    source = M.docker_mount_source(tmp_path, platform_name="nt")
    assert Path(source).is_absolute()
    assert "\\" not in source
    assert "," not in source


def test_analytical_gate_checks_both_contraction_frames(tmp_path):
    dat = tmp_path / "job.dat"
    dat.write_text(
        " displacements (vx,vy,vz) for set ALLNODES and time  1.0000000E+00\n"
        " 1  0.0 0.0 0.0\n"
        " 2 -5.0125629E-05 0.0 0.0\n"
        " 3  0.0 -5.0125629E-05 0.0\n"
        " 4  0.0 0.0 -5.0125629E-05\n"
        " stresses (elem, integ.pnt.,sxx,syy,szz,sxy,sxz,syz) for set POLYMER and time 1.0\n"
        " displacements (vx,vy,vz) for set ALLNODES and time  2.0000000E+00\n"
        " 1  0.0 0.0 0.0\n"
        " 2 -1.0050506E-04 0.0 0.0\n"
        " 3  0.0 -1.0050506E-04 0.0\n"
        " 4  0.0 0.0 -1.0050506E-04\n",
        encoding="ascii",
    )

    result = M.evaluate_analytical_smoke(dat)

    assert result["status"] == "ANALYTICAL_SMOKE_PASS_UNVALIDATED"
    assert all(result["checks"].values())
    assert result["frames"][1]["edges"][0]["magnitude_ratio"] == pytest.approx(1.0)


@pytest.mark.skipif(
    os.environ.get("RUN_CCX_EIGENSTRAIN_INTEGRATION") != "1",
    reason="set RUN_CCX_EIGENSTRAIN_INTEGRATION=1 to run Docker CalculiX",
)
def test_docker_ccx_eigenstrain_integration(tmp_path):
    result = M.run(tmp_path / "docker_smoke", solve=True, timeout_s=300)
    assert result["status"] == "SOLVER_PASS_UNVALIDATED", json.dumps(result, indent=2)
    assert result["stage"] == "SOLVED_ANALYTICAL_SMOKE_PASS"
    assert result["execution"]["files_present"] == {"dat": True, "frd": True, "sta": True}
    assert all(result["analytical_comparison"]["checks"].values())
