# -*- coding: utf-8 -*-
"""Punching animation (real OpenRadioss frames) around the round hole / H4 / H1 / H2.

Per frame, three panels:
  1. top view, equivalent plastic strain (blank, live elements, drawn bottom-up so the top layer shows)
  2. top view, von Mises stress
  3. vertical section along the line round-hole centre -> H4 (blank coloured by plastic strain, tools grey)
Orientation = the inset of Crack_発生位置_PM7TCB.pdf (model rotated 180 deg about the round hole,
right = -x_model, down = +y_model). Frames -> PNG -> MP4 (ffmpeg, H.264, yuv420p).

usage: python render_punch_anim.py <label> <vtk_dir> <first_frame> <last_frame> <time_offset_ms> <out.mp4> "<title>"
"""
import os
import re
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scan_rupture_sites import HOTSPOTS_MM   # noqa: E402

for cand in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if cand in {f.name for f in fm.fontManager.ttflist}:
        plt.rcParams["font.family"] = cand
        break

HOLE = np.array(HOTSPOTS_MM["ROUND_HOLE"])
H4 = np.array(HOTSPOTS_MM["H4"])
WIN_R = (-1.7, 3.7)      # right [mm] (drawing frame)
WIN_D = (-2.6, 4.2)      # down  [mm]
SEC_HALF = 0.015         # section slab half-thickness [mm]
SEC_S = (-0.9, 1.7)      # along hole -> H4 [mm]
SEC_Z = (-0.6, 1.9)      # z [mm]


