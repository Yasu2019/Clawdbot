import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import hashlib
import json
from pathlib import Path

import meshio
import numpy as np
import pyvista as pv
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import extract_arbitrary_model_boundaries as boundary_extractor
import moldflow_step_case_builder as M


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_stl(path: Path, points: list[tuple[float, float, float]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    a, b, c = points
    path.write_text(
        "solid patch\n"
        "  facet normal 0 0 1\n"
        "    outer loop\n"
        f"      vertex {a[0]} {a[1]} {a[2]}\n"
        f"      vertex {b[0]} {b[1]} {b[2]}\n"
        f"      vertex {c[0]} {c[1]} {c[2]}\n"
        "    endloop\n"
        "  endfacet\n"
        "endsolid patch\n",
        encoding="ascii",
    )


def _write_template(template: Path) -> None:
    (template / "0").mkdir(parents=True)
    (template / "constant" / "triSurface").mkdir(parents=True)
    (template / "system").mkdir(parents=True)
    (template / "constant" / "triSurface" / "Moldflow.stl").write_text(
        "legacy template surface\n", encoding="ascii"
    )
    (template / "constant" / "transportProperties").write_text(
        "transportModel Newtonian;\n", encoding="ascii"
    )
    (template / "0" / "U").write_text(
        "FoamFile { object U; }\n"
        "dimensions [0 1 -1 0 0 0 0];\n"
        "internalField uniform (0 0 0);\n"
        "boundaryField\n{\n"
        " gate { type fixedValue; value uniform (-1 0 0); }\n"
        " vent { type pressureInletOutletVelocity; value uniform (0 0 0); }\n"
        " moldflow { type noSlip; }\n"
        "}\n",
        encoding="ascii",
    )
    (template / "0" / "alpha.polymer").write_text(
        "FoamFile { object alpha.polymer; }\n"
        "dimensions [0 0 0 0 0 0 0];\n"
        "internalField uniform 0;\n"
        "boundaryField\n{\n"
        " gate { type fixedValue; value uniform 1; }\n"
        " vent { type inletOutlet; inletValue uniform 0; value uniform 0; }\n"
        " moldflow { type zeroGradient; }\n"
        "}\n",
        encoding="ascii",
    )
    (template / "0" / "p_rgh").write_text(
        "FoamFile { object p_rgh; }\n"
        "dimensions [1 -1 -2 0 0 0 0];\n"
        "internalField uniform 0;\n"
        "boundaryField\n{\n"
        " gate { type fixedFluxPressure; value uniform 0; }\n"
        " vent { type totalPressure; p0 uniform 0; value uniform 0; }\n"
        " moldflow { type fixedFluxPressure; value uniform 0; }\n"
        "}\n",
        encoding="ascii",
    )
    (template / "system" / "snappyHexMeshDict").write_text(
        "FoamFile { object snappyHexMeshDict; }\n"
        "maxLocalCells 10; maxGlobalCells 20;\n"
        "locationInMesh (0.0492 0.0003 0.0253);\n",
        encoding="ascii",
    )
    (template / "system" / "surfaceFeatureExtractDict").write_text(
        "Moldflow.stl {}\n", encoding="ascii"
    )
    (template / "system" / "topoSetDict").write_text(
        "actions (legacyCylinder);\n", encoding="ascii"
    )
    (template / "system" / "createPatchDict").write_text(
        "patches (legacyGate);\n", encoding="ascii"
    )
    (template / "system" / "controlDict").write_text(
        "endTime 1; writeControl timeStep; writeInterval 1;\n", encoding="ascii"
    )


def _write_contract(root: Path) -> Path:
    model = root / "model.stl"
    _write_stl(model, [(0, 0, 0), (10, 0, 0), (0, 10, 10)])
    spec = root / "selectors.json"
    spec.write_text('{"units":"mm"}\n', encoding="utf-8")
    surfaces = {
        "gate_main": [(0, 0, 0), (0, 1, 0), (0, 0, 1)],
        "vent_far": [(10, 0, 0), (10, 1, 0), (10, 0, 1)],
        "outer_wall": [(0, 0, 0), (10, 0, 0), (0, 10, 10)],
    }
    roles = {"gate_main": "gate", "vent_far": "vent", "outer_wall": "wall"}
    patches = {}
    for name, points in surfaces.items():
        surface = root / "patch_surfaces" / f"{name}.stl"
        _write_stl(surface, points)
        role = roles[name]
        patches[name] = {
            "patch_name": name,
            "surface_file": f"patch_surfaces/{name}.stl",
            "face_count": 1,
            "area_model_units2": 0.5,
            "role": role,
            "openfoam_patch_type": "patch" if role in ("gate", "vent") else "wall",
        }
    artifact = {
        "schema": M.BOUNDARY_ARTIFACT_SCHEMA,
        "status": "PASS",
        "patches": patches,
        "consumer_contract": "test fixture",
    }
    (root / "openfoam_patch_artifacts.json").write_text(
        json.dumps(artifact, indent=2) + "\n", encoding="utf-8"
    )
    contract = {
        "schema": M.BOUNDARY_CONTRACT_SCHEMA,
        "status": "PASS",
        "units": "mm",
        "face_count": 3,
        "node_count": 9,
        "groups": {"gate_main": [0], "vent_far": [1], "outer_wall": [2]},
        "roles": {
            "gate": ["gate_main"],
            "vent": ["vent_far"],
            "wall": ["outer_wall"],
            "hole": [],
        },
        "checks": {
            "all_faces_classified_once": True,
            "surface_topology": True,
            "empty_required_groups": [],
        },
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


def test_contract_build_generates_patch_driven_snappy_case(tmp_path):
    template = tmp_path / "template"
    _write_template(template)
    contract_path = _write_contract(tmp_path / "contract")
    gate_spec_path = tmp_path / "gate_spec.json"
    gate_spec_path.write_text(
        json.dumps(
            {
                "version": 1,
                "gates": [
                    {"patch": "gate_main", "role": "injection", "enabled": True}
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "case"

    manifest = M.build_case(
        run_dir,
        template,
        None,
        gate_spec_path,
        {
            "mesh_mode": "snappyhexmesh",
            "physics_category": "resin_fill_vof",
            "boundary_contract_path": str(contract_path),
            "location_in_mesh_m": [0.001, 0.001, 0.001],
            "inlet_velocity_xyz": [2.5, 0.0, 0.0],
        },
    )

    snappy = (run_dir / "system" / "snappyHexMeshDict").read_text(encoding="utf-8")
    feature_dict = (run_dir / "system" / "surfaceFeatureExtractDict").read_text(encoding="utf-8")
    assert "gate_main.stl" in snappy and "vent_far.stl" in snappy and "outer_wall.stl" in snappy
    assert "patchInfo { type patch; }" in snappy
    assert "patchInfo { type wall; }" in snappy
    assert "Moldflow.stl" not in snappy
    assert "gate_main.eMesh" in snappy
    assert "gate_main.stl" in feature_dict and "outer_wall.stl" in feature_dict
    assert "actions ();" in (run_dir / "system" / "topoSetDict").read_text(encoding="utf-8")
    assert "patches ();" in (run_dir / "system" / "createPatchDict").read_text(encoding="utf-8")
    assert not (run_dir / "constant" / "triSurface" / "Moldflow.stl").exists()
    scaled = pv.read(run_dir / "constant" / "triSurface" / "vent_far.stl")
    assert scaled.bounds[0] == pytest.approx(0.01)
    u_text = (run_dir / "0" / "U").read_text(encoding="utf-8")
    assert "gate_main" in u_text and "uniform (2.5 0 0)" in u_text
    assert "vent_far" in u_text and "outer_wall" in u_text
    assert manifest["bbox_source"] == "boundary_contract_patch_surfaces"
    assert manifest["patches"]["gates"] == ["gate_main"]
    assert manifest["boundary_contract"]["sha256"] == _sha256(contract_path)
    assert manifest["boundary_contract"]["roles"]["vent"] == ["vent_far"]
    assert manifest["boundary_contract"]["legacy_patch_split"] == "disabled_noop_dictionaries"
    assert manifest["boundary_contract"]["patches"]["gate_main"]["case_surface_sha256"]


def test_contract_build_fails_closed_on_model_hash_mismatch(tmp_path):
    contract_path = _write_contract(tmp_path / "contract")
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    Path(contract["model"]["path"]).write_text("changed\n", encoding="ascii")

    with pytest.raises(ValueError, match="model sha256 mismatch"):
        M.load_boundary_contract({"boundary_contract_path": str(contract_path)})


def test_contract_build_requires_explicit_gate_velocity_and_location(tmp_path):
    contract_path = _write_contract(tmp_path / "contract")
    template = tmp_path / "template"
    _write_template(template)
    gate_spec_path = tmp_path / "gate_spec.json"
    gate_spec_path.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="location_in_mesh_m is required"):
        M.build_mfalign_snappy_case(
            tmp_path / "case_no_location",
            template,
            None,
            gate_spec_path,
            {},
            {"boundary_contract_path": str(contract_path)},
        )
    with pytest.raises(ValueError, match="explicit inlet_velocity_xyz"):
        M.build_mfalign_snappy_case(
            tmp_path / "case_no_velocity",
            template,
            None,
            gate_spec_path,
            {},
            {
                "boundary_contract_path": str(contract_path),
                "location_in_mesh_m": [0.001, 0.001, 0.001],
            },
        )


def test_legacy_snappy_path_is_unchanged_without_contract(tmp_path):
    template = tmp_path / "template"
    _write_template(template)
    surface = tmp_path / "legacy.stl"
    _write_stl(surface, [(0, 0, 0), (100, 60, 0), (0, 0, 50)])
    gate_spec_path = tmp_path / "gate_spec.json"
    gate_spec_path.write_text("{}\n", encoding="utf-8")

    manifest = M.build_mfalign_snappy_case(
        tmp_path / "case",
        template,
        surface,
        gate_spec_path,
        {},
        {
            "mesh_mode": "snappyhexmesh",
            "physics_category": "resin_fill_vof",
            "geometry_units": "mm",
            "location_in_mesh_m": [0.001, 0.001, 0.001],
        },
    )

    assert (tmp_path / "case" / "constant" / "triSurface" / "Moldflow.stl").is_file()
    assert "legacyCylinder" in (tmp_path / "case" / "system" / "topoSetDict").read_text(encoding="utf-8")
    assert manifest["patches"] == {"gates": ["gate"], "vents": ["vent"], "walls": ["moldflow"]}
    assert "boundary_contract" not in manifest


def test_real_extractor_contract_drives_case_builder_end_to_end(tmp_path):
    points = np.asarray(
        [
            [-1, -1, 0],
            [1, -1, 0],
            [1, 1, 0],
            [-1, 1, 0],
            [0, 0, 1],
        ],
        dtype=float,
    )
    triangles = np.asarray(
        [[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 2, 1], [0, 3, 2]],
        dtype=int,
    )
    model = tmp_path / "surface.vtu"
    meshio.write(model, meshio.Mesh(points=points, cells=[("triangle", triangles)]))
    selector_spec = tmp_path / "selectors.json"
    selector_spec.write_text(
        json.dumps(
            {
                "units": "mm",
                "tolerance": 0.2,
                "gates": [
                    {
                        "name": "gate_main",
                        "center": [0, -0.65, 0.35],
                        "normal": [0, -1, 1],
                        "diameter": 1.0,
                    }
                ],
                "vents": [
                    {
                        "name": "vent_top",
                        "center": [0, 0.65, 0.35],
                        "normal": [0, 1, 1],
                        "diameter": 1.0,
                    }
                ],
                "holes": [],
            }
        ),
        encoding="utf-8",
    )
    extracted_dir = tmp_path / "extracted"
    extracted = boundary_extractor.run(model, selector_spec, extracted_dir)
    assert extracted["status"] == "PASS"

    template = tmp_path / "template"
    _write_template(template)
    gate_spec = tmp_path / "gate_spec.json"
    gate_spec.write_text(
        json.dumps(
            {
                "version": 1,
                "gates": [
                    {"patch": "gate_main", "role": "injection", "enabled": True}
                ],
            }
        ),
        encoding="utf-8",
    )
    run_dir = tmp_path / "case"
    manifest = M.build_case(
        run_dir,
        template,
        None,
        gate_spec,
        {
            "mesh_mode": "snappyhexmesh",
            "physics_category": "resin_fill_vof",
            "boundary_contract_path": str(extracted_dir / "boundary_groups_manifest.json"),
            "location_in_mesh_m": [0.0, 0.0, 0.0003],
            "inlet_velocity_xyz": [0.0, 0.0, 1.0],
        },
    )

    assert manifest["boundary_contract"]["sha256"] == _sha256(
        extracted_dir / "boundary_groups_manifest.json"
    )
    assert manifest["patches"]["gates"] == ["gate_main"]
    assert manifest["patches"]["vents"] == ["vent_top"]
    assert (run_dir / "constant" / "triSurface" / "gate_main.stl").is_file()
    assert (run_dir / "constant" / "triSurface" / "vent_top.stl").is_file()
