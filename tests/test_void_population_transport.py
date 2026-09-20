from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json

import numpy as np
import pytest

from scripts.void_population_transport import run, solve_population_transport
from scripts.validate_void_full_coupling_gate import validate_void_model


def model(**changes):
    payload = {
        "time_s": [0.0, 0.1, 0.2],
        "element_ids": [101, 102],
        "cell_volume_m3": [1.0, 1.0],
        "owner": [0],
        "neighbour": [1],
        "face_volume_flux_m3_s": [[0.2], [0.2]],
        "initial_number_density_per_m3": [10.0, 0.0],
        "initial_void_fraction": [0.02, 0.0],
        "nucleation_rate_per_m3_s": 0.0,
        "seed_volume_m3": 1.0e-6,
        "growth_rate_per_s": 0.0,
        "coalescence_kernel_m3_s": 0.0,
        "hydrostatic_tensile_stress_pa": [[0.0, 0.0], [0.0, 0.0], [0.0, 0.0]],
        "stress_threshold_pa": 0.0,
        "stress_growth_coeff_per_pa_s": 0.0,
        "stress_nucleation_coeff_per_m3_s_pa": 0.0,
        "void_stress_relaxation_pa_per_fraction": 0.0,
        "max_void_fraction": 0.25,
        "max_transport_cfl": 0.8,
        "max_growth_exponent": 0.25,
        "data_status": "VIRTUAL",
        "coupling_mode": "OFFLINE_ONE_WAY",
    }
    payload.update(changes)
    return payload


def test_zero_source_internal_advection_conserves_count_and_gas_volume():
    result = solve_population_transport(**model())
    conservation = result["conservation"]
    assert conservation["final_total_bubble_count"] == pytest.approx(10.0)
    assert conservation["final_total_gas_volume_m3"] == pytest.approx(0.02)
    assert abs(conservation["bubble_count_balance_residual"]) < 1.0e-13
    assert abs(conservation["gas_volume_balance_residual_m3"]) < 1.0e-15
    assert result["frames"][-1]["number_density_per_m3"][1] > 0.0
    assert result["frames"][-1]["void_fraction"][1] > 0.0


def test_opposite_face_flux_remains_conservative():
    result = solve_population_transport(
        **model(
            initial_number_density_per_m3=[2.0, 8.0],
            initial_void_fraction=[0.01, 0.04],
            face_volume_flux_m3_s=[[-0.4], [-0.4]],
        )
    )
    assert result["frames"][-1]["total_bubble_count"] == pytest.approx(10.0)
    assert result["frames"][-1]["total_gas_volume_m3"] == pytest.approx(0.05)


def test_coalescence_reduces_count_and_preserves_gas_volume():
    baseline = solve_population_transport(
        **model(face_volume_flux_m3_s=[[0.0], [0.0]], time_s=[0.0, 0.1, 0.2])
    )
    result = solve_population_transport(
        **model(
            face_volume_flux_m3_s=[[0.0], [0.0]],
            coalescence_kernel_m3_s=0.5,
        )
    )
    assert result["frames"][-1]["total_bubble_count"] < baseline["frames"][-1]["total_bubble_count"]
    assert result["frames"][-1]["total_gas_volume_m3"] == pytest.approx(
        baseline["frames"][-1]["total_gas_volume_m3"]
    )
    assert result["conservation"]["coalesced_count_removed"] > 0.0


def test_nucleation_and_growth_are_positive_audited_sources():
    result = solve_population_transport(
        **model(
            face_volume_flux_m3_s=[[0.0], [0.0]],
            initial_number_density_per_m3=[0.0, 0.0],
            initial_void_fraction=[0.0, 0.0],
            nucleation_rate_per_m3_s=20.0,
            seed_volume_m3=1.0e-4,
            growth_rate_per_s=0.5,
        )
    )
    final = result["frames"][-1]
    assert final["total_bubble_count"] == pytest.approx(8.0)
    assert final["total_gas_volume_m3"] > 8.0e-4
    assert result["conservation"]["nucleated_count"] == pytest.approx(8.0)
    assert result["conservation"]["declared_gas_volume_sources_m3"] == pytest.approx(
        final["total_gas_volume_m3"]
    )


def test_stress_feedback_adds_sources_and_void_relaxation_reduces_feedback():
    common = model(
        face_volume_flux_m3_s=[[0.0], [0.0]],
        initial_number_density_per_m3=[1.0, 1.0],
        initial_void_fraction=[0.01, 0.01],
        hydrostatic_tensile_stress_pa=[[2.0e6, 2.0e6]] * 3,
        stress_threshold_pa=1.0e6,
        stress_growth_coeff_per_pa_s=2.0e-7,
        stress_nucleation_coeff_per_m3_s_pa=1.0e-5,
    )
    no_relaxation = solve_population_transport(**common)
    relaxed = solve_population_transport(
        **{**common, "void_stress_relaxation_pa_per_fraction": 1.0e8}
    )
    assert no_relaxation["frames"][-1]["total_bubble_count"] > 2.0
    assert no_relaxation["frames"][-1]["total_gas_volume_m3"] > 0.02
    assert relaxed["frames"][-1]["total_gas_volume_m3"] < no_relaxation["frames"][-1]["total_gas_volume_m3"]
    assert no_relaxation["stress_feedback"]["fields"]["effective_tensile_excess_pa"][1] == [1.0e6, 1.0e6]


