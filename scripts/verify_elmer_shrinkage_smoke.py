"""Run an independently solved Elmer thermo-shrinkage verification specimen.

The specimen is one first-order tetrahedron.  Its three coordinate-plane faces
are constrained only in their normal directions, so the exact stress-free
solution for a uniform temperature change is ``u = alpha * delta_T * x``.
This is a numerical wiring check with virtual material data, not a material
calibration or a product-level warpage validation.
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
import math
import re
import shutil
import subprocess
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Sequence


SCHEMA = "clawstack.elmer.shrinkage.smoke.v1"
CLASSIFICATION = "UNCALIBRATED_SCREENING"
DEFAULT_IMAGE = "eperera/elmerfem:latest"
SIDE_LENGTH_M = 0.01
REFERENCE_TEMPERATURE_K = 293.15
SOLVE_TEMPERATURE_K = 283.15
THERMAL_EXPANSION_PER_K = 1.0e-4
YOUNGS_MODULUS_PA = 3.0e9
POISSON_RATIO = 0.35


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_native_mesh(mesh_dir: Path, side_length_m: float) -> list[Path]:
    mesh_dir.mkdir(parents=True)
    paths = [
        mesh_dir / "mesh.header",
        mesh_dir / "mesh.nodes",
        mesh_dir / "mesh.elements",
        mesh_dir / "mesh.boundary",
    ]
    paths[0].write_text("4 1 4\n2\n303 4\n504 1\n", encoding="ascii")
    paths[1].write_text(
        "1 -1 0.0 0.0 0.0\n"
        f"2 -1 {side_length_m:.12e} 0.0 0.0\n"
        f"3 -1 0.0 {side_length_m:.12e} 0.0\n"
        f"4 -1 0.0 0.0 {side_length_m:.12e}\n",
        encoding="ascii",
    )
    paths[2].write_text("1 1 504 1 2 3 4\n", encoding="ascii")
    paths[3].write_text(
        "1 1 1 0 303 1 3 4\n"  # x=0: constrain displacement component 1
        "2 2 1 0 303 1 2 4\n"  # y=0: constrain displacement component 2
        "3 3 1 0 303 1 2 3\n"  # z=0: constrain displacement component 3
        "4 4 1 0 303 2 3 4\n",  # free slanted face; temperature is prescribed
        encoding="ascii",
    )
    return paths


def _sif_text(
    *,
    reference_temperature_k: float,
    solve_temperature_k: float,
    thermal_expansion_per_k: float,
    youngs_modulus_pa: float,
    poisson_ratio: float,
) -> str:
    return f"""! Elmer independent thermo-shrinkage smoke; virtual material only
! Exact affine solution: displacement = alpha * (T-Tref) * coordinate
Header
  CHECK KEYWORDS Warn
  Mesh DB "." "mesh"
  Include Path ""
  Results Directory "."
End

Simulation
  Max Output Level = 5
  Coordinate System = "Cartesian 3D"
  Coordinate Mapping(3) = 1 2 3
  Simulation Type = "Steady State"
  Steady State Max Iterations = 1
  Output Intervals = 1
  Solver Input File = "case.sif"
  Post File = "case.result"
End

Constants
  Gravity(4) = 0 0 0 0
End

Body 1
  Name = "Shrinkage tetrahedron"
  Target Bodies(1) = 1
  Equation = 1
  Material = 1
  Initial Condition = 1
End

Equation 1
  Name = "Thermal then structural"
  Active Solvers(3) = 1 2 3
End

Solver 1
  Equation = "Heat Equation"
  Procedure = "HeatSolve" "HeatSolver"
  Variable = "Temperature"
  Variable DOFs = 1
  Linear System Solver = "Direct"
  Linear System Direct Method = "UMFPACK"
  Linear System Convergence Tolerance = 1.0e-12
  Steady State Convergence Tolerance = 1.0e-12
  Nonlinear System Max Iterations = 1
End

