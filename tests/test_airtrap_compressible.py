from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from derive_airtrap_compressible import (
    SCREENING_STATUS,
    derive_airtrap_compressible,
    load_openfoam_airtrap_history,
    main,
)


def _thermodynamic_fields(alpha: np.ndarray):
    shape = alpha.shape
    pressure = np.full(shape, 101_325.0)
    temperature = np.full(shape, 300.0)
    density = np.full(shape, 1.2)
    return pressure, temperature, density


def test_actual_cell_graph_and_explicit_vent_control_isolation_and_persistence():
    # The interface at cell 1 breaks the only topological path from cell 0 to
    # the explicit vent at cell 4.  No coordinate or gate-distance input exists.
    alpha = np.asarray(
        [
            [0.0, 0.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
            [0.0, 1.0, 0.0, 0.0, 0.0],
        ]
    )
    pressure, temperature, density = _thermodynamic_fields(alpha)
    result = derive_airtrap_compressible(
        alpha,
        pressure,
        temperature,
        density,
        [0.0, 1.0, 2.0],
        [0, 1, 2, 3],
        [1, 2, 3, 4],
        np.ones(5),
        [4],
        np.zeros((3, 1)),
        persistence_frames=2,
        vent_flux_method="test_gas_mass_flux",
        vent_flux_phase_exact=True,
    )

    assert result["status"] == SCREENING_STATUS
    assert result["calibration"] == "UNCALIBRATED_SCREENING"
    assert result["probability_prediction"] is False
    assert result["fully_coupled_two_phase_gas_model"] is False
    assert result["frames"][0]["isolated_component_count"] == 0
    assert result["frames"][1]["isolated_component_count"] == 1
    assert result["frames"][1]["persistent_isolated_component_count"] == 0
    assert result["frames"][2]["persistent_isolated_component_count"] == 1
    assert result["frames"][2]["current_persistent_cell_ranges"] == [[0, 0]]
    assert result["persistent_track_count"] == 1


def test_component_pressure_temperature_volume_and_mass_are_field_derived():
    alpha = np.asarray([[0.0, 1.0], [0.0, 1.0]])
    pressure = np.asarray([[202_650.0, 101_325.0], [303_975.0, 101_325.0]])
    temperature = np.full_like(alpha, 300.0)
    density = np.full_like(alpha, 900.0)
    result = derive_airtrap_compressible(
        alpha,
        pressure,
        temperature,
        density,
        [0.0, 1.0],
        [0],
        [1],
        [1.0e-3, 1.0e-3],
        [1],
        np.zeros((2, 1)),
        persistence_frames=1,
        gas_specific_R_J_kgK=287.05,
    )

    first = result["frames"][0]["components"][0]
    assert first["classification"] == "ISOLATED_GAS_COMPONENT_CANDIDATE"
    assert first["gas_volume_m3"] == pytest.approx(1.0e-3)
    assert first["mean_pressure_Pa"] == pytest.approx(202_650.0)
    assert first["mean_temperature_K"] == pytest.approx(300.0)
    assert first["pressure_ratio_to_reference"] == pytest.approx(2.0)
    assert first["ideal_gas_reconstructed_mass_kg"] == pytest.approx(
        202_650.0 / (287.05 * 300.0) * 1.0e-3
    )
    # rho is not silently treated as gas density; it is an independent mixture audit.
    assert first["mixture_mass_in_component_cells_kg"] == pytest.approx(0.9)


def test_signed_vent_flux_is_integrated_in_physical_time():
    alpha = np.zeros((3, 1))
    pressure, temperature, density = _thermodynamic_fields(alpha)
    result = derive_airtrap_compressible(
        alpha,
        pressure,
        temperature,
        density,
        [0.0, 1.0, 3.0],
        [],
        [],
        [1.0],
        [0],
        [[0.0], [0.002], [0.002]],
        vent_flux_method="rhoPhi.air_written_gas_mass_flux",
        vent_flux_phase_exact=True,
    )

    final_flux = result["frames"][-1]["vent_gas_mass_flux"]
    assert final_flux["cumulative_outward_kg"] == pytest.approx(0.005)
    assert final_flux["cumulative_net_outward_kg"] == pytest.approx(0.005)
    assert result["vent_flux_audit"]["phase_flux_exact"] is True
    assert result["frames"][-1]["isolated_component_count"] == 0


def test_missing_vent_flux_fails_closed_but_preserves_topology_diagnostics():
    alpha = np.zeros((2, 1))
    pressure, temperature, density = _thermodynamic_fields(alpha)
    result = derive_airtrap_compressible(
        alpha,
        pressure,
        temperature,
        density,
        [0.0, 1.0],
        [],
        [],
        [1.0],
        [0],
        None,
    )

    assert result["status"] == "HOLD"
    assert result["hold_reasons"] == ["VENT_GAS_MASS_FLUX_MISSING"]
    assert result["vent_flux_audit"]["available"] is False
    assert "vent_gas_mass_flux" not in result["frames"][0]


def test_invalid_thermodynamic_field_or_vent_definition_is_rejected():
    alpha = np.zeros((2, 1))
    _, temperature, density = _thermodynamic_fields(alpha)
    with pytest.raises(ValueError, match="absolute p must be positive"):
        derive_airtrap_compressible(
            alpha,
            np.zeros_like(alpha),
            temperature,
            density,
            [0.0, 1.0],
            [],
            [],
            [1.0],
            [0],
            np.zeros((2, 1)),
        )
    with pytest.raises(ValueError, match="explicit vent"):
        derive_airtrap_compressible(
            alpha,
            np.ones_like(alpha) * 101_325.0,
            temperature,
            density,
            [0.0, 1.0],
            [],
            [],
            [1.0],
            [],
            np.zeros((2, 0)),
        )


def _write_mesh(case: Path) -> None:
    mesh = case / "constant" / "polyMesh"
    mesh.mkdir(parents=True)
    header = "FoamFile\n{\n format ascii;\n}\n"
    (mesh / "points").write_text(
        header + "4\n(\n(0 0 0)\n(1 0 0)\n(0 1 0)\n(0 0 1)\n)\n",
        encoding="utf-8",
    )
    (mesh / "faces").write_text(
        header + "4\n(\n3(0 2 1)\n3(0 1 3)\n3(0 3 2)\n3(1 2 3)\n)\n",
        encoding="utf-8",
    )
    (mesh / "owner").write_text(header + "4\n(\n0\n0\n0\n0\n)\n", encoding="utf-8")
    (mesh / "neighbour").write_text(header + "0\n(\n)\n", encoding="utf-8")
    (mesh / "boundary").write_text(
        header
        + "1\n(\nvent\n{\n type patch;\n nFaces 4;\n startFace 0;\n}\n)\n",
        encoding="utf-8",
    )


def _write_scalar(
    directory: Path,
    name: str,
    dimensions: str,
    internal: float,
    patch_value: float,
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / name).write_text(
        "FoamFile\n{\n format ascii;\n class volScalarField;\n}\n"
        f"dimensions [{dimensions}];\n"
        f"internalField uniform {internal};\n"
        "boundaryField\n{\n"
        " vent\n {\n  type fixedValue;\n"
        f"  value uniform {patch_value};\n"
        " }\n}\n",
        encoding="utf-8",
    )


def _write_flux(directory: Path, value: float) -> None:
    (directory / "rhoPhi.air").write_text(
        "FoamFile\n{\n format ascii;\n class surfaceScalarField;\n}\n"
        "dimensions [1 0 -1 0 0 0 0];\n"
        "internalField uniform 0;\n"
        "boundaryField\n{\n"
        " vent\n {\n  type calculated;\n"
        f"  value uniform {value};\n"
        " }\n}\n",
        encoding="utf-8",
    )


def test_openfoam_loader_reads_polyhedron_volume_fields_vents_and_written_gas_flux(tmp_path: Path):
    case = tmp_path / "case"
    _write_mesh(case)
    for time_name, alpha_value, flux_value in (("0", 0.0, 0.001), ("1", 1.0, 0.002)):
        directory = case / time_name
        _write_scalar(directory, "alpha.polymer", "0 0 0 0 0 0 0", alpha_value, alpha_value)
        _write_scalar(directory, "p", "1 -1 -2 0 0 0 0", 101_325.0, 101_325.0)
        _write_scalar(directory, "T", "0 0 0 1 0 0 0", 300.0, 300.0)
        _write_scalar(directory, "rho", "1 -3 0 0 0 0 0", 1.2, 1.2)
        _write_flux(directory, flux_value)

    loaded = load_openfoam_airtrap_history(case, ["vent"])

    assert loaded["alpha"].shape == (2, 1)
    assert loaded["cell_volumes_m3"].tolist() == pytest.approx([1.0 / 6.0])
    assert loaded["vent_face_cells"].tolist() == [0, 0, 0, 0]
    assert loaded["vent_gas_mass_flux_kg_s"].shape == (2, 4)
    assert loaded["vent_gas_mass_flux_kg_s"][0].tolist() == pytest.approx([0.001] * 4)
    assert loaded["vent_flux_method"] == "rhoPhi.air_written_gas_mass_flux"
    assert loaded["vent_flux_phase_exact"] is True
    assert len(loaded["source_sha256"]) == 10


def test_openfoam_loader_fails_closed_when_flux_or_explicit_vent_is_missing(tmp_path: Path):
    case = tmp_path / "case"
    _write_mesh(case)
    for time_name in ("0", "1"):
        directory = case / time_name
        _write_scalar(directory, "alpha.polymer", "0 0 0 0 0 0 0", 0.0, 0.0)
        _write_scalar(directory, "p", "1 -1 -2 0 0 0 0", 101_325.0, 101_325.0)
        _write_scalar(directory, "T", "0 0 0 1 0 0 0", 300.0, 300.0)
        _write_scalar(directory, "rho", "1 -3 0 0 0 0 0", 1.2, 1.2)

    with pytest.raises(FileNotFoundError, match="lacks rhoPhi"):
        load_openfoam_airtrap_history(case, ["vent"])
    with pytest.raises(ValueError, match="not found"):
        load_openfoam_airtrap_history(case, ["not_a_vent"])


def test_cli_writes_auditable_json_and_npz_without_validation_claim(tmp_path: Path):
    case = tmp_path / "case"
    _write_mesh(case)
    for time_name, alpha_value in (("0", 0.0), ("1", 0.25)):
        directory = case / time_name
        _write_scalar(directory, "alpha.polymer", "0 0 0 0 0 0 0", alpha_value, alpha_value)
        _write_scalar(directory, "p", "1 -1 -2 0 0 0 0", 120_000.0, 120_000.0)
        _write_scalar(directory, "T", "0 0 0 1 0 0 0", 310.0, 310.0)
        _write_scalar(directory, "rho", "1 -3 0 0 0 0 0", 1.3, 1.3)
        _write_flux(directory, 0.001)
    output = tmp_path / "airtrap_report.json"

    return_code = main(
        [str(case), "--vent-patch", "vent", "--output", str(output), "--persistence-frames", "1"]
    )

    assert return_code == 0
    report = json.loads(output.read_text(encoding="utf-8"))
    assert report["status"] == SCREENING_STATUS
    assert report["validated_manufacturing_result"] is False
    assert report["source"]["vent_patches"][0]["name"] == "vent"
    assert report["array_evidence"]["path"] == "airtrap_report.npz"
    assert (tmp_path / "airtrap_report.npz").is_file()
