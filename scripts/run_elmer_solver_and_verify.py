"""Run ElmerSolver for a prepared Elmer case and verify result evidence.

If ElmerSolver is not installed, the script records a HOLD report instead of
pretending that the independent comparison was solved.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _artifact_state(case_dir: Path) -> dict[str, tuple[int, int]]:
    """Snapshot possible results without deleting pre-existing user evidence."""

    state: dict[str, tuple[int, int]] = {}
    for pattern in ("case.result", "*.vtu"):
        for path in case_dir.rglob(pattern):
            if path.is_file():
                stat = path.stat()
                state[path.relative_to(case_dir).as_posix()] = (
                    int(stat.st_size),
                    int(stat.st_mtime_ns),
                )
    return state


def _changed_artifacts(
    case_dir: Path,
    before: dict[str, tuple[int, int]],
    pattern: str,
) -> list[Path]:
    changed: list[Path] = []
    for path in case_dir.rglob(pattern):
        if not path.is_file() or path.stat().st_size <= 0:
            continue
        stat = path.stat()
        relative = path.relative_to(case_dir).as_posix()
        current = (int(stat.st_size), int(stat.st_mtime_ns))
        if before.get(relative) != current:
            changed.append(path)
    return sorted(changed, key=lambda item: item.stat().st_mtime_ns)


def _write_report(output: Path, report: dict[str, Any]) -> dict[str, Any]:
    (output / "elmer_solver_verification.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return report


def run_elmer(
    case_dir: Path,
    output: Path,
    *,
    solver: str = "ElmerSolver",
    timeout_s: float = 1200.0,
    docker_image: str | None = None,
    docker_executable: str = "docker",
) -> dict:
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    sif = case_dir / "case.sif"
    if not sif.exists():
        raise FileNotFoundError(sif)
    solver_path = shutil.which(solver)
    docker_path = shutil.which(docker_executable) if docker_image else None
    execution_mode = "host" if solver_path else ("docker" if docker_path else "unavailable")
    report = {
        "schema": "clawstack.elmer.execution.verify.v1",
        "case_dir": str(case_dir.resolve()),
        "solver": solver,
        "solver_path": solver_path,
        "execution_mode": execution_mode,
        "docker_image": docker_image,
        "sif": str(sif.resolve()),
        "sif_sha256": sha256(sif),
    }
    if solver_path is None and docker_path is None:
        report.update(
            status="HOLD_SOLVER_NOT_FOUND",
            returncode=None,
            finished=False,
            files_present={"result": False, "log": False},
            limitations=["ElmerSolver executable is not available on PATH; independent Elmer comparison has not been solved."],
        )
        return _write_report(output, report)

    before = _artifact_state(case_dir)
    if solver_path:
        command = [solver_path, sif.name]
    else:
        command = [
            str(docker_path),
            "run",
            "--rm",
            "--entrypoint",
            solver,
            "-v",
            f"{case_dir.resolve()}:/case",
            "-w",
            "/case",
            str(docker_image),
            sif.name,
        ]
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            cwd=case_dir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout_s,
        )
        returncode = completed.returncode
        solver_output = completed.stdout or ""
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = None
        solver_output = (
            exc.stdout.decode(errors="replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or "")
        )
    log = output / "ElmerSolver.log"
    log.write_text(solver_output, encoding="utf-8", errors="replace")
    changed_results = _changed_artifacts(case_dir, before, "case.result")
    changed_vtus = _changed_artifacts(case_dir, before, "*.vtu")
    result = changed_results[-1] if changed_results else None
    upper_log = solver_output.upper()
    completion_marker = "ELMER SOLVER FINISHED AT" in upper_log
    fatal_markers = [marker for marker in ("ERROR::", "FATAL") if marker in upper_log]
    clean_execution = bool(
        not timed_out
        and returncode == 0
        and completion_marker
        and not fatal_markers
        and result is not None
    )
    version_match = re.search(r"Version:\s*([^\s(]+)", solver_output, re.IGNORECASE)
    report.update(
        status="SOLVER_PASS_UNVALIDATED" if clean_execution else ("HOLD_TIMEOUT" if timed_out else "HOLD"),
        returncode=returncode,
        finished=clean_execution,
        timed_out=timed_out,
        elapsed_s=time.monotonic() - started,
        solver_version=version_match.group(1) if version_match else None,
        command=command,
        completion_marker=completion_marker,
        fatal_markers=fatal_markers,
        files_present={
            "result": result is not None,
            "log": log.is_file() and log.stat().st_size > 0,
            "vtu": bool(changed_vtus),
        },
        log=str(log.resolve()),
        log_sha256=sha256(log),
        result=str(result.resolve()) if result else None,
        result_sha256=sha256(result) if result else None,
        result_relative_path=result.relative_to(case_dir).as_posix() if result else None,
        vtu=[
            {
                "path": path.relative_to(case_dir).as_posix(),
                "sha256": sha256(path),
                "bytes": path.stat().st_size,
            }
            for path in changed_vtus
        ],
        stale_artifacts_ignored=sorted(before),
        limitations=[
            "Execution evidence only; field-level comparison with CalculiX still requires matching Elmer mesh/material mapping.",
            "Only artifacts created or changed by this invocation are accepted; pre-existing results are preserved but ignored.",
        ],
    )
    return _write_report(output, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--solver", default="ElmerSolver")
    parser.add_argument("--timeout-s", type=float, default=1200.0)
    parser.add_argument("--docker-image")
    parser.add_argument("--docker-executable", default="docker")
    report = run_elmer(**vars(parser.parse_args()))
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "SOLVER_PASS_UNVALIDATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
