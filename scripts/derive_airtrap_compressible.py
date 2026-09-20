"""Derive geometry-dependent compressed-air-trap evidence from OpenFOAM.

The detector follows gas-connected components on the actual owner/neighbour
cell graph.  A component is a trapped-gas *candidate* only after the resolved
polymer front disconnects it from every explicitly named vent face.  Pressure,
temperature and density histories are audited at the same OpenFOAM times, and
the vent gas-mass flux is integrated when a written ``rhoPhi.air``,
``alphaRhoPhi.air``, ``rhoPhi`` or ``phi`` field is available.

This is deliberately an uncalibrated screening result.  It does not assign a
defect probability and does not claim sub-cell bubble nucleation, coalescence,
or fully coupled gas/polymer thermodynamics.
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
from typing import Any, Sequence

import numpy as np


SCHEMA = "clawstack.airtrap.compressible_connectivity.v1"
SCREENING_STATUS = "FIELD_DERIVED_COMPRESSIBLE_AIRTRAP_SCREENING"
HOLD_STATUS = "HOLD"
CALIBRATION_CLASS = "UNCALIBRATED_SCREENING"

_FLOAT = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?"
_DIMENSIONS = {
    "alpha": "0 0 0 0 0 0 0",
    "p": "1 -1 -2 0 0 0 0",
    "T": "0 0 0 1 0 0 0",
    "rho": "1 -3 0 0 0 0 0",
    "mass_flux": "1 0 -1 0 0 0 0",
    "volume_flux": "0 3 -1 0 0 0 0",
}


def _finite_array(name: str, values: Any, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def _true_runs(mask: np.ndarray) -> list[list[int]]:
    """Encode a Boolean cell map as inclusive zero-based index ranges."""
    return _index_runs(np.flatnonzero(np.asarray(mask, dtype=bool)))


def _index_runs(indices: Sequence[int] | np.ndarray) -> list[list[int]]:
    """Encode sorted unique zero-based indices without allocating a mesh mask."""
    indices = np.asarray(indices, dtype=int)
    if not len(indices):
        return []
    if indices.ndim != 1 or np.any(np.diff(indices) <= 0):
        indices = np.unique(indices)
    runs: list[list[int]] = []
    start = previous = int(indices[0])
    for raw in indices[1:]:
        value = int(raw)
        if value != previous + 1:
            runs.append([start, previous])
            start = value
        previous = value
    runs.append([start, previous])
    return runs


def _cell_components(
    active: np.ndarray,
    owner: np.ndarray,
    neighbour: np.ndarray,
) -> list[np.ndarray]:
    """Return connected active-cell components in deterministic cell order."""
    n_cells = len(active)
    adjacency: list[list[int]] = [[] for _ in range(n_cells)]
    for left, right in zip(owner.tolist(), neighbour.tolist()):
        if active[left] and active[right]:
            adjacency[left].append(right)
            adjacency[right].append(left)
    visited = np.zeros(n_cells, dtype=bool)
    components: list[np.ndarray] = []
    for seed in np.flatnonzero(active):
        if visited[seed]:
            continue
        stack = [int(seed)]
        visited[seed] = True
        cells: list[int] = []
        while stack:
            cell = stack.pop()
            cells.append(cell)
            for adjacent in adjacency[cell]:
                if not visited[adjacent]:
                    visited[adjacent] = True
                    stack.append(adjacent)
        components.append(np.asarray(sorted(cells), dtype=int))
    return components


def _validate_inputs(
    alpha: Any,
    pressure: Any,
    temperature: Any,
    density: Any,
    time_s: Any,
    owner: Any,
    neighbour: Any,
    cell_volumes_m3: Any,
    vent_face_cells: Any,
    *,
    alpha_bound_tolerance: float,
) -> tuple[np.ndarray, ...]:
    times = _finite_array("time_s", time_s)
    if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0.0):
        raise ValueError("time_s must contain at least two strictly increasing values")
    alpha_values = _finite_array("alpha", alpha)
    if alpha_values.ndim != 2 or alpha_values.shape[0] != len(times) or alpha_values.shape[1] == 0:
        raise ValueError("alpha must have shape (n_times, n_cells) with at least one cell")
    n_times, n_cells = alpha_values.shape
    if np.any(alpha_values < -alpha_bound_tolerance) or np.any(
        alpha_values > 1.0 + alpha_bound_tolerance
    ):
        raise ValueError("alpha lies outside its bounded numerical tolerance")
    alpha_values = np.clip(alpha_values, 0.0, 1.0)

    pressure_values = _finite_array("p", pressure, (n_times, n_cells))
    temperature_values = _finite_array("T", temperature, (n_times, n_cells))
    density_values = _finite_array("rho", density, (n_times, n_cells))
    if np.any(pressure_values <= 0.0):
        raise ValueError("absolute p must be positive")
    if np.any(temperature_values <= 0.0):
        raise ValueError("T must be positive Kelvin")
    if np.any(density_values <= 0.0):
        raise ValueError("rho must be positive")

    owners = np.asarray(owner, dtype=int)
    neighbours = np.asarray(neighbour, dtype=int)
    if owners.ndim != 1 or neighbours.ndim != 1 or owners.shape != neighbours.shape:
        raise ValueError("owner and neighbour must be equal-length internal-face arrays")
    if len(owners) and (
        np.any(owners < 0)
        or np.any(neighbours < 0)
        or np.any(owners >= n_cells)
        or np.any(neighbours >= n_cells)
        or np.any(owners == neighbours)
    ):
        raise ValueError("owner/neighbour contain invalid cell indices")

    volumes = _finite_array("cell_volumes_m3", cell_volumes_m3, (n_cells,))
    if np.any(volumes <= 0.0):
        raise ValueError("cell volumes must be positive")
    vent_cells = np.asarray(vent_face_cells, dtype=int)
    if vent_cells.ndim != 1 or not len(vent_cells):
        raise ValueError("at least one explicit vent boundary face is required")
    if np.any(vent_cells < 0) or np.any(vent_cells >= n_cells):
        raise ValueError("vent face owner cell is outside the mesh")
    return (
        alpha_values,
        pressure_values,
        temperature_values,
        density_values,
        times,
        owners,
        neighbours,
        volumes,
        vent_cells,
    )


def derive_airtrap_compressible(
    alpha: Sequence[Sequence[float]],
    p: Sequence[Sequence[float]],
    T: Sequence[Sequence[float]],
    rho: Sequence[Sequence[float]],
    time_s: Sequence[float],
    owner: Sequence[int],
    neighbour: Sequence[int],
    cell_volumes_m3: Sequence[float],
    vent_face_cells: Sequence[int],
    vent_gas_mass_flux_kg_s: Sequence[Sequence[float]] | None,
    *,
    gas_fraction_threshold: float = 0.5,
    persistence_frames: int = 2,
    gas_specific_R_J_kgK: float = 287.05,
    reference_pressure_Pa: float = 101_325.0,
    alpha_bound_tolerance: float = 1.0e-6,
    vent_flux_method: str = "unspecified",
    vent_flux_phase_exact: bool = False,
) -> dict[str, Any]:
    """Track vent-connected and isolated gas components through real fields.

    ``vent_gas_mass_flux_kg_s`` is signed positive out of the domain and has
    one column per explicit vent face.  Passing ``None`` preserves topology
    diagnostics but intentionally returns ``HOLD`` because the vent-flow audit
    is incomplete.
    """
    if not 0.0 < gas_fraction_threshold < 1.0:
        raise ValueError("gas_fraction_threshold must lie in (0,1)")
    if isinstance(persistence_frames, bool) or not isinstance(persistence_frames, (int, np.integer)) or persistence_frames < 1:
        raise ValueError("persistence_frames must be a positive integer")
    if not math.isfinite(gas_specific_R_J_kgK) or gas_specific_R_J_kgK <= 0.0:
        raise ValueError("gas_specific_R_J_kgK must be positive")
    if not math.isfinite(reference_pressure_Pa) or reference_pressure_Pa <= 0.0:
        raise ValueError("reference_pressure_Pa must be positive")

    (
        alpha_values,
        pressure_values,
        temperature_values,
        density_values,
        times,
        owners,
        neighbours,
        volumes,
        vent_cells,
    ) = _validate_inputs(
        alpha,
        p,
        T,
        rho,
        time_s,
        owner,
        neighbour,
        cell_volumes_m3,
        vent_face_cells,
        alpha_bound_tolerance=alpha_bound_tolerance,
    )
    n_times, n_cells = alpha_values.shape

    hold_reasons: list[str] = []
    flux_values: np.ndarray | None
    if vent_gas_mass_flux_kg_s is None:
        flux_values = None
        hold_reasons.append("VENT_GAS_MASS_FLUX_MISSING")
    else:
        flux_values = _finite_array("vent_gas_mass_flux_kg_s", vent_gas_mass_flux_kg_s)
        if flux_values.shape != (n_times, len(vent_cells)):
            raise ValueError(
                "vent_gas_mass_flux_kg_s must have shape "
                f"{(n_times, len(vent_cells))}, got {flux_values.shape}"
            )

    current_trapped = np.zeros((n_times, n_cells), dtype=bool)
    persistent_now = np.zeros((n_times, n_cells), dtype=bool)
    persistent_ever = np.zeros((n_times, n_cells), dtype=bool)
    frames: list[dict[str, Any]] = []
    previous_tracks: dict[int, set[int]] = {}
    track_state: dict[int, dict[str, Any]] = {}
    next_track_id = 0

    gas_fraction_all = 1.0 - alpha_values
    ideal_gas_density = pressure_values / (gas_specific_R_J_kgK * temperature_values)
    total_gas_mass = np.sum(gas_fraction_all * ideal_gas_density * volumes[None, :], axis=1)
    total_gas_volume = np.sum(gas_fraction_all * volumes[None, :], axis=1)
    total_mixture_mass = np.sum(density_values * volumes[None, :], axis=1)

    if flux_values is not None:
        outward_rate = np.sum(np.maximum(flux_values, 0.0), axis=1)
        inward_rate = np.sum(np.maximum(-flux_values, 0.0), axis=1)
        net_outward_rate = np.sum(flux_values, axis=1)
        cumulative_outward = np.zeros(n_times, dtype=float)
        cumulative_inward = np.zeros(n_times, dtype=float)
        cumulative_net = np.zeros(n_times, dtype=float)
        for index in range(1, n_times):
            dt = float(times[index] - times[index - 1])
            cumulative_outward[index] = cumulative_outward[index - 1] + 0.5 * dt * (
                outward_rate[index - 1] + outward_rate[index]
            )
            cumulative_inward[index] = cumulative_inward[index - 1] + 0.5 * dt * (
                inward_rate[index - 1] + inward_rate[index]
            )
            cumulative_net[index] = cumulative_net[index - 1] + 0.5 * dt * (
                net_outward_rate[index - 1] + net_outward_rate[index]
            )
    else:
        outward_rate = inward_rate = net_outward_rate = None
        cumulative_outward = cumulative_inward = cumulative_net = None

    for time_index, time_value in enumerate(times):
        gas_fraction = gas_fraction_all[time_index]
        active = gas_fraction >= gas_fraction_threshold
        components = _cell_components(active, owners, neighbours)
        vent_active_cells = set(int(value) for value in vent_cells if active[value])

        # Match components to the immediately preceding frame by maximum cell
        # overlap.  Greedy one-to-one assignment gives deterministic split and
        # merge handling without pretending to solve a population balance.
        candidates: list[tuple[int, int, int]] = []
        component_sets = [set(int(value) for value in component) for component in components]
        previous_cell_track = np.full(n_cells, -1, dtype=int)
        for track_id, previous_cells in previous_tracks.items():
            if previous_cells:
                previous_cell_track[np.fromiter(previous_cells, dtype=int)] = track_id
        for component_index, cells in enumerate(component_sets):
            previous_ids = previous_cell_track[components[component_index]]
            previous_ids = previous_ids[previous_ids >= 0]
            if len(previous_ids):
                track_ids, overlap_counts = np.unique(previous_ids, return_counts=True)
                candidates.extend(
                    (-int(overlap), int(track_id), component_index)
                    for track_id, overlap in zip(track_ids, overlap_counts)
                )
        candidates.sort()
        assigned_tracks: dict[int, int] = {}
        used_tracks: set[int] = set()
        for _, track_id, component_index in candidates:
            if component_index not in assigned_tracks and track_id not in used_tracks:
                assigned_tracks[component_index] = track_id
                used_tracks.add(track_id)
        for component_index in range(len(components)):
            if component_index not in assigned_tracks:
                assigned_tracks[component_index] = next_track_id
                next_track_id += 1

        component_rows: list[dict[str, Any]] = []
        next_previous: dict[int, set[int]] = {}
        for component_index, component in enumerate(components):
            cells = component_sets[component_index]
            track_id = assigned_tracks[component_index]
            next_previous[track_id] = cells
            connected = bool(cells & vent_active_cells)
            trapped = not connected
            state = track_state.setdefault(
                track_id,
                {
                    "track_id": track_id,
                    "first_time_s": float(time_value),
                    "last_time_s": float(time_value),
                    "observed_frames": 0,
                    "trapped_frames": 0,
                    "maximum_consecutive_trapped_frames": 0,
                    "current_consecutive_trapped_frames": 0,
                    "ever_vent_connected": False,
                    "ever_persistent": False,
                },
            )
            state["last_time_s"] = float(time_value)
            state["observed_frames"] += 1
            state["ever_vent_connected"] = bool(state["ever_vent_connected"] or connected)
            if trapped:
                state["trapped_frames"] += 1
                state["current_consecutive_trapped_frames"] += 1
                current_trapped[time_index, component] = True
            else:
                state["current_consecutive_trapped_frames"] = 0
            state["maximum_consecutive_trapped_frames"] = max(
                int(state["maximum_consecutive_trapped_frames"]),
                int(state["current_consecutive_trapped_frames"]),
            )
            persistent = trapped and state["current_consecutive_trapped_frames"] >= persistence_frames
            if persistent:
                state["ever_persistent"] = True
                persistent_now[time_index, component] = True

            weights = gas_fraction[component] * volumes[component]
            gas_volume = float(np.sum(weights))
            if gas_volume <= 0.0:
                raise ValueError("active gas component has nonpositive gas volume")
            mean_p = float(np.dot(pressure_values[time_index, component], weights) / gas_volume)
            mean_T = float(np.dot(temperature_values[time_index, component], weights) / gas_volume)
            gas_mass = float(
                np.dot(ideal_gas_density[time_index, component], weights)
            )
            component_rows.append(
                {
                    "component_index": component_index,
                    "track_id": track_id,
                    "classification": (
                        "VENT_CONNECTED_GAS_PATH" if connected else "ISOLATED_GAS_COMPONENT_CANDIDATE"
                    ),
                    "vent_connected": connected,
                    "persistent_candidate": persistent,
                    "cell_count": int(len(component)),
                    "cell_index_ranges": _index_runs(component),
                    "cell_ids_preview": [int(value) for value in component[:20]],
                    "cell_ids_preview_truncated": bool(len(component) > 20),
                    "geometric_capacity_volume_m3": float(np.sum(volumes[component])),
                    "gas_volume_m3": gas_volume,
                    "ideal_gas_reconstructed_mass_kg": gas_mass,
                    "mixture_mass_in_component_cells_kg": float(
                        np.dot(density_values[time_index, component], volumes[component])
                    ),
                    "mean_pressure_Pa": mean_p,
                    "maximum_pressure_Pa": float(np.max(pressure_values[time_index, component])),
                    "mean_temperature_K": mean_T,
                    "pressure_ratio_to_reference": mean_p / reference_pressure_Pa,
                    "current_consecutive_trapped_frames": int(
                        state["current_consecutive_trapped_frames"]
                    ),
                }
            )
        previous_tracks = next_previous
        if time_index:
            persistent_ever[time_index] = persistent_ever[time_index - 1]
        persistent_ever[time_index] |= persistent_now[time_index]

        frame: dict[str, Any] = {
            "time_s": float(time_value),
            "gas_active_cell_count": int(np.count_nonzero(active)),
            "component_count": len(component_rows),
            "vent_connected_component_count": sum(row["vent_connected"] for row in component_rows),
            "isolated_component_count": sum(not row["vent_connected"] for row in component_rows),
            "persistent_isolated_component_count": sum(
                row["persistent_candidate"] for row in component_rows
            ),
            "current_trapped_cell_ranges": _true_runs(current_trapped[time_index]),
            "current_persistent_cell_ranges": _true_runs(persistent_now[time_index]),
            "ever_persistent_cell_ranges": _true_runs(persistent_ever[time_index]),
            "total_gas_volume_m3": float(total_gas_volume[time_index]),
            "total_ideal_gas_reconstructed_mass_kg": float(total_gas_mass[time_index]),
            "total_mixture_mass_kg": float(total_mixture_mass[time_index]),
            "components": component_rows,
        }
        if flux_values is not None:
            frame["vent_gas_mass_flux"] = {
                "outward_kg_s": float(outward_rate[time_index]),
                "inward_kg_s": float(inward_rate[time_index]),
                "net_outward_kg_s": float(net_outward_rate[time_index]),
                "cumulative_outward_kg": float(cumulative_outward[time_index]),
                "cumulative_inward_kg": float(cumulative_inward[time_index]),
                "cumulative_net_outward_kg": float(cumulative_net[time_index]),
                "vent_only_mass_residual_kg": float(
                    total_gas_mass[time_index]
                    + cumulative_net[time_index]
                    - total_gas_mass[0]
                ),
            }
        frames.append(frame)

    persistent_tracks = [
        dict(state)
        for _, state in sorted(track_state.items())
        if bool(state["ever_persistent"])
    ]
    final_persistent_tracks = [
        row["track_id"]
        for row in frames[-1]["components"]
        if row["persistent_candidate"]
    ]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": HOLD_STATUS if hold_reasons else SCREENING_STATUS,
        "calibration": CALIBRATION_CLASS,
        "claim_scope": "GEOMETRY_DEPENDENT_PERSISTENT_TRAPPED_GAS_COMPONENT_CANDIDATES",
        "probability_prediction": False,
        "validated_manufacturing_result": False,
        "fully_coupled_two_phase_gas_model": False,
        "absence_of_candidates_proves_no_defect": False,
        "method": "vof_gas_components_on_owner_neighbour_graph_with_explicit_vent_faces",
        "hold_reasons": hold_reasons,
        "units": {
            "time": "s",
            "volume": "m3",
            "pressure": "Pa_absolute",
            "temperature": "K",
            "mass": "kg",
            "mass_flux": "kg/s_positive_outward",
        },
        "parameters": {
            "gas_fraction_threshold": float(gas_fraction_threshold),
            "persistence_frames": int(persistence_frames),
            "gas_specific_R_J_kgK": float(gas_specific_R_J_kgK),
            "reference_pressure_Pa": float(reference_pressure_Pa),
        },
        "mesh": {
            "cell_count": n_cells,
            "internal_face_count": int(len(owners)),
            "vent_face_count": int(len(vent_cells)),
            "vent_owner_cell_count": int(len(np.unique(vent_cells))),
            "cell_volume_total_m3": float(np.sum(volumes)),
        },
        "vent_flux_audit": {
            "available": flux_values is not None,
            "method": vent_flux_method,
            "phase_flux_exact": bool(vent_flux_phase_exact),
            "integration": "trapezoidal_in_physical_time" if flux_values is not None else None,
            "scope": "explicit_vent_patches_only",
        },
        "time_s": [float(value) for value in times],
        "frames": frames,
        "persistent_track_count": len(persistent_tracks),
        "persistent_tracks": persistent_tracks,
        "final_persistent_track_ids": final_persistent_tracks,
        "ever_persistent_cell_ranges": _true_runs(persistent_ever[-1]),
        "limitations": [
            "A VOF threshold defines resolved gas connectivity; sub-cell bubbles and films are not resolved.",
            "Gas mass is reconstructed with p/(R*T); rho is retained as an independent mixture-mass audit.",
            "The positive OpenFOAM p field is required and interpreted as absolute pressure; gauge-pressure input is invalid.",
            "rhoPhi and phi require a gas-fraction reconstruction unless a gas-specific mass-flux field exists.",
            "Component overlap tracking is diagnostic and is not bubble nucleation/coalescence physics.",
            "Vent-only mass residual is not a whole-boundary conservation proof.",
            "Measured material, vent-discharge and gas-generation calibration is still required.",
        ],
        "_array_evidence": {
            "current_trapped": current_trapped,
            "persistent_now": persistent_now,
            "persistent_ever": persistent_ever,
            "total_gas_mass_kg": total_gas_mass,
            "total_gas_volume_m3": total_gas_volume,
            "total_mixture_mass_kg": total_mixture_mass,
            "vent_gas_mass_flux_kg_s": flux_values,
        },
    }
    return report


def _read_text(path: Path) -> str:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8", errors="strict") as stream:
            return stream.read()
    return path.read_text(encoding="utf-8", errors="strict")


def _strip_comments(text: str) -> str:
    return re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)


def _field_path(directory: Path, name: str) -> Path | None:
    direct = directory / name
    compressed = directory / f"{name}.gz"
    if direct.is_file():
        return direct
    if compressed.is_file():
        return compressed
    return None


def _dimensions(text: str) -> str:
    match = re.search(r"\bdimensions\s*\[([^]]+)\]\s*;", text)
    if not match:
        raise ValueError("OpenFOAM field has no dimensions entry")
    return " ".join(match.group(1).split())


def _balanced_block(text: str, brace_index: int) -> str:
    if brace_index >= len(text) or text[brace_index] != "{":
        raise ValueError("balanced block must start at an opening brace")
    depth = 0
    for index in range(brace_index, len(text)):
        if text[index] == "{":
            depth += 1
        elif text[index] == "}":
            depth -= 1
            if depth == 0:
                return text[brace_index + 1 : index]
    raise ValueError("unterminated OpenFOAM dictionary block")


def _named_block(text: str, name: str) -> str | None:
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*\{{", text)
    if not match:
        return None
    brace = text.find("{", match.start())
    return _balanced_block(text, brace)


def _scalar_values_after_keyword(block: str, keyword: str, expected_count: int) -> np.ndarray | None:
    nonuniform = re.search(
        rf"\b{re.escape(keyword)}\s+nonuniform\s+List<scalar>\s+(\d+)\s*\(\s*(.*?)\s*\)\s*;",
        block,
        re.S,
    )
    if nonuniform:
        count = int(nonuniform.group(1))
        values = np.asarray([float(value) for value in re.findall(_FLOAT, nonuniform.group(2))])
        if count != expected_count or len(values) != count:
            raise ValueError(f"{keyword} nonuniform count differs from patch/cell count")
        return values
    uniform = re.search(rf"\b{re.escape(keyword)}\s+uniform\s+({_FLOAT})\s*;", block)
    if uniform:
        return np.full(expected_count, float(uniform.group(1)), dtype=float)
    return None


def _read_internal_scalar(path: Path, expected_count: int, expected_dimensions: str) -> np.ndarray:
    text = _strip_comments(_read_text(path))
    if _dimensions(text) != expected_dimensions:
        raise ValueError(f"unexpected dimensions in {path}: {_dimensions(text)}")
    values = _scalar_values_after_keyword(text, "internalField", expected_count)
    if values is None or not np.isfinite(values).all():
        raise ValueError(f"unsupported/non-finite internal scalar field: {path}")
    return values


def _read_patch_scalar(path: Path, patch: str, expected_count: int) -> np.ndarray | None:
    text = _strip_comments(_read_text(path))
    boundary = _named_block(text, "boundaryField")
    if boundary is None:
        return None
    patch_block = _named_block(boundary, patch)
    if patch_block is None:
        return None
    values = _scalar_values_after_keyword(patch_block, "value", expected_count)
    if values is not None and not np.isfinite(values).all():
        raise ValueError(f"non-finite patch values in {path}:{patch}")
    return values


def _read_mesh_list(path: Path, kind: str) -> Any:
    text = _strip_comments(_read_text(path))
    text = re.sub(r"\bFoamFile\s*\{.*?\}", "", text, flags=re.S)
    # ``$`` under multiline mode can stop at the first point/face closing
    # parenthesis.  Anchor at the true end of the list so nested ``(...)``
    # entries remain inside the captured body.
    match = re.search(r"^\s*(\d+)\s*\n\s*\(\s*(.*)\s*\)\s*;?\s*\Z", text, re.S)
    if not match:
        raise ValueError(f"unsupported ASCII OpenFOAM {kind} list: {path}")
    count = int(match.group(1))
    body = match.group(2)
    if kind == "points":
        rows = re.findall(r"\(([^()]*)\)", body)
        values = np.asarray([[float(value) for value in row.split()] for row in rows], dtype=float)
        if values.shape != (count, 3) or not np.isfinite(values).all():
            raise ValueError(f"invalid points list: {path}")
        return values
    if kind == "faces":
        rows = re.findall(r"(\d+)\s*\(([^()]*)\)", body)
        faces = [[int(value) for value in row.split()] for _, row in rows]
        if len(faces) != count or any(len(face) != int(rows[i][0]) or len(face) < 3 for i, face in enumerate(faces)):
            raise ValueError(f"invalid faces list: {path}")
        return faces
    values = np.asarray([int(value) for value in re.findall(r"[-+]?\d+", body)], dtype=int)
    if len(values) != count:
        raise ValueError(f"invalid label list: {path}")
    return values


def _boundary_patches(path: Path) -> dict[str, dict[str, Any]]:
    text = _strip_comments(_read_text(path))
    text = re.sub(r"\bFoamFile\s*\{.*?\}", "", text, flags=re.S)
    list_start = re.search(r"(?m)^\s*\d+\s*\n\s*\(", text)
    if not list_start:
        raise ValueError(f"unsupported boundary list: {path}")
    body = text[list_start.end() :]
    patches: dict[str, dict[str, Any]] = {}
    position = 0
    header = re.compile(r"(?m)^\s*([^\s{}();]+)\s*\{")
    while True:
        match = header.search(body, position)
        if not match:
            break
        name = match.group(1)
        brace = body.find("{", match.start())
        block = _balanced_block(body, brace)
        n_faces = re.search(r"\bnFaces\s+(\d+)\s*;", block)
        start_face = re.search(r"\bstartFace\s+(\d+)\s*;", block)
        patch_type = re.search(r"\btype\s+([^;\s]+)\s*;", block)
        if not n_faces or not start_face:
            raise ValueError(f"boundary patch {name} lacks nFaces/startFace")
        patches[name] = {
            "nFaces": int(n_faces.group(1)),
            "startFace": int(start_face.group(1)),
            "type": patch_type.group(1) if patch_type else "unspecified",
        }
        # Continue after this exact balanced block, not inside nested entries.
        depth = 0
        end = brace
        for end in range(brace, len(body)):
            if body[end] == "{":
                depth += 1
            elif body[end] == "}":
                depth -= 1
                if depth == 0:
                    break
        position = end + 1
    if not patches:
        raise ValueError(f"no boundary patches parsed: {path}")
    return patches


def _poly_mesh_geometry(mesh: Path) -> dict[str, Any]:
    points = _read_mesh_list(mesh / "points", "points")
    faces: list[list[int]] = _read_mesh_list(mesh / "faces", "faces")
    owner_all = _read_mesh_list(mesh / "owner", "owner")
    neighbour = _read_mesh_list(mesh / "neighbour", "neighbour")
    if len(owner_all) != len(faces) or len(neighbour) > len(owner_all):
        raise ValueError("owner/neighbour counts do not match faces")
    if not len(owner_all):
        raise ValueError("mesh has no faces")
    n_cells = int(max(np.max(owner_all), np.max(neighbour) if len(neighbour) else -1) + 1)
    if n_cells <= 0 or np.any(owner_all < 0) or np.any(owner_all >= n_cells):
        raise ValueError("invalid owner cell labels")
    if len(neighbour) and (
        np.any(neighbour < 0) or np.any(neighbour >= n_cells) or np.any(owner_all[: len(neighbour)] == neighbour)
    ):
        raise ValueError("invalid neighbour cell labels")
    if any(min(face) < 0 or max(face) >= len(points) or len(set(face)) < 3 for face in faces):
        raise ValueError("face references invalid point labels")

    cell_faces: list[list[tuple[int, int]]] = [[] for _ in range(n_cells)]
    for face_index, owner_cell in enumerate(owner_all):
        cell_faces[int(owner_cell)].append((face_index, 1))
        if face_index < len(neighbour):
            cell_faces[int(neighbour[face_index])].append((face_index, -1))
    volumes = np.zeros(n_cells, dtype=float)
    for cell, references in enumerate(cell_faces):
        vertex_ids = sorted({vertex for face_index, _ in references for vertex in faces[face_index]})
        if not references or len(vertex_ids) < 4:
            raise ValueError(f"cell {cell} is not a closed three-dimensional polyhedron")
        centre = np.mean(points[vertex_ids], axis=0)
        signed_volume = 0.0
        for face_index, direction in references:
            vertices = faces[face_index]
            if direction < 0:
                vertices = list(reversed(vertices))
            first = points[vertices[0]] - centre
            for index in range(1, len(vertices) - 1):
                second = points[vertices[index]] - centre
                third = points[vertices[index + 1]] - centre
                signed_volume += float(np.dot(first, np.cross(second, third))) / 6.0
        if not math.isfinite(signed_volume) or signed_volume <= 0.0:
            raise ValueError(f"cell {cell} has nonpositive oriented volume {signed_volume}")
        volumes[cell] = signed_volume
    return {
        "points": points,
        "faces": faces,
        "owner_all": owner_all,
        "owner_internal": owner_all[: len(neighbour)],
        "neighbour": neighbour,
        "cell_volumes_m3": volumes,
        "patches": _boundary_patches(mesh / "boundary"),
    }


def _numeric_time_dirs(case: Path) -> list[tuple[float, Path]]:
    rows: list[tuple[float, Path]] = []
    for child in case.iterdir():
        if not child.is_dir():
            continue
        try:
            value = float(child.name)
        except ValueError:
            continue
        if math.isfinite(value) and value >= 0.0:
            rows.append((value, child))
    rows.sort(key=lambda row: row[0])
    if len(rows) < 2:
        raise ValueError("at least two numeric OpenFOAM time directories are required")
    if any(rows[index][0] <= rows[index - 1][0] for index in range(1, len(rows))):
        raise ValueError("OpenFOAM time directories are not strictly increasing")
    return rows


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_openfoam_airtrap_history(
    case_dir: str | Path,
    vent_patches: Sequence[str],
    *,
    gas_specific_R_J_kgK: float = 287.05,
) -> dict[str, Any]:
    """Load same-time fields, mesh topology and explicit vent phase flux."""
    case = Path(case_dir).resolve()
    if not case.is_dir():
        raise FileNotFoundError(f"OpenFOAM case directory not found: {case}")
    if not vent_patches or any(not str(name).strip() for name in vent_patches):
        raise ValueError("one or more explicit --vent-patch names are required")
    if len(set(vent_patches)) != len(vent_patches):
        raise ValueError("vent patch names must be unique")
    if not math.isfinite(gas_specific_R_J_kgK) or gas_specific_R_J_kgK <= 0.0:
        raise ValueError("gas_specific_R_J_kgK must be positive")
    mesh_dir = case / "constant" / "polyMesh"
    geometry = _poly_mesh_geometry(mesh_dir)
    n_cells = len(geometry["cell_volumes_m3"])
    owner_all = geometry["owner_all"]
    patch_rows: list[dict[str, Any]] = []
    vent_face_cells: list[int] = []
    vent_face_patch: list[str] = []
    selected_face_indices: set[int] = set()
    for patch_name in vent_patches:
        if patch_name not in geometry["patches"]:
            raise ValueError(f"explicit vent patch not found in mesh boundary: {patch_name}")
        patch = geometry["patches"][patch_name]
        start = int(patch["startFace"])
        count = int(patch["nFaces"])
        if count <= 0 or start < len(geometry["neighbour"]) or start + count > len(owner_all):
            raise ValueError(f"invalid boundary-face range for vent patch {patch_name}")
        patch_type = str(patch.get("type", "unspecified")).lower()
        if "wall" in patch_type or patch_type in {
            "empty",
            "symmetry",
            "symmetryplane",
            "wedge",
            "cyclic",
        }:
            raise ValueError(f"vent patch {patch_name} has non-exhaust boundary type {patch_type}")
        face_indices = set(range(start, start + count))
        if selected_face_indices & face_indices:
            raise ValueError(f"selected vent patch face ranges overlap at {patch_name}")
        selected_face_indices.update(face_indices)
        cells = owner_all[start : start + count]
        vent_face_cells.extend(int(value) for value in cells)
        vent_face_patch.extend([patch_name] * count)
        patch_rows.append({"name": patch_name, **patch, "owner_cells": [int(value) for value in cells]})

    times: list[float] = []
    alpha_rows: list[np.ndarray] = []
    pressure_rows: list[np.ndarray] = []
    temperature_rows: list[np.ndarray] = []
    density_rows: list[np.ndarray] = []
    flux_rows: list[np.ndarray] = []
    flux_methods: list[str] = []
    phase_exact_rows: list[bool] = []
    source_hashes: dict[str, str] = {}
    patch_flux_rows: list[dict[str, Any]] = []

    for time_value, directory in _numeric_time_dirs(case):
        paths = {
            "alpha": _field_path(directory, "alpha.polymer") or _field_path(directory, "alpha"),
            "p": _field_path(directory, "p"),
            "T": _field_path(directory, "T"),
            "rho": _field_path(directory, "rho"),
        }
        missing = [name for name, path in paths.items() if path is None]
        if missing:
            raise FileNotFoundError(f"time {directory.name} lacks required fields: {missing}")
        alpha = _read_internal_scalar(paths["alpha"], n_cells, _DIMENSIONS["alpha"])
        pressure = _read_internal_scalar(paths["p"], n_cells, _DIMENSIONS["p"])
        temperature = _read_internal_scalar(paths["T"], n_cells, _DIMENSIONS["T"])
        density = _read_internal_scalar(paths["rho"], n_cells, _DIMENSIONS["rho"])

        flux_path = next(
            (
                candidate
                for name in ("rhoPhi.air", "alphaRhoPhi.air", "rhoPhi", "phi")
                if (candidate := _field_path(directory, name)) is not None
            ),
            None,
        )
        if flux_path is None:
            raise FileNotFoundError(
                f"time {directory.name} lacks rhoPhi.air/alphaRhoPhi.air/rhoPhi/phi vent flux"
            )
        flux_name = flux_path.name[:-3] if flux_path.suffix == ".gz" else flux_path.name
        flux_text = _strip_comments(_read_text(flux_path))
        dimensions = _dimensions(flux_text)
        if flux_name in ("rhoPhi.air", "alphaRhoPhi.air"):
            if dimensions != _DIMENSIONS["mass_flux"]:
                raise ValueError(f"gas-specific flux has wrong dimensions: {flux_path}")
            flux_method = f"{flux_name}_written_gas_mass_flux"
            phase_exact = True
        elif flux_name == "rhoPhi":
            if dimensions != _DIMENSIONS["mass_flux"]:
                raise ValueError(f"rhoPhi has wrong dimensions: {flux_path}")
            flux_method = "rhoPhi_times_vent_gas_fraction"
            phase_exact = False
        else:
            if dimensions != _DIMENSIONS["volume_flux"]:
                raise ValueError(f"phi has wrong dimensions: {flux_path}")
            flux_method = "phi_times_ideal_gas_density_and_vent_gas_fraction"
            phase_exact = False

        face_flux: list[float] = []
        patch_flux: dict[str, Any] = {}
        face_offset = 0
        for patch in patch_rows:
            name = str(patch["name"])
            count = int(patch["nFaces"])
            owner_cells = np.asarray(patch["owner_cells"], dtype=int)
            values = _read_patch_scalar(flux_path, name, count)
            if values is None:
                raise ValueError(f"written vent flux values missing for {directory.name}:{name}")
            if not phase_exact:
                alpha_face = _read_patch_scalar(paths["alpha"], name, count)
                alpha_basis = "written_alpha_patch"
                if alpha_face is None:
                    alpha_face = alpha[owner_cells]
                    alpha_basis = "vent_owner_cell_alpha_fallback"
                if np.any(alpha_face < -1.0e-6) or np.any(alpha_face > 1.0 + 1.0e-6):
                    raise ValueError(f"vent alpha lies outside bounded tolerance: {directory.name}:{name}")
                gas_fraction_face = np.clip(1.0 - alpha_face, 0.0, 1.0)
                if flux_name == "rhoPhi":
                    values = values * gas_fraction_face
                    density_basis = None
                else:
                    p_face = _read_patch_scalar(paths["p"], name, count)
                    T_face = _read_patch_scalar(paths["T"], name, count)
                    if p_face is None:
                        p_face = pressure[owner_cells]
                    if T_face is None:
                        T_face = temperature[owner_cells]
                    if np.any(p_face <= 0.0) or np.any(T_face <= 0.0):
                        raise ValueError(f"nonpositive vent p/T prevents phi conversion: {directory.name}:{name}")
                    gas_density_face = p_face / (gas_specific_R_J_kgK * T_face)
                    values = values * gas_fraction_face * gas_density_face
                    density_basis = f"ideal_gas_p_over_{gas_specific_R_J_kgK:.12g}T"
            else:
                alpha_basis = None
                density_basis = None
            face_flux.extend(float(value) for value in values)
            patch_flux[name] = {
                "face_offset": face_offset,
                "face_count": count,
                "net_outward_gas_mass_flux_kg_s": float(np.sum(values)),
                "outward_gas_mass_flux_kg_s": float(np.sum(np.maximum(values, 0.0))),
                "inward_gas_mass_flux_kg_s": float(np.sum(np.maximum(-values, 0.0))),
                "alpha_basis": alpha_basis,
                "density_basis": density_basis,
            }
            face_offset += count

        times.append(time_value)
        alpha_rows.append(alpha)
        pressure_rows.append(pressure)
        temperature_rows.append(temperature)
        density_rows.append(density)
        flux_rows.append(np.asarray(face_flux, dtype=float))
        flux_methods.append(flux_method)
        phase_exact_rows.append(phase_exact)
        patch_flux_rows.append({"time_s": time_value, "patches": patch_flux})
        for key, path in paths.items():
            source_hashes[f"{directory.name}/{key}:{path.name}"] = _sha256(path)
        source_hashes[f"{directory.name}/vent_flux:{flux_path.name}"] = _sha256(flux_path)

    if len(set(flux_methods)) != 1 or len(set(phase_exact_rows)) != 1:
        raise ValueError(f"vent flux source/method changes across time: {flux_methods}")
    return {
        "case_dir": str(case),
        "time_s": np.asarray(times, dtype=float),
        "alpha": np.stack(alpha_rows),
        "p": np.stack(pressure_rows),
        "T": np.stack(temperature_rows),
        "rho": np.stack(density_rows),
        "owner": geometry["owner_internal"],
        "neighbour": geometry["neighbour"],
        "cell_volumes_m3": geometry["cell_volumes_m3"],
        "vent_face_cells": np.asarray(vent_face_cells, dtype=int),
        "vent_face_patch": vent_face_patch,
        "vent_gas_mass_flux_kg_s": np.stack(flux_rows),
        "vent_flux_method": flux_methods[0],
        "vent_flux_phase_exact": phase_exact_rows[0],
        "vent_patches": patch_rows,
        "patch_flux_history": patch_flux_rows,
        "source_sha256": source_hashes,
        "mesh_source_sha256": {
            name: _sha256(mesh_dir / name)
            for name in ("points", "faces", "owner", "neighbour", "boundary")
        },
    }


def _json_report(result: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in result.items() if key != "_array_evidence"}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case_dir", type=Path)
    parser.add_argument("--vent-patch", action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--gas-fraction-threshold", type=float, default=0.5)
    parser.add_argument("--persistence-frames", type=int, default=2)
    parser.add_argument("--gas-specific-R", type=float, default=287.05)
    parser.add_argument("--reference-pressure-Pa", type=float, default=101_325.0)
    args = parser.parse_args(argv)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise FileExistsError(args.output)

    try:
        loaded = load_openfoam_airtrap_history(
            args.case_dir,
            args.vent_patch,
            gas_specific_R_J_kgK=args.gas_specific_R,
        )
        result = derive_airtrap_compressible(
            loaded["alpha"],
            loaded["p"],
            loaded["T"],
            loaded["rho"],
            loaded["time_s"],
            loaded["owner"],
            loaded["neighbour"],
            loaded["cell_volumes_m3"],
            loaded["vent_face_cells"],
            loaded["vent_gas_mass_flux_kg_s"],
            gas_fraction_threshold=args.gas_fraction_threshold,
            persistence_frames=args.persistence_frames,
            gas_specific_R_J_kgK=args.gas_specific_R,
            reference_pressure_Pa=args.reference_pressure_Pa,
            vent_flux_method=loaded["vent_flux_method"],
            vent_flux_phase_exact=loaded["vent_flux_phase_exact"],
        )
        result["source"] = {
            "case_dir": loaded["case_dir"],
            "vent_patches": loaded["vent_patches"],
            "vent_face_patch": loaded["vent_face_patch"],
            "patch_flux_history": loaded["patch_flux_history"],
            "field_sha256": loaded["source_sha256"],
            "mesh_sha256": loaded["mesh_source_sha256"],
        }
    except (OSError, ValueError, KeyError, TypeError) as error:
        result = {
            "schema": SCHEMA,
            "status": HOLD_STATUS,
            "calibration": CALIBRATION_CLASS,
            "claim_scope": "NO_AIRTRAP_RESULT",
            "probability_prediction": False,
            "validated_manufacturing_result": False,
            "hold_reasons": [f"INVALID_OR_MISSING_OPENFOAM_EVIDENCE: {error}"],
            "limitations": [
                "No candidate map is emitted when required fields, topology, explicit vents, or vent flux are missing."
            ],
        }

    arrays = result.get("_array_evidence")
    if arrays is not None:
        npz_path = args.output.with_suffix(".npz")
        if npz_path.exists():
            raise FileExistsError(npz_path)
        np.savez_compressed(
            npz_path,
            **{key: value for key, value in arrays.items() if value is not None},
        )
        result["array_evidence"] = {
            "path": npz_path.name,
            "sha256": _sha256(npz_path),
            "keys": sorted(key for key, value in arrays.items() if value is not None),
        }
    report = _json_report(result)
    with args.output.open("x", encoding="utf-8") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    print(
        json.dumps(
            {
                "status": report["status"],
                "persistent_track_count": report.get("persistent_track_count", 0),
                "output": str(args.output.resolve()),
            },
            ensure_ascii=False,
        )
    )
    return 0 if report["status"] == SCREENING_STATUS else 2


if __name__ == "__main__":
    raise SystemExit(main())
