import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
from types import SimpleNamespace

from scripts.run_elmer_solver_and_verify import run_elmer


def test_run_elmer_records_hold_when_solver_missing(tmp_path, monkeypatch):
    case = tmp_path / "case"
    case.mkdir()
    (case / "case.sif").write_text("Header\nEnd\n", encoding="ascii")
    monkeypatch.setattr("shutil.which", lambda name: None)

    report = run_elmer(case, tmp_path / "out")

    assert report["status"] == "HOLD_SOLVER_NOT_FOUND"
    assert report["files_present"]["result"] is False
    assert (tmp_path / "out" / "elmer_solver_verification.json").is_file()


def test_run_elmer_accepts_changed_nested_result_with_completion_marker(tmp_path, monkeypatch):
    case = tmp_path / "case"
    mesh = case / "mesh"
    mesh.mkdir(parents=True)
    (case / "case.sif").write_text("Header\nEnd\n", encoding="ascii")

    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/ElmerSolver")

    def fake_run(command, **kwargs):
        (mesh / "case.result").write_text("result\n", encoding="ascii")
        (mesh / "case0001.vtu").write_text("vtu\n", encoding="ascii")
        return SimpleNamespace(
            returncode=0,
            stdout="ELMER SOLVER (v) Version: 9.0\nElmer Solver finished at 12:00\n",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    report = run_elmer(case, tmp_path / "out")

    assert report["status"] == "SOLVER_PASS_UNVALIDATED"
    assert report["result_relative_path"] == "mesh/case.result"
    assert report["files_present"]["vtu"] is True
    assert report["solver_version"] == "9.0"


def test_stale_result_does_not_make_failed_run_pass(tmp_path, monkeypatch):
    case = tmp_path / "case"
    case.mkdir()
    (case / "case.sif").write_text("Header\nEnd\n", encoding="ascii")
    (case / "case.result").write_text("old result\n", encoding="ascii")
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/ElmerSolver")
    monkeypatch.setattr(
        "subprocess.run",
        lambda *args, **kwargs: SimpleNamespace(returncode=1, stdout="ERROR:: failed\n"),
    )

    report = run_elmer(case, tmp_path / "out")

    assert report["status"] == "HOLD"
    assert report["files_present"]["result"] is False
    assert report["stale_artifacts_ignored"] == ["case.result"]


def test_docker_adapter_is_used_when_host_solver_is_missing(tmp_path, monkeypatch):
    case = tmp_path / "case"
    case.mkdir()
    (case / "case.sif").write_text("Header\nEnd\n", encoding="ascii")

    def which(name):
        return "C:/docker.exe" if name == "docker" else None

    monkeypatch.setattr("shutil.which", which)

    def fake_run(command, **kwargs):
        (case / "case.result").write_text("result\n", encoding="ascii")
        return SimpleNamespace(
            returncode=0,
            stdout="Version: 8.4\nElmer Solver finished at 12:00\n",
        )

    monkeypatch.setattr("subprocess.run", fake_run)
    report = run_elmer(
        case,
        tmp_path / "out",
        docker_image="eperera/elmerfem:latest",
    )

    assert report["status"] == "SOLVER_PASS_UNVALIDATED"
    assert report["execution_mode"] == "docker"
    assert "--entrypoint" in report["command"]
