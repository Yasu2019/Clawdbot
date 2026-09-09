#!/usr/bin/env python3
"""Apply the virtual thermal/rheology/PVT chain to a screening VTU.

This is a deterministic theory-path test.  The resulting fields are tagged
virtual and must be replaced by measured material data before design use.
"""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np, pyvista as pv
from molding_physics_models import cross_wlf_viscosity, pvt_shrink_strain, solidification_fraction, anisotropic_shrink_strain, fiber_orientation_tensor, cooling_step

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--card',type=Path,default=Path('config/virtual_material_pp_screening.json')); args=ap.parse_args()
 card=json.loads(args.card.read_text(encoding='utf-8'))
 g=pv.read(args.input); alpha=np.asarray(g.cell_data['alpha_fill'] if 'alpha_fill' in g.cell_data else g.cell_data['alpha.polymer'],float)
 arr=np.asarray(g.cell_data['arrival_time_s'],float); p=np.asarray(g.cell_data['pressure_MPa_calibrated'],float)
 centers=np.asarray(g.cell_centers().points); x,y,z=centers.T
 face=np.zeros(g.n_cells,dtype=np.int16); mult=np.full(g.n_cells,0.75,dtype=float); tol=0.0025
 face[np.abs(x-0.0)<tol]=1; face[np.abs(x-0.1)<tol]=2
 face[(np.abs(y-0.0)<tol)&(face==0)]=3; face[(np.abs(y-0.06)<tol)&(face==0)]=4
 face[(np.abs(z-0.0)<tol)&(face==0)]=5; face[(np.abs(z-0.05)<tol)&(face==0)]=6
 hole=((x-0.05)**2+(y-0.03)**2 < 0.012**2); face[hole & (np.abs(z-0.001)<tol)]=7
 for k,v in {1:1.0,2:0.65,3:1.0,4:0.65,5:1.2,6:0.8,7:0.9}.items(): mult[face==k]=v
 # Virtual melt-to-mold cooling over the arrival/packing history.
 melt=float(card['process']['melt_temperature_K'])-273.15; mold=float(card['process']['mold_temperature_K'])-273.15
 thermal=card['thermal']; rho_card=float(thermal['rho_reference']); cp_card=float(thermal['cp']); h_card=float(thermal['wall_heat_transfer_W_m2K']); k_card=float(thermal['conductivity'])
 h_surface=h_card*mult
 T=np.array([cooling_step(melt,mold,max(float(t),0.0),h_w_m2k=float(h_surface[i]),thickness_m=0.002,rho_kg_m3=rho_card,cp_j_kgk=cp_card,conductivity_w_mk=k_card) for i,t in enumerate(arr)])
 shear=np.maximum(1e-3, np.asarray(g.cell_data.get('U',np.zeros((g.n_cells,3))))[:,0] if 'U' in g.cell_data else np.full(g.n_cells,10.0))
 # Cap the virtual rheology for numerical conditioning; the measured card
 # must provide the valid low-temperature branch and solver limits.
 w=card['cross_wlf']; eta0=min(1.0e6,float(w['D1'])); tau=float(w['tauStar_Pa']); wn=float(w['n']); ref=float(card['process']['melt_temperature_K'])-273.15; c1=float(w['A1']); c2=float(w['A2_C'])
 def safe_eta(t,s):
  try: return min(1.0e9,cross_wlf_viscosity(float(t),float(s),eta0_pa_s=eta0,tau_pa=tau,n=wn,ref_c=ref,wlf_c1=c1,wlf_c2=c2))
  except OverflowError: return 1.0e9
 eta=np.array([safe_eta(t,s) for t,s in zip(T,shear)])
 solid=np.array([solidification_fraction(float(t)) for t in T])
 cte=float(card['structural']['cte_1_K'])
 shrink=np.array([pvt_shrink_strain(float(t),float(pp),cte_1k=cte,crystallinity=0.0) for t,pp in zip(T,p)])
 orient=fiber_orientation_tensor((1,0,0)); anis=np.array([anisotropic_shrink_strain(float(e),orient) for e in shrink])
 # Two-domain Tait density screening expression using the card parameters.
 tait=card['tait_two_domain']; rho_ref=1.0/max(float(tait['A0']),1e-12); B_mpa=max(float(tait['B0'])/1e6,1e-6); C=float(tait['C']); b=float(tait['b']); tref=float(tait['Tref_K'])
 T_k=T+273.15
 rho=rho_ref/(1.0-C*np.log1p(np.maximum(p,0.0)/B_mpa)) * (1.0-b*(T_k-tref))
 rho=np.maximum(rho,1e-6)
 for n,v in {'temperature_C_theory':T,'cross_wlf_viscosity_Pa_s':eta,'solidification_fraction':solid,'tait_density_kg_m3':rho,'pvt_shrink_strain':shrink,'shrink_x':anis[:,0],'shrink_y':anis[:,1],'shrink_z':anis[:,2],'surface_region_id':face,'h_surface_W_m2K':h_surface}.items(): g.cell_data[n]=np.asarray(v,dtype=np.float32)
 args.output.parent.mkdir(parents=True,exist_ok=True); g.save(args.output,binary=True)
 m={'status':'VIRTUAL_THEORY_PATH_COMPLETE','formal_status':'SCREENING_ONLY','material_card':str(args.card.resolve()),'material_id':card['identity']['material_id'],'cells':int(g.n_cells),'fields_added':['temperature_C_theory','cross_wlf_viscosity_Pa_s','tait_density_kg_m3','pvt_shrink_strain','shrink_x','shrink_y','shrink_z'],'summary':{'temperature_C':[float(T.min()),float(T.max())],'viscosity_Pa_s':[float(eta.min()),float(eta.max())],'density_kg_m3':[float(rho.min()),float(rho.max())],'shrink_strain':[float(shrink.min()),float(shrink.max())]},'replace_with_measured':['PVT','Cross-WLF parameters','cooling curve','CTE']}
 (args.output.with_suffix('.manifest.json')).write_text(json.dumps(m,indent=2)+'\n'); print(json.dumps(m,indent=2))
if __name__=='__main__': main()
