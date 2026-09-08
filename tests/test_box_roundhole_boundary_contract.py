import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_gate_and_vent_contract_is_explicit():
    process = json.loads((ROOT / "config/box_roundhole_v5_spec.json").read_text())["process"]
    assert process["gate_count"] == 2
    assert process["gate_diameter_mm"] == 4.0
    assert process["vent_count"] == 2
    assert process["vent_diameter_mm"] == 2.0
    assert math.isclose(2 * math.pi * 2**2, 25.132741228718345)
    assert process["vent_definition_status"].startswith("ASSUMED_")


def test_mesh_builder_does_not_classify_whole_end_faces_as_ports():
    source = (ROOT / "scripts/build_box_roundhole_v5_geometry.py").read_text()
    assert "area - gate_area" in source
    assert "area - vent_area" in source
    assert "occ.addDisk" in source
