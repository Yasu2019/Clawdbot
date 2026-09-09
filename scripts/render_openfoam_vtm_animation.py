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
        mb=pv.read(f); mesh=mb['internal']; pl=pv.Plotter(off_screen=True, window_size=(960,540)); pl.set_background('white')
        if args.field in mesh.array_names: pl.add_mesh(mesh, scalars=args.field, cmap='turbo', clim=[0,1], opacity=1.0, show_edges=False)
        else: pl.add_mesh(mesh, color='steelblue', show_edges=False)
        pl.add_text(f'{args.title} | {args.field} | snapshot {f.stem} | PROXY_GAP', font_size=12, color='black'); pl.camera_position='iso'; pl.add_axes(); png=Path(td)/f'{i:04d}.png'; pl.screenshot(str(png)); pl.close(); frames.append(iio.imread(png))
    out.parent.mkdir(parents=True, exist_ok=True)
    for j, frame in enumerate(frames): iio.imwrite(Path(td)/f'{j:04d}.png', frame)
    subprocess.run(['ffmpeg','-y','-loglevel','error','-framerate','2','-i',str(Path(td)/'%04d.png'),'-c:v','libx264','-pix_fmt','yuv420p',str(out)], check=True)
print(out)
