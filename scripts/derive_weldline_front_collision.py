"""Derive persistent weld-line collision candidates from OpenFOAM histories.

The detector uses the first time each cell crosses an ``alpha`` threshold and
the internal-face cell graph.  A cell is marked only when at least two recent
predecessor cells feed it from sufficiently different incident directions at
nearly the same time.  The result is deliberately labelled as a field-derived,
uncalibrated *candidate*: it is neither a weld-strength prediction nor a
validated manufacturing result.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any, Sequence

import numpy as np


RESULT_CLASS = "FIELD_DERIVED_COLLISION_CANDIDATE"
CALIBRATION_CLASS = "UNCALIBRATED"


def _as_finite_array(name: str, values: Any, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def _validate_history(
    alpha: Any,
    time_s: Any,
    owner: Any,
    neighbour: Any,
    cell_centres: Any,
    velocity: Any,
    temperature: Any,
    pressure: Any,
    *,
    alpha_bound_tolerance: float,
) -> tuple[np.ndarray, ...]:
    times = _as_finite_array("time_s", time_s)
    if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0.0):
        raise ValueError("time_s must contain at least two strictly increasing values")

    alpha_values = _as_finite_array("alpha", alpha)
    if alpha_values.ndim != 2 or alpha_values.shape[0] != len(times):
        raise ValueError("alpha must have shape (n_times, n_cells)")
    n_times, n_cells = alpha_values.shape
    if n_cells == 0:
        raise ValueError("alpha history has no cells")
    if np.any(alpha_values < -alpha_bound_tolerance) or np.any(alpha_values > 1.0 + alpha_bound_tolerance):
        raise ValueError("alpha lies outside its bounded numerical tolerance")
    # MULES can leave tiny round-off overshoots.  Clipping only those tolerated
    # values avoids changing any physically meaningful first-arrival crossing.
    alpha_values = np.clip(alpha_values, 0.0, 1.0)

    centres = _as_finite_array("cell_centres", cell_centres, (n_cells, 3))
    velocity_values = _as_finite_array("U", velocity, (n_times, n_cells, 3))
    temperature_values = _as_finite_array("T", temperature, (n_times, n_cells))
    pressure_values = _as_finite_array("p", pressure, (n_times, n_cells))
    if np.any(temperature_values <= 0.0):
        raise ValueError("T must be positive in Kelvin")

    owners = np.asarray(owner, dtype=int)
    neighbours = np.asarray(neighbour, dtype=int)
    if owners.ndim != 1 or neighbours.ndim != 1 or owners.shape != neighbours.shape:
        raise ValueError("owner and neighbour must be equal-length internal-face lists")
    if len(owners) == 0:
        raise ValueError("owner/neighbour contain no internal faces")
    if (
        np.any(owners < 0)
        or np.any(neighbours < 0)
        or np.any(owners >= n_cells)
        or np.any(neighbours >= n_cells)
        or np.any(owners == neighbours)
    ):
        raise ValueError("owner/neighbour contain invalid cell indices")
    return (
        alpha_values,
        times,
        owners,
        neighbours,
        centres,
        velocity_values,
        temperature_values,
        pressure_values,
    )


def _first_arrival_fields(
    alpha: np.ndarray,
    times: np.ndarray,
    velocity: np.ndarray,
    temperature: np.ndarray,
    pressure: np.ndarray,
    threshold: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Linearly interpolate threshold time and fields at the first crossing."""
    n_times, n_cells = alpha.shape
    arrival = np.full(n_cells, np.inf, dtype=float)
    crossing_index = np.full(n_cells, -1, dtype=int)
    u_arrival = np.full((n_cells, 3), np.nan, dtype=float)
    t_arrival = np.full(n_cells, np.nan, dtype=float)
    p_arrival = np.full(n_cells, np.nan, dtype=float)

    for cell in range(n_cells):
        hits = np.flatnonzero(alpha[:, cell] >= threshold)
        if not len(hits):
            continue
        upper = int(hits[0])
        crossing_index[cell] = upper
        if upper == 0:
            fraction = 0.0
            lower = 0
        else:
            lower = upper - 1
            a0 = float(alpha[lower, cell])
            a1 = float(alpha[upper, cell])
            if a1 > a0:
                fraction = float(np.clip((threshold - a0) / (a1 - a0), 0.0, 1.0))
            else:
                # The first stored value above the threshold is still evidence
                # of arrival, but a flat/decreasing interval cannot be safely
                # interpolated backwards.
                fraction = 1.0
        arrival[cell] = float(times[lower] + fraction * (times[upper] - times[lower]))
        u_arrival[cell] = velocity[lower, cell] + fraction * (
            velocity[upper, cell] - velocity[lower, cell]
        )
        t_arrival[cell] = float(
            temperature[lower, cell]
            + fraction * (temperature[upper, cell] - temperature[lower, cell])
        )
        p_arrival[cell] = float(
            pressure[lower, cell]
            + fraction * (pressure[upper, cell] - pressure[lower, cell])
        )
    return arrival, crossing_index, u_arrival, t_arrival, p_arrival


