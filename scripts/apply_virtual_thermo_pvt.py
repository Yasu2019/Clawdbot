#!/usr/bin/env python3
"""Apply the virtual thermal/rheology/PVT chain to a screening VTU.

This is a deterministic theory-path test.  The resulting fields are tagged
virtual and must be replaced by measured material data before design use.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np, pyvista as pv
from molding_physics_models import cross_wlf_viscosity, pvt_shrink_strain, solidification_fraction, anisotropic_shrink_strain, fiber_orientation_tensor

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); args=ap.parse_args()
 g=pv.read(args.input); alpha=np.asarray(g.cell_data['alpha_fill'] if 'alpha_fill' in g.cell_data else g.cell_data['alpha.polymer'],float)
 arr=np.asarray(g.cell_data['arrival_time_s'],float); p=np.asarray(g.cell_data['pressure_MPa_calibrated'],float)
 # Virtual melt-to-mold cooling over the arrival/packing history.
 T=235.0-45.0*np.clip(arr/max(float(arr.max()),1e-12),0,1)
 shear=np.maximum(1e-3, np.asarray(g.cell_data.get('U',np.zeros((g.n_cells,3))))[:,0] if 'U' in g.cell_data else np.full(g.n_cells,10.0))
 # Cap the virtual rheology for numerical conditioning; the measured card
 # must provide the valid low-temperature branch and solver limits.
 eta=np.array([min(1.0e9,cross_wlf_viscosity(float(t),float(s))) for t,s in zip(T,shear)])
 solid=np.array([solidification_fraction(float(t)) for t in T])
 shrink=np.array([pvt_shrink_strain(float(t),float(pp),crystallinity=0.0) for t,pp in zip(T,p)])
 orient=fiber_orientation_tensor((1,0,0)); anis=np.array([anisotropic_shrink_strain(float(e),orient) for e in shrink])
 # Two-domain Tait density screening expression (positive, finite).
 rho=900.0/(1.0-0.0894*np.log1p(np.maximum(p,0.0)/200.0)) * (1.0-2.0e-4*(T-230.0))
 for n,v in {'temperature_C_theory':T,'cross_wlf_viscosity_Pa_s':eta,'solidification_fraction':solid,'tait_density_kg_m3':rho,'pvt_shrink_strain':shrink,'shrink_x':anis[:,0],'shrink_y':anis[:,1],'shrink_z':anis[:,2]}.items(): g.cell_data[n]=np.asarray(v,dtype=np.float32)
 args.output.parent.mkdir(parents=True,exist_ok=True); g.save(args.output,binary=True)
 m={'status':'VIRTUAL_THEORY_PATH_COMPLETE','formal_status':'SCREENING_ONLY','cells':int(g.n_cells),'fields_added':['temperature_C_theory','cross_wlf_viscosity_Pa_s','tait_density_kg_m3','pvt_shrink_strain','shrink_x','shrink_y','shrink_z'],'summary':{'temperature_C':[float(T.min()),float(T.max())],'viscosity_Pa_s':[float(eta.min()),float(eta.max())],'density_kg_m3':[float(rho.min()),float(rho.max())],'shrink_strain':[float(shrink.min()),float(shrink.max())]},'replace_with_measured':['PVT','Cross-WLF parameters','cooling curve','CTE']}
 (args.output.with_suffix('.manifest.json')).write_text(json.dumps(m,indent=2)+'\n'); print(json.dumps(m,indent=2))
if __name__=='__main__': main()