Solver 2
  Equation = "Stress Analysis"
  Procedure = "StressSolve" "StressSolver"
  Variable = -dofs 3 "Displacement"
  Calculate Stresses = Logical True
  Linear System Solver = "Direct"
  Linear System Direct Method = "UMFPACK"
  Linear System Convergence Tolerance = 1.0e-12
  Steady State Convergence Tolerance = 1.0e-12
End

Solver 3
  Exec Solver = "After All"
  Equation = "ResultOutput"
  Procedure = "ResultOutputSolve" "ResultOutputSolver"
  Output File Name = "shrinkage"
  Vtu Format = Logical True
  Binary Output = Logical False
  Ascii Output = Logical True
  Save Geometry Ids = Logical True
End

Material 1
  Name = "Virtual isotropic polymer"
  Density = 1000.0
  Heat Capacity = 1800.0
  Heat Conductivity = 0.20
  Youngs Modulus = {youngs_modulus_pa:.12e}
  Poisson Ratio = {poisson_ratio:.12e}
  Heat Expansion Coefficient = {thermal_expansion_per_k:.12e}
  Reference Temperature = {reference_temperature_k:.12e}
End

Initial Condition 1
  Temperature = {solve_temperature_k:.12e}
End

Boundary Condition 1
  Name = "x symmetry"
  Target Boundaries(1) = 1
  Displacement 1 = 0.0
  Temperature = {solve_temperature_k:.12e}
End

Boundary Condition 2
  Name = "y symmetry"
  Target Boundaries(1) = 2
  Displacement 2 = 0.0
  Temperature = {solve_temperature_k:.12e}
End

Boundary Condition 3
  Name = "z symmetry"
  Target Boundaries(1) = 3
  Displacement 3 = 0.0
  Temperature = {solve_temperature_k:.12e}
End

Boundary Condition 4
  Name = "free cooled face"
  Target Boundaries(1) = 4
  Temperature = {solve_temperature_k:.12e}
