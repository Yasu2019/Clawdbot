from pathlib import Path
import json
import pyvista as pv

def test_void_mechanism_contract_is_separate():
    p=Path(__file__).resolve().parents[1]/'artifacts/box_roundhole_v5/virtual_e2e_20260909_r7/quality/void_mechanisms.vtu'
    if not p.exists(): return
    g=pv.read(p); names=[x for x in g.cell_data if x.startswith('void_') and x.endswith('_risk')]
    assert len(names) >= 10
    m=json.loads(p.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    assert m['formal_status']=='SCREENING_ONLY'
    assert 'material_gas' in m['unknown_without_measurements']