def _adjacency(n_cells: int, owner: np.ndarray, neighbour: np.ndarray) -> list[list[int]]:
    adjacent: list[list[int]] = [[] for _ in range(n_cells)]
    for left, right in zip(owner.tolist(), neighbour.tolist()):
        adjacent[left].append(right)
        adjacent[right].append(left)
    # Duplicate internal faces would otherwise count one incoming front twice.
    return [sorted(set(row)) for row in adjacent]


def _incident_direction(
    source: int,
    target: int,
    centres: np.ndarray,
    u_arrival: np.ndarray,
    *,
    velocity_epsilon: float,
    min_inward_cosine: float,
) -> tuple[np.ndarray, str] | None:
    geometric = centres[target] - centres[source]
    distance = float(np.linalg.norm(geometric))
    if distance <= 0.0:
        return None
    geometric /= distance
    local_u = u_arrival[source]
    speed = float(np.linalg.norm(local_u))
    if speed <= velocity_epsilon:
        return geometric, "cell_graph_geometry"
    direction = local_u / speed
    if float(np.dot(direction, geometric)) < min_inward_cosine:
        # A neighbour whose resolved flow points away from the target is not an
        # incoming branch, even if its alpha threshold was crossed recently.
        return None
    return direction, "velocity_at_source_arrival"