End
"""


def build_case(
    case_dir: Path,
    *,
    side_length_m: float = SIDE_LENGTH_M,
    reference_temperature_k: float = REFERENCE_TEMPERATURE_K,
    solve_temperature_k: float = SOLVE_TEMPERATURE_K,
    thermal_expansion_per_k: float = THERMAL_EXPANSION_PER_K,
    youngs_modulus_pa: float = YOUNGS_MODULUS_PA,
    poisson_ratio: float = POISSON_RATIO,
) -> dict:
    """Create a self-contained Elmer native-mesh verification case."""
    if case_dir.exists():
        raise FileExistsError(case_dir)
    if side_length_m <= 0.0 or thermal_expansion_per_k <= 0.0:
        raise ValueError("side length and thermal expansion must be positive")
    if solve_temperature_k <= 0.0 or reference_temperature_k <= 0.0:
        raise ValueError("temperatures must be positive Kelvin values")
    if solve_temperature_k >= reference_temperature_k:
        raise ValueError("the shrinkage smoke requires solve_temperature_k < reference_temperature_k")
    if youngs_modulus_pa <= 0.0 or not (-1.0 < poisson_ratio < 0.5):
        raise ValueError("invalid isotropic elastic constants")

    case_dir.mkdir(parents=True)
    mesh_paths = _write_native_mesh(case_dir / "mesh", side_length_m)
    sif = case_dir / "case.sif"
    sif.write_text(
        _sif_text(
            reference_temperature_k=reference_temperature_k,
            solve_temperature_k=solve_temperature_k,
            thermal_expansion_per_k=thermal_expansion_per_k,
            youngs_modulus_pa=youngs_modulus_pa,
            poisson_ratio=poisson_ratio,
        ),
        encoding="ascii",
    )
    delta_t_k = solve_temperature_k - reference_temperature_k
    expected_strain = thermal_expansion_per_k * delta_t_k
    manifest = {
        "schema": SCHEMA,
        "status": "INPUT_READY_NOT_SOLVED",
        "result_classification": CLASSIFICATION,
        "solver": "ElmerSolver",
        "geometry": {
            "kind": "single_C3D4_equivalent_tetrahedron",
            "side_length_m": side_length_m,
            "node_count": 4,
            "element_count": 1,
            "boundary_triangle_count": 4,
        },
        "material": {
            "identity": "virtual_isotropic_polymer",
            "measured": False,
            "youngs_modulus_Pa": youngs_modulus_pa,
            "poisson_ratio": poisson_ratio,
            "thermal_expansion_per_K": thermal_expansion_per_k,
        },
        "thermal_load": {
            "reference_temperature_K": reference_temperature_k,
            "solve_temperature_K": solve_temperature_k,
            "delta_temperature_K": delta_t_k,
            "expected_isotropic_strain": expected_strain,
        },
        "constraints": {
            "x_zero_face": "u_x=0",
            "y_zero_face": "u_y=0",
            "z_zero_face": "u_z=0",
            "purpose": "remove rigid modes while preserving exact free isotropic contraction",
        },
        "files": {
            str(path.relative_to(case_dir)).replace("\\", "/"): sha256(path)
            for path in [sif, *mesh_paths]
        },
        "limitations": [
            "Virtual material and temperature data; classification is UNCALIBRATED_SCREENING.",
            "One linear tetrahedron verifies solver wiring and sign/magnitude only.",
            "No OpenFOAM history mapping, product fixture, contact, pressure, or full-model convergence is proven.",
        ],
    }
    (case_dir / "input_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_ascii_data_array(element: ET.Element, *, components: int) -> list[tuple[float, ...]]:
    if element.attrib.get("format", "ascii").lower() != "ascii":
        raise ValueError("only ASCII VTU DataArray output is accepted")
    values = [float(value) for value in (element.text or "").split()]
    if len(values) == 0 or len(values) % components:
        raise ValueError(f"VTU DataArray length is not divisible by {components}")
    return [tuple(values[index:index + components]) for index in range(0, len(values), components)]


def parse_ascii_vtu(path: Path) -> dict:
    """Read coordinates and the nodal displacement vector from an ASCII VTU."""
    root = ET.parse(path).getroot()
    points_array = root.find(".//Points/DataArray")
    if points_array is None:
        raise ValueError(f"VTU has no Points DataArray: {path}")
    points = _parse_ascii_data_array(points_array, components=3)
    displacement_array = None
    scalar_fields: dict[str, list[float]] = {}
    available_names = []
    for array in root.findall(".//PointData/DataArray"):
        name = array.attrib.get("Name", "")
        available_names.append(name)
        components = int(array.attrib.get("NumberOfComponents", "1"))
        if components == 1 and name:
            scalar_fields[name] = [row[0] for row in _parse_ascii_data_array(array, components=1)]
        if name.casefold() == "displacement":
            displacement_array = array
    if displacement_array is None:
        raise ValueError(f"VTU has no nodal Displacement field; fields={available_names}")
    components = int(displacement_array.attrib.get("NumberOfComponents", "1"))
    if components != 3:
        raise ValueError(f"Displacement must have 3 components, got {components}")
    displacement = _parse_ascii_data_array(displacement_array, components=3)
    if len(points) != len(displacement):
        raise ValueError("VTU coordinate/displacement counts differ")
    return {
        "points_m": points,
        "displacement_m": displacement,
        "scalar_fields": scalar_fields,
        "fields": available_names,
    }


def verify_affine_contraction(
    points: Sequence[Sequence[float]],
    displacement: Sequence[Sequence[float]],
    *,
    side_length_m: float,
    expected_strain: float,
    relative_tolerance: float = 1.0e-5,
    absolute_tolerance_m: float = 1.0e-10,
) -> dict:
    """Compare the Elmer field with the exact affine thermal-contraction field."""
    if len(points) != 4 or len(displacement) != 4:
        raise ValueError("the verification specimen must contain exactly four nodal vectors")
    expected_points = [
        (0.0, 0.0, 0.0),
        (side_length_m, 0.0, 0.0),
        (0.0, side_length_m, 0.0),
        (0.0, 0.0, side_length_m),
    ]
    raw_points = [tuple(float(value) for value in point) for point in points]
    raw_displacement = [tuple(float(value) for value in vector) for vector in displacement]
    coordinate_candidates = {
        "original": raw_points,
        # Elmer 8.4 ResultOutputSolver may write displaced VTU coordinates.
        "deformed": [
            tuple(raw_points[node][axis] - raw_displacement[node][axis] for axis in range(3))
            for node in range(4)
        ],
    }
    coordinate_tolerance_m = max(1.0e-12, side_length_m * 1.0e-9)
    candidate_matches = []
    for semantics, candidate_points in coordinate_candidates.items():
        indices = []
        distances_for_match = []
        used: set[int] = set()
        for expected_point in expected_points:
            distances = [
                math.sqrt(sum((point[axis] - expected_point[axis]) ** 2 for axis in range(3)))
                for point in candidate_points
            ]
            index = min(range(len(distances)), key=distances.__getitem__)
            if index in used:
                distances_for_match.append(float("inf"))
            else:
                used.add(index)
                indices.append(index)
                distances_for_match.append(distances[index])
        candidate_matches.append((max(distances_for_match), semantics, indices))
    maximum_coordinate_error_m, coordinate_semantics, matched_indices = min(candidate_matches)
    if maximum_coordinate_error_m > coordinate_tolerance_m or len(matched_indices) != 4:
        raise ValueError("VTU points do not match the generated tetrahedron in original or deformed coordinates")
    actual_by_node = [raw_displacement[index] for index in matched_indices]

    expected = [tuple(expected_strain * coordinate for coordinate in point) for point in expected_points]
    error_sq = sum(
        (actual_by_node[node][axis] - expected[node][axis]) ** 2
        for node in range(4)
        for axis in range(3)
    )
    expected_sq = sum(value * value for vector in expected for value in vector)
    relative_l2 = math.sqrt(error_sq) / max(math.sqrt(expected_sq), 1.0e-300)
    maximum_absolute_error_m = max(
        abs(actual_by_node[node][axis] - expected[node][axis])
        for node in range(4)
        for axis in range(3)
    )
    axial_displacements_m = [actual_by_node[1][0], actual_by_node[2][1], actual_by_node[3][2]]
    expected_axial_displacement_m = expected_strain * side_length_m
    axial_analytical_ratios = [
        value / expected_axial_displacement_m for value in axial_displacements_m
    ]
    contraction_direction_pass = (
        expected_strain < 0.0
        and all(value < 0.0 for value in axial_displacements_m)
    )
    magnitude_pass = (
        relative_l2 <= relative_tolerance
        and maximum_absolute_error_m <= absolute_tolerance_m
    )
    return {
        "analytical_model": "u_i=alpha*(T-Tref)*x_i",
        "expected_strain": expected_strain,
        "expected_axial_displacement_m": expected_axial_displacement_m,
        "axial_displacements_m": axial_displacements_m,
        "axial_analytical_ratios": axial_analytical_ratios,
        "mean_axial_analytical_ratio": sum(axial_analytical_ratios) / len(axial_analytical_ratios),
        "relative_l2_error": relative_l2,
        "relative_tolerance": relative_tolerance,
        "maximum_absolute_error_m": maximum_absolute_error_m,
        "absolute_tolerance_m": absolute_tolerance_m,
        "vtu_coordinate_semantics": coordinate_semantics,
        "maximum_coordinate_match_error_m": maximum_coordinate_error_m,
        "contraction_direction_pass": contraction_direction_pass,
        "magnitude_pass": magnitude_pass,
        "pass": contraction_direction_pass and magnitude_pass,
    }


def _write_final_manifest(case_dir: Path, report: dict) -> dict:
    manifest_path = case_dir / "elmer_shrinkage_smoke_manifest.json"
    manifest_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def _availability_hold(case_dir: Path, *, status: str, reason: str, image: str) -> dict:
    return _write_final_manifest(
        case_dir,
        {
            "schema": SCHEMA,
            "status": status,
            "result_classification": CLASSIFICATION,
            "solver": "ElmerSolver",
            "container_image": image,
            "returncode": None,
            "checks": {"docker_available": False, "solver_completed": False, "analytical_match": False},
            "limitations": [reason, "No independent Elmer solve result is claimed."],
        },
    )


def run_smoke(
    case_dir: Path,
    *,
    image: str = DEFAULT_IMAGE,
    timeout_s: float = 120.0,
    docker_executable: str | None = None,
) -> dict:
    """Build, execute, and verify the specimen in an ephemeral Docker container."""
    input_manifest = build_case(case_dir)
    docker = docker_executable or shutil.which("docker")
    if not docker:
        return _availability_hold(
            case_dir,
            status="HOLD_DOCKER_NOT_FOUND",
            reason="Docker executable is unavailable; ElmerSolver was not executed.",
            image=image,
        )
    try:
        docker_info = subprocess.run(
            [docker, "info", "--format", "{{.ServerVersion}}"],
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 20.0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _availability_hold(
            case_dir,
            status="HOLD_DOCKER_UNAVAILABLE",
            reason=f"Docker daemon probe failed: {type(exc).__name__}: {exc}",
            image=image,
        )
    if docker_info.returncode != 0:
        return _availability_hold(
            case_dir,
            status="HOLD_DOCKER_UNAVAILABLE",
            reason="Docker daemon probe returned nonzero; ElmerSolver was not executed.",
            image=image,
        )
    try:
        image_probe = subprocess.run(
            [docker, "image", "inspect", image, "--format", "{{.Id}}"],
            capture_output=True,
            text=True,
            timeout=min(timeout_s, 20.0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return _availability_hold(
            case_dir,
            status="HOLD_IMAGE_PROBE_FAILED",
            reason=f"Elmer image probe failed: {type(exc).__name__}: {exc}",
            image=image,
        )
    if image_probe.returncode != 0 or not image_probe.stdout.strip():
        return _availability_hold(
            case_dir,
            status="HOLD_IMAGE_NOT_FOUND",
            reason=f"Required local Docker image is missing: {image}",
            image=image,
        )

    command = [
        docker,
        "run",
        "--rm",
        "--entrypoint",
        "ElmerSolver",
        "-v",
        f"{case_dir.resolve()}:/case",
        "-w",
        "/case",
        image,
        "case.sif",
    ]
    started = time.monotonic()
    timed_out = False
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        returncode = completed.returncode
        output = (completed.stdout or "") + (completed.stderr or "")
    except subprocess.TimeoutExpired as exc:
        timed_out = True
        returncode = None
        stdout = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
        stderr = exc.stderr.decode(errors="replace") if isinstance(exc.stderr, bytes) else (exc.stderr or "")
        output = stdout + stderr
    elapsed_s = time.monotonic() - started
    log = case_dir / "ElmerSolver.log"
    log.write_text(output, encoding="utf-8", errors="replace")

    vtu_candidates = sorted(case_dir.rglob("*.vtu"))
    parsed = None
    selected_vtu = None
    parse_errors = []
    for candidate in vtu_candidates:
        try:
            parsed = parse_ascii_vtu(candidate)
            selected_vtu = candidate
            break
        except (ET.ParseError, OSError, ValueError) as exc:
            parse_errors.append(f"{candidate.name}: {exc}")
    analytical = None
    temperature_values_k = None
    thermal_load_match = False
    if parsed is not None:
        analytical = verify_affine_contraction(
            parsed["points_m"],
            parsed["displacement_m"],
            side_length_m=float(input_manifest["geometry"]["side_length_m"]),
            expected_strain=float(input_manifest["thermal_load"]["expected_isotropic_strain"]),
        )
        temperature_values_k = next(
            (values for name, values in parsed["scalar_fields"].items() if name.casefold() == "temperature"),
            None,
        )
        solve_temperature_k = float(input_manifest["thermal_load"]["solve_temperature_K"])
        thermal_load_match = bool(
            temperature_values_k
            and len(temperature_values_k) == 4
            and max(abs(value - solve_temperature_k) for value in temperature_values_k) <= 1.0e-8
        )
    upper_log = output.upper()
    completion_marker = "ELMER SOLVER FINISHED AT" in upper_log
    fatal_markers = [marker for marker in ("ERROR::", "FATAL") if marker in upper_log]
    result_candidates = sorted(case_dir.rglob("case.result"))
    result_file = result_candidates[0] if len(result_candidates) == 1 else None
    execution_pass = (
        not timed_out
        and returncode == 0
        and completion_marker
        and not fatal_markers
        and selected_vtu is not None
        and result_file is not None
        and result_file.is_file()
    )
    numerical_pass = bool(analytical and analytical["pass"] and thermal_load_match)
    if timed_out:
        status = "HOLD_SOLVER_TIMEOUT"
    elif not execution_pass:
        status = "HOLD_SOLVER_OR_OUTPUT_FAILED"
    elif not numerical_pass:
        status = "FAILED_NUMERICS"
    else:
        status = "NUMERICALLY_COMPLETE_UNCALIBRATED"
    artifacts = {
        "input_manifest": {
            "path": "input_manifest.json",
            "sha256": sha256(case_dir / "input_manifest.json"),
        },
        "solver_log": {"path": log.name, "sha256": sha256(log)},
        "result": (
            {"path": result_file.relative_to(case_dir).as_posix(), "sha256": sha256(result_file)}
            if result_file is not None and result_file.is_file()
            else None
        ),
        "vtu": (
            {"path": selected_vtu.relative_to(case_dir).as_posix(), "sha256": sha256(selected_vtu)}
            if selected_vtu is not None
            else None
        ),
    }
    report = {
        "schema": SCHEMA,
        "status": status,
        "result_classification": CLASSIFICATION,
        "engineering_claim": "NONE",
        "solver": "ElmerSolver",
        "solver_version": (
            re.search(r"Version:\s*([^\s(]+)", output).group(1)
            if re.search(r"Version:\s*([^\s(]+)", output)
            else None
        ),
        "container_image": image,
        "container_image_id": image_probe.stdout.strip(),
        "docker_server_version": docker_info.stdout.strip(),
        "returncode": returncode,
        "elapsed_s": elapsed_s,
        "checks": {
            "docker_available": True,
            "solver_completed": execution_pass,
            "completion_marker": completion_marker,
            "no_fatal_markers": not fatal_markers,
            "result_file_present": bool(result_file and result_file.is_file()),
            "ascii_vtu_with_displacement_present": selected_vtu is not None,
            "thermal_load_applied": thermal_load_match,
            "analytical_match": numerical_pass,
        },
        "observed_temperature_K": temperature_values_k,
        "analytical_verification": analytical,
        "artifacts": artifacts,
        "parse_errors": parse_errors,
        "fatal_markers": fatal_markers,
        "limitations": input_manifest["limitations"] + [
            "This proves an independent Elmer linear thermoelastic smoke path only.",
            "The specimen does not validate arbitrary-model OpenFOAM-to-Elmer field transfer.",
        ],
    }
    return _write_final_manifest(case_dir, report)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True, help="new directory for the generated case and evidence")
    parser.add_argument("--image", default=DEFAULT_IMAGE)
    parser.add_argument("--timeout-s", type=float, default=120.0)
    args = parser.parse_args()
    report = run_smoke(args.output, image=args.image, timeout_s=args.timeout_s)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "NUMERICALLY_COMPLETE_UNCALIBRATED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
