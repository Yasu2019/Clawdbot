"""P1校正版の実VTKフレームから、斜め上視点の3Dアニメーションを作る(v3)。

v2はZしきい値だけでスラグを判定したため、材料全体の一般的なたわみまで
「落下」と誤判定し、しきい値未満の領域が大きくなりすぎて破綻した。
v3は「削除(破断)要素の位置」を先にクラスタリングして各穴の実際の
バウンディングボックスを特定し、そのXY範囲内にある低z材料だけをその穴の
スラグとして描く。演出・捏造なし、座標・クラスタとも実データから直接生成。
"""
import sys
import glob
import re
import numpy as np
import matplotlib
matplotlib.use("Agg")
matplotlib.rcParams["animation.ffmpeg_path"] = (
    r"C:\Users\yasu\AppData\Local\Microsoft\WinGet\Packages\\"
    r"Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin\ffmpeg.exe"
)
import matplotlib.pyplot as plt
from matplotlib.tri import Triangulation
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


def top_by_bin(nodes_xyz, binsize):
    best = {}
    for x, y, z in nodes_xyz:
        key = (round(x / binsize), round(y / binsize))
        if key not in best or z > best[key][2]:
            best[key] = (x, y, z)
    return list(best.values())


def connected_blobs(xy_list, cell, min_pts):
    occ = {}
    for i, (x, y) in enumerate(xy_list):
        occ.setdefault((round(x / cell), round(y / cell)), []).append(i)
    visited, blobs = set(), []
    for key in occ:
        if key in visited:
            continue
        stack, comp = [key], []
        visited.add(key)
        while stack:
            k = stack.pop()
            comp.extend(occ[k])
            kx, ky = k
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1),
                          (1, 1), (1, -1), (-1, 1), (-1, -1)):
                nk = (kx + dx, ky + dy)
                if nk in occ and nk not in visited:
                    visited.add(nk)
                    stack.append(nk)
        if len(comp) >= min_pts:
            blobs.append(comp)
    return blobs


def surf(ax, pts3, edge_xy_max, edge_z_max, **kw):
    """xy距離とz差の両方で辺を制限する。z差の制限で、シート断面際の
    垂直な偽の毛羽立ち(v2で確認済みの問題)を防ぐ。スラグは傾いて自然な
    高さ変化があるためedge_z_maxをシートより大きく取る。"""
    if len(pts3) < 4:
        return
    xs = np.array([p[0] for p in pts3])
    ys = np.array([p[1] for p in pts3])
    zs = np.array([p[2] for p in pts3])
    tri = Triangulation(xs, ys)
    tx, ty, tz = xs[tri.triangles], ys[tri.triangles], zs[tri.triangles]
    dxy01 = np.hypot(tx[:, 0] - tx[:, 1], ty[:, 0] - ty[:, 1])
    dxy12 = np.hypot(tx[:, 1] - tx[:, 2], ty[:, 1] - ty[:, 2])
    dxy20 = np.hypot(tx[:, 2] - tx[:, 0], ty[:, 2] - ty[:, 0])
    dz01 = np.abs(tz[:, 0] - tz[:, 1])
    dz12 = np.abs(tz[:, 1] - tz[:, 2])
    dz20 = np.abs(tz[:, 2] - tz[:, 0])
    keep = (dxy01 < edge_xy_max) & (dxy12 < edge_xy_max) & (dxy20 < edge_xy_max)
    keep &= (dz01 < edge_z_max) & (dz12 < edge_z_max) & (dz20 < edge_z_max)
    if not keep.any():
        return
    tri.set_mask(~keep)
    ax.plot_trisurf(tri, zs, edgecolor="none", shade=True, **kw)


files = sorted(glob.glob(sys.argv[1]), key=lambda p: int(re.search(r"f(\d\d)\.vtk", p).group(1)))
out = sys.argv[2]
print("frames:", len(files))

