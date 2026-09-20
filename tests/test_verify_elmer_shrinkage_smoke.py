from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from scripts.verify_elmer_shrinkage_smoke import (
    CLASSIFICATION,
    DEFAULT_IMAGE,
    build_case,
    parse_ascii_vtu,
    run_smoke,
    verify_affine_contraction,
)


def _write_ascii_vtu(
    path: Path,
    strain: float,
    side: float = 0.01,
    *,
    deformed_points: bool = False,
    include_temperature: bool = False,
) -> None:
    points = [(0.0, 0.0, 0.0), (side, 0.0, 0.0), (0.0, side, 0.0), (0.0, 0.0, side)]
    displacement = [tuple(strain * value for value in point) for point in points]
    output_points = (
        [tuple(points[node][axis] + displacement[node][axis] for axis in range(3)) for node in range(4)]
        if deformed_points
        else points
    )
    point_text = " ".join(str(value) for point in output_points for value in point)
    displacement_text = " ".join(str(value) for vector in displacement for value in vector)
    temperature_array = (
        '<DataArray type="Float64" Name="temperature" NumberOfComponents="1" format="ascii">'
        '283.15 283.15 283.15 283.15</DataArray>'
        if include_temperature
        else ""
    )
    path.write_text(
        f"""<?xml version="1.0"?>
<VTKFile type="UnstructuredGrid" version="0.1" byte_order="LittleEndian">
  <UnstructuredGrid><Piece NumberOfPoints="4" NumberOfCells="1">
    <PointData>{temperature_array}<DataArray type="Float64" Name="Displacement" NumberOfComponents="3" format="ascii">{displacement_text}</DataArray></PointData>
    <Points><DataArray type="Float64" NumberOfComponents="3" format="ascii">{point_text}</DataArray></Points>
  </Piece></UnstructuredGrid>
</VTKFile>
""",
        encoding="ascii",
    )


def test_build_case_writes_native_tetra_mesh_and_thermal_shrinkage_sif(tmp_path):
    case = tmp_path / "elmer_case"
    manifest = build_case(case)

    assert manifest["status"] == "INPUT_READY_NOT_SOLVED"
    assert manifest["result_classification"] == CLASSIFICATION
    assert manifest["thermal_load"]["expected_isotropic_strain"] == pytest.approx(-1.0e-3)
    assert (case / "mesh" / "mesh.header").read_text(encoding="ascii").splitlines() == [
        "4 1 4", "2", "303 4", "504 1"
    ]
    assert (case / "mesh" / "mesh.elements").read_text(encoding="ascii") == "1 1 504 1 2 3 4\n"
    boundary = (case / "mesh" / "mesh.boundary").read_text(encoding="ascii")
    assert "1 1 1 0 303 1 3 4" in boundary
    assert "4 4 1 0 303 2 3 4" in boundary
    sif = (case / "case.sif").read_text(encoding="ascii")
    assert 'Procedure = "StressSolve" "StressSolver"' in sif
    assert "Heat Expansion Coefficient = 1.000000000000e-04" in sif
    assert "Reference Temperature = 2.931500000000e+02" in sif
    assert "Temperature = 2.831500000000e+02" in sif
    assert "Binary Output = Logical False" in sif
    assert set(manifest["files"]) == {
        "case.sif", "mesh/mesh.header", "mesh/mesh.nodes", "mesh/mesh.elements", "mesh/mesh.boundary"
    }


def test_build_case_rejects_noncontracting_temperature_load(tmp_path):
    with pytest.raises(ValueError, match="requires solve_temperature_k < reference_temperature_k"):
        build_case(tmp_path / "invalid_case", reference_temperature_k=293.15, solve_temperature_k=293.15)


def test_parse_and_verify_exact_ascii_vtu(tmp_path):
    vtu = tmp_path / "exact.vtu"
    _write_ascii_vtu(vtu, strain=-1.0e-3, include_temperature=True)

    parsed = parse_ascii_vtu(vtu)
    check = verify_affine_contraction(
        parsed["points_m"], parsed["displacement_m"], side_length_m=0.01, expected_strain=-1.0e-3
    )

    assert check["pass"] is True
    assert check["contraction_direction_pass"] is True
    assert check["relative_l2_error"] == pytest.approx(0.0)
    assert check["axial_displacements_m"] == pytest.approx([-1.0e-5] * 3)
    assert check["axial_analytical_ratios"] == pytest.approx([1.0] * 3)
    assert check["mean_axial_analytical_ratio"] == pytest.approx(1.0)
    assert parsed["scalar_fields"]["temperature"] == pytest.approx([283.15] * 4)


def test_verify_accepts_elmer_deformed_vtu_coordinates(tmp_path):
    vtu = tmp_path / "deformed.vtu"
    _write_ascii_vtu(vtu, strain=-1.0e-3, deformed_points=True)
    parsed = parse_ascii_vtu(vtu)

    check = verify_affine_contraction(
        parsed["points_m"], parsed["displacement_m"], side_length_m=0.01, expected_strain=-1.0e-3
    )

    assert check["pass"] is True
    assert check["vtu_coordinate_semantics"] == "deformed"


def test_verify_rejects_wrong_sign_even_if_magnitude_matches(tmp_path):
    vtu = tmp_path / "expansion.vtu"
    _write_ascii_vtu(vtu, strain=1.0e-3)
    parsed = parse_ascii_vtu(vtu)

    check = verify_affine_contraction(
        parsed["points_m"], parsed["displacement_m"], side_length_m=0.01, expected_strain=-1.0e-3
    )

    assert check["pass"] is False
    assert check["contraction_direction_pass"] is False
    assert check["relative_l2_error"] == pytest.approx(2.0)


def test_run_smoke_records_explicit_hold_when_docker_is_missing(tmp_path, monkeypatch):
    monkeypatch.setattr("scripts.verify_elmer_shrinkage_smoke.shutil.which", lambda _name: None)
    case = tmp_path / "hold_case"

    report = run_smoke(case)

    assert report["status"] == "HOLD_DOCKER_NOT_FOUND"
    assert report["result_classification"] == CLASSIFICATION
    assert report["checks"]["solver_completed"] is False
    stored = json.loads((case / "elmer_shrinkage_smoke_manifest.json").read_text(encoding="utf-8"))
    assert stored["status"] == "HOLD_DOCKER_NOT_FOUND"


def _local_elmer_image_available() -> bool:
    docker = shutil.which("docker")
    if not docker:
        return False
    try:
        probe = subprocess.run(
            [docker, "image", "inspect", DEFAULT_IMAGE, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=15.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False
    return probe.returncode == 0 and bool(probe.stdout.strip())


@pytest.mark.skipif(not _local_elmer_image_available(), reason="local Elmer Docker image is unavailable")
def test_real_elmer_docker_shrinkage_smoke(tmp_path):
    report = run_smoke(tmp_path / "live_case", timeout_s=120.0)

    assert report["status"] == "NUMERICALLY_COMPLETE_UNCALIBRATED", json.dumps(report, indent=2)
    assert report["returncode"] == 0
    assert report["checks"]["solver_completed"] is True
    assert report["checks"]["thermal_load_applied"] is True
    assert report["checks"]["analytical_match"] is True
    assert report["solver_version"] == "8.4"
    assert report["artifacts"]["result"]["path"] == "mesh/case.result"
    assert report["artifacts"]["vtu"]["path"] == "mesh/shrinkage0001.vtu"
    assert report["analytical_verification"]["mean_axial_analytical_ratio"] == pytest.approx(1.0)
    assert report["analytical_verification"]["relative_l2_error"] <= 1.0e-5
