#!/usr/bin/env python3
"""Run a deterministic virtual gate/vent/viscosity uncertainty ensemble."""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np
import pyvista as pv
from scipy.spatial import cKDTree

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--config',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    cfg=json.loads(a.config.read_text(encoding='utf-8')); obj=pv.read(a.source); g=obj['internal'] if hasattr(obj,'keys') and 'internal' in obj.keys() else obj
    xyz=np.asarray(g.cell_centers().points,float); gates=np.asarray(cfg['gates_mm'],float)/1000; vents=np.asarray(cfg['vents_mm'],float)/1000
    gd=np.linalg.norm(xyz[:,None,:]-gates[None,:,:],axis=2); gid=np.argmin(gd,axis=1).astype(np.int16); dist=gd.min(axis=1)
    vd=cKDTree(vents).query(xyz,k=1)[0]; _,nn=cKDTree(xyz).query(xyz,k=9,workers=1); diff=gid[nn[:,1:]]!=gid[:,None]
    rng=np.random.default_rng(int(cfg.get('seed',20260910))); n=int(cfg.get('samples',32));
    speed=rng.uniform(*cfg['injection_speed_m_s_range'],n); mu=rng.uniform(*cfg['viscosity_pa_s_range'],n); area=rng.uniform(*cfg['total_vent_area_mm2_range'],n)
    arrivals=[]; welds=[]; max_vd=float(cfg.get('vent_influence_length_mm',18))/1000; ref_mu=float(cfg.get('reference_viscosity_pa_s',80)); ref_speed=float(cfg.get('reference_speed_m_s',.02)); tau=float(cfg.get('weld_time_tolerance_s',.025))
    for s,m,ar in zip(speed,mu,area):
        visc=(m/ref_mu)**float(cfg.get('viscosity_exponent',.20)); relief=float(cfg.get('vent_relief_gain',.18))*(ar/max(float(cfg.get('reference_vent_area_mm2',12)),1e-12))*np.exp(-vd/max_vd); relief=np.clip(relief,0,float(cfg.get('max_vent_relief',.35)))
        # Compressible-air effect is represented only by a bounded vent-relief
        # proxy; no gas pressure PDE is claimed here.
        local=s/max(visc,1e-9)*(1+relief); at=dist/np.maximum(local,1e-9); arrivals.append(at)
        dt=np.abs(at[nn[:,1:]]-at[:,None]); md=np.min(np.where(diff,dt,np.inf),axis=1); welds.append(np.where(np.isfinite(md),np.exp(-md/tau),0.0))
    A=np.asarray(arrivals); W=np.asarray(welds); prob=(W>=float(cfg.get('candidate_threshold',.55))).mean(axis=0); mean=W.mean(axis=0); atmean=A.mean(axis=0)
    g.cell_data['ensemble_mean_arrival_s']=atmean.astype(np.float32); g.cell_data['ensemble_weld_probability']=prob.astype(np.float32); g.cell_data['ensemble_mean_weld_risk']=mean.astype(np.float32); g.cell_data['ensemble_arrival_p95_s']=np.percentile(A,95,axis=0).astype(np.float32)
    a.out.parent.mkdir(parents=True,exist_ok=True); g.save(a.out,binary=True)
    top=np.argsort(prob)[-max(1,g.n_cells//100):]; report={'status':'VIRTUAL_UNCERTAINTY_SCREENING','samples':n,'seed':int(cfg.get('seed',20260910)),'source':str(a.source.resolve()),'output':str(a.out.resolve()),'ranges':{'injection_speed_m_s':list(cfg['injection_speed_m_s_range']),'viscosity_pa_s':list(cfg['viscosity_pa_s_range']),'total_vent_area_mm2':list(cfg['total_vent_area_mm2_range'])},'weld_probability':{'threshold':float(cfg.get('candidate_threshold',.55)),'max':float(prob.max()),'mean':float(prob.mean()),'top_1pct_centroid_mm':(xyz[top].mean(0)*1000).tolist(),'top_1pct_bbox_min_mm':(xyz[top].min(0)*1000).tolist(),'top_1pct_bbox_max_mm':(xyz[top].max(0)*1000).tolist()},'limitations':['Virtual vent-relief proxy; no compressible-air pressure PDE.','No measured Cross-WLF/PVT/thermal calibration.','Probability is conditional on the stated virtual ranges.']}; a.out.with_suffix('.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); print(json.dumps(report,ensure_ascii=False,indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
