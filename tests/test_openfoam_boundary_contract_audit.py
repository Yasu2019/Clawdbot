from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import audit_openfoam_boundary_contract as A


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _foam_header(*, class_name: str, object_name: str) -> str:
    return (
        "FoamFile\n"
        "{\n"
        "    format ascii;\n"
        f"    class {class_name};\n"
        f"    object {object_name};\n"
        "}\n"
    )


def _write_mesh(
    case_dir: Path,
    *,
    omit_vent: bool = False,
    extra_patch: bool = False,
    overlap: bool = False,
    invalid_range: bool = False,
    gate_type: str = "patch",
) -> None:
    mesh_dir = case_dir / "constant" / "polyMesh"
    mesh_dir.mkdir(parents=True)
    points = [
        (0, 0, 0),
        (1, 0, 0),
        (1, 1, 0),
        (0, 1, 0),
        (0, 0, 1),
        (1, 0, 1),
        (1, 1, 1),
        (0, 1, 1),
    ]
    faces = [
        (0, 3, 2, 1),
        (4, 5, 6, 7),
        (0, 1, 5, 4),
        (1, 2, 6, 5),
        (2, 3, 7, 6),
        (3, 0, 4, 7),
    ]
    if extra_patch:
        faces.append((0, 3, 2, 1))
    points_text = _foam_header(class_name="vectorField", object_name="points")
    points_text += f"{len(points)}\n(\n"
    points_text += "\n".join(f"({x} {y} {z})" for x, y, z in points)
    points_text += "\n)\n"
    (mesh_dir / "points").write_text(points_text, encoding="utf-8")

    faces_text = _foam_header(class_name="faceList", object_name="faces")
    faces_text += f"{len(faces)}\n(\n"
    faces_text += "\n".join(
        f"{len(face)}({' '.join(str(point_id) for point_id in face)})" for face in faces
    )
    faces_text += "\n)\n"
    (mesh_dir / "faces").write_text(faces_text, encoding="utf-8")
    owner_text = _foam_header(class_name="labelList", object_name="owner")
    owner_text += f"{len(faces)}\n(\n"
    owner_text += "\n".join("0" for _ in faces)
    owner_text += "\n)\n"
    (mesh_dir / "owner").write_text(owner_text, encoding="utf-8")
    neighbour_text = _foam_header(class_name="labelList", object_name="neighbour")
    neighbour_text += "0\n(\n)\n"
    (mesh_dir / "neighbour").write_text(neighbour_text, encoding="utf-8")

    patches = [("gate_main", gate_type, 1, 0)]
    if not omit_vent:
        patches.append(("vent_far", "patch", 1, 1))
    wall_start = 1 if overlap else 2
    patches.append(("outer_wall", "wall", 40 if invalid_range else 4, wall_start))
    if extra_patch:
        patches.append(("defaultFaces", "patch", 1, 6))
    boundary_text = _foam_header(class_name="polyBoundaryMesh", object_name="boundary")
    boundary_text += f"{len(patches)}\n(\n"
    for name, patch_type, count, start in patches:
        boundary_text += (
            f"{name}\n{{\n"
            f"    type {patch_type};\n"
            f"    nFaces {count};\n"
            f"    startFace {start};\n"
            "}\n"
        )
    boundary_text += ")\n"
    (mesh_dir / "boundary").write_text(boundary_text, encoding="utf-8")


def _write_contract(root: Path, *, gate_area: float = 1.0) -> Path:
    root.mkdir(parents=True)
    model = root / "model.stl"
    model.write_text("solid verified-model\nendsolid verified-model\n", encoding="ascii")
    spec = root / "selectors.json"
    spec.write_text('{"units":"m","source":"virtual-test"}\n', encoding="utf-8")
    groups = {
        "gate_main": [0],
        "vent_far": [1],
        # The source has eight wall triangles; snappy is allowed to make four
        # polygon faces while preserving the wall area.
        "outer_wall": list(range(2, 10)),
    }
    area_by_group = {"gate_main": gate_area, "vent_far": 1.0, "outer_wall": 4.0}
    patches = {
        "gate_main": {
            "patch_name": "gate_main",
            "surface_file": "patch_surfaces/gate_main.stl",
            "face_count": 1,
            "area_model_units2": gate_area,
            "role": "gate",
            "openfoam_patch_type": "patch",
        },
        "vent_far": {
            "patch_name": "vent_far",
            "surface_file": "patch_surfaces/vent_far.stl",
            "face_count": 1,
            "area_model_units2": 1.0,
            "role": "vent",
            "openfoam_patch_type": "patch",
        },
        "outer_wall": {
            "patch_name": "outer_wall",
            "surface_file": "patch_surfaces/outer_wall.stl",
            "face_count": 8,
            "area_model_units2": 4.0,
            "role": "wall",
            "openfoam_patch_type": "wall",
        },
    }
    artifact = {
        "schema": A.ARTIFACT_SCHEMA,
        "status": "PASS",
        "patches": patches,
        "consumer_contract": "post-mesh area audit required",
    }
    (root / "openfoam_patch_artifacts.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    contract = {
        "schema": A.CONTRACT_SCHEMA,
        "status": "PASS",
        "units": "m",
        "face_count": 10,
        "node_count": 8,
        "groups": groups,
        "roles": {
            "gate": ["gate_main"],
            "vent": ["vent_far"],
            "wall": ["outer_wall"],
            "hole": [],
        },
        "area_by_group": area_by_group,
        "checks": {"all_faces_classified_once": True, "surface_topology": True},
        "surface_topology": {
            "checks": {
                "watertight": True,
                "manifold": True,
                "orientation_consistent": True,
                "nonzero_enclosed_volume": True,
            }
        },
        "model": {"path": str(model), "sha256": _sha256(model), "suffix": ".stl"},
        "spec": {"path": str(spec), "sha256": _sha256(spec)},
        "openfoam_artifacts": artifact,
    }
    path = root / "boundary_groups_manifest.json"
    path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")
    return path


