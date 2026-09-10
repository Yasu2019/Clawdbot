"""Render one OpenFOAM field at a time as a spatial 3-D MP4."""
import argparse, re, tempfile
from pathlib import Path
import pyvista as pv
from PIL import Image
import imageio.v2 as iio
import subprocess

ap = argparse.ArgumentParser()
ap.add_argument('vtk_dir', type=Path)
ap.add_argument('out', type=Path)
ap.add_argument('--field', default='alpha.polymer')
ap.add_argument('--title', default='OpenFOAM spatial field')
ap.add_argument('--clip-x-mm', type=float, default=None,
                help='Keep the x >= value side to expose the internal fill front')
ap.add_argument('--youtube', action='store_true',
                help='Render 16:9 1920x1080 output at 30 fps')
ap.add_argument('--camera', choices=('iso', 'top_oblique'), default='iso',
                help='Camera view; top_oblique shows the bottom round hole through the opening')
args = ap.parse_args()
vtk_dir, out = args.vtk_dir, args.out
def snapshot_key(path: Path) -> tuple[int, str]:
    """Sort VTK snapshots by numeric export index, never lexicographically."""
    match = re.search(r"case_(\d+)\.vtm$", path.name)
    return (int(match.group(1)), path.name) if match else (10**18, path.name)

files = sorted(vtk_dir.glob('case_*.vtm'), key=snapshot_key)
if not files: raise SystemExit('no VTK snapshots')
frames=[]
with tempfile.TemporaryDirectory() as td:
    for i, f in enumerate(files):
        mb=pv.read(f); mesh=mb['internal']
        if args.clip_x_mm is not None:
            mesh = mesh.clip(normal='x', origin=(args.clip_x_mm, 0, 0), invert=False)
        size = (1920,1080) if args.youtube else (960,540)
        pl=pv.Plotter(off_screen=True, window_size=size); pl.set_background('white')
        if args.field in mesh.array_names: pl.add_mesh(mesh, scalars=args.field, cmap='turbo', clim=[0,1], opacity=1.0, show_edges=False)
        else: pl.add_mesh(mesh, color='steelblue', show_edges=False)
        pl.add_text(f'{args.title} | {args.field} | snapshot {f.stem} | VIRTUAL SCREENING', font_size=18 if args.youtube else 12, color='black')
        if args.camera == 'top_oblique':
            # High oblique view is intentional: the front wall must not hide
            # the open-box bottom and its round hole.
            pl.camera_position=((0.155,-0.125,0.245),(0.05,0.03,0.004),(0,0,1))
            pl.camera.zoom(1.02)
        else:
            pl.camera_position='iso'
        pl.add_axes(); png=Path(td)/f'{i:04d}.png'; pl.screenshot(str(png)); pl.close(); frames.append(iio.imread(png))
    out.parent.mkdir(parents=True, exist_ok=True)
    for j, frame in enumerate(frames): iio.imwrite(Path(td)/f'{j:04d}.png', frame)
    fps = '30' if args.youtube else '2'
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate',fps,'-i',str(Path(td)/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p','-movflags','+faststart',str(out)], check=True)
print(out)
