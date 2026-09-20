"""Conservative reduced void-population transport on one cell/time grid.

The state variables are bubble count density and gas-volume fraction.  Internal
face advection is finite-volume conservative, coalescence removes bubble count
without changing gas volume, and nucleation/growth are recorded as explicit
sources.  Prescribed structural tensile stress and a local void-relaxation
closure modify the source rates on the same cells and time intervals.

This is an offline reduced population model.  It is not direct, iterative,
bidirectional OpenFOAM/CalculiX coupling and therefore cannot release a product
or manufacturing claim.  Virtual coefficients are always classified as
``UNCALIBRATED_SCREENING`` and the production gate remains ``HOLD``.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Sequence

import numpy as np


SCHEMA = "clawstack.void.population.transport.v1"
COUPLING_MODE = "OFFLINE_ONE_WAY"
MECHANISMS = ("nucleation", "growth", "coalescence", "transport", "stress_feedback")


def _finite_array(name: str, values: Any, shape: tuple[int, ...] | None = None) -> np.ndarray:
    array = np.asarray(values, dtype=float)
    if shape is not None and array.shape != shape:
        raise ValueError(f"{name} must have shape {shape}, got {array.shape}")
    if not np.isfinite(array).all():
        raise ValueError(f"{name} contains non-finite values")
    return array


def _interval_field(name: str, values: Any, intervals: int, cells: int) -> np.ndarray:
    """Broadcast a scalar/cell/interval field to ``(intervals, cells)``."""
    array = _finite_array(name, values)
    if array.ndim == 0:
        return np.full((intervals, cells), float(array))
    if array.shape == (cells,):
        return np.broadcast_to(array, (intervals, cells)).copy()
    if array.shape == (intervals, cells):
        return array.copy()
    raise ValueError(
        f"{name} must be scalar, shape ({cells},), or shape ({intervals}, {cells})"
    )


def _integer_array(name: str, values: Any) -> np.ndarray:
    numeric = _finite_array(name, values)
    if numeric.ndim != 1 or np.any(numeric != np.floor(numeric)):
        raise ValueError(f"{name} must be a one-dimensional exact-integer array")
    if np.any(numeric < np.iinfo(np.int64).min) or np.any(numeric > np.iinfo(np.int64).max):
        raise ValueError(f"{name} lies outside int64 range")
    return numeric.astype(np.int64)


def _canonical_sha256(payload: Any) -> str:
    encoded = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _validate_faces(owner: Any, neighbour: Any, cells: int) -> tuple[np.ndarray, np.ndarray]:
    owners = _integer_array("owner", owner)
    neighbours = _integer_array("neighbour", neighbour)
    if owners.ndim != 1 or neighbours.ndim != 1 or owners.shape != neighbours.shape:
        raise ValueError("owner and neighbour must be equal-length one-dimensional arrays")
    if (
        np.any(owners < 0)
        or np.any(neighbours < 0)
        or np.any(owners >= cells)
        or np.any(neighbours >= cells)
        or np.any(owners == neighbours)
    ):
        raise ValueError("owner/neighbour contains an invalid cell index")
    unordered = [tuple(sorted((int(left), int(right)))) for left, right in zip(owners, neighbours)]
    if len(set(unordered)) != len(unordered):
        raise ValueError("duplicate internal face connection")
    return owners, neighbours


def _transport_step(
    count_density: np.ndarray,
    void_fraction: np.ndarray,
    cell_volume: np.ndarray,
    owner: np.ndarray,
    neighbour: np.ndarray,
    face_flux: np.ndarray,
    dt_s: float,
    max_transport_cfl: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    """Apply one positivity-preserving, conservative upwind transport step."""
    outflow = np.zeros_like(cell_volume)
    for left, right, flux in zip(owner, neighbour, face_flux):
        if flux >= 0.0:
            outflow[left] += flux
        else:
            outflow[right] -= flux
    cell_cfl = dt_s * outflow / cell_volume
    peak_cfl = float(np.max(cell_cfl)) if len(cell_cfl) else 0.0
    if peak_cfl > max_transport_cfl * (1.0 + 1.0e-12):
        raise ValueError(
            f"transport CFL {peak_cfl:.9g} exceeds declared limit {max_transport_cfl:.9g}"
        )

    count = count_density * cell_volume
    gas_volume = void_fraction * cell_volume
    count_delta = np.zeros_like(count)
    gas_delta = np.zeros_like(gas_volume)
    for left, right, flux in zip(owner, neighbour, face_flux):
        if flux >= 0.0:
            donor, receiver, flow = int(left), int(right), float(flux)
        else:
            donor, receiver, flow = int(right), int(left), float(-flux)
        moved_count = dt_s * flow * count_density[donor]
        moved_gas = dt_s * flow * void_fraction[donor]
        count_delta[donor] -= moved_count
        count_delta[receiver] += moved_count
        gas_delta[donor] -= moved_gas
        gas_delta[receiver] += moved_gas

    before_count = float(np.sum(count))
    before_gas = float(np.sum(gas_volume))
    count += count_delta
    gas_volume += gas_delta
    tolerance_count = 64.0 * np.finfo(float).eps * max(
        float(np.max(np.abs(count), initial=0.0)), 1.0e-300
    )
    tolerance_gas = 64.0 * np.finfo(float).eps * max(
        float(np.max(np.abs(gas_volume), initial=0.0)), 1.0e-300
    )
    if np.any(count < -tolerance_count) or np.any(gas_volume < -tolerance_gas):
        raise ValueError("transport produced a negative conserved state; reduce the time step")
    count = np.maximum(count, 0.0)
    gas_volume = np.maximum(gas_volume, 0.0)
    return count / cell_volume, gas_volume / cell_volume, {
        "maximum_cfl": peak_cfl,
        "count_balance_error": float(np.sum(count) - before_count),
        "gas_volume_balance_error_m3": float(np.sum(gas_volume) - before_gas),
    }


def _population_sources(
    count_density: np.ndarray,
    void_fraction: np.ndarray,
    initial_void_fraction: np.ndarray,
    cell_volume: np.ndarray,
    dt_s: float,
    base_nucleation_rate: np.ndarray,
    seed_volume_m3: float,
    base_growth_rate: np.ndarray,
    coalescence_kernel: np.ndarray,
    tensile_stress_pa: np.ndarray,
    stress_threshold_pa: float,
    stress_growth_coeff_per_pa_s: float,
    stress_nucleation_coeff_per_m3_s_pa: float,
    void_stress_relaxation_pa_per_fraction: float,
    max_growth_exponent: float,
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    """Apply positive local sources and exact volume-preserving coalescence."""
    relaxed_stress = tensile_stress_pa - void_stress_relaxation_pa_per_fraction * np.maximum(
        void_fraction - initial_void_fraction, 0.0
    )
    stress_excess = np.maximum(relaxed_stress - stress_threshold_pa, 0.0)
    nucleation_rate = base_nucleation_rate + stress_nucleation_coeff_per_m3_s_pa * stress_excess
    growth_rate = base_growth_rate + stress_growth_coeff_per_pa_s * stress_excess
    if np.any(nucleation_rate < 0.0) or np.any(growth_rate < 0.0):
        raise ValueError("effective nucleation and growth rates must remain nonnegative")
    growth_exponent = growth_rate * dt_s
    if np.any(growth_exponent > max_growth_exponent * (1.0 + 1.0e-12)):
        raise ValueError(
            "source time-step limit exceeded by growth exponent; reduce the time interval"
        )

    count_before = count_density * cell_volume
    gas_before = void_fraction * cell_volume

    added_count_density = nucleation_rate * dt_s
    count_density = count_density + added_count_density
    seed_fraction_added = added_count_density * seed_volume_m3
    void_fraction = void_fraction + seed_fraction_added
    gas_after_nucleation = void_fraction * cell_volume

    # Exponential growth is positivity preserving and exposes its exact source
    # contribution for the global gas-volume balance.
    void_fraction = void_fraction * np.exp(growth_exponent)
    gas_after_growth = void_fraction * cell_volume

    count_pre_coalescence = count_density * cell_volume
    # dn/dt = -K n^2 has this exact nonnegative update for constant K.
    count_density = count_density / (1.0 + coalescence_kernel * count_density * dt_s)
    count_after = count_density * cell_volume

    return count_density, void_fraction, {
        "effective_nucleation_rate_per_m3_s": nucleation_rate,
        "effective_growth_rate_per_s": growth_rate,
        "effective_tensile_excess_pa": stress_excess,
        "nucleated_count": float(np.sum(added_count_density * cell_volume)),
        "nucleated_gas_volume_m3": float(np.sum(gas_after_nucleation - gas_before)),
        "growth_gas_volume_m3": float(np.sum(gas_after_growth - gas_after_nucleation)),
        "coalesced_count_removed": float(np.sum(count_pre_coalescence - count_after)),
        "count_before_sources": float(np.sum(count_before)),
        "gas_volume_before_sources_m3": float(np.sum(gas_before)),
    }


def solve_population_transport(
    *,
    time_s: Sequence[float],
    element_ids: Sequence[int],
    cell_volume_m3: Sequence[float],
    owner: Sequence[int],
    neighbour: Sequence[int],
    face_volume_flux_m3_s: Any,
    initial_number_density_per_m3: Sequence[float],
    initial_void_fraction: Sequence[float],
    nucleation_rate_per_m3_s: Any,
    seed_volume_m3: float,
    growth_rate_per_s: Any,
    coalescence_kernel_m3_s: Any,
    hydrostatic_tensile_stress_pa: Any,
    stress_threshold_pa: float,
    stress_growth_coeff_per_pa_s: float,
    stress_nucleation_coeff_per_m3_s_pa: float,
    void_stress_relaxation_pa_per_fraction: float,
    max_void_fraction: float,
    max_transport_cfl: float = 0.8,
    max_growth_exponent: float = 0.25,
    data_status: str = "VIRTUAL",
    coupling_mode: str = COUPLING_MODE,
) -> dict[str, Any]:
    """Solve all five reduced mechanisms on one explicit grid and time axis."""
    times = _finite_array("time_s", time_s)
    if times.ndim != 1 or len(times) < 2 or np.any(np.diff(times) <= 0.0):
        raise ValueError("time_s must contain at least two strictly increasing values")
    ids = _integer_array("element_ids", element_ids)
    if not len(ids) or np.any(ids <= 0) or len(set(ids.tolist())) != len(ids):
        raise ValueError("element_ids must be a nonempty unique positive-integer list")
    cells = len(ids)
    intervals = len(times) - 1
    volumes = _finite_array("cell_volume_m3", cell_volume_m3, (cells,))
    if np.any(volumes <= 0.0):
        raise ValueError("cell volumes must be positive")
    owners, neighbours = _validate_faces(owner, neighbour, cells)
    face_flux = _finite_array(
        "face_volume_flux_m3_s", face_volume_flux_m3_s, (intervals, len(owners))
    )
    count_density = _finite_array(
        "initial_number_density_per_m3", initial_number_density_per_m3, (cells,)
    )
    void_fraction = _finite_array("initial_void_fraction", initial_void_fraction, (cells,))
    if np.any(count_density < 0.0) or np.any(void_fraction < 0.0):
        raise ValueError("initial population state must be nonnegative")
    if np.any((void_fraction > 0.0) != (count_density > 0.0)):
        raise ValueError("initial bubble count and gas volume must be present together")

    scalar_controls = {
        "seed_volume_m3": seed_volume_m3,
        "stress_threshold_pa": stress_threshold_pa,
        "stress_growth_coeff_per_pa_s": stress_growth_coeff_per_pa_s,
        "stress_nucleation_coeff_per_m3_s_pa": stress_nucleation_coeff_per_m3_s_pa,
        "void_stress_relaxation_pa_per_fraction": void_stress_relaxation_pa_per_fraction,
        "max_void_fraction": max_void_fraction,
        "max_transport_cfl": max_transport_cfl,
        "max_growth_exponent": max_growth_exponent,
    }
    if not np.isfinite(list(scalar_controls.values())).all():
        raise ValueError("model controls must be finite")
    if seed_volume_m3 < 0.0 or stress_threshold_pa < 0.0:
        raise ValueError("seed volume and stress threshold must be nonnegative")
    if min(
        stress_growth_coeff_per_pa_s,
        stress_nucleation_coeff_per_m3_s_pa,
        void_stress_relaxation_pa_per_fraction,
    ) < 0.0:
        raise ValueError("stress feedback coefficients must be nonnegative")
    if not 0.0 < max_void_fraction < 1.0 or np.any(void_fraction > max_void_fraction):
        raise ValueError("void fraction must lie within the declared physical bound")
    if not 0.0 < max_transport_cfl <= 1.0 or max_growth_exponent <= 0.0:
        raise ValueError("invalid time-step controls")
    if data_status not in ("VIRTUAL", "MEASURED"):
        raise ValueError("data_status must be VIRTUAL or MEASURED")
    if coupling_mode != COUPLING_MODE:
        raise ValueError(
            "this solver implements OFFLINE_ONE_WAY only; direct bidirectional coupling cannot be claimed"
        )

    nucleation = _interval_field(
        "nucleation_rate_per_m3_s", nucleation_rate_per_m3_s, intervals, cells
    )
    growth = _interval_field("growth_rate_per_s", growth_rate_per_s, intervals, cells)
    coalescence = _interval_field(
        "coalescence_kernel_m3_s", coalescence_kernel_m3_s, intervals, cells
    )
    if np.any(nucleation < 0.0) or np.any(growth < 0.0) or np.any(coalescence < 0.0):
        raise ValueError("base mechanism rates must be nonnegative")
    stress = _finite_array(
        "hydrostatic_tensile_stress_pa", hydrostatic_tensile_stress_pa, (len(times), cells)
    )

    initial_count_density = count_density.copy()
    initial_void = void_fraction.copy()
    initial_total_count = float(np.sum(count_density * volumes))
    initial_total_gas = float(np.sum(void_fraction * volumes))
    frames: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    mechanism_history = {
        "nucleation": [np.zeros(cells)],
        "growth": [np.zeros(cells)],
        "coalescence": [np.zeros(cells)],
        "transport": [np.zeros(cells)],
        "stress_feedback": [np.zeros(cells)],
    }

    def append_frame(time_value: float) -> None:
        count = count_density * volumes
        gas = void_fraction * volumes
        radius = np.zeros(cells)
        active = count > 0.0
        radius[active] = np.cbrt(3.0 * gas[active] / (4.0 * math.pi * count[active]))
        frames.append(
            {
                "time_s": float(time_value),
                "number_density_per_m3": count_density.tolist(),
                "void_fraction": void_fraction.tolist(),
                "mean_bubble_radius_m": radius.tolist(),
                "total_bubble_count": float(np.sum(count)),
                "total_gas_volume_m3": float(np.sum(gas)),
            }
        )

    append_frame(times[0])
    source_count_added = 0.0
    source_gas_added = 0.0
    coalesced_count_removed = 0.0
    maximum_cfl = 0.0
    transport_count_error = 0.0
    transport_gas_error = 0.0

    for interval, dt_s in enumerate(np.diff(times)):
        before_transport_count = count_density * volumes
        count_density, void_fraction, transport_audit = _transport_step(
            count_density,
            void_fraction,
            volumes,
            owners,
            neighbours,
            face_flux[interval],
            float(dt_s),
            max_transport_cfl,
        )
        after_transport_count = count_density * volumes
        transport_cell_delta = after_transport_count - before_transport_count
        tensile_midpoint = 0.5 * (stress[interval] + stress[interval + 1])
        count_density, void_fraction, source_audit = _population_sources(
            count_density,
            void_fraction,
            initial_void,
            volumes,
            float(dt_s),
            nucleation[interval],
            seed_volume_m3,
            growth[interval],
            coalescence[interval],
            tensile_midpoint,
            stress_threshold_pa,
            stress_growth_coeff_per_pa_s,
            stress_nucleation_coeff_per_m3_s_pa,
            void_stress_relaxation_pa_per_fraction,
            max_growth_exponent,
        )
        if not np.isfinite(count_density).all() or not np.isfinite(void_fraction).all():
            raise ValueError("non-finite population state")
        if np.any(count_density < 0.0) or np.any(void_fraction < 0.0):
            raise ValueError("population update violated positivity")
        if np.any(void_fraction > max_void_fraction * (1.0 + 1.0e-12)):
            raise ValueError(
                "population update exceeds maximum_void_fraction; reduce the time step or source"
            )

        maximum_cfl = max(maximum_cfl, transport_audit["maximum_cfl"])
        transport_count_error = max(
            transport_count_error, abs(transport_audit["count_balance_error"])
        )
        transport_gas_error = max(
            transport_gas_error, abs(transport_audit["gas_volume_balance_error_m3"])
        )
        source_count_added += source_audit["nucleated_count"]
        source_gas_added += (
            source_audit["nucleated_gas_volume_m3"]
            + source_audit["growth_gas_volume_m3"]
        )
        coalesced_count_removed += source_audit["coalesced_count_removed"]
        diagnostics.append(
            {
                "interval": interval,
                "start_time_s": float(times[interval]),
                "end_time_s": float(times[interval + 1]),
                "transport": transport_audit,
                "nucleated_count": source_audit["nucleated_count"],
                "nucleated_gas_volume_m3": source_audit["nucleated_gas_volume_m3"],
                "growth_gas_volume_m3": source_audit["growth_gas_volume_m3"],
                "coalesced_count_removed": source_audit["coalesced_count_removed"],
                "maximum_effective_tensile_excess_pa": float(
                    np.max(source_audit["effective_tensile_excess_pa"])
                ),
            }
        )
        mechanism_history["nucleation"].append(
            source_audit["effective_nucleation_rate_per_m3_s"].copy()
        )
        mechanism_history["growth"].append(
            source_audit["effective_growth_rate_per_s"].copy()
        )
        mechanism_history["coalescence"].append(coalescence[interval].copy())
        mechanism_history["transport"].append((transport_cell_delta / volumes / dt_s).copy())
        mechanism_history["stress_feedback"].append(
            source_audit["effective_tensile_excess_pa"].copy()
        )
        append_frame(times[interval + 1])

    final_total_count = frames[-1]["total_bubble_count"]
    final_total_gas = frames[-1]["total_gas_volume_m3"]
    count_residual = (
        final_total_count
        - initial_total_count
        - source_count_added
        + coalesced_count_removed
    )
    gas_residual = final_total_gas - initial_total_gas - source_gas_added
    count_scale = max(
        abs(initial_total_count),
        abs(final_total_count),
        source_count_added,
        coalesced_count_removed,
        1.0e-300,
    )
    gas_scale = max(abs(initial_total_gas), abs(final_total_gas), source_gas_added, 1.0e-300)
    count_relative = abs(count_residual) / count_scale
    gas_relative = abs(gas_residual) / gas_scale
    tolerance = 1.0e-11
    numerical_pass = (
        count_relative <= tolerance
        and gas_relative <= tolerance
        and transport_count_error <= tolerance * count_scale
        and transport_gas_error <= tolerance * gas_scale
    )
    if not numerical_pass:
        raise ValueError("global conservative balance audit failed")

    mesh_identity = {
        "element_ids": ids.tolist(),
        "cell_volume_m3": volumes.tolist(),
        "owner": owners.tolist(),
        "neighbour": neighbours.tolist(),
    }
    truth_classification = (
        "UNCALIBRATED_SCREENING"
        if data_status == "VIRTUAL"
        else "MEASURED_INPUT_REDUCED_MODEL_UNVALIDATED"
    )
    hold_reasons = [
        "openfoam_calculix_direct_bidirectional_runtime_coupling_not_implemented",
        "reduced_population_closures_not_validated_for_product_claims",
        "mesh_and_time_step_convergence_not_demonstrated_by_this_run",
    ]
    if data_status == "VIRTUAL":
        hold_reasons.insert(0, "virtual_population_and_feedback_coefficients_not_measured_calibrated")

    mechanism_fields = {
        "nucleation": "effective_nucleation_rate_per_m3_s",
        "growth": "effective_growth_rate_per_s",
        "coalescence": "coalescence_kernel_m3_s",
        "transport": "bubble_count_density_transport_rate_per_m3_s",
        "stress_feedback": "effective_tensile_excess_pa",
    }
    result: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "NUMERICAL_PASS_PRODUCTION_HOLD",
        "numerical_status": "PASS",
        "truth_classification": truth_classification,
        "data_status": data_status,
        "coupling_mode": coupling_mode,
        "full_bidirectional_coupling_claim": False,
        "engineering_claim": "NONE",
        "coupling_evidence": {
            "same_element_grid": True,
            "same_time_grid": True,
            "internal_face_transport_conservative": True,
            "stress_history_mode": "PRESCRIBED_WITH_LOCAL_VOID_RELAXATION",
            "openfoam_runtime_feedback": False,
            "calculix_or_elmer_runtime_resolve": False,
        },
        "time_s": times.tolist(),
        "element_ids": ids.tolist(),
        "mesh_identity_sha256": _canonical_sha256(mesh_identity),
        "time_grid_sha256": _canonical_sha256(times.tolist()),
        "mechanisms": list(MECHANISMS),
        "frames": frames,
        "interval_diagnostics": diagnostics,
        "conservation": {
            "initial_total_bubble_count": initial_total_count,
            "final_total_bubble_count": final_total_count,
            "nucleated_count": source_count_added,
            "coalesced_count_removed": coalesced_count_removed,
            "bubble_count_balance_residual": count_residual,
            "bubble_count_relative_residual": count_relative,
            "initial_total_gas_volume_m3": initial_total_gas,
            "final_total_gas_volume_m3": final_total_gas,
            "declared_gas_volume_sources_m3": source_gas_added,
            "gas_volume_balance_residual_m3": gas_residual,
            "gas_volume_relative_residual": gas_relative,
            "maximum_internal_transport_count_balance_error": transport_count_error,
            "maximum_internal_transport_gas_volume_balance_error_m3": transport_gas_error,
        },
        "bounds": {
            "minimum_number_density_per_m3": float(
                min(min(frame["number_density_per_m3"]) for frame in frames)
            ),
            "minimum_void_fraction": float(min(min(frame["void_fraction"]) for frame in frames)),
            "maximum_void_fraction": float(max(max(frame["void_fraction"]) for frame in frames)),
            "declared_maximum_void_fraction": max_void_fraction,
            "maximum_transport_cfl": maximum_cfl,
            "declared_maximum_transport_cfl": max_transport_cfl,
            "declared_maximum_growth_exponent": max_growth_exponent,
        },
        "production_gate": {"status": "HOLD", "hold_reasons": hold_reasons},
        "limitations": [
            "monodisperse cell moment closure; no resolved bubble-size distribution",
            "first-order upwind internal-face transport; exterior boundary flux is not represented",
            "reduced transport-grid identity covers element IDs, volumes and connectivity, not full geometric coordinates",
            "prescribed stress history with local void relaxation, not an iterative structural re-solve",
            "growth and nucleation closures require measured calibration and convergence evidence",
        ],
        "model_controls": scalar_controls,
        "initial_state_sha256": _canonical_sha256(
            {
                "number_density_per_m3": initial_count_density.tolist(),
                "void_fraction": initial_void.tolist(),
            }
        ),
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }
    # Keep the five blocks compatible with the strict same-grid mechanism gate.
    for mechanism in MECHANISMS:
        result[mechanism] = {
            "status": "SOLVED_REDUCED_MODEL",
            "time_s": times.tolist(),
            "element_ids": ids.tolist(),
            "fields": {
                mechanism_fields[mechanism]: [row.tolist() for row in mechanism_history[mechanism]]
            },
            "mesh_identity_sha256": result["mesh_identity_sha256"],
            "time_grid_sha256": result["time_grid_sha256"],
        }
    return result


def run(input_path: Path, output_path: Path) -> dict[str, Any]:
    """Run a JSON card without overwriting evidence and attach provenance."""
    if output_path.exists():
        raise FileExistsError(output_path)
    raw = input_path.read_bytes()
    card = json.loads(raw.decode("utf-8-sig"))
    required = {
        "time_s",
        "element_ids",
        "cell_volume_m3",
        "owner",
        "neighbour",
        "face_volume_flux_m3_s",
        "initial_number_density_per_m3",
        "initial_void_fraction",
        "nucleation_rate_per_m3_s",
        "seed_volume_m3",
        "growth_rate_per_s",
        "coalescence_kernel_m3_s",
        "hydrostatic_tensile_stress_pa",
        "stress_threshold_pa",
        "stress_growth_coeff_per_pa_s",
        "stress_nucleation_coeff_per_m3_s_pa",
        "void_stress_relaxation_pa_per_fraction",
        "max_void_fraction",
        "data_status",
    }
    missing = sorted(required - set(card))
    if missing:
        raise ValueError(f"missing explicit input fields: {missing}")
    allowed = required | {"max_transport_cfl", "max_growth_exponent", "coupling_mode"}
    unknown = sorted(set(card) - allowed)
    if unknown:
        raise ValueError(f"unknown input fields: {unknown}")
    result = solve_population_transport(**card)
    result["input_sha256"] = hashlib.sha256(raw).hexdigest()
    result["input_path"] = str(input_path.resolve())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = run(args.input, args.output)
    print(json.dumps({
        "status": result["status"],
        "truth_classification": result["truth_classification"],
        "production_gate": result["production_gate"],
    }, ensure_ascii=False, indent=2))
    return 0 if result["numerical_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
