import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_virtual_card_emits_dictionary_and_keeps_calibration_gate_closed(tmp_path):
    out = tmp_path / "generalizedPolymerThermo"
    result = subprocess.run(
        [sys.executable, "scripts/prepare_material_card.py",
         "--card", "config/virtual_material_pp_screening.json", "--output", str(out)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    manifest = json.loads((out.parent / "material_card_preflight.json").read_text())
    assert manifest["data_status"] == "VIRTUAL_SCREENING_ONLY"
    assert manifest["formal_calibration_gate"] is False
    dictionary = out.read_text()
    assert "coupleCrossWLF true;" in dictionary
    assert "A0 0.00111;" in dictionary
    assert json.loads(result.stdout)["errors"] == []


def test_missing_experimental_card_fields_is_rejected(tmp_path):
    card = json.loads((ROOT / "config/virtual_material_pp_screening.json").read_text())
    del card["tait_two_domain"]["B0"]
    card_path = tmp_path / "invalid.json"
    card_path.write_text(json.dumps(card))
    result = subprocess.run(
        [sys.executable, "scripts/prepare_material_card.py",
         "--card", str(card_path), "--output", str(tmp_path / "out")],
        cwd=ROOT, capture_output=True, text=True,
    )
    assert result.returncode != 0
    assert "missing tait_two_domain.B0" in result.stderr or "missing tait_two_domain.B0" in result.stdout


def test_case_install_is_explicit_and_recorded(tmp_path):
    case = tmp_path / "case"
    out = tmp_path / "card" / "generalizedPolymerThermo"
    subprocess.run(
        [sys.executable, "scripts/prepare_material_card.py",
         "--card", "config/virtual_material_pp_screening.json",
         "--output", str(out), "--case", str(case)],
        cwd=ROOT, capture_output=True, text=True, check=True,
    )
    installed = case / "constant" / "generalizedPolymerThermo"
    assert installed.exists()
    assert installed.read_text() == out.read_text()