def derive_weldline_front_collision(
    alpha: Sequence[Sequence[float]],
    time_s: Sequence[float],
    owner: Sequence[int],
    neighbour: Sequence[int],
    cell_centres: Sequence[Sequence[float]],
    U: Sequence[Sequence[Sequence[float]]],
    T: Sequence[Sequence[float]],
    p: Sequence[Sequence[float]],
    *,
    alpha_threshold: float = 0.5,
    min_collision_angle_deg: float = 100.0,
    max_arrival_time_delta_s: float | None = None,
    max_predecessor_lag_s: float | None = None,
    velocity_epsilon: float = 1.0e-12,
    min_inward_cosine: float = 0.05,
    alpha_bound_tolerance: float = 1.0e-6,
) -> dict[str, Any]:
    """Return persistent front-collision candidates from cell-field histories.

    ``owner``/``neighbour`` must describe internal cell-to-cell faces.  Incident
    directions use source-cell velocity when it demonstrably points toward the
    target; a zero-velocity history falls back to cell-graph geometry.  Two
    incoming branches must have close first-arrival times and an angle above
    ``min_collision_angle_deg``.
    """
    if not 0.0 < alpha_threshold <= 1.0:
        raise ValueError("alpha_threshold must lie in (0, 1]")
    if not 0.0 < min_collision_angle_deg <= 180.0:
        raise ValueError("min_collision_angle_deg must lie in (0, 180]")
    if not -1.0 <= min_inward_cosine <= 1.0:
        raise ValueError("min_inward_cosine must lie in [-1, 1]")
    if velocity_epsilon < 0.0 or alpha_bound_tolerance < 0.0:
        raise ValueError("numerical tolerances must be nonnegative")

    (
        alpha_values,
        times,
        owners,
        neighbours,
        centres,
        velocity_values,
        temperature_values,
        pressure_values,
    ) = _validate_history(
        alpha,
        time_s,
        owner,
        neighbour,
        cell_centres,
        U,
        T,
        p,
        alpha_bound_tolerance=alpha_bound_tolerance,
    )
    typical_dt = float(np.median(np.diff(times)))
    if max_arrival_time_delta_s is None:
        max_arrival_time_delta_s = 1.5 * typical_dt
    if max_predecessor_lag_s is None:
        max_predecessor_lag_s = 1.5 * typical_dt
    if max_arrival_time_delta_s < 0.0 or max_predecessor_lag_s <= 0.0:
        raise ValueError("arrival tolerances must be nonnegative, with positive predecessor lag")

    arrival, crossing_index, u_arrival, t_arrival, p_arrival = _first_arrival_fields(
        alpha_values,
        times,
        velocity_values,
        temperature_values,
        pressure_values,
        alpha_threshold,
    )
    adjacent = _adjacency(alpha_values.shape[1], owners, neighbours)
    candidates: list[dict[str, Any]] = []
    time_epsilon = max(1.0e-12, typical_dt * 1.0e-9)

    for target, target_time in enumerate(arrival):
        if not math.isfinite(float(target_time)):
            continue
        incident: list[dict[str, Any]] = []
        for source in adjacent[target]:
            source_time = float(arrival[source])
            if not math.isfinite(source_time):
                continue
            lag = float(target_time) - source_time
            # A true predecessor must arrive strictly before the target.  Cells
            # belonging to the same initially filled gate blob often share an
            # identical first-arrival time and can surround one another in an
            # unstructured mesh; accepting zero lag would turn that initial
            # condition into a false weld event.
            if lag <= time_epsilon or lag > max_predecessor_lag_s + time_epsilon:
                continue
            direction_data = _incident_direction(
                source,
                target,
                centres,
                u_arrival,
                velocity_epsilon=velocity_epsilon,
                min_inward_cosine=min_inward_cosine,
            )
            if direction_data is None:
                continue
            direction, direction_source = direction_data
            incident.append(
                {
                    "cell_id": int(source),
                    "arrival_time_s": source_time,
                    "lag_to_collision_s": lag,
                    "direction": direction,
                    "direction_source": direction_source,
                }
            )

        best_pair: tuple[float, float, dict[str, Any], dict[str, Any]] | None = None
        for left_index in range(len(incident)):
            for right_index in range(left_index + 1, len(incident)):
                left = incident[left_index]
                right = incident[right_index]
                delta = abs(float(left["arrival_time_s"]) - float(right["arrival_time_s"]))
                if delta > max_arrival_time_delta_s + time_epsilon:
                    continue
                cosine = float(
                    np.clip(np.dot(left["direction"], right["direction"]), -1.0, 1.0)
                )
                angle = math.degrees(math.acos(cosine))
                if angle + 1.0e-10 < min_collision_angle_deg:
                    continue
                if best_pair is None or (angle, -delta) > (best_pair[0], -best_pair[1]):
                    best_pair = (angle, delta, left, right)
        if best_pair is None:
            continue

        angle, delta, left, right = best_pair
        event_index = int(np.searchsorted(times, target_time, side="left"))
        event_index = min(max(event_index, 0), len(times) - 1)
        candidates.append(
            {
                "cell_id": int(target),
                "cell_index_base": 0,
                "position": [float(v) for v in centres[target]],
                "collision_time_s": float(target_time),
                "stored_time_index": event_index,
                "collision_angle_deg": float(angle),
                "arrival_time_delta_s": float(delta),
                "temperature_K": float(t_arrival[target]),
                "pressure_Pa": float(p_arrival[target]),
                "incoming_cell_ids": [int(left["cell_id"]), int(right["cell_id"])],
                "incoming_arrival_time_s": [
                    float(left["arrival_time_s"]),
                    float(right["arrival_time_s"]),
                ],
                "incoming_directions": [
                    [float(v) for v in left["direction"]],
                    [float(v) for v in right["direction"]],
                ],
                "direction_sources": [left["direction_source"], right["direction_source"]],
            }
        )

    candidates.sort(key=lambda row: (row["collision_time_s"], row["cell_id"]))
    instantaneous = np.zeros((len(times), alpha_values.shape[1]), dtype=bool)
    for row in candidates:
        instantaneous[int(row["stored_time_index"]), int(row["cell_id"])] = True
    persistent = np.maximum.accumulate(instantaneous, axis=0)
    arrival_json = [float(value) if math.isfinite(float(value)) else None for value in arrival]

    return {
        "schema": "clawstack.weldline.front_collision.v1",
        "status": RESULT_CLASS,
        "calibration": CALIBRATION_CLASS,
        "claim_scope": "LOCATION_CANDIDATE_ONLY",
        "strength_prediction": False,
        "validated_manufacturing_result": False,
        "method": "alpha_first_arrival_internal_face_multi_direction_collision",
        "units": {"time": "s", "temperature": "K", "pressure": "Pa", "position": "input_mesh_units"},
        "parameters": {
            "alpha_threshold": float(alpha_threshold),
            "min_collision_angle_deg": float(min_collision_angle_deg),
            "max_arrival_time_delta_s": float(max_arrival_time_delta_s),
            "max_predecessor_lag_s": float(max_predecessor_lag_s),
            "min_inward_cosine": float(min_inward_cosine),
        },
        "time_s": [float(value) for value in times],
        "first_arrival_time_s": arrival_json,
        "first_arrival_stored_index": [int(value) for value in crossing_index],
        "candidate_count": len(candidates),
        "candidates": candidates,
        "instantaneous_collision_map": instantaneous.tolist(),
        "persistent_union_map": persistent.tolist(),
        "persistent_cell_ids": np.flatnonzero(persistent[-1]).astype(int).tolist(),
    }


