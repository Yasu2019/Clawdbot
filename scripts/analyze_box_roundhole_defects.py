#!/usr/bin/env python3
"""Produce an honest six-phenomena screening report for the box case."""
from __future__ import annotations
import argparse, json, math, re
from pathlib import Path

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--thermal-log', type=Path, required=True)
    p.add_argument('--theory', type=Path, default=Path('artifacts/box_roundhole_v5/theory_screening_package/theory_screening_result.json'))
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    log = a.thermal_log.read_text(errors='replace')
    times = [float(x) for x in re.findall(r'^Time = ([0-9.eE+-]+)', log, re.M)]
    phase = [float(x) for x in re.findall(r'Phase-1 volume fraction = ([0-9.eE+-]+)', log)]
    bounds = [(float(x), float(y)) for x, y in re.findall(r'temperatureBound event: min=\s*([0-9.eE+-]+) max=\s*([0-9.eE+-]+)', log)]
    theory = json.loads(a.theory.read_text()) if a.theory.exists() else {}
    final_t = times[-1] if times else None
    final_phase = phase[-1] if phase else None
    report = {
        'schema': 'clawstack.box_roundhole.six_phenomena_screening.v1',
        'truth_status': 'VIRTUAL_SCREENING_NOT_CALIBRATED',
        'geometry': 'open-top hollow box 100x60x50 mm, wall 2 mm, bottom through-hole dia 20 mm',
        'openfoam_thermal': {'final_time_s': final_t, 'phase1_volume_fraction': final_phase,
                             'temperature_bound_events': len(bounds),
                             'pre_bound_temperature_range_K': [min((x for x, _ in bounds), default=None), max((y for _, y in bounds), default=None)],
                             'log_end': bool(re.search(r'^End$', log, re.M))},
        'phenomena': {
            'filling': {'status': 'PARTIAL_SCREENING', 'observed_phase_volume_fraction': final_phase, 'note': 'Short thermal run only; not full fill.'},
            'warpage': {'status': 'NOT_COMPUTED', 'note': 'Requires solved cooling/shrinkage field mapped to structural FEM.'},
            'sink': {'status': 'NOT_COMPUTED', 'note': 'Requires packing pressure, local thickness and solidification/PVT history.'},
            'shrinkage': {'status': 'THEORY_SCREENING', 'linear_strain': theory.get('shrinkage_linear_strain'), 'note': 'Uniform generalized estimate; not a calibrated PVT result.'},
            'air_trap': {'status': 'TOPOLOGY_SCREENING', 'vent_count': 2, 'note': 'Vent patches exist; trapped-air pressure/temperature field not yet solved.'},
            'weld_line': {'status': theory.get('weld_line', {}).get('status', 'CANDIDATE_SCREENING'), 'candidate_cells': theory.get('weld_line', {}).get('candidate_cells'), 'note': 'Arrival-time proxy only; no weld strength prediction.'}
        },
        'limitations': ['Virtual PP card', 'No full fill/pack/cool sequence', 'No calibrated structural material law']
    }
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0
if __name__ == '__main__':
    raise SystemExit(main())
