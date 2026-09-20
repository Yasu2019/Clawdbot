import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))
import build_ccx_continuous_reanalysis_deck as M


def test_continuous_reanalysis_deck_writes_one_step_per_history_frame(tmp_path):
    base = tmp_path / "base.inp"
    base.write_text("*NODE\n1,0,0,0\n*ELEMENT,TYPE=C3D4,ELSET=POLYMER\n1,1,1,1,1\n*STEP\nold\n", encoding="utf-8")
    hist_dir = tmp_path / "history"
    hist_dir.mkdir()
    (hist_dir / "temperature_0000.inc").write_text("*TEMPERATURE\n1,20\n", encoding="ascii")
    (hist_dir / "temperature_0001.inc").write_text("*TEMPERATURE\n1,30\n", encoding="ascii")
    (hist_dir / "pressure_0000.csv").write_text("target_id,pressure_Pa\n1,1\n", encoding="ascii")
    (hist_dir / "pressure_0001.csv").write_text("target_id,pressure_Pa\n1,2\n", encoding="ascii")
    manifest = {
        "schema": "clawstack.calculix.deck.export.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "target_count": 1,
        "target_entity": "node",
        "frames": [
            {"time_s": 0.1, "temperature_include": "temperature_0000.inc", "pressure_csv": "pressure_0000.csv"},
            {"time_s": 0.3, "temperature_include": "temperature_0001.inc", "pressure_csv": "pressure_0001.csv"},
        ],
        "reference_state": {"stress_free_temperature_K": 500, "shrinkage_counting": "cte_only"},
        "constraints": {"release": "after_pack"},
    }
    manifest_path = hist_dir / "calculix_history_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = M.run(base, manifest_path, tmp_path / "out")
    text = Path(report["deck"]).read_text(encoding="utf-8")

    assert report["status"] == "WRITTEN_NOT_SOLVED"
    assert report["step_count"] == 2
    assert text.count("*STEP") == 2
    assert "old" not in text
    assert "*INCLUDE, INPUT=temperature_0001.inc" in text
    assert "2.000000000000e-01, 2.000000000000e-01" in text
    assert report["shrinkage_policy"]["representation"] == "mapped_temperature_with_material_cte"