def _read_openfoam_label_list(path: Path) -> np.ndarray:
    """Read an ASCII OpenFOAM labelList such as owner or neighbour."""
    text = path.read_text(encoding="utf-8", errors="strict")
    pattern = re.compile(r"(?m)^\s*(\d+)\s*\n\s*\(\s*([\s\S]*?)\s*\)\s*;?")
    for match in pattern.finditer(text):
        count = int(match.group(1))
        values = [int(value) for value in re.findall(r"[-+]?\d+", match.group(2))]
        if len(values) == count:
            return np.asarray(values, dtype=int)
    raise ValueError(f"unsupported ASCII OpenFOAM labelList: {path}")


def load_openfoam_case(case_dir: str | Path) -> dict[str, Any]:
    """Load fields with the existing strict multiphysics history parser."""
    case = Path(case_dir).resolve()
    try:
        from cae_multiphysics_contract import read_openfoam_history, read_vector_field
    except ImportError:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from cae_multiphysics_contract import read_openfoam_history, read_vector_field

    history = read_openfoam_history(case)
    snapshots = history["snapshots"]
    centre_candidates = (case / "constant" / "C", case / "0" / "C")
    centre_path = next((path for path in centre_candidates if path.is_file()), None)
    if centre_path is None:
        raise FileNotFoundError("cell-centre field C is required (run postProcess -func writeCellCentres)")
    centres = read_vector_field(centre_path)
    mesh = case / "constant" / "polyMesh"
    owner_all = _read_openfoam_label_list(mesh / "owner")
    neighbour = _read_openfoam_label_list(mesh / "neighbour")
    if len(owner_all) < len(neighbour):
        raise ValueError("owner list is shorter than neighbour list")
    owner = owner_all[: len(neighbour)]
    if len(centres) != int(history["cell_count"]):
        raise ValueError("cell-centre count differs from field history")
    return {
        "case_dir": str(case),
        "time_s": history["time_s"],
        "alpha": np.stack([row["fields"]["alpha"] for row in snapshots]),
        "U": np.stack([row["fields"]["U"] for row in snapshots]),
        "T": np.stack([row["fields"]["T"] for row in snapshots]),
        "p": np.stack([row["fields"]["p"] for row in snapshots]),
        "owner": owner,
        "neighbour": neighbour,
        "cell_centres": centres,
        "source_fields": history["source_fields"],
        "source_sha256": history["source_sha256"],
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Derive uncalibrated, persistent weld-front collision candidates from an OpenFOAM case."
    )
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--alpha-threshold", type=float, default=0.5)
    parser.add_argument("--min-angle-deg", type=float, default=100.0)
    parser.add_argument("--max-arrival-delta-s", type=float)
    parser.add_argument("--max-predecessor-lag-s", type=float)
    args = parser.parse_args(argv)

    loaded = load_openfoam_case(args.case_dir)
    result = derive_weldline_front_collision(
        loaded["alpha"],
        loaded["time_s"],
        loaded["owner"],
        loaded["neighbour"],
        loaded["cell_centres"],
        loaded["U"],
        loaded["T"],
        loaded["p"],
        alpha_threshold=args.alpha_threshold,
        min_collision_angle_deg=args.min_angle_deg,
        max_arrival_time_delta_s=args.max_arrival_delta_s,
        max_predecessor_lag_s=args.max_predecessor_lag_s,
    )
    result["source"] = {
        "case_dir": loaded["case_dir"],
        "source_fields": loaded["source_fields"],
        "source_sha256": loaded["source_sha256"],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "status": result["status"],
                "calibration": result["calibration"],
                "candidate_count": result["candidate_count"],
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
