"""Run the seven-track CAE regression gate and emit an auditable JSON report."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TRACKS = {
    "openfoam_physics": [
        "tests/test_cross_wlf_reference.py",
        "tests/test_cross_wlf_openfoam2512_reference.py",
        "tests/test_molding_physics_models.py",
    ],
    "resume_and_failure": [
        "tests/test_summarize_openfoam_log_progress.py",
        "tests/test_vivobook_openfoam_remote_monitor.py",
        "tests/test_vivobook_openfoam_autoresume_install.py",
    ],
    "conservative_transfer": [
        "tests/test_openfoam_ccx_history.py",
        "tests/test_coarse_voxel_exact_transfer.py",
        "tests/test_export_elmer_history_case.py",
    ],
    "six_defects": [
        "tests/test_airtrap_connectivity.py",
        "tests/test_void_bubble_dynamics.py",
        "tests/test_validate_void_full_coupling_gate.py",
    ],
    "arbitrary_3d": ["tests/test_arbitrary_model_boundaries.py"],
    "verification": [
        "tests/test_compare_packing_resolution.py",
        "tests/test_ccx_pressure_orientation_benchmark.py",
    ],
    "visual_qa": [
        "tests/test_render_coupled_cae_youtube_package.py",
        "tests/test_box_roundhole_acceptance_gate.py",
    ],
}


def run_track(name: str, tests: list[str], basetemp: Path) -> dict:
    missing = [test for test in tests if not (ROOT / test).is_file()]
    if missing:
        return {"status": "MISSING_TESTS", "tests": tests, "missing": missing, "returncode": 2}
    basetemp.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", *tests, "-q", "--basetemp", str(basetemp / name)]
    proc = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {
        "status": "PASS" if proc.returncode == 0 else "FAIL",
        "tests": tests,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-3000:],
        "stderr_tail": proc.stderr[-1500:],
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts" / "box_roundhole_v5" / "cae_7track_acceptance.json")
    parser.add_argument("--track", action="append", choices=tuple(TRACKS))
    args = parser.parse_args()
    selected = args.track or list(TRACKS)
    basetemp = ROOT / ".pytest_tmp_cae_7track_runner"
    results = {name: run_track(name, TRACKS[name], basetemp) for name in selected}
    passed = sum(item["status"] == "PASS" for item in results.values())
    report = {
        "schema": "clawstack.cae.seven_track_acceptance.v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": "PASS" if passed == len(results) else "FAIL",
        "passed_tracks": passed,
        "total_tracks": len(results),
        "tracks": results,
        "interpretation": "A PASS proves regression-gate behavior, not measured-material validation or production accuracy.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
