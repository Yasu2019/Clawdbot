from pathlib import Path
import json

def test_generated_acceptance_gate_is_screening_only():
    p=Path(__file__).resolve().parents[1]/'artifacts/box_roundhole_v5/virtual_e2e_20260909_r6/acceptance_gate.json'
    if not p.exists(): return
    data=json.loads(p.read_text(encoding='utf-8'))
    assert data['status']=='PASS_SCREENING'
    assert data['formal_status']=='SCREENING_ONLY'
