#!/usr/bin/env python3
"""Derive separate, explicitly labelled void-mechanism screening fields."""
from __future__ import annotations
import argparse,json
from pathlib import Path
import numpy as np, pyvista as pv

MECHANISMS={
 'air_entrapment':'cavity air trapped by advancing front / vent distance',
 'material_gas':'moisture, volatiles, or degradation gas; requires material/process data',
 'pvt_shrink_void':'skin/core solidification and volumetric shrinkage under low pressure',
 'underpack':'insufficient pressure during packing/hold',
 'gate_freeze':'gate solidification before packing pressure reaches the cavity',
 'thick_section':'thick section or thickness transition retains hot core',
 'weld_adjacent':'front meeting / weld-adjacent pressure and cooling risk',
 'cold_fill':'low melt temperature or premature solidification during fill',
 'thermal_degradation':'temperature-time exposure above degradation threshold',
 'fiber_density':'fiber orientation/density heterogeneity; requires fiber/material data',
 'geometry_constriction':'round-hole, corner, and local-thickness flow-constriction risk',
}

def derive(source: Path, out: Path, card: Path | None = None) -> dict:
 g=pv.read(source); n=g.n_cells; a=np.asarray(g.cell_data.get('alpha_fill',g.cell_data.get('alpha.polymer')),float)
 p=np.asarray(g.cell_data.get('pressure_MPa_calibrated',np.full(n,1.0)),float)
 t=np.asarray(g.cell_data.get('temperature_C_theory',g.cell_data.get('temperature_C_proxy',np.full(n,200.0))),float)
 solid=np.asarray(g.cell_data.get('solidification_fraction',np.clip((260-t)/80,0,1)),float)
 shrink=np.abs(np.asarray(g.cell_data.get('pvt_shrink_strain',np.zeros(n)),float))
 arrival=np.asarray(g.cell_data.get('arrival_time_s',np.zeros(n)),float)
 weld=np.asarray(g.cell_data.get('weld_risk_proxy',np.zeros(n)),float)
 centers=np.asarray(g.cell_centers().points); x,y,z=centers.T
 vent_dist=np.minimum(np.abs(x-0.1),np.abs(x-0.0))/0.1
 thick=np.asarray(g.cell_data.get('half_thickness_m_proxy',np.zeros(n)),float)
 region=np.asarray(g.cell_data.get('surface_region_id',np.zeros(n)),float)
 edge_x=np.minimum(x-x.min(),x.max()-x)
 edge_y=np.minimum(y-y.min(),y.max()-y)
 corner=np.exp(-edge_x/0.003)*np.exp(-edge_y/0.003)
 hole=(region==7).astype(float)
 t25,t90=np.percentile(thick,[25,90]) if np.ptp(thick)>0 else (0.0,1.0)
 thick_factor=np.clip((thick-t25)/max(t90-t25,1e-12),0,1)
 geometry_constriction=np.clip(0.45*hole+0.35*corner+0.20*thick_factor,0,1)
 card_data = {}
 if card is not None and card.exists():
  card_data = json.loads(card.read_text(encoding='utf-8'))
 gas_cfg = card_data.get('gas_generation', {})
 moisture = max(float(gas_cfg.get('moisture_ppm', 0.0)), 0.0)
 volatile = max(float(gas_cfg.get('volatile_mass_fraction', 0.0)), 0.0)
 degradation_c = float(gas_cfg.get('degradation_temperature_C', 280.0))
 # The virtual card defaults to zero gas.  When measured card values are
 # supplied, moisture/volatile loading scales the gas source and temperature
 # above the degradation threshold activates it.  This is a screening proxy,
 # not a kinetic gas-generation model.
 gas_load = np.clip(moisture / 1000.0 + volatile / 0.01, 0.0, 1.0)
 gas_activation = np.clip((t - degradation_c) / 40.0, 0.0, 1.0)
 material_gas = np.clip(gas_load * (0.25 + 0.75 * gas_activation) * (0.5 + 0.5 * (1.0 - solid)), 0.0, 1.0)
 fields={
  'air_entrapment':np.clip((1-a)*(.5+.5*vent_dist),0,1),
  'material_gas':material_gas,
  'pvt_shrink_void':np.clip(shrink/0.01*(1-solid)*(1-np.clip(p/30,0,1)),0,1),
  'underpack':np.clip((10-p)/10,0,1),
  'gate_freeze':np.clip(solid*(arrival<0.5),0,1),
  'thick_section':np.clip((thick-np.percentile(thick,50))/max(np.ptp(thick),1e-12),0,1),
  'weld_adjacent':np.clip(weld,0,1),
  'cold_fill':np.clip((180-t)/80,0,1),
  'thermal_degradation':np.clip((t-280)/40,0,1),
  'fiber_density':np.zeros(n),
  'geometry_constriction':geometry_constriction,
 }
 for k,v in fields.items(): g.cell_data['void_'+k+'_risk']=np.asarray(v,dtype=np.float32)
 out.parent.mkdir(parents=True,exist_ok=True); g.save(out,binary=True)
 summary={k:{'mean':float(np.mean(v)),'max':float(np.max(v)),'fraction_over_0_7':float(np.mean(v>=.7)),'status':'SCREENING_ONLY'} for k,v in fields.items()}
 unknown = [] if gas_cfg.get('data_status') == 'MEASURED' else ['material_gas']
 unknown.append('fiber_density')
 manifest={'schema':'clawstack.void_mechanisms.v1','formal_status':'SCREENING_ONLY','source':str(source.resolve()),'output':str(out.resolve()),'cells':int(n),'mechanisms':MECHANISMS,'summary':summary,'gas_generation':{'card':str(card.resolve()) if card else None,'moisture_ppm':moisture,'volatile_mass_fraction':volatile,'degradation_temperature_C':degradation_c,'data_status':gas_cfg.get('data_status','UNSPECIFIED')},'unknown_without_measurements':unknown,'required_measurements':['moisture/volatile content','TGA/degradation curve','PVT','packing pressure','gate freeze time','fiber orientation']}
 out.with_suffix('.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n',encoding='utf-8'); return manifest

if __name__=='__main__':
 ap=argparse.ArgumentParser(); ap.add_argument('--source',type=Path,required=True); ap.add_argument('--output',type=Path,required=True); ap.add_argument('--card',type=Path); a=ap.parse_args(); print(json.dumps(derive(a.source.resolve(),a.output.resolve(),a.card.resolve() if a.card else None),ensure_ascii=False,indent=2))
