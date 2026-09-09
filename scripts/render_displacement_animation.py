#!/usr/bin/env python3
"""Visual-only 1x/10x deformation animation for virtual screening."""
from __future__ import annotations
import argparse,json,subprocess
from pathlib import Path
import numpy as np, pyvista as pv

def main():
 ap=argparse.ArgumentParser(); ap.add_argument('--series',type=Path,required=True); ap.add_argument('--quality',type=Path,required=True); ap.add_argument('--out',type=Path,required=True); ap.add_argument('--kind',choices=['warpage','sink','shrink'],required=True); ap.add_argument('--scales',default='1,10,50,100'); args=ap.parse_args()
 args.out.mkdir(parents=True,exist_ok=True)
 files=json.loads(args.series.read_text())['files']; sel=[x for x in files if float(x['time'])<=.5]
 if sel[-1]['name']!=files[-1]['name']: sel.append(files[-1])
 base=pv.read(args.quality)
 for scale in [int(x) for x in args.scales.split(',')]:
  frames=[]
  for i,it in enumerate(sel):
   snap=pv.read(args.series.parent/Path(it['name']).stem/'internal.vtu'); alpha=np.asarray(snap.cell_data['alpha.polymer'],float)
   g=base.copy(); risk=np.asarray(g.cell_data['warpage_risk_proxy' if args.kind=='warpage' else 'sink_risk_proxy'],float)
   if args.kind=='shrink' and 'pvt_shrink_strain' in g.cell_data: risk=np.clip(np.abs(np.asarray(g.cell_data['pvt_shrink_strain'],float))/0.01,0,1)
   dyn=np.clip(risk*(.05+.95*alpha),0,1)
   centers=np.asarray(g.cell_centers().points); xmin,xmax=centers[:,0].min(),centers[:,0].max(); ymin,ymax=centers[:,1].min(),centers[:,1].max()
   xx=(centers[:,0]-(xmin+xmax)/2)/max((xmax-xmin)/2,1e-12); yy=(centers[:,1]-(ymin+ymax)/2)/max((ymax-ymin)/2,1e-12)
   if args.kind=='warpage': shape=.5*(xx*xx-yy*yy)
   else: shape=-np.exp(-((xx/.55)**2+(yy/.55)**2))
   disp=dyn*shape*0.0002*scale # 0.2 mm base virtual magnitude, 2 mm at 10x
   # Prefer the thermo/PVT-derived shrink strain when the E2E output carries it;
   # fall back to the relative-risk field only for legacy screening artefacts.
   if 'pvt_shrink_strain' in g.cell_data:
    pvt=np.asarray(g.cell_data['pvt_shrink_strain'],float)
    pvt_norm=np.clip(np.abs(pvt)/max(float(np.percentile(np.abs(pvt),95)),1e-12),0,1)
    disp=(np.sign(shape)*pvt_norm*np.abs(shape)*0.0002*scale)
    dyn=pvt_norm
   g.cell_data['virtual_displacement_m']=disp.astype('float32')
   g.cell_data['visual_risk']=dyn.astype('float32')
   s=g.extract_surface().cell_data_to_point_data(); pts=s.points.copy(); z0=pts[:,2].mean(); # point proxy from surface data
   d=np.asarray(s.point_data['virtual_displacement_m']); s.points[:,2]+=d
   s.point_data['displacement_mm']=(d*1000.0).astype('float32')
   p=pv.Plotter(off_screen=True,window_size=(1400,800)); p.set_background('white')
   # Make the deformation visible: colored displacement plus undeformed outline.
   lim=0.2*scale; p.add_mesh(s,scalars='visual_risk',cmap='turbo',clim=(0,1),show_edges=False,
                              scalar_bar_args={'title':f'Virtual deformation field ({scale}x)'})
   p.add_mesh(base.extract_surface(),color='black',style='wireframe',line_width=1,opacity=.22)
   p.view_isometric(); p.camera.zoom(1.2); p.add_text(f'{args.kind} deformation {scale}x | t={it["time"]:.2f} s | virtual displacement | SCREENING ONLY',color='black',font_size=18)
   fn=args.out/f'{args.kind}_{scale}x_{i:03d}.png'; p.screenshot(fn); p.close(); frames.append(fn)
  mp4=args.out/f'box100x60x50_{args.kind}_deformation_{scale}x.mp4'; subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','4','-i',str(args.out/f'{args.kind}_{scale}x_%03d.png'),'-pix_fmt','yuv420p',str(mp4)],check=True)
  for f in frames: f.unlink()
 print(json.dumps({'kind':args.kind,'scales':[1,10],'base_virtual_displacement_mm':.2,'status':'VISUAL_EXAGGERATION_ONLY'},indent=2))
if __name__=='__main__': main()