X0, X1 = 0.1735, 0.1905
Y0, Y1 = -1.892, -1.868
Z0, Z1 = -3.0e-3, 1.2e-3
BIN = 45.0e-6
MARGIN = 0.3e-3           # 穴バウンディングボックスの拡張マージン
HOLE_MIN_PTS = 200        # これ未満の破断クラスタはノイズとみなし無視する

sheet_colors = "#c9553a"
slug_colors = ["#7a3d28", "#5c4a2e", "#6b3a3a", "#3d5a4a"]

fig = plt.figure(figsize=(7.5, 7.5), dpi=110)
ax = fig.add_subplot(111, projection="3d")
writer = FFMpegWriter(fps=6, metadata=dict(
    title="PANEL4MM_P1_calibrated oblique v3 (real OpenRadioss result, Eps_s=0.5)"))

with writer.saving(fig, out, dpi=110):
    for idx, path in enumerate(files):
        pts, cells, part, ero, t = load(path)

        mat_nodes = {}
        dead_xy = []
        for c, p, e in zip(cells, part, ero):
            if p != 2:
                continue
            if e < 0.5:
                xs = [pts[n][0] for n in c]
                ys = [pts[n][1] for n in c]
                dead_xy.append((sum(xs) / len(xs), sum(ys) / len(ys)))
                continue
            for n in c:
                x, y, z = pts[n]
                if n not in mat_nodes or z > mat_nodes[n][2]:
                    mat_nodes[n] = (x, y, z)
        if not mat_nodes:
            continue
        all_pts = list(mat_nodes.values())
        zmax = max(p[2] for p in all_pts)

        # 穴の位置を破断要素クラスタから特定する(小さいノイズ状クラスタは除外)
        holes = []
        if len(dead_xy) > 10:
            for idxs in connected_blobs(dead_xy, cell=0.15e-3, min_pts=1):
                if len(idxs) < HOLE_MIN_PTS:
                    continue
                xs = [dead_xy[i][0] for i in idxs]
                ys = [dead_xy[i][1] for i in idxs]
                holes.append((min(xs) - MARGIN, max(xs) + MARGIN,
                              min(ys) - MARGIN, max(ys) + MARGIN))

        # 各穴のバウンディングボックス内で、シートより明確に低い材料をスラグとする
        slug_pts_per_hole = [[] for _ in holes]
        sheet_src = []
        for (x, y, z) in all_pts:
            assigned = False
            for hi, (x0, x1, y0, y1) in enumerate(holes):
                if x0 <= x <= x1 and y0 <= y <= y1 and z < zmax - 80e-6:
                    slug_pts_per_hole[hi].append((x, y, z))
                    assigned = True
                    break
            if not assigned:
                sheet_src.append((x, y, z))

        sheet_top = top_by_bin(sheet_src, BIN)

        ax.clear()
        surf(ax, sheet_top, 150e-6, 60e-6, color=sheet_colors, alpha=0.95)
        n_slugs = 0
        for hi, slug_pts in enumerate(slug_pts_per_hole):
            if len(slug_pts) < 15:
                continue
            slug_top = top_by_bin(slug_pts, BIN)
            surf(ax, slug_top, 130e-6, 400e-6, color=slug_colors[hi % len(slug_colors)], alpha=0.97)
            n_slugs += 1

        ax.set_xlim(X0, X1)
        ax.set_ylim(Y0, Y1)
        ax.set_zlim(Z0, Z1)
        ax.view_init(elev=35, azim=-55)
        ax.set_box_aspect((X1 - X0, Y1 - Y0, (Z1 - Z0) * 1.3))
        ax.set_title("OpenRadioss PANEL4MM_P1_calibrated  t=%.4f ms (real simulation)" % (t * 1e3))
        ax.set_xlabel("x [m]")
        ax.set_ylabel("y [m]")
        ax.set_zlabel("z [m]")
        writer.grab_frame()
        print("frame", idx, "t=%.4f holes=%d slugs_drawn=%d sheet_cols=%d"
              % (t * 1e3, len(holes), n_slugs, len(sheet_top)))

print("saved", out)
