from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from derive_weldline_front_collision import derive_weldline_front_collision


def _history_from_arrival_steps(arrival_step: list[int], n_times: int) -> np.ndarray:
    alpha = np.zeros((n_times, len(arrival_step)), dtype=float)
    for cell, first_step in enumerate(arrival_step):
        alpha[first_step:, cell] = 1.0
    return alpha


def _fields(times: np.ndarray, centres: np.ndarray, velocity_by_cell: np.ndarray):
    n_times = len(times)
    n_cells = len(centres)
    velocity = np.repeat(velocity_by_cell[None, :, :], n_times, axis=0)
    temperature = np.asarray(
        [[500.0 + 10.0 * time + cell for cell in range(n_cells)] for time in times],
        dtype=float,
    )
    pressure = np.asarray(
        [[1.0e6 + 1000.0 * time + cell for cell in range(n_cells)] for time in times],
        dtype=float,
    )
    return velocity, temperature, pressure


def test_one_direction_chain_does_not_create_a_collision_candidate():
    times = np.arange(5.0)
    centres = np.asarray([[float(cell), 0.0, 0.0] for cell in range(5)])
    alpha = _history_from_arrival_steps([0, 1, 2, 3, 4], len(times))
    velocity, temperature, pressure = _fields(
        times, centres, np.tile([1.0, 0.0, 0.0], (len(centres), 1))
    )

    result = derive_weldline_front_collision(
        alpha,
        times,
        [0, 1, 2, 3],
        [1, 2, 3, 4],
        centres,
        velocity,
        temperature,
        pressure,
    )

    assert result["status"] == "FIELD_DERIVED_COLLISION_CANDIDATE"
    assert result["calibration"] == "UNCALIBRATED"
    assert result["candidate_count"] == 0
    assert result["persistent_cell_ids"] == []
    assert not np.asarray(result["persistent_union_map"], dtype=bool).any()


def test_opposing_y_fronts_collide_and_persist_after_fill_completion():
    # 0 -> 1 -> 4 <- 3 <- 2, followed by 4 -> 5.  Cells 1 and 3 arrive
    # together with opposing velocity directions, so cell 4 is the merge.
    times = np.arange(4.0)
    centres = np.asarray(
        [
            [-2.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [2.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    alpha = _history_from_arrival_steps([0, 1, 0, 1, 2, 3], len(times))
    velocity_by_cell = np.asarray(
        [
            [1.0, 0.0, 0.0],
            [1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [-1.0, 0.0, 0.0],
            [0.0, 1.0, 0.0],
            [0.0, 1.0, 0.0],
        ]
    )
    velocity, temperature, pressure = _fields(times, centres, velocity_by_cell)

    result = derive_weldline_front_collision(
        alpha,
        times,
        [0, 2, 1, 3, 4],
        [1, 3, 4, 4, 5],
        centres,
        velocity,
        temperature,
        pressure,
    )

    assert result["candidate_count"] == 1
    collision = result["candidates"][0]
    assert collision["cell_id"] == 4
    assert collision["collision_angle_deg"] == pytest.approx(180.0)
    assert collision["arrival_time_delta_s"] == pytest.approx(0.0)
    assert collision["collision_time_s"] == pytest.approx(1.5)
    assert collision["temperature_K"] == pytest.approx(519.0)
    assert collision["pressure_Pa"] == pytest.approx(1_001_504.0)
    assert set(collision["incoming_cell_ids"]) == {1, 3}
    assert collision["direction_sources"] == [
        "velocity_at_source_arrival",
        "velocity_at_source_arrival",
    ]

    instantaneous = np.asarray(result["instantaneous_collision_map"], dtype=bool)
    persistent = np.asarray(result["persistent_union_map"], dtype=bool)
    assert instantaneous[:, 4].tolist() == [False, False, True, False]
    assert persistent[:, 4].tolist() == [False, False, True, True]
    assert result["persistent_cell_ids"] == [4]
    assert alpha[-1].tolist() == [1.0] * 6  # fully filled yet candidate remains visible


def test_zero_velocity_uses_mesh_direction_without_strength_claims():
    times = np.arange(3.0)
    centres = np.asarray([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    alpha = _history_from_arrival_steps([0, 0, 1], len(times))
    velocity = np.zeros((len(times), len(centres), 3), dtype=float)
    temperature = np.full((len(times), len(centres)), 500.0)
    pressure = np.full((len(times), len(centres)), 2.0e6)

    result = derive_weldline_front_collision(
        alpha, times, [0, 1], [2, 2], centres, velocity, temperature, pressure
    )

    assert result["candidate_count"] == 1
    assert result["candidates"][0]["direction_sources"] == [
        "cell_graph_geometry",
        "cell_graph_geometry",
    ]
    assert result["strength_prediction"] is False
    assert result["validated_manufacturing_result"] is False
    assert result["claim_scope"] == "LOCATION_CANDIDATE_ONLY"


def test_simultaneous_initial_gate_blob_is_not_a_collision():
    times = np.arange(2.0)
    centres = np.asarray([[-1.0, 0.0, 0.0], [1.0, 0.0, 0.0], [0.0, 0.0, 0.0]])
    alpha = np.ones((len(times), len(centres)), dtype=float)
    velocity = np.zeros((len(times), len(centres), 3), dtype=float)
    temperature = np.full((len(times), len(centres)), 500.0)
    pressure = np.full((len(times), len(centres)), 2.0e6)

    result = derive_weldline_front_collision(
        alpha, times, [0, 1], [2, 2], centres, velocity, temperature, pressure
    )

    assert result["candidate_count"] == 0
    assert result["persistent_cell_ids"] == []


def test_rejects_non_monotone_time_or_unbounded_alpha():
    centres = np.asarray([[0.0, 0.0, 0.0], [1.0, 0.0, 0.0]])
    velocity = np.zeros((2, 2, 3), dtype=float)
    temperature = np.full((2, 2), 500.0)
    pressure = np.full((2, 2), 1.0e6)
    with pytest.raises(ValueError, match="strictly increasing"):
        derive_weldline_front_collision(
            [[1.0, 0.0], [1.0, 1.0]],
            [0.0, 0.0],
            [0],
            [1],
            centres,
            velocity,
            temperature,
            pressure,
        )
    with pytest.raises(ValueError, match="bounded numerical tolerance"):
        derive_weldline_front_collision(
            [[1.0, 0.0], [1.0, 1.1]],
            [0.0, 1.0],
            [0],
            [1],
            centres,
            velocity,
            temperature,
            pressure,
        )
