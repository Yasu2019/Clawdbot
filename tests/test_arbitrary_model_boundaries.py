import json
import sys
from pathlib import Path

import meshio
import numpy as np

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


def test_step_requires_triangulation(tmp_path):
    step = tmp_path / "part.step"
    step.write_text("ISO-10303-21;", encoding="ascii")
    try:
        M.load_tri_surface(step)
    except ValueError as exc:
        assert "triangulation" in str(exc)
    else:
        raise AssertionError("STEP should require explicit triangulation in this runner")
