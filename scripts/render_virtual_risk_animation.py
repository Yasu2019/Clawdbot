#!/usr/bin/env python3
"""Render time-varying virtual risk animations from OpenFOAM VTK snapshots."""
from __future__ import annotations
import argparse, json, subprocess
from pathlib import Path
import numpy as np
import pyvista as pv

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--series',type=Path,required=True); ap.add_argument('--quality',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--case',default='box100x60x50')
    a=ap.parse_args(); out=a.out.resolve(); out.mkdir(parents=True,exist_ok=True)
    series=json.loads(a.series.read_text())['files']; selected=series[::max(1,len(series)//12)]
    if selected[-1]['name'] != series[-1]['name']: selected.append(series[-1])
    base=pv.read(a.quality); names=['warpage','sink','weld','airtrap']
    surfaces={n:base.extract_surface() for n in names}
    # Keep camera and scalar range identical across frames.
    for n in names:
        frames=[]
        for i,item in enumerate(selected):
            # The converter emits both case_N.vtm and case_N/internal.vtu.
            internal=a.series.parent/Path(item['name']).stem/'internal.vtu'
            snap=pv.read(internal); alpha=np.asarray(snap.cell_data['alpha.polymer'],float)
            g=base.copy()
            if n=='airtrap': field=np.clip(1-alpha,0,1)
            elif n=='weld': field=np.clip(np.asarray(base.cell_data['weld_risk_proxy'])*np.exp(-((alpha-.55)/.30)**2),0,1)
            elif n=='sink': field=np.clip(np.asarray(base.cell_data['sink_risk_proxy'])*(0.08+0.92*alpha),0,1)
            else: field=np.clip(np.asarray(base.cell_data['warpage_risk_proxy'])*(0.08+0.92*alpha),0,1)
            g.cell_data['anim_field']=field.astype(np.float32)
            p=pv.Plotter(off_screen=True,window_size=(1400,800)); p.set_background('white')
            p.add_mesh(g.extract_surface(),scalars='anim_field',cmap='turbo',clim=(0,1),scalar_bar_args={'title':'Relative risk 0-1'})
            p.view_xy(); p.camera.roll=90; p.camera.zoom(1.15)
            p.add_text(f'{a.case} {n} | t={item["time"]:.2f} s | VIRTUAL SCREENING ONLY',color='black',font_size=18)
            fn=out/f'{n}_{i:03d}.png'; p.screenshot(fn); p.close(); frames.append(fn)
        mp4=out/f'{a.case}_{n}_virtual_animation.mp4'
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','6','-i',str(out/f'{n}_%03d.png'),'-pix_fmt','yuv420p',str(mp4)],check=True)
        for f in frames: f.unlink()
    (out/'animation_manifest.json').write_text(json.dumps({'status':'ANIMATED_FROM_OPENFOAM_TIME_SERIES','frames':len(selected),'videos':[str(x) for x in out.glob('*.mp4')]},indent=2)+'\n')
    print(json.dumps({'frames':len(selected),'out':str(out)},indent=2)); return 0
if __name__=='__main__': raise SystemExit(main())
