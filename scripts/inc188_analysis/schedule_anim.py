# -*- coding: utf-8 -*-
"""INC-188: explanatory animation - punch / stripper motion of the single-stroke model (P1r34f) versus the
station-like model (P1r36f). Side view, not to scale horizontally. usage: python schedule_anim.py OUT.mp4"""
import os
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import Rectangle

for cand in ("Yu Gothic", "Meiryo", "MS Gothic"):
    if cand in {f.name for f in fm.fontManager.ttflist}:
        plt.rcParams["font.family"] = cand
        break

TIP0 = {"矩形": 1.8, "トリム": 2.4, "丸": 3.0}
XC = {"矩形": 1.0, "トリム": 2.2, "丸": 3.4}
W = 0.6


def interp(pts, t):
    xs, ys = zip(*pts)
    return float(np.interp(t, xs, ys))


old = [(0, 0), (50, -0.745), (501, -3.0), (511, -3.0), (731, -0.8), (2000, -0.8)]            # all punches (um, mm)
old_str = [(0, 0), (40, -0.19), (731, -0.19), (761, 0.11), (2000, 0.11)]
new = {"矩形": [(0, 0), (40, 0), (92.7, -0.790), (274.7, -1.70), (374.7, -0.70), (2000, -0.70)],
       "トリム": [(0, 0), (274.7, 0), (367.3, -1.390), (549.3, -2.30), (649.3, -1.30), (2000, -1.30)],
       "丸": [(0, 0), (549.3, 0), (682.0, -1.990), (864.0, -2.90), (964.0, -1.90), (2000, -1.90)]}
new_str = [(0, 0), (40, -0.19), (964, -0.19), (994, 0.11), (2000, 0.11)]
plug_off = {"矩形": 90.7, "トリム": 365.3, "丸": 680.0}


def draw(ax, t, station):
    ax.add_patch(Rectangle((0.3, 0.0), 3.8, 0.5, fc="#9aa5ab", ec="none"))           # die
    for k in XC:
        ax.add_patch(Rectangle((XC[k] - W / 2 - 0.02, 0.0), W + 0.04, 0.5, fc="white", ec="none"))  # die opening
    ax.add_patch(Rectangle((0.3, 0.505), 3.8, 0.5, fc="#c9a227", ec="none", alpha=0.85))  # sheet
    s = interp(new_str if station else old_str, t)
    zs = 1.2 + s
    ax.add_patch(Rectangle((0.3, zs), 3.8, 0.35, fc="#5f7d8c", ec="none"))           # stripper
    for k in XC:
        ax.add_patch(Rectangle((XC[k] - W / 2 - 0.02, zs), W + 0.04, 0.35, fc="white", ec="none"))  # opening
        if station and t < plug_off[k]:
            ax.add_patch(Rectangle((XC[k] - W / 2, zs), W, 0.35, fc="#3e8ed0", ec="none"))  # plug
        d = interp(new[k] if station else old, t)
        tip = TIP0[k] + d
        ax.add_patch(Rectangle((XC[k] - W / 2, tip), W, 1.6, fc="#2b2f33", ec="none"))  # punch
        ax.text(XC[k], 3.25, k, ha="center", fontsize=11)
    ax.set_xlim(0.3, 4.1); ax.set_ylim(-0.2, 3.5); ax.set_aspect("equal"); ax.set_xticks([]); ax.set_yticks([0, 0.5, 1.0, 2.0, 3.0])
    ax.set_ylabel("高さ [mm]")


out = sys.argv[1]
tmp = out + "_frames"
os.makedirs(tmp, exist_ok=True)
for k, t in enumerate(np.arange(0, 1010, 10)):
    fig, axs = plt.subplots(1, 2, figsize=(13, 6.2), dpi=90)
    draw(axs[0], t, False); axs[0].set_title("従来（P1r34f）：3本が一緒に下がる、ストリッパーは全部の穴が開いている", fontsize=10)
    draw(axs[1], t, True); axs[1].set_title("工程ごと（P1r36f）：1本ずつ抜く、まだ抜かない穴は栓（青）で押さえる", fontsize=10)
    fig.suptitle(f"パンチとストリッパーの動き（計算時刻 {t:.0f} µs）  黄＝板、黒＝パンチ、灰＝ダイ、濃灰＝ストリッパー", fontsize=12)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(os.path.join(tmp, f"{k:04d}.png")); plt.close(fig)
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", "10", "-i", os.path.join(tmp, "%04d.png"),
                "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "28",
                "-movflags", "+faststart", out], check=True)
print("wrote", out, os.path.getsize(out))
