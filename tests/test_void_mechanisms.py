import json

import numpy as np
import pyvista as pv

from scripts.derive_void_mechanisms import derive


def test_void_mechanism_contract_is_separate():
    from pathlib import Path
    p = Path(__file__).resolve().parents[1] / 'artifacts/box_roundhole_v5/virtual_e2e_20260909_r7/quality/void_mechanisms.vtu'
    if not p.exists():
        return
    g = pv.read(p)
    names = [x for x in g.cell_data if x.startswith('void_') and x.endswith('_risk')]
    assert len(names) >= 10
    m = json.loads(p.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    assert m['formal_status'] == 'SCREENING_ONLY'
    assert 'material_gas' in m['unknown_without_measurements']


def _grid(tmp_path):
    mesh = pv.ImageData(dimensions=(3, 2, 2), spacing=(1, 1, 1), origin=(0, 0, 0))
    n = mesh.n_cells
    mesh.cell_data['alpha_fill'] = np.ones(n)
    mesh.cell_data['pressure_MPa_calibrated'] = np.full(n, 1.0)
    mesh.cell_data['temperature_C_theory'] = np.full(n, 300.0)
    mesh.cell_data['solidification_fraction'] = np.zeros(n)
    mesh.cell_data['pvt_shrink_strain'] = np.zeros(n)
    mesh.cell_data['arrival_time_s'] = np.ones(n)
    mesh.cell_data['weld_risk_proxy'] = np.zeros(n)
    mesh.cell_data['half_thickness_m_proxy'] = np.ones(n)
    source = tmp_path / 'source.vti'
    mesh.save(source)
    return source


def test_virtual_card_keeps_material_gas_zero(tmp_path):
    source = _grid(tmp_path)
    card = tmp_path / 'card.json'
    card.write_text(json.dumps({'gas_generation': {'moisture_ppm': 0, 'volatile_mass_fraction': 0,
                                                    'degradation_temperature_C': 280,
                                                    'data_status': 'VIRTUAL_SCREENING_ONLY'}}))
    manifest = derive(source, tmp_path / 'out.vti', card)
    assert manifest['summary']['material_gas']['max'] == 0.0
    assert 'material_gas' in manifest['unknown_without_measurements']


def test_measured_gas_card_activates_material_gas_field(tmp_path):
    source = _grid(tmp_path)
    card = tmp_path / 'card.json'
    card.write_text(json.dumps({'gas_generation': {'moisture_ppm': 500, 'volatile_mass_fraction': 0.01,
                                                    'degradation_temperature_C': 280,
                                                    'data_status': 'MEASURED'}}))
    manifest = derive(source, tmp_path / 'out.vti', card)
    assert manifest['summary']['material_gas']['max'] > 0.0
    assert 'material_gas' not in manifest['unknown_without_measurements']


def test_geometry_constriction_field_is_emitted(tmp_path):
    source = _grid(tmp_path)
    manifest = derive(source, tmp_path / 'out.vti')
    assert 'geometry_constriction' in manifest['summary']
    output = pv.read(tmp_path / 'out.vti')
    assert 'void_geometry_constriction_risk' in output.cell_data
