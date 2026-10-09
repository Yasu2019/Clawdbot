# -*- coding: utf-8 -*-
"""INC-188: side-by-side animation of several 2D axisymmetric runs at the same frame (= same stroke).
usage: python axi_anim4.py DIR OUT.mp4 "TAG:label" ["TAG:label" ...]"""
import os
import subprocess
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.collections import PolyCollection

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from axi_analyze import read_vtk  # noqa: E402

for cand in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if cand in {f.name for f in fm.fontManager.ttflist}:
        plt.rcParams["font.family"] = cand
        break

d, out = sys.argv[1], sys.argv[2]
runs = [a.split(":", 1) for a in sys.argv[3:]]
tmp = out + "_frames"
os.makedirs(tmp, exist_ok=True)
for k, fr in enumerate(range(1, 41)):
    fig, axs = plt.subplots(1, len(runs), figsize=(4.2 * len(runs), 6.2), dpi=90, squeeze=False)
    t_show = None
    for ax, (tag, lab) in zip(axs[0], runs):
        p = f"{d}/vtk_{tag}/f{fr:03d}.vtk"
        if not os.path.exists(p):
            ax.set_axis_off(); continue
        t, pts, cells, data = read_vtk(p)
        t_show = t
        part = [int(v) for v in data["PART_ID"]]
        ero = [int(v) for v in data["EROSION_STATUS"]]
        ep = [float(v) for v in data.get("3DELEM_Plastic_Strain", ["0"] * len(cells))]
        live = [c for c, e in zip(range(len(cells)), ero) if e == 1]
        polys = [[(pts[n][0] * 1e3, pts[n][2] * 1e3) for n in cells[c][:4]] for c in live]
        cols = [ep[c] if part[c] == 2 else -1 for c in live]
        pc = PolyCollection(polys, array=cols, cmap="turbo", clim=(0, 1.5), edgecolors="none")
        pc.cmap.set_under("#b8b8b8")
        ax.add_collection(pc)
        ax.set_xlim(0.18, 0.42); ax.set_ylim(-0.12, 0.56); ax.set_aspect("equal")
        ax.set_title(lab, fontsize=10)
        ax.set_xlabel("半径 r [mm]")
    axs[0][0].set_ylabel("高さ z [mm]")
    if t_show is not None:
        fig.suptitle(f"丸穴の断面（2D 軸対称）  パンチの押し込み量 {max(0.0, (5 * t_show - 3e-6) * 1e3):.3f} mm（板厚 0.5 mm）", fontsize=13)
    fig.colorbar(pc, ax=axs[0].tolist(), fraction=0.02, pad=0.01, label="相当塑性ひずみ（灰色＝工具）")
    fig.savefig(os.path.join(tmp, f"{k:04d}.png")); plt.close(fig)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "5", "-i", os.path.join(tmp, "%04d.png"),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "26",
                "-movflags", "+faststart", out], check=True)
print("wrote", out, os.path.getsize(out))
