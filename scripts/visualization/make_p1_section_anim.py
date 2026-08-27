"""P1校正版の実VTKフレームから、矩形パンチを通る断面(y-z)のアニメーションを作る。
スラグが消滅せず下方へ落下することを、このセッションで検証済みの断面表示手法
(plot_section.py と同じ考え方)で明確に示す。演出・捏造なし。
"""
import sys
import glob
import re
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["animation.ffmpeg_path"] = (
    r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages\\"
    r"Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)
import matplotlib.pyplot as plt
from matplotlib.animation import FFMpegWriter


def load(path):
    with open(path, encoding="utf-8") as f:
        lines = f.read().split("\n")
    pi = [k for k, l in enumerate(lines) if l.startswith("POINTS ")][0]
    n = int(lines[pi].split()[1])
    pts, k = [], pi + 1
    while len(pts) < n:
        v = [float(x) for x in lines[k].split()]
        for j in range(0, len(v), 3):
            pts.append(v[j:j + 3])
        k += 1
    ci = [k for k, l in enumerate(lines) if l.startswith("CELLS ")][0]
    nc = int(lines[ci].split()[1])
    cells, k = [], ci + 1
    while len(cells) < nc:
        v = [int(x) for x in lines[k].split()]
        if v:
            cells.append(v[1:])
        k += 1

    def block(name, cast=float):
        idx = [k for k, l in enumerate(lines) if l.startswith("SCALARS " + name)]
        if not idx:
            return None
        out, k = [], idx[0] + 2
        while len(out) < nc and k < len(lines):
            out += [cast(float(x)) for x in lines[k].split()]
            k += 1
        return out[:nc]

    tl = [k for k, l in enumerate(lines) if l.strip() == "TIME 1 1 double"]
    t = float(lines[tl[0] + 1]) if tl else 0.0
    return pts[:n], cells, block("PART_ID", int), block("EROSION_STATUS"), t


files = sorted(glob.glob(sys.argv[1]), key=lambda p: int(re.search(r"f(\d\d)\.vtk", p).group(1)))
out = sys.argv[2]
print("frames:", len(files))

# 右下矩形パンチ(実測center ~186.809,-1883.546 [mm]、幅1.696x1.284)を通る
# y一定のスライスを取る。座標系はP1のグローバルオフセット(m)。
Y_SLICE = -1.883546
Y_TOL = 0.15e-3
X0, X1 = 0.1735, 0.1905     # モデル全幅
Z0, Z1 = -3.0e-3, 1.5e-3
COL = {1: "#4a6fa5", 2: "#c9553a", 3: "#4a6fa5", 4: "#4a6fa5"}

fig, ax = plt.subplots(figsize=(6.5, 7.5), dpi=110)
writer = FFMpegWriter(fps=5, metadata=dict(
    title="PANEL4MM_P1_calibrated cross-section (real OpenRadioss result)"))

with writer.saving(fig, out, dpi=110):
    for idx, path in enumerate(files):
        pts, cells, part, ero, t = load(path)
        ax.clear()
        n_slug = 0
        for c, p, e in zip(cells, part, ero):
            ys = [pts[n][1] for n in c]
            ymid = sum(ys) / len(ys)
            if abs(ymid - Y_SLICE) > Y_TOL:
                continue
            if p == 2 and e < 0.5:
                continue  # 削除要素は描かない
            xs = [pts[n][0] for n in c]
            zs = [pts[n][2] for n in c]
            xmin, xmax = min(xs), max(xs)
            zmin, zmax = min(zs), max(zs)
            if (xmax - xmin) > 1.0e-3 or (zmax - zmin) > 1.0e-3:
                continue  # 飛散した孤立要素は描かない(P1既知の挙動)
            ax.add_patch(plt.Rectangle((xmin, zmin), xmax - xmin, zmax - zmin,
                                       facecolor=COL.get(p, "#999"), edgecolor="none", alpha=0.85))
            if p == 2 and zmax < 0.9e-3:
                n_slug += 1
        ax.set_xlim(X0, X1)
        ax.set_ylim(Z0, Z1)
        ax.set_aspect("equal")
        ax.axhline(0.6e-3, color="#888", lw=0.5, ls=":")
        ax.axhline(1.1e-3, color="#888", lw=0.5, ls=":")
        ax.set_title("PANEL4MM_P1_calibrated cross-section  t=%.4f ms (real, y=%.3fmm)"
                     % (t * 1e3, Y_SLICE * 1e3), fontsize=10)
        ax.set_xlabel("x [m]")
        ax.set_ylabel("z [m]")
        writer.grab_frame()
        print("frame", idx, "t=%.4f slug_elems=%d" % (t * 1e3, n_slug))

print("saved", out)
