#!/usr/bin/env python3
"""Fail-closed acceptance gate for the virtual-material E2E run."""
from __future__ import annotations
import argparse,json
from pathlib import Path

def validate(root: Path) -> dict:
    manifest=root/'virtual_e2e_manifest.json'
    errors=[]
    if not manifest.is_file(): errors.append('virtual_e2e_manifest.json missing')
    else:
        m=json.loads(manifest.read_text(encoding='utf-8'))
        for key in ('thermo_pvt','quality_evaluator','calculix'):
            if key not in m: errors.append(f'{key} missing')
        if m.get('formal_status')!='SCREENING_ONLY': errors.append('formal_status must remain SCREENING_ONLY')
        if m.get('thermo_pvt',{}).get('returncode')!=0: errors.append('thermo_pvt failed')
        if m.get('quality_evaluator',{}).get('returncode')!=0: errors.append('quality evaluator failed')
        ccx=m.get('calculix',{})
        for k in ('prepare_returncode','run_returncode','audit_returncode'):
            if ccx.get(k)!=0: errors.append(f'calculix {k} failed')
    required=['virtual_fields.vtu','virtual_thermo_pvt.vtu','virtual_thermo_pvt.manifest.json','quality/summary.json','calculix_from_pvt/solver_run.json','calculix_from_pvt/result_audit.json']
    missing=[x for x in required if not (root/x).is_file()]
    errors.extend('missing '+x for x in missing)
    result={'schema':'clawstack.virtual_e2e_acceptance.v1','status':'PASS_SCREENING' if not errors else 'FAIL_SCREENING','formal_status':'SCREENING_ONLY','root':str(root.resolve()),'errors':errors}
    (root/'acceptance_gate.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    return result

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('root',type=Path); a=ap.parse_args(); r=validate(a.root.resolve()); print(json.dumps(r,indent=2)); raise SystemExit(0 if r['status']=='PASS_SCREENING' else 2)
