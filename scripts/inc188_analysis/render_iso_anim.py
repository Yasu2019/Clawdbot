# -*- coding: utf-8 -*-
"""INC-188: 3D isometric punching animation (pyvista, off-screen) - 2026-10-11.

Per frame, two views of the region around the round hole / H4 / H1 / H2:
  left  = isometric view from above, sheet coloured by equivalent plastic strain, punches (and
          station plugs) in translucent grey, die and stripper hidden;
  right = same view with the sheet cut along A-A (round-hole centre -> H4) to show the strain
          through the thickness.
Only live (not eroded) sheet elements are drawn, so cut lines open up as the punches go through.

usage: python render_iso_anim.py <label> <vtk_dir> <first> <last> <time_offset_ms> <out.mp4> "<title>"
"""
import glob
import os
import shutil
import subprocess
import sys

import numpy as np
import pyvista as pv

pv.OFF_SCREEN = True
HOLE = np.array([185.657e-3, -1882.188e-3])
H4 = np.array([185.55e-3, -1881.25e-3])
BOX = (HOLE[0] - 3.4e-3, HOLE[0] + 1.6e-3, HOLE[1] - 2.5e-3, HOLE[1] + 4.0e-3)   # x, y window [m]
FONT = "C:/Windows/Fonts/YuGothM.ttc"


def frame_png(path, png, title):
    g = pv.read(path)
    cen = g.cell_centers().points
    inbox = (cen[:, 0] > BOX[0]) & (cen[:, 0] < BOX[1]) & (cen[:, 1] > BOX[2]) & (cen[:, 1] < BOX[3])
    part = np.asarray(g.cell_data["PART_ID"]).astype(int)
    ero = np.asarray(g.cell_data["EROSION_STATUS"])
    eps = np.asarray(g.cell_data["3DELEM_Plastic_Strain"])
    sheet = g.extract_cells(np.where(inbox & (part == 2) & (ero >= 0.5))[0])
    sheet.cell_data["eps"] = eps[np.where(inbox & (part == 2) & (ero >= 0.5))[0]]
    tools = g.extract_cells(np.where(inbox & ((part == 4) | (part >= 5)) & (cen[:, 2] < 2.2e-3))[0])
    u = (H4 - HOLE) / np.linalg.norm(H4 - HOLE)
    normal = (-u[1], u[0], 0.0)
    pl = pv.Plotter(off_screen=True, shape=(1, 2), window_size=(1800, 820), border=False)
    for k, clip in enumerate((False, True)):
        pl.subplot(0, k)
        s = sheet.extract_surface(algorithm=None) if not clip else sheet.clip(normal=normal, origin=(HOLE[0], HOLE[1], 0.0), invert=False).extract_surface(algorithm=None)
        pl.add_mesh(s, scalars="eps", cmap="turbo", clim=(0, 0.8), show_scalar_bar=(k == 1),
                    scalar_bar_args={"title": "eps_p", "vertical": True, "position_x": 0.90, "position_y": 0.25, "height": 0.5})
        if tools.n_cells:
            t = tools.extract_surface(algorithm=None)
            if clip:
                t = t.clip(normal=normal, origin=(HOLE[0], HOLE[1], 0.0), invert=False)
            pl.add_mesh(t, color="#9aa3a8", opacity=0.35)
        pl.camera_position = [(HOLE[0] + 4.5e-3, HOLE[1] - 6.0e-3, 5.5e-3), (HOLE[0] - 0.6e-3, HOLE[1] + 0.6e-3, 0.6e-3), (0, 0, 1)]
        pl.camera.zoom(1.25)
        pl.add_text(("Cut along A-A (hole centre -> H4)" if clip else title), font_size=11, position="upper_left")
        h4p = np.array([[H4[0], H4[1], 1.02e-3]])
        pl.add_point_labels(h4p, ["H4"], font_size=14, text_color="magenta", point_color="magenta", point_size=10, shape=None)
    pl.screenshot(png)
    pl.close()


def main():
    label, vdir, f0, f1, off, out, title = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6], sys.argv[7]
    tmp = out + "_iso"
    os.makedirs(tmp, exist_ok=True)
    for fr in range(f0, f1 + 1):
        p = os.path.join(vdir, f"f{fr:03d}.vtk")
        png = os.path.join(tmp, f"{fr:04d}.png")
        if os.path.exists(png) or not os.path.exists(p) or os.path.getsize(p) < 10_000_000:
            continue
        try:
            with open(p, "rb") as fh:
                fh.seek(0)
                head = fh.read(4096).decode("ascii", "replace")
            t = float(head.split("TIME 1 1 double")[1].split()[0]) * 1e3
            frame_png(p, png, f"{title}   t = {t:.3f} ms" + (f" (standard {t + off:.3f} ms)" if off else ""))
            print(label, fr, f"t={t:.3f}", flush=True)
        except Exception as ex:   # truncated frame
            print(label, fr, "skip:", ex, flush=True)
    seq = tmp + "_seq"
    shutil.rmtree(seq, ignore_errors=True); os.makedirs(seq)
    for k, pth in enumerate(sorted(glob.glob(os.path.join(tmp, "*.png")))):
        shutil.copy(pth, os.path.join(seq, f"{k:04d}.png"))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "4", "-i", os.path.join(seq, "%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                    "-movflags", "+faststart", out], check=True)
    print("wrote", out, os.path.getsize(out))


if __name__ == "__main__":
    main()
