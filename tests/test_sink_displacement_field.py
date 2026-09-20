from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import math
from pathlib import Path

import numpy as np
import pytest

from scripts.derive_sink_from_displacement import (
    RESULT_CLASSIFICATION,
    derive_sink_field,
    load_ccx_frd_displacement,
)


POINTS = np.asarray(
    [
        [0.0, 0.0, 0.0],
        [-1.0, -1.0, 0.0],
        [1.0, -1.0, 0.0],
        [1.0, 1.0, 0.0],
        [-1.0, 1.0, 0.0],
    ],
    dtype=float,
)
NORMALS = np.tile([0.0, 0.0, 1.0], (len(POINTS), 1))
NEIGHBORS = {
    10: [11, 12, 13, 14],
    11: [12, 13, 14],
    12: [11, 13, 14],
    13: [11, 12, 14],
    14: [11, 12, 13],
}
NODE_IDS = [10, 11, 12, 13, 14]


def _derive(displacement, **kwargs):
    return derive_sink_field(
        POINTS,
        NORMALS,
        displacement,
        node_ids=NODE_IDS,
        neighborhoods=NEIGHBORS,
        length_unit="mm",
        measured_calibration=True,
        **kwargs,
    )


def test_uniform_isotropic_shrink_is_not_reported_as_sink():
    shrink_strain = -0.02
    displacement = shrink_strain * POINTS

    result = _derive(displacement)

    assert result["status"] == "PASS_FIELD_DERIVED"
    assert result["decomposition"]["uniform_isotropic_strain"] == pytest.approx(shrink_strain)
    assert result["surface_depression"]["max_sink_depth_um"] == pytest.approx(0.0, abs=1.0e-9)


def test_rigid_translation_and_rotation_are_not_reported_as_sink():
    angle = math.radians(31.0)
    rotation = np.asarray(
        [
            [math.cos(angle), -math.sin(angle), 0.0],
            [math.sin(angle), math.cos(angle), 0.0],
            [0.0, 0.0, 1.0],
        ]
    )
    translation = np.asarray([5.0, -2.0, 3.0])
    deformed = POINTS @ rotation.T + translation

    result = _derive(deformed - POINTS)

    assert result["surface_depression"]["max_sink_depth_um"] == pytest.approx(0.0, abs=1.0e-8)
    assert result["decomposition"]["rms_residual_m"] == pytest.approx(0.0, abs=1.0e-12)


def test_local_dimple_is_positive_inward_sink_after_global_shrink_removal():
    displacement = -0.01 * POINTS
    displacement[0, 2] -= 0.20  # 0.20 mm inward local depression

    result = _derive(displacement)
    center = result["surface_depression"]["field"][0]

    assert center["sink_depth_mm"] == pytest.approx(0.20, rel=1.0e-10, abs=1.0e-12)
    assert result["surface_depression"]["max_sink_depth_um"] == pytest.approx(200.0)
    assert center["residual_normal_displacement_m"] < center["local_reference_normal_displacement_m"]


def test_display_50x_changes_visualization_only_not_physical_sink():
    displacement = np.zeros_like(POINTS)
    displacement[0, 2] = -0.08

    physical = _derive(displacement, display_scale=1.0)
    exaggerated = _derive(displacement, display_scale=50.0)
    p = physical["surface_depression"]["field"][0]
    x50 = exaggerated["surface_depression"]["field"][0]

    assert x50["sink_depth_m"] == pytest.approx(p["sink_depth_m"])
    assert x50["sink_depth_mm"] == pytest.approx(0.08)
    assert x50["display_sink_depth_m"] == pytest.approx(50.0 * p["sink_depth_m"])
    assert exaggerated["visualization"]["physical_metrics_scaled"] is False


def test_explicit_outer_inner_pair_separates_uniform_and_local_thickness_loss():
    points = np.asarray(
        [
            [0.0, 0.0, 1.0], [0.0, 0.0, -1.0],
            [10.0, 0.0, 1.0], [10.0, 0.0, -1.0],
            [0.0, 10.0, 1.0], [0.0, 10.0, -1.0],
            [10.0, 10.0, 1.0], [10.0, 10.0, -1.0],
        ]
    )
    normals = np.asarray([[0.0, 0.0, 1.0], [0.0, 0.0, -1.0]] * 4)
    node_ids = list(range(100, 108))
    displacement = -0.01 * points
    displacement[0, 2] -= 0.10
    result = derive_sink_field(
        points,
        normals,
        displacement,
        node_ids=node_ids,
        opposing_pairs=[(100, 101), (102, 103), (104, 105), (106, 107)],
        length_unit="mm",
        measured_calibration=True,
    )

    pair0 = result["thickness_change"]["field"][0]
    uniform_pairs = result["thickness_change"]["field"][1:]
    assert result["thickness_change"]["valid_pair_count"] == 4
    assert pair0["excess_thickness_loss_mm"] > 0.07
    assert max(pair["excess_thickness_loss_mm"] for pair in uniform_pairs) < pair0["excess_thickness_loss_mm"]
    assert "which face visibly sinks" in result["limitations"][1]


def test_missing_local_context_and_calibration_fail_closed_but_keep_classification():
    result = derive_sink_field(POINTS, NORMALS, np.zeros_like(POINTS), length_unit="mm")

    assert result["status"] == "HOLD"
    assert result["result_classification"] == RESULT_CLASSIFICATION
    assert result["engineering_claim"] == "NONE"
    assert set(result["production_gate"]["hold_reasons"]) == {
        "local_neighborhood_or_inner_outer_mapping_missing",
        "measured_material_and_process_calibration_missing",
    }


def test_invalid_or_sparse_neighborhood_is_hold_not_false_zero():
    result = derive_sink_field(
        POINTS,
        NORMALS,
        np.zeros_like(POINTS),
        node_ids=NODE_IDS,
        neighborhoods={10: [11]},
        length_unit="mm",
        measured_calibration=True,
    )

    assert result["status"] == "HOLD"
    assert result["surface_depression"]["valid_node_count"] == 0
    assert result["surface_depression"]["field"][0]["sink_depth_m"] is None
    assert result["production_gate"]["hold_reasons"] == [
        "local_neighborhood_or_inner_outer_mapping_invalid"
    ]


def test_load_last_ascii_calculix_frd_displacement_block(tmp_path: Path):
    frd = tmp_path / "job.frd"
    frd.write_text(
        "    1PSTEP    1\n"
        " -4  DISP        4    1\n"
        " -5  D1          D2          D3\n"
        " -1         10 1.00000E-03 2.00000E-03 3.00000E-03\n"
        " -3\n"
        "    1PSTEP    2\n"
        " -4  DISP        4    1\n"
        " -5  D1          D2          D3\n"
        " -1         10-4.00000D-03 5.00000D-03-6.00000D-03\n"
        " -1         11 0.00000E+00 0.00000E+00 0.00000E+00\n"
        " -3\n",
        encoding="ascii",
    )

    displacement = load_ccx_frd_displacement(frd)

    assert displacement[10] == pytest.approx((-4.0e-3, 5.0e-3, -6.0e-3))
    assert displacement[11] == pytest.approx((0.0, 0.0, 0.0))
