#!/usr/bin/env python3
"""Render the gate/vent/viscosity-aware virtual weld candidate field."""
from __future__ import annotations
import argparse, subprocess, tempfile
from pathlib import Path
import numpy as np
import pyvista as pv

def main() -> int:
    ap=argparse.ArgumentParser(); ap.add_argument('--input',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); a=ap.parse_args()
    g=pv.read(a.input); arrival=np.asarray(g.cell_data['virtual_arrival_time_s'],float); weld=np.asarray(g.cell_data['virtual_weld_candidate'],float)
    tmax=float(arrival.max()); times=np.linspace(0,tmax,31)
    with tempfile.TemporaryDirectory() as td:
        for i,t in enumerate(times):
            # Candidate color persists after local front arrival; this avoids
            # the misleading disappearance seen in the old weld animation.
            field=np.where(arrival <= t, weld, 0.0).astype(np.float32)
            g.cell_data['display_weld_candidate']=field
            p=pv.Plotter(off_screen=True,window_size=(1920,1080)); p.set_background('white')
            p.add_mesh(g.extract_surface(),scalars='display_weld_candidate',cmap='turbo',clim=(0,1),scalar_bar_args={'title':'Weld candidate 0-1'})
            p.camera_position=((0.185,-0.145,0.315),(0.05,0.03,0.004),(0,0,1)); p.camera.zoom(1.0); p.add_axes()
            p.add_text('Weld-line candidate | gate/vent/viscosity-aware arrival | blue=low, red=high | virtual only',color='black',font_size=24)
            p.add_text(f'front-arrival time t={t:.2f} s | not weld strength',position='lower_left',color='black',font_size=20)
            p.screenshot(str(Path(td)/f'{i:04d}.png')); p.close()
        a.out.parent.mkdir(parents=True,exist_ok=True)
        subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','3','-i',str(Path(td)/'%04d.png'),'-r','30','-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(a.out)],check=True)
    print(a.out); return 0
if __name__=='__main__': raise SystemExit(main())
