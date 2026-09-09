#!/usr/bin/env python3
"""Visual-only 1x/10x deformation animation for virtual screening."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
import numpy as np, pyvista as pv

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--series',type=Path,required=True); ap.add_argument('--quality',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--kind',choices=['warpage','sink'],required=True); args=ap.parse_args()
 args.out.mkdir(parents=True,exist_ok=True)
 files=json.loads(args.series.read_text())['files']; sel=[x for x in files if float(x['time'])<=.5]
 if sel[-1]['name']!=files[-1]['name']: sel.append(files[-1])
 base=pv.read(args.quality)
 for scale in (1,10):
  frames=[]
  for i,it in enumerate(sel):
   snap=pv.read(args.series.parent/Path(it['name']).stem/'internal.vtu'); alpha=np.asarray(snap.cell_data['alpha.polymer'],float)
   g=base.copy(); risk=np.asarray(g.cell_data['warpage_risk_proxy' if args.kind=='warpage' else 'sink_risk_proxy'],float)
   dyn=np.clip(risk*(.05+.95*alpha),0,1)
   centers=np.asarray(g.cell_centers().points); xmin,xmax=centers[:,0].min(),centers[:,0].max(); ymin,ymax=centers[:,1].min(),centers[:,1].max()
   xx=(centers[:,0]-(xmin+xmax)/2)/max((xmax-xmin)/2,1e-12); yy=(centers[:,1]-(ymin+ymax)/2)/max((ymax-ymin)/2,1e-12)
   if args.kind=='warpage': shape=.5*(xx*xx-yy*yy)
   else: shape=-np.exp(-((xx/.55)**2+(yy/.55)**2))
   disp=dyn*shape*0.0002*scale # 0.2 mm base virtual magnitude, 2 mm at 10x
   g.cell_data['virtual_displacement_m']=disp.astype('float32')
   s=g.extract_surface().cell_data_to_point_data(); pts=s.points.copy(); z0=pts[:,2].mean(); # point proxy from surface data
   d=np.asarray(s.point_data['virtual_displacement_m']); s.points[:,2]+=d
   p=pv.Plotter(off_screen=True,window_size=(1400,800)); p.set_background('white'); p.add_mesh(s,color='lightsteelblue',show_edges=False)
   p.view_isometric(); p.camera.zoom(1.2); p.add_text(f'{args.kind} deformation {scale}x | t={it["time"]:.2f} s | virtual displacement | SCREENING ONLY',color='black',font_size=18)
   fn=args.out/f'{args.kind}_{scale}x_{i:03d}.png'; p.screenshot(fn); p.close(); frames.append(fn)
  mp4=args.out/f'box100x60x50_{args.kind}_deformation_{scale}x.mp4'; subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','4','-i',str(args.out/f'{args.kind}_{scale}x_%03d.png'),'-pix_fmt','yuv420p',str(mp4)],check=True)
  for f in frames: f.unlink()
 print(json.dumps({'kind':args.kind,'scales':[1,10],'base_virtual_displacement_mm':.2,'status':'VISUAL_EXAGGERATION_ONLY'},indent=2))
if __name__=='__main__': main()
