import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import meshio
import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import extract_arbitrary_model_boundaries as M


def test_sidecar_driven_boundary_extraction_classifies_all_faces(tmp_path):
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
    triangles = np.asarray([[0, 1, 4], [1, 2, 4], [2, 3, 4], [3, 0, 4], [0, 2, 1], [0, 3, 2]], dtype=int)
    model = tmp_path / "surface.vtu"
    meshio.write(model, meshio.Mesh(points=points, cells=[("triangle", triangles)]))
    spec = {
        "units": "mm",
        "tolerance": 0.2,
        "gates": [{"name": "gate_main", "center": [0, -0.65, 0.35], "normal": [0, -1, 1], "diameter": 1.0}],
        "vents": [{"name": "vent_top", "center": [0, 0.65, 0.35], "normal": [0, 1, 1], "diameter": 1.0}],
        "holes": [],
    }
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    report = M.run(model, spec_path, tmp_path / "out")

    assert report["status"] == "PASS"
    assert report["checks"]["all_faces_classified_once"]
    assert report["area_by_group"]["gate_main"] > 0
    assert report["area_by_group"]["vent_top"] > 0
    assert report["surface_topology"]["checks"]["watertight"] is True
    assert report["model"]["sha256"]
    patches = report["openfoam_artifacts"]["patches"]
    assert (tmp_path / "out" / patches["gate_main"]["surface_file"]).is_file()
    assert (tmp_path / "out" / "openfoam_patch_artifacts.json").is_file()


def test_step_requires_triangulation(tmp_path):
    step = tmp_path / "part.step"
    step.write_text("ISO-10303-21;", encoding="ascii")
    with pytest.raises((RuntimeError, ValueError)) as exc_info:
        M.load_tri_surface(step)
    assert "STEP" in str(exc_info.value)


def test_real_step_is_tessellated_when_ocp_is_available(tmp_path):
    pytest.importorskip("OCP")
    from OCP.BRepPrimAPI import BRepPrimAPI_MakeBox
    from OCP.IFSelect import IFSelect_RetDone
    from OCP.STEPControl import STEPControl_AsIs, STEPControl_Writer

    step = tmp_path / "box.step"
    writer = STEPControl_Writer()
    assert writer.Transfer(BRepPrimAPI_MakeBox(1.0, 2.0, 3.0).Shape(), STEPControl_AsIs) == IFSelect_RetDone
    assert writer.Write(str(step)) == IFSelect_RetDone

    points, triangles = M.load_tri_surface(step, step_linear_deflection=0.1)
    topology = M.validate_surface(points, triangles)

    assert len(points) >= 8
    assert len(triangles) >= 12
    assert topology["checks"]["watertight"] is True


def test_open_surface_is_fail_closed_and_exports_audit_artifacts(tmp_path):
    points = np.asarray([[0, 0, 0], [1, 0, 0], [0, 1, 0]], dtype=float)
    triangles = np.asarray([[0, 1, 2]], dtype=int)
    model = tmp_path / "open_surface.vtu"
    meshio.write(model, meshio.Mesh(points=points, cells=[("triangle", triangles)]))
    spec = {"units": "mm", "gates": [], "vents": [], "holes": []}
    spec_path = tmp_path / "spec.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")

    report = M.run(model, spec_path, tmp_path / "out")

    assert report["status"] == "HOLD"
    assert report["surface_topology"]["checks"]["watertight"] is False
    assert report["surface_topology"]["open_edge_count"] == 3
    assert (tmp_path / "out" / "boundary_groups_manifest.json").is_file()


def test_missing_explicit_required_patch_is_hold():
    points = np.asarray(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]], dtype=float
    )
    triangles = np.asarray([[0, 2, 1], [0, 1, 3], [1, 2, 3], [2, 0, 3]], dtype=int)
    report = M.classify(points, triangles, {
        "required_groups": ["gate_missing"],
        "gates": [],
        "vents": [],
        "holes": [],
    })
    assert report["status"] == "HOLD"
    assert report["checks"]["empty_required_groups"] == ["gate_missing"]