def test_eigenstrain_history_is_applied_as_c3d4_initial_strain_increments(tmp_path):
    base = tmp_path / "base.inp"
    base.write_text(
        "*NODE\n"
        "1,0,0,0\n2,1,0,0\n3,0,1,0\n4,0,0,1\n"
        "*ELEMENT, TYPE=C3D4, ELSET=POLYMER\n"
        "10,1,2,3,4\n"
        "*MATERIAL, NAME=POLYMER\n*ELASTIC\n1000,0.3\n"
        "*SOLID SECTION, ELSET=POLYMER, MATERIAL=POLYMER\n"
        "*STEP\nold\n*END STEP\n",
        encoding="utf-8",
    )
    hist_dir = tmp_path / "history"
    hist_dir.mkdir()
    for index in range(2):
        (hist_dir / f"temperature_element_{index:04d}.csv").write_text(
            "element_id,temperature_K\n10,293.15\n", encoding="ascii"
        )
        (hist_dir / f"pressure_{index:04d}.csv").write_text(
            "target_id,pressure_Pa\n10,0\n", encoding="ascii"
        )
    (hist_dir / "eigenstrain_0000.csv").write_text(
        "target_id,eigenstrain\n10,-1.000000000000e-02\n", encoding="ascii"
    )
    (hist_dir / "eigenstrain_0001.csv").write_text(
        "target_id,eigenstrain\n10,-2.500000000000e-02\n", encoding="ascii"
    )
    manifest = {
        "schema": "clawstack.calculix.deck.export.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "target_count": 1,
        "target_entity": "element",
        "element_integration_points": {"10": 1},
        "frames": [
            {
                "time_s": 0.1,
                "temperature_element_csv": "temperature_element_0000.csv",
                "pressure_csv": "pressure_0000.csv",
                "eigenstrain_csv": "eigenstrain_0000.csv",
            },
            {
                "time_s": 0.3,
                "temperature_element_csv": "temperature_element_0001.csv",
                "pressure_csv": "pressure_0001.csv",
                "eigenstrain_csv": "eigenstrain_0001.csv",
            },
        ],
        "reference_state": {
            "stress_free_temperature_K": 500,
            "shrinkage_counting": "eigenstrain_only",
            "eigenstrain_frame_semantics": "total_from_stress_free",
            "strain_measure": "green_lagrange",
            "reference_configuration": "stress_free_geometry",
            "eigenstrain_value_kind": "isotropic_normal_component",
        },
        "constraints": {"release": "after_pack"},
    }
    manifest_path = hist_dir / "calculix_history_manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    report = M.run(base, manifest_path, tmp_path / "out")
    deck = Path(report["deck"]).read_text(encoding="utf-8")
    initial = (tmp_path / "out" / "eigenstrain_initial.inc").read_text(encoding="ascii")
    first = (tmp_path / "out" / "eigenstrain_increment_0000.inc").read_text(encoding="ascii")
    second = (tmp_path / "out" / "eigenstrain_increment_0001.inc").read_text(encoding="ascii")

    assert "*INCLUDE, INPUT=eigenstrain_initial.inc" in deck
    assert deck.index("*INCLUDE, INPUT=eigenstrain_initial.inc") < deck.index("*STEP")
    assert "*INCLUDE, INPUT=eigenstrain_increment_0001.inc" in deck
    assert "*INCLUDE, INPUT=temperature_element_0000.csv" not in deck
    assert "Element-mapped physical temperature retained for audit only: temperature_element_0000.csv" in deck
    assert "2.000000000000e-01, 2.000000000000e-01" in deck
    assert "*INITIAL CONDITIONS, TYPE=PLASTIC STRAIN" in initial
    assert "10, 1, 0., 0., 0., 0., 0., 0." in initial
    assert "10, 1, -1.000000000000e-02, -1.000000000000e-02, -1.000000000000e-02" in first
    assert "10, 1, -1.500000000000e-02, -1.500000000000e-02, -1.500000000000e-02" in second
    assert report["shrinkage_policy"]["representation"] == "initial_strain_increase_isotropic_c3d4"
    assert report["shrinkage_policy"]["physical_temperature_applied"] is False


def test_cte_only_rejects_eigenstrain_csv(tmp_path):
    base = tmp_path / "base.inp"
    base.write_text("*NODE\n1,0,0,0\n*STEP\nold\n", encoding="utf-8")
    hist_dir = tmp_path / "history"
    hist_dir.mkdir()
    (hist_dir / "temperature.inc").write_text("*TEMPERATURE\n1,20\n", encoding="ascii")
    (hist_dir / "pressure.csv").write_text("target_id,pressure_Pa\n1,0\n", encoding="ascii")
    (hist_dir / "eigenstrain.csv").write_text("target_id,eigenstrain\n1,-0.01\n", encoding="ascii")
    manifest = {
        "schema": "clawstack.calculix.deck.export.v1",
        "status": "WRITTEN_NOT_SOLVED",
        "target_count": 1,
        "target_entity": "node",
        "frames": [{
            "time_s": 0.1,
            "temperature_include": "temperature.inc",
            "pressure_csv": "pressure.csv",
            "eigenstrain_csv": "eigenstrain.csv",
        }],
        "reference_state": {"stress_free_temperature_K": 293.15, "shrinkage_counting": "cte_only"},
    }
    manifest_path = hist_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    try:
        M.run(base, manifest_path, tmp_path / "out")
    except ValueError as exc:
        assert "forbidden" in str(exc)
    else:
        raise AssertionError("cte_only accepted eigenstrain loading")


def test_eigenstrain_ip_map_and_existing_initial_state_fail_closed():
    with pytest.raises(ValueError, match="map every eigenstrain target"):
        M._integration_point_map(None, 1)
    with pytest.raises(ValueError, match="positive integer counts"):
        M._integration_point_map({"10": 0}, 1)
    with pytest.raises(ValueError, match="already defines initial"):
        M._reject_conflicting_initial_strain_state(
            "*INITIAL CONDITIONS, TYPE=STRESS\n10,0,0,0,0,0,0\n*STEP\n"
        )
