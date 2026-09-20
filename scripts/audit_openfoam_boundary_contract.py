"""Audit a BoundaryContract against a generated OpenFOAM ``polyMesh``.

The source surface is re-tessellated by ``snappyHexMesh``.  Consequently the
source triangle count is evidence, but it is not an acceptance criterion.
Acceptance is based on patch identity/type, valid non-overlapping face ranges,
and polygon area agreement in SI units.  The command fails closed with a
machine-readable HOLD manifest.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import gzip
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any

import numpy as np


SCHEMA = "clawstack.openfoam.boundary.audit.v1"
CONTRACT_SCHEMA = "clawstack.arbitrary.boundary.groups.v1"
ARTIFACT_SCHEMA = "clawstack.openfoam.boundary.surface_artifacts.v1"
ROLES = {"gate", "vent", "wall", "hole"}
UNIT_SCALE_TO_M = {
    "m": 1.0,
    "metre": 1.0,
    "meter": 1.0,
    "mm": 1.0e-3,
    "millimetre": 1.0e-3,
    "millimeter": 1.0e-3,
}
_TOKEN_RE = re.compile(r'"(?:\\.|[^"\\])*"|[(){};]|[^\s(){};]+')
_SHA_RE = re.compile(r"[0-9a-f]{64}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _resolve_reference(raw_path: Any, *, base_dir: Path) -> Path:
    if not isinstance(raw_path, str) or not raw_path.strip():
        raise ValueError("hashed reference path is missing")
    path = Path(raw_path)
    return path.resolve() if path.is_absolute() else (base_dir / path).resolve()


def _verify_hashed_reference(contract: dict[str, Any], key: str, *, base_dir: Path) -> dict[str, str]:
    reference = contract.get(key)
    if not isinstance(reference, dict):
        raise ValueError(f"contract {key} reference is missing")
    expected = str(reference.get("sha256", "")).lower()
    if _SHA_RE.fullmatch(expected) is None:
        raise ValueError(f"contract {key}.sha256 is invalid")
    path = _resolve_reference(reference.get("path"), base_dir=base_dir)
    if not path.is_file():
        raise ValueError(f"contract {key} file is missing: {path}")
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(
            f"contract {key} sha256 mismatch: expected {expected}, got {actual}"
        )
    return {"path": str(path), "sha256": actual}


def _openfoam_file(poly_mesh_dir: Path, name: str) -> Path:
    plain = poly_mesh_dir / name
    compressed = poly_mesh_dir / f"{name}.gz"
    if plain.is_file() and compressed.is_file():
        raise ValueError(f"ambiguous OpenFOAM file; both exist: {plain} and {compressed}")
    if plain.is_file():
        return plain
    if compressed.is_file():
        return compressed
    raise FileNotFoundError(f"OpenFOAM polyMesh file is missing: {plain}[.gz]")


def _read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="strict") as stream:
            return stream.read()
    return path.read_text(encoding="utf-8")


def _without_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", " ", text, flags=re.DOTALL)
    return re.sub(r"//[^\r\n]*", " ", text)


def _data_tokens(path: Path) -> list[str]:
    text = _without_comments(_read_text(path))
    header_match = re.search(r"\bFoamFile\b", text)
    if header_match is None:
        raise ValueError(f"OpenFOAM FoamFile header is missing: {path}")
    open_brace = text.find("{", header_match.end())
    if open_brace < 0:
        raise ValueError(f"OpenFOAM FoamFile header is malformed: {path}")
    depth = 0
    close_brace = -1
    for index in range(open_brace, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                close_brace = index
                break
    if close_brace < 0:
        raise ValueError(f"OpenFOAM FoamFile header is unterminated: {path}")
    header = text[open_brace : close_brace + 1]
    format_match = re.search(r"\bformat\s+([^;]+);", header)
    if format_match is None or format_match.group(1).strip().lower() != "ascii":
        raise ValueError(f"only ASCII OpenFOAM polyMesh files are supported: {path}")
    return _TOKEN_RE.findall(text[close_brace + 1 :])


def _unquote(token: str) -> str:
    if len(token) >= 2 and token[0] == token[-1] == '"':
        return token[1:-1]
    return token


def _consume_list_start(tokens: list[str], path: Path) -> tuple[int, int]:
    if len(tokens) < 2:
        raise ValueError(f"OpenFOAM list is truncated: {path}")
    try:
        count = int(tokens[0])
    except ValueError as exc:
        raise ValueError(f"OpenFOAM list count is invalid in {path}: {tokens[0]!r}") from exc
    if count < 0 or tokens[1] != "(":
        raise ValueError(f"OpenFOAM list start is invalid: {path}")
    return count, 2


def read_points(path: Path) -> np.ndarray:
    tokens = _data_tokens(path)
    count, cursor = _consume_list_start(tokens, path)
    points: list[list[float]] = []
    for _ in range(count):
        if cursor >= len(tokens) or tokens[cursor] != "(":
            raise ValueError(f"point tuple is missing in {path}")
        cursor += 1
        if cursor + 3 >= len(tokens):
            raise ValueError(f"point tuple is truncated in {path}")
        try:
            point = [float(tokens[cursor + offset]) for offset in range(3)]
        except ValueError as exc:
            raise ValueError(f"point coordinate is invalid in {path}") from exc
        cursor += 3
        if tokens[cursor] != ")":
            raise ValueError(f"point tuple has more or fewer than three coordinates in {path}")
        cursor += 1
        points.append(point)
    if cursor >= len(tokens) or tokens[cursor] != ")":
        raise ValueError(f"point list is unterminated in {path}")
    array = np.asarray(points, dtype=float)
    if array.shape != (count, 3) or not np.isfinite(array).all():
        raise ValueError(f"point array is invalid in {path}")
    return array


def read_faces(path: Path) -> list[list[int]]:
    tokens = _data_tokens(path)
    count, cursor = _consume_list_start(tokens, path)
    faces: list[list[int]] = []
    for _ in range(count):
        if cursor >= len(tokens):
            raise ValueError(f"face list is truncated in {path}")
        try:
            vertex_count = int(tokens[cursor])
        except ValueError as exc:
            raise ValueError(f"face vertex count is invalid in {path}") from exc
        cursor += 1
        if vertex_count < 3 or cursor >= len(tokens) or tokens[cursor] != "(":
            raise ValueError(f"face must contain at least three vertices in {path}")
        cursor += 1
        if cursor + vertex_count >= len(tokens):
            raise ValueError(f"face connectivity is truncated in {path}")
        try:
            face = [int(tokens[cursor + offset]) for offset in range(vertex_count)]
        except ValueError as exc:
            raise ValueError(f"face point index is invalid in {path}") from exc
        cursor += vertex_count
        if tokens[cursor] != ")":
            raise ValueError(f"face vertex count does not match connectivity in {path}")
        cursor += 1
        faces.append(face)
    if cursor >= len(tokens) or tokens[cursor] != ")":
        raise ValueError(f"face list is unterminated in {path}")
    return faces


def read_boundary(path: Path) -> list[dict[str, Any]]:
    tokens = _data_tokens(path)
    count, cursor = _consume_list_start(tokens, path)
    patches: list[dict[str, Any]] = []
    names: set[str] = set()
    for _ in range(count):
        if cursor >= len(tokens):
            raise ValueError(f"boundary list is truncated in {path}")
        name = _unquote(tokens[cursor])
        cursor += 1
        if not name or name in names:
            raise ValueError(f"duplicate/empty boundary patch name in {path}: {name!r}")
        names.add(name)
        if cursor >= len(tokens) or tokens[cursor] != "{":
            raise ValueError(f"boundary patch dictionary is missing for {name!r}")
        cursor += 1
        values: dict[str, str] = {}
        depth = 1
        while cursor < len(tokens) and depth:
            token = tokens[cursor]
            if token == "{":
                depth += 1
                cursor += 1
                continue
            if token == "}":
                depth -= 1
                cursor += 1
                continue
            if depth == 1 and token in {"type", "nFaces", "startFace"}:
                if cursor + 1 >= len(tokens):
                    raise ValueError(f"boundary key {token!r} has no value for {name!r}")
                values[token] = _unquote(tokens[cursor + 1])
            cursor += 1
        if depth:
            raise ValueError(f"boundary patch dictionary is unterminated for {name!r}")
        missing = sorted({"type", "nFaces", "startFace"} - set(values))
        if missing:
            raise ValueError(f"boundary patch {name!r} is missing keys: {', '.join(missing)}")
        try:
            n_faces = int(values["nFaces"])
            start_face = int(values["startFace"])
        except ValueError as exc:
            raise ValueError(f"boundary face range is invalid for {name!r}") from exc
        patches.append(
            {
                "name": name,
                "type": values["type"],
                "nFaces": n_faces,
                "startFace": start_face,
            }
        )
    if cursor >= len(tokens) or tokens[cursor] != ")":
        raise ValueError(f"boundary list is unterminated in {path}")
    return patches


def read_label_list(path: Path) -> list[int]:
    tokens = _data_tokens(path)
    count, cursor = _consume_list_start(tokens, path)
    if cursor + count >= len(tokens):
        raise ValueError(f"label list is truncated in {path}")
    try:
        labels = [int(tokens[cursor + offset]) for offset in range(count)]
    except ValueError as exc:
        raise ValueError(f"label list contains a non-integer in {path}") from exc
    cursor += count
    if cursor >= len(tokens) or tokens[cursor] != ")":
        raise ValueError(f"label list is unterminated in {path}")
    return labels


def _polygon_area(points: np.ndarray, face: list[int]) -> float:
    if len(set(face)) < 3:
        raise ValueError("face has fewer than three unique point indices")
    if min(face) < 0 or max(face) >= len(points):
        raise ValueError("face references a point outside the points list")
    vertices = points[np.asarray(face, dtype=int)]
    area_vector = np.cross(vertices, np.roll(vertices, -1, axis=0)).sum(axis=0) * 0.5
    area = float(np.linalg.norm(area_vector))
    if not math.isfinite(area) or area <= 0.0:
        raise ValueError("face polygon area is non-positive or non-finite")
    return area


def _combined_mesh_sha(paths: dict[str, Path]) -> str:
    digest = hashlib.sha256()
    for logical_name in sorted(paths):
        path = paths[logical_name]
        digest.update(logical_name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _contract_scale_to_m(contract: dict[str, Any]) -> float:
    units = str(contract.get("units", "")).strip().lower()
    if units not in UNIT_SCALE_TO_M:
        raise ValueError(f"contract units are not metrically defined: {contract.get('units')!r}")
    return UNIT_SCALE_TO_M[units]


def _validate_contract(contract_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"boundary contract is unreadable: {contract_path}: {exc}") from exc
    if not isinstance(contract, dict):
        raise ValueError("boundary contract root must be an object")
    if contract.get("schema") != CONTRACT_SCHEMA or contract.get("status") != "PASS":
        raise ValueError("boundary contract schema/status is not an accepted PASS contract")
    checks = contract.get("checks")
    if not isinstance(checks, dict) or checks.get("all_faces_classified_once") is not True:
        raise ValueError("boundary contract did not classify all source faces exactly once")
    topology = contract.get("surface_topology")
    topology_checks = topology.get("checks") if isinstance(topology, dict) else None
    required_topology = {
        "watertight",
        "manifold",
        "orientation_consistent",
        "nonzero_enclosed_volume",
    }
    if not isinstance(topology_checks, dict) or any(
        topology_checks.get(key) is not True for key in required_topology
    ):
        raise ValueError("boundary contract source surface topology is not fully valid")

    face_count = contract.get("face_count")
    groups = contract.get("groups")
    roles = contract.get("roles")
    area_by_group = contract.get("area_by_group")
    if not isinstance(face_count, int) or face_count <= 0 or not isinstance(groups, dict):
        raise ValueError("boundary contract face_count/groups are invalid")
    if not isinstance(roles, dict) or not isinstance(area_by_group, dict):
        raise ValueError("boundary contract roles/area_by_group are missing")
    all_ids: list[int] = []
    role_by_group: dict[str, str] = {}
    for role, names in roles.items():
        if role not in ROLES or not isinstance(names, list):
            raise ValueError(f"boundary contract role is invalid: {role!r}")
        for name in names:
            if not isinstance(name, str) or name not in groups or name in role_by_group:
                raise ValueError(f"boundary contract role membership is invalid: {name!r}")
            role_by_group[name] = role
    for name, ids in groups.items():
        if not isinstance(name, str) or not isinstance(ids, list) or any(
            not isinstance(face_id, int) for face_id in ids
        ):
            raise ValueError(f"boundary contract face group is invalid: {name!r}")
        all_ids.extend(ids)
        if ids and name not in role_by_group:
            raise ValueError(f"non-empty boundary group has no role: {name!r}")
        area = area_by_group.get(name)
        if not isinstance(area, (int, float)) or not math.isfinite(float(area)) or float(area) < 0:
            raise ValueError(f"boundary contract area is invalid: {name!r}")
    if len(all_ids) != face_count or set(all_ids) != set(range(face_count)):
        raise ValueError("boundary contract source faces are missing, duplicated, or out of range")

    artifact = contract.get("openfoam_artifacts")
    if not isinstance(artifact, dict):
        raise ValueError("boundary contract openfoam_artifacts is missing")
    if artifact.get("schema") != ARTIFACT_SCHEMA or artifact.get("status") != "PASS":
        raise ValueError("boundary contract OpenFOAM artifact schema/status is invalid")
    artifact_patches = artifact.get("patches")
    if not isinstance(artifact_patches, dict) or not artifact_patches:
        raise ValueError("boundary contract OpenFOAM patches are missing")

    external_path = contract_path.parent / "openfoam_patch_artifacts.json"
    if external_path.is_file():
        try:
            external = json.loads(external_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"external patch artifact is unreadable: {external_path}: {exc}") from exc
        if external != artifact:
            raise ValueError("embedded and external OpenFOAM patch artifacts differ")

    patch_names: set[str] = set()
    expected_nonempty = {name for name, ids in groups.items() if ids}
    if set(artifact_patches) != expected_nonempty:
        raise ValueError("OpenFOAM artifact patches do not match non-empty contract groups")
    for group_name, patch in artifact_patches.items():
        if not isinstance(patch, dict):
            raise ValueError(f"OpenFOAM artifact patch is invalid: {group_name!r}")
        patch_name = patch.get("patch_name")
        role = role_by_group.get(group_name)
        expected_type = "patch" if role in {"gate", "vent"} else "wall"
        if not isinstance(patch_name, str) or not patch_name or patch_name in patch_names:
            raise ValueError(f"OpenFOAM patch name is invalid/duplicated: {patch_name!r}")
        patch_names.add(patch_name)
        if patch.get("role") != role or patch.get("openfoam_patch_type") != expected_type:
            raise ValueError(f"OpenFOAM patch role/type conflicts with contract: {group_name!r}")
        source_count = patch.get("face_count")
        area = patch.get("area_model_units2")
        if source_count != len(groups[group_name]):
            raise ValueError(f"OpenFOAM source face count conflicts with group: {group_name!r}")
        if not isinstance(area, (int, float)) or not math.isclose(
            float(area), float(area_by_group[group_name]), rel_tol=1.0e-12, abs_tol=1.0e-15
        ):
            raise ValueError(f"OpenFOAM source area conflicts with contract: {group_name!r}")
    for required_role in ("gate", "vent", "wall"):
        if not any(groups.get(name) for name in roles.get(required_role, [])):
            raise ValueError(f"boundary contract has no non-empty {required_role} group")

    references = {
        "model": _verify_hashed_reference(contract, "model", base_dir=contract_path.parent),
        "spec": _verify_hashed_reference(contract, "spec", base_dir=contract_path.parent),
    }
    return contract, {"role_by_group": role_by_group, "references": references}


def _relative_error(actual: float, expected: float, abs_tolerance: float) -> float:
    denominator = max(abs(expected), abs_tolerance, float(np.finfo(float).tiny))
    return abs(actual - expected) / denominator


def _is_within_area_tolerance(
    actual: float, expected: float, *, relative_tolerance: float, absolute_tolerance: float
) -> bool:
    return abs(actual - expected) <= absolute_tolerance + relative_tolerance * abs(expected)


def _case_manifest_binding(case_dir: Path, contract_path: Path) -> dict[str, Any]:
    path = case_dir / "cad_manifest.json"
    if not path.is_file():
        return {"present": False, "status": "NOT_PROVIDED"}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"case cad_manifest.json is unreadable: {path}: {exc}") from exc
    binding = payload.get("boundary_contract") if isinstance(payload, dict) else None
    if not isinstance(binding, dict):
        raise ValueError("case cad_manifest.json has no boundary_contract binding")
    expected = _sha256(contract_path)
    if binding.get("sha256") != expected:
        raise ValueError("case cad_manifest boundary contract sha256 mismatch")
    return {"present": True, "status": "VERIFIED", "path": str(path), "sha256": _sha256(path)}


def _audit(
    case_dir: Path,
    contract_path: Path,
    *,
    poly_mesh_dir: Path | None,
    area_relative_tolerance: float,
    area_absolute_tolerance_m2: float,
    allowed_extra_patches: set[str],
) -> dict[str, Any]:
    if area_relative_tolerance < 0 or area_absolute_tolerance_m2 < 0:
        raise ValueError("area tolerances must be non-negative")
    case_dir = case_dir.resolve()
    contract_path = contract_path.resolve()
    mesh_dir = (poly_mesh_dir or case_dir / "constant" / "polyMesh").resolve()
    contract, contract_info = _validate_contract(contract_path)
    scale = _contract_scale_to_m(contract)
    case_binding = _case_manifest_binding(case_dir, contract_path)

    mesh_paths = {
        name: _openfoam_file(mesh_dir, name) for name in ("points", "faces", "boundary")
    }
    for optional_name in ("owner", "neighbour"):
        try:
            mesh_paths[optional_name] = _openfoam_file(mesh_dir, optional_name)
        except FileNotFoundError:
            pass
    points = read_points(mesh_paths["points"])
    faces = read_faces(mesh_paths["faces"])
    boundaries = read_boundary(mesh_paths["boundary"])
    face_areas = np.asarray([_polygon_area(points, face) for face in faces], dtype=float)

    failures: list[str] = []
    owner_labels = read_label_list(mesh_paths["owner"]) if "owner" in mesh_paths else None
    neighbour_labels = (
        read_label_list(mesh_paths["neighbour"]) if "neighbour" in mesh_paths else None
    )
    if owner_labels is not None and len(owner_labels) != len(faces):
        failures.append("mesh.owner_count_does_not_match_faces")
    internal_face_count = len(neighbour_labels) if neighbour_labels is not None else None
    interval_owner: dict[int, str] = {}
    actual_by_name: dict[str, dict[str, Any]] = {}
    invalid_ranges: list[dict[str, Any]] = []
    overlaps: list[dict[str, Any]] = []
    for patch in boundaries:
        start = patch["startFace"]
        count = patch["nFaces"]
        end = start + count
        range_valid = start >= 0 and count >= 0 and end <= len(faces)
        patch["endFaceExclusive"] = end
        patch["range_valid"] = range_valid
        if not range_valid:
            invalid_ranges.append({"patch": patch["name"], "startFace": start, "nFaces": count})
            patch["area_m2"] = None
            continue
        patch["area_m2"] = float(face_areas[start:end].sum())
        for face_id in range(start, end):
            previous = interval_owner.get(face_id)
            if previous is not None:
                overlaps.append({"face_id": face_id, "patches": [previous, patch["name"]]})
            else:
                interval_owner[face_id] = patch["name"]
        actual_by_name[patch["name"]] = patch
    if invalid_ranges:
        failures.append("mesh.boundary_face_range_invalid")
    if overlaps:
        failures.append("mesh.boundary_face_ranges_overlap")
    coverage: dict[str, Any]
    if internal_face_count is None:
        coverage = {"status": "NOT_CHECKED_NO_NEIGHBOUR_FILE"}
    else:
        expected_boundary_ids = set(range(internal_face_count, len(faces)))
        actual_boundary_ids = set(interval_owner)
        missing_boundary_ids = sorted(expected_boundary_ids - actual_boundary_ids)
        internal_or_invalid_ids = sorted(actual_boundary_ids - expected_boundary_ids)
        coverage = {
            "status": "PASS"
            if not missing_boundary_ids and not internal_or_invalid_ids
            else "HOLD",
            "internal_face_count": internal_face_count,
            "expected_boundary_face_count": len(expected_boundary_ids),
            "covered_boundary_face_count": len(actual_boundary_ids & expected_boundary_ids),
            "missing_face_count": len(missing_boundary_ids),
            "missing_face_ids_sample": missing_boundary_ids[:50],
            "internal_or_invalid_face_count": len(internal_or_invalid_ids),
            "internal_or_invalid_face_ids_sample": internal_or_invalid_ids[:50],
        }
        if missing_boundary_ids:
            failures.append("mesh.boundary_face_ranges_have_gaps")
        if internal_or_invalid_ids:
            failures.append("mesh.boundary_range_includes_internal_face")

    patch_results: dict[str, dict[str, Any]] = {}
    expected_names: set[str] = set()
    artifact_patches = contract["openfoam_artifacts"]["patches"]
    expected_total = 0.0
    actual_total = 0.0
    for group_name, source in artifact_patches.items():
        patch_name = source["patch_name"]
        expected_names.add(patch_name)
        expected_area = float(source["area_model_units2"]) * scale * scale
        expected_total += expected_area
        actual = actual_by_name.get(patch_name)
        actual_area = float(actual["area_m2"]) if actual and actual["area_m2"] is not None else 0.0
        actual_total += actual_area
        area_ok = bool(actual) and actual["nFaces"] > 0 and _is_within_area_tolerance(
            actual_area,
            expected_area,
            relative_tolerance=area_relative_tolerance,
            absolute_tolerance=area_absolute_tolerance_m2,
        )
        type_ok = bool(actual) and actual["type"] == source["openfoam_patch_type"]
        if actual is None:
            failures.append(f"patch.{patch_name}.missing")
        elif actual["nFaces"] <= 0:
            failures.append(f"patch.{patch_name}.empty")
        if actual is not None and not type_ok:
            failures.append(f"patch.{patch_name}.type_mismatch")
        if not area_ok:
            failures.append(f"patch.{patch_name}.area_out_of_tolerance")
        patch_results[group_name] = {
            "patch_name": patch_name,
            "role": source["role"],
            "expected_openfoam_type": source["openfoam_patch_type"],
            "actual_openfoam_type": actual["type"] if actual else None,
            "expected_source_face_count": int(source["face_count"]),
            "actual_mesh_face_count": int(actual["nFaces"]) if actual else 0,
            "face_count_is_acceptance_criterion": False,
            "expected_area_m2": expected_area,
            "actual_area_m2": actual_area,
            "absolute_area_error_m2": abs(actual_area - expected_area),
            "relative_area_error": _relative_error(
                actual_area, expected_area, area_absolute_tolerance_m2
            ),
            "area_within_tolerance": area_ok,
            "type_matches_role_contract": type_ok,
            "startFace": actual["startFace"] if actual else None,
            "endFaceExclusive": actual["endFaceExclusive"] if actual else None,
            "range_valid": actual["range_valid"] if actual else False,
        }

    extras = sorted(
        patch["name"]
        for patch in boundaries
        if patch["nFaces"] > 0
        and patch["name"] not in expected_names
        and patch["name"] not in allowed_extra_patches
    )
    if extras:
        failures.append("mesh.extra_nonempty_semantic_patches")
    total_ok = _is_within_area_tolerance(
        actual_total,
        expected_total,
        relative_tolerance=area_relative_tolerance,
        absolute_tolerance=area_absolute_tolerance_m2,
    )
    if not total_ok:
        failures.append("mesh.total_boundary_area_out_of_tolerance")

    failures = list(dict.fromkeys(failures))
    status = "PASS" if not failures else "HOLD"
    return {
        "schema": SCHEMA,
        "status": status,
        "truth_status": "UNCALIBRATED_SCREENING",
        "acceptance": "BOUNDARY_CONTRACT_RECONCILED" if status == "PASS" else "BOUNDARY_CONTRACT_HOLD",
        "case_dir": str(case_dir),
        "contract": {
            "path": str(contract_path),
            "sha256": _sha256(contract_path),
            "schema": contract["schema"],
            "units": contract["units"],
            "scale_to_m": scale,
            "model": contract_info["references"]["model"],
            "spec": contract_info["references"]["spec"],
            "case_manifest_binding": case_binding,
        },
        "mesh": {
            "poly_mesh_dir": str(mesh_dir),
            "sha256": _combined_mesh_sha(mesh_paths),
            "files": {name: str(path) for name, path in sorted(mesh_paths.items())},
            "point_count": int(len(points)),
            "face_count": int(len(faces)),
            "boundary_patch_count": int(len(boundaries)),
            "owner_count": len(owner_labels) if owner_labels is not None else None,
            "internal_face_count": internal_face_count,
        },
        "tolerances": {
            "area_relative": area_relative_tolerance,
            "area_absolute_m2": area_absolute_tolerance_m2,
        },
        "patches": patch_results,
        "total_area": {
            "expected_m2": expected_total,
            "actual_m2": actual_total,
            "absolute_error_m2": abs(actual_total - expected_total),
            "relative_error": _relative_error(
                actual_total, expected_total, area_absolute_tolerance_m2
            ),
            "within_tolerance": total_ok,
        },
        "boundary_ranges": boundaries,
        "boundary_coverage": coverage,
        "invalid_ranges": invalid_ranges,
        "overlaps": overlaps,
        "extra_nonempty_patches": extras,
        "allowed_extra_patches": sorted(allowed_extra_patches),
        "failures": failures,
        "limitations": [
            "Source triangle count is not compared to snappyHexMesh face count because remeshing changes topology",
            "This audit proves geometry/boundary consistency, not material calibration or product accuracy",
        ],
    }


def audit_boundary_contract(
    case_dir: Path,
    contract_path: Path,
    *,
    poly_mesh_dir: Path | None = None,
    area_relative_tolerance: float = 0.10,
    area_absolute_tolerance_m2: float = 1.0e-12,
    allowed_extra_patches: set[str] | None = None,
) -> dict[str, Any]:
    """Return a fail-closed JSON-serializable audit manifest."""
    try:
        return _audit(
            Path(case_dir),
            Path(contract_path),
            poly_mesh_dir=Path(poly_mesh_dir) if poly_mesh_dir is not None else None,
            area_relative_tolerance=float(area_relative_tolerance),
            area_absolute_tolerance_m2=float(area_absolute_tolerance_m2),
            allowed_extra_patches=set(allowed_extra_patches or ()),
        )
    except Exception as exc:
        return {
            "schema": SCHEMA,
            "status": "HOLD",
            "truth_status": "UNCALIBRATED_SCREENING",
            "acceptance": "BOUNDARY_CONTRACT_HOLD",
            "case_dir": str(Path(case_dir).resolve()),
            "contract": {"path": str(Path(contract_path).resolve())},
            "failures": ["audit.exception"],
            "exception": {"type": type(exc).__name__, "message": str(exc)},
            "limitations": [
                "Audit input could not be verified; no boundary claim is permitted"
            ],
        }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case-dir", type=Path, required=True)
    parser.add_argument("--boundary-contract", type=Path, required=True)
    parser.add_argument("--poly-mesh-dir", type=Path)
    parser.add_argument("--area-relative-tolerance", type=float, default=0.10)
    parser.add_argument("--area-absolute-tolerance-m2", type=float, default=1.0e-12)
    parser.add_argument("--allow-extra-patch", action="append", default=[])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = audit_boundary_contract(
        args.case_dir,
        args.boundary_contract,
        poly_mesh_dir=args.poly_mesh_dir,
        area_relative_tolerance=args.area_relative_tolerance,
        area_absolute_tolerance_m2=args.area_absolute_tolerance_m2,
        allowed_extra_patches=set(args.allow_extra_patch),
    )
    output = args.output or args.case_dir / "boundary_contract_audit.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0 if manifest["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