def load(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    t = float(re.search(r"TIME 1 1 double\s+([-0-9.eE+]+)", txt).group(1))

    def section(header_re, count, per):
        m = re.search(header_re, txt, re.M)
        start = m.end()
        arr = np.fromstring(txt[start:start + 40 * count * per], sep=" ", count=count * per)
        return arr

    n = int(re.search(r"^POINTS (\d+)", txt, re.M).group(1))
    pts = section(r"^POINTS \d+ \w+\s*\n", n, 3).reshape(n, 3) * 1e3
    nc, ns = map(int, re.search(r"^CELLS (\d+) (\d+)", txt, re.M).groups())
    cells_raw = section(r"^CELLS \d+ \d+\s*\n", 1, ns).astype(np.int64)
    # tets only (5 ints per cell); fall back to a generic walk if mixed
    if ns == 5 * nc:
        cells = cells_raw.reshape(nc, 5)[:, 1:5]
    else:
        out, i = [], 0
        while len(out) < nc:
            k = cells_raw[i]; out.append(cells_raw[i + 1:i + 1 + min(k, 4)]); i += k + 1
        cells = np.array(out)

    def scal(name):
        m = re.search(r"^SCALARS " + re.escape(name) + r" \w+ 1\s*\nLOOKUP_TABLE \w+\s*\n", txt, re.M)
        if not m:
            return None
        return np.fromstring(txt[m.end():m.end() + 25 * nc], sep=" ", count=nc)

    return t, pts, cells, scal("PART_ID").astype(int), scal("EROSION_STATUS"), scal("3DELEM_Plastic_Strain"), scal("3DELEM_Von_Mises")


def main():
    label, vdir, f0, f1, off, out, title = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6], sys.argv[7]
    tmp = out + "_frames"
    os.makedirs(tmp, exist_ok=True)
    u = (H4 - HOLE) / np.linalg.norm(H4 - HOLE)          # section direction (model frame)
    hot = {k: np.array(HOTSPOTS_MM[k]) - HOLE for k in ("H4", "H1", "H2")}
    for i, fr in enumerate(range(f0, f1 + 1)):
        png = os.path.join(tmp, f"{i:04d}.png")
        if os.path.exists(png):
            continue
        t, P, C, part, ero, eps, vm = load(os.path.join(vdir, f"f{fr:03d}.vtk"))
        cen = P[C].mean(axis=1)
        dx, dy = cen[:, 0] - HOLE[0], cen[:, 1] - HOLE[1]
        R, D = -dx, dy                                      # drawing frame
        blank = (part == 2) & (ero >= 0.5)
        win = blank & (R > WIN_R[0]) & (R < WIN_R[1]) & (D > WIN_D[0]) & (D < WIN_D[1])
        idx = np.where(win)[0]
        idx = idx[np.argsort(cen[idx, 2])]                  # bottom first, top layer drawn last
        fig, ax = plt.subplots(1, 3, figsize=(19, 6.6), dpi=90, gridspec_kw={"width_ratios": [1, 1, 1.05]})
        for a, val, vmax, cm, lab in ((ax[0], eps, 0.8, "turbo", "相当塑性ひずみ"),
                                      (ax[1], vm / 1e6, 600, "inferno", "von Mises [MPa]")):
            sc = a.scatter(R[idx], D[idx], c=val[idx], s=1.0, cmap=cm, vmin=0, vmax=vmax, linewidths=0)
            a.set_xlim(*WIN_R); a.set_ylim(WIN_D[1], WIN_D[0]); a.set_aspect("equal")
            a.set_xlabel("右 [mm]"); a.set_ylabel("下 [mm]"); a.set_title(lab + "（上から）")
            plt.colorbar(sc, ax=a, fraction=0.046, pad=0.02)
            for k, h in hot.items():
                a.plot(-h[0], h[1], "+", color="white", ms=12, mew=2)
                a.text(-h[0] + 0.12, h[1] - 0.12, k, color="white", fontsize=11, weight="bold")
            a.add_patch(plt.Circle((0, 0), 0.28, fill=False, ec="white", ls=":", lw=1))
        # section
        rel = cen[:, :2] - HOLE
        s = rel @ u
        perp = rel @ np.array([-u[1], u[0]])
        sl = (np.abs(perp) < SEC_HALF) & (s > SEC_S[0]) & (s < SEC_S[1]) & (cen[:, 2] > SEC_Z[0]) & (cen[:, 2] < SEC_Z[1])
        tool = (np.abs(perp) < 0.12) & (s > SEC_S[0]) & (s < SEC_S[1]) & (cen[:, 2] > SEC_Z[0]) & (cen[:, 2] < SEC_Z[1]) & (part != 2)
        bl = sl & blank
        a = ax[2]
        a.scatter(s[tool], cen[tool, 2], c="#8a8a8a", s=22, linewidths=0, alpha=0.6)
        sc = a.scatter(s[bl], cen[bl, 2], c=eps[bl], s=3, cmap="turbo", vmin=0, vmax=0.8, linewidths=0)
        a.axvline(0.28, color="k", ls=":", lw=0.8); a.axvline(np.linalg.norm(H4 - HOLE), color="magenta", ls="--", lw=1)
        a.text(np.linalg.norm(H4 - HOLE), SEC_Z[1] - 0.1, " H4", color="magenta", fontsize=11)
        a.text(0.28, SEC_Z[1] - 0.1, " 丸パンチ刃先", fontsize=9)
        a.set_xlim(*SEC_S); a.set_ylim(*SEC_Z); a.set_aspect("equal")
        a.set_xlabel("丸穴中心 → H4 方向 [mm]"); a.set_ylabel("z [mm]"); a.set_title("断面（灰色＝パンチ・ダイ・ストリッパー）")
        plt.colorbar(sc, ax=a, fraction=0.046, pad=0.02)
        tstd = t * 1e3 + off
        fig.suptitle(f"{title}    t = {t*1e3:.3f} ms" + (f"（標準時刻 {tstd:.3f} ms）" if off else ""), fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, 0.95))
        fig.savefig(png); plt.close(fig)
        print(label, fr, f"t={t*1e3:.3f}", flush=True)
    ff = os.environ.get("FFMPEG", "ffmpeg")
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", "4", "-i", os.path.join(tmp, "%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "26", "-movflags", "+faststart", out], check=True)
    print("wrote", out, os.path.getsize(out))


if __name__ == "__main__":
    main()
