#!/usr/bin/env python3
"""Validate a material card and emit the solver's generalized thermo dictionary."""
from __future__ import annotations
import argparse, json, shutil
from pathlib import Path

REQ = {
    'identity': ['material_id', 'data_status'],
    'process': ['melt_temperature_K', 'mold_temperature_K'],
    'thermal': ['rho_reference', 'cp', 'conductivity'],
    'cross_wlf': ['D1', 'D2_C', 'D3_C_MPa', 'A1', 'A2_C', 'tauStar_Pa', 'n'],
    'tait_two_domain': ['A0', 'A1p', 'B0', 'B1p', 'C', 'b', 'Tref_K'],
    'structural': ['youngs_modulus_Pa', 'poisson_ratio', 'cte_1_K']
}

def validate(card: dict) -> list[str]:
    errors=[]
    for section, keys in REQ.items():
        if section not in card: errors.append(f'missing section: {section}'); continue
        for key in keys:
            if key not in card[section]: errors.append(f'missing {section}.{key}')
    status=card.get('identity',{}).get('data_status')
    if status not in {'VIRTUAL_SCREENING_ONLY','MEASURED_UNCALIBRATED','CALIBRATED','VALIDATED'}:
        errors.append('identity.data_status must be an allowed status')
    return errors

def main():
    ap=argparse.ArgumentParser(); ap.add_argument('--card',type=Path,required=True); ap.add_argument('--output',type=Path,required=True)
    ap.add_argument('--case',type=Path, help='Optional OpenFOAM case directory; install the generated dictionary under constant/')
    args=ap.parse_args(); card=json.loads(args.card.read_text(encoding='utf-8')); errors=validate(card)
    if errors: raise SystemExit(json.dumps({'status':'INVALID','errors':errors},ensure_ascii=False))
    w=card['cross_wlf']; t=card['tait_two_domain']
    text='''FoamFile\n{{ version 2.0; format ascii; class dictionary; object generalizedPolymerThermo; }}\nD1 {D1};\nD2_C {D2_C};\nD3_C_MPa {D3_C_MPa};\nA1 {A1};\nA2_C {A2_C};\ntauStar_Pa {tauStar_Pa};\nn {n};\nA0 {A0};\nA1p {A1p};\nB0 {B0};\nB1p {B1p};\nC {C};\nb {b};\nTref_K {Tref_K};\ncoupleCrossWLF true;\n'''.format(**w,**t)
    args.output.parent.mkdir(parents=True,exist_ok=True); args.output.write_text(text,encoding='utf-8')
    installed = None
    if args.case:
        target = args.case / 'constant' / 'generalizedPolymerThermo'
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(args.output, target)
        installed = str(target)
    manifest={'schema':'clawstack.material_card_preflight.v1','material_id':card['identity']['material_id'],'data_status':card['identity']['data_status'],'solver_dictionary':str(args.output),'installed_dictionary':installed,'formal_calibration_gate':card['identity']['data_status'] in {'CALIBRATED','VALIDATED'},'errors':[]}
    (args.output.parent/'material_card_preflight.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8'); print(json.dumps(manifest,indent=2,ensure_ascii=False))
if __name__=='__main__': main()
