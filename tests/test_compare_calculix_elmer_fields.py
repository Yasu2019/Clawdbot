import importlib.util
from pathlib import Path

import numpy as np
import pytest


meshio = pytest.importorskip("meshio")
ROOT = Path(__file__).parents[1]
SPEC = importlib.util.spec_from_file_location(
    "compare_calculix_elmer_fields",
    ROOT / "scripts" / "compare_calculix_elmer_fields.py",
)
M = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(M)


POINTS = np.array(
    [[0.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]],
    dtype=float,
)
CELLS = [("tetra", np.array([[0, 1, 2, 3]], dtype=int))]
IDENTITY = {"geometry_id": "g-1", "mesh_id": "m-1", "history_id": "h-1"}


def _fields(scale=1.0):
    displacement = POINTS * 0.001 * scale
    temperature = np.array([350.0, 345.0, 340.0, 335.0]) * scale
    stress = np.array([2.0e6, 2.1e6, 2.2e6, 2.3e6]) * scale
    return {
        "Displacement": displacement,
        "Temperature": temperature,
        "vonMises": stress,
    }


def _write(path: Path, points=POINTS, point_data=None):
    meshio.write(path, meshio.Mesh(points, CELLS, point_data=point_data or _fields()))


def test_identical_fields_pass_as_uncalibrated_screening(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    _write(elmer)

    report = M.compare_vtu_files(ccx, elmer, identity=IDENTITY)

    assert report["status"] == "CROSS_SOLVER_NUMERICAL_PASS_UNCALIBRATED"
    assert report["classification"] == "UNCALIBRATED_SCREENING"
    assert report["failed_checks"] == []
    assert report["same_geometry_mesh_history"] is True


def test_permuted_node_order_is_matched_by_reference_coordinates(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    permutation = np.array([2, 0, 3, 1])
    fields = _fields()
    permuted_fields = {name: values[permutation] for name, values in fields.items()}
    inverse = np.argsort(permutation)
    permuted_cells = [("tetra", inverse[np.array([[0, 1, 2, 3]])])]
    meshio.write(
        elmer,
        meshio.Mesh(POINTS[permutation], permuted_cells, point_data=permuted_fields),
    )

    report = M.compare_vtu_files(ccx, elmer, identity=IDENTITY)

    assert report["status"].startswith("CROSS_SOLVER_NUMERICAL_PASS")
    assert report["mapping"]["maximum_match_distance"] == pytest.approx(0.0)


def test_deformed_elmer_coordinates_are_normalized(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    fields = _fields()
    _write(ccx, point_data=fields)
    _write(elmer, points=POINTS + fields["Displacement"], point_data=fields)

    with pytest.raises(ValueError, match="within tolerance"):
        M.compare_vtu_files(ccx, elmer, identity=IDENTITY)

    report = M.compare_vtu_files(
        ccx, elmer, identity=IDENTITY, elmer_coordinates_deformed=True
    )
    assert report["status"].startswith("CROSS_SOLVER_NUMERICAL_PASS")


def test_field_difference_above_tolerance_is_hold(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    _write(elmer, point_data=_fields(scale=2.0))

    report = M.compare_vtu_files(ccx, elmer, identity=IDENTITY)

    assert report["status"] == "HOLD"
    assert "field.temperature.relative_l2_error" in report["failed_checks"]
    assert "field.von_mises_stress.relative_l2_error" in report["failed_checks"]


def test_missing_required_field_fails_closed(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    fields = _fields()
    fields.pop("vonMises")
    _write(elmer, point_data=fields)

    with pytest.raises(ValueError, match="von_mises_stress"):
        M.compare_vtu_files(ccx, elmer, identity=IDENTITY)


def test_missing_identity_fails_closed(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    _write(elmer)

    with pytest.raises(ValueError, match="history_id"):
        M.compare_vtu_files(
            ccx,
            elmer,
            identity={"geometry_id": "g-1", "mesh_id": "m-1", "history_id": ""},
        )


def test_calibrated_flag_does_not_claim_experimental_validation(tmp_path):
    ccx = tmp_path / "ccx.vtu"
    elmer = tmp_path / "elmer.vtu"
    _write(ccx)
    _write(elmer)

    report = M.compare_vtu_files(ccx, elmer, identity=IDENTITY, calibrated=True)

    assert report["status"] == "CROSS_SOLVER_NUMERICAL_PASS_CALIBRATED_INPUT"
    assert "not agreement with experiment" in report["limitations"][0]
