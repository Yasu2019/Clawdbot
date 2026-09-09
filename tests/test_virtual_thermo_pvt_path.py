from pathlib import Path
import json
import pyvista as pv
import numpy as np

ROOT = Path(__file__).resolve().parents[1]

def test_virtual_thermo_pvt_output_has_finite_fields():
    source = ROOT / 'artifacts/box_roundhole_v5/virtual_e2e_20260909/virtual_thermo_pvt.vtu'
    if not source.exists():
        return  # optional generated artefact in clean CI checkouts
    g = pv.read(source)
    required = ['temperature_C_theory','cross_wlf_viscosity_Pa_s','tait_density_kg_m3','pvt_shrink_strain','shrink_x','shrink_y','shrink_z']
    assert all(name in g.cell_data for name in required)
    for name in required:
        assert np.isfinite(np.asarray(g.cell_data[name])).all()
    manifest = json.loads(source.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    assert manifest['formal_status'] == 'SCREENING_ONLY'