def test_valid_mesh_passes_by_area_even_when_snappy_face_count_differs(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir)
    contract = _write_contract(tmp_path / "contract")

    report = A.audit_boundary_contract(
        case_dir, contract, area_relative_tolerance=1.0e-12
    )

    assert report["status"] == "PASS"
    assert report["truth_status"] == "UNCALIBRATED_SCREENING"
    assert len(report["mesh"]["sha256"]) == 64
    wall = report["patches"]["outer_wall"]
    assert wall["expected_source_face_count"] == 8
    assert wall["actual_mesh_face_count"] == 4
    assert wall["face_count_is_acceptance_criterion"] is False
    assert wall["actual_area_m2"] == pytest.approx(4.0)
    assert report["total_area"]["within_tolerance"] is True
    assert report["boundary_coverage"]["status"] == "PASS"


@pytest.mark.parametrize(
    ("mesh_options", "expected_failure"),
    [
        ({"omit_vent": True}, "patch.vent_far.missing"),
        ({"extra_patch": True}, "mesh.extra_nonempty_semantic_patches"),
        ({"overlap": True}, "mesh.boundary_face_ranges_overlap"),
        ({"invalid_range": True}, "mesh.boundary_face_range_invalid"),
        ({"gate_type": "wall"}, "patch.gate_main.type_mismatch"),
    ],
)
def test_mesh_boundary_failures_are_hold(
    tmp_path: Path, mesh_options: dict[str, object], expected_failure: str
) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir, **mesh_options)
    contract = _write_contract(tmp_path / "contract")

    report = A.audit_boundary_contract(case_dir, contract)

    assert report["status"] == "HOLD"
    assert expected_failure in report["failures"]


def test_area_deviation_is_hold_and_reports_both_patch_and_total(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir)
    contract = _write_contract(tmp_path / "contract", gate_area=2.0)

    report = A.audit_boundary_contract(
        case_dir, contract, area_relative_tolerance=0.01
    )

    assert report["status"] == "HOLD"
    assert "patch.gate_main.area_out_of_tolerance" in report["failures"]
    assert "mesh.total_boundary_area_out_of_tolerance" in report["failures"]
    assert report["patches"]["gate_main"]["relative_area_error"] == pytest.approx(0.5)


def test_mm_contract_area_is_scaled_to_si_mesh_area(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir)
    contract_path = _write_contract(tmp_path / "contract")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["units"] = "mm"
    for group_name in contract["area_by_group"]:
        contract["area_by_group"][group_name] *= 1.0e6
        contract["openfoam_artifacts"]["patches"][group_name][
            "area_model_units2"
        ] *= 1.0e6
    artifact_path = contract_path.parent / "openfoam_patch_artifacts.json"
    artifact_path.write_text(
        json.dumps(contract["openfoam_artifacts"], indent=2) + "\n", encoding="utf-8"
    )
    contract_path.write_text(json.dumps(contract, indent=2) + "\n", encoding="utf-8")

    report = A.audit_boundary_contract(
        case_dir, contract_path, area_relative_tolerance=1.0e-12
    )

    assert report["status"] == "PASS"
    assert report["contract"]["scale_to_m"] == pytest.approx(0.001)
    assert report["total_area"]["expected_m2"] == pytest.approx(6.0)


def test_model_sha_mismatch_fails_closed_before_mesh_claim(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir)
    contract_path = _write_contract(tmp_path / "contract")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    Path(contract["model"]["path"]).write_text("changed\n", encoding="utf-8")

    report = A.audit_boundary_contract(case_dir, contract_path)

    assert report["status"] == "HOLD"
    assert report["failures"] == ["audit.exception"]
    assert "model sha256 mismatch" in report["exception"]["message"]


def test_case_manifest_must_bind_the_same_contract(tmp_path: Path) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir)
    contract = _write_contract(tmp_path / "contract")
    (case_dir / "cad_manifest.json").write_text(
        json.dumps({"boundary_contract": {"sha256": "0" * 64}}) + "\n",
        encoding="utf-8",
    )

    report = A.audit_boundary_contract(case_dir, contract)

    assert report["status"] == "HOLD"
    assert "cad_manifest boundary contract sha256 mismatch" in report["exception"]["message"]


def test_cli_returns_nonzero_and_writes_hold_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    case_dir = tmp_path / "case"
    _write_mesh(case_dir, omit_vent=True)
    contract = _write_contract(tmp_path / "contract")
    output = tmp_path / "audit.json"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "audit_openfoam_boundary_contract.py",
            "--case-dir",
            str(case_dir),
            "--boundary-contract",
            str(contract),
            "--output",
            str(output),
        ],
    )

    assert A.main() == 2
    assert json.loads(output.read_text(encoding="utf-8"))["status"] == "HOLD"