def test_positive_and_void_fraction_bound():
    result = solve_population_transport(**model())
    assert result["bounds"]["minimum_number_density_per_m3"] >= 0.0
    assert result["bounds"]["minimum_void_fraction"] >= 0.0
    assert result["bounds"]["maximum_void_fraction"] <= 0.25
    with pytest.raises(ValueError, match="maximum_void_fraction"):
        solve_population_transport(
            **model(
                face_volume_flux_m3_s=[[0.0], [0.0]],
                initial_number_density_per_m3=[0.0, 0.0],
                initial_void_fraction=[0.0, 0.0],
                nucleation_rate_per_m3_s=1.0e7,
                seed_volume_m3=1.0e-3,
            )
        )


def test_transport_cfl_and_source_time_step_are_rejected():
    with pytest.raises(ValueError, match="transport CFL"):
        solve_population_transport(
            **model(
                time_s=[0.0, 1.0],
                face_volume_flux_m3_s=[[1.0]],
                hydrostatic_tensile_stress_pa=[[0.0, 0.0], [0.0, 0.0]],
            )
        )
    with pytest.raises(ValueError, match="source time-step"):
        solve_population_transport(
            **model(
                time_s=[0.0, 1.0],
                face_volume_flux_m3_s=[[0.0]],
                growth_rate_per_s=0.3,
                hydrostatic_tensile_stress_pa=[[0.0, 0.0], [0.0, 0.0]],
            )
        )


def test_manifest_is_complete_but_truthfully_held(tmp_path):
    input_path = tmp_path / "void_input.json"
    output_path = tmp_path / "void_manifest.json"
    input_path.write_text(json.dumps(model()), encoding="utf-8")
    result = run(input_path, output_path)

    assert result["numerical_status"] == "PASS"
    assert result["status"] == "NUMERICAL_PASS_PRODUCTION_HOLD"
    assert result["truth_classification"] == "UNCALIBRATED_SCREENING"
    assert result["production_gate"]["status"] == "HOLD"
    assert result["full_bidirectional_coupling_claim"] is False
    assert result["coupling_evidence"] == {
        "same_element_grid": True,
        "same_time_grid": True,
        "internal_face_transport_conservative": True,
        "stress_history_mode": "PRESCRIBED_WITH_LOCAL_VOID_RELAXATION",
        "openfoam_runtime_feedback": False,
        "calculix_or_elmer_runtime_resolve": False,
    }
    assert "openfoam_calculix_direct_bidirectional_runtime_coupling_not_implemented" in result["production_gate"]["hold_reasons"]
    assert set(result["mechanisms"]) == {
        "nucleation", "growth", "coalescence", "transport", "stress_feedback"
    }
    assert len(result["input_sha256"]) == 64
    assert len(result["source_sha256"]) == 64
    for mechanism in result["mechanisms"]:
        assert result[mechanism]["time_s"] == result["time_s"]
        assert result[mechanism]["element_ids"] == result["element_ids"]
        assert result[mechanism]["mesh_identity_sha256"] == result["mesh_identity_sha256"]
    gate = validate_void_model(output_path)
    assert gate["status"] == "INPUT_READY_NOT_SOLVED"


def test_direct_bidirectional_claim_is_rejected():
    with pytest.raises(ValueError, match="direct bidirectional coupling cannot be claimed"):
        solve_population_transport(**model(coupling_mode="OPENFOAM_BIDIRECTIONAL_RUNTIME"))


def test_invalid_grid_and_initial_pairing_are_rejected():
    with pytest.raises(ValueError, match="strictly increasing"):
        solve_population_transport(**model(time_s=[0.0, 0.1, 0.1]))
    with pytest.raises(ValueError, match="present together"):
        solve_population_transport(
            **model(initial_number_density_per_m3=[1.0, 0.0], initial_void_fraction=[0.0, 0.0])
        )
    with pytest.raises(ValueError, match="exact-integer"):
        solve_population_transport(**model(element_ids=[101.5, 102]))


def test_mechanism_histories_are_finite_and_same_shape():
    result = solve_population_transport(**model())
    expected = (len(result["time_s"]), len(result["element_ids"]))
    for mechanism in result["mechanisms"]:
        values = next(iter(result[mechanism]["fields"].values()))
        array = np.asarray(values, dtype=float)
        assert array.shape == expected
        assert np.isfinite(array).all()
