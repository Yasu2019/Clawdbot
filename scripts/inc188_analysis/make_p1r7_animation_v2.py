"""P1r7の実VTKフレームから、応力三軸度・Von Mises等価応力・最大主応力の
3Dアニメーションを作る(make_p1r7_animation.pyの拡張版、画像サイズ拡大)。
使い方: python make_p1r7_animation_v2.py "p1r7_all/f*.vtk" out.mp4 MODE [elev] [azim]
  MODE = triax | vonmises | principal
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
matplotlib.rcParams["font.family"] = "Noto Sans JP"
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

    ti = [k for k, l in enumerate(lines) if l.startswith("TENSORS ")]
    tens = None
    if ti:
        tens, k = [], ti[0] + 1
        vals = []
        while len(tens) < nc:
            vals += [float(x) for x in lines[k].split()]
            k += 1
            while len(vals) >= 9:
                tens.append(vals[:9])
                vals = vals[9:]
        tens = tens[:nc]

    tl = [k for k, l in enumerate(lines) if l.strip() == "TIME 1 1 double"]
    t = float(lines[tl[0] + 1]) if tl else 0.0
    return (pts[:n], cells, block("PART_ID", int), block("EROSION_STATUS"),
            block("3DELEM_Von_Mises"), tens, t)


def triaxiality(vm, tens):
    sxx, sxy, sxz, syx, syy, syz, szx, szy, szz = tens
    sm = (sxx + syy + szz) / 3.0
    if vm is None or vm < 1e4:
        return 0.0
    return sm / vm


def max_principal(tens):
    sxx, sxy, sxz, syx, syy, syz, szx, szy, szz = tens
    M = np.array([[sxx, sxy, sxz], [syx, syy, syz], [szx, szy, szz]])
    eigvals = np.linalg.eigvalsh((M + M.T) / 2.0)
    return eigvals[-1]


def top_by_bin(nodes_xyzv, binsize):
    best = {}
    for x, y, z, v in nodes_xyzv:
        key = (round(x / binsize), round(y / binsize))
        if key not in best or z > best[key][2]:
            best[key] = (x, y, z, v)
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


def surf(ax, pts4, edge_xy_max, edge_z_max, grid_step=55.0e-6,
         cmap=None, vmin=None, vmax=None, **kw):
    if len(pts4) < 4:
        return None
    from scipy.interpolate import griddata
    from scipy.spatial import cKDTree
    pts4 = np.asarray(pts4)
    xs, ys, zs, vs = pts4[:, 0], pts4[:, 1], pts4[:, 2], pts4[:, 3]
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    if x1 - x0 < grid_step or y1 - y0 < grid_step:
        return None
    gx = np.arange(x0, x1, grid_step)
    gy = np.arange(y0, y1, grid_step)
    if len(gx) < 2 or len(gy) < 2:
        return None
    GX, GY = np.meshgrid(gx, gy)
    GZ = griddata((xs, ys), zs, (GX, GY), method="linear")
    tree = cKDTree(np.column_stack([xs, ys]))
    dist, idx = tree.query(np.column_stack([GX.ravel(), GY.ravel()]))
    dist = dist.reshape(GX.shape)
    dz_nearest = np.abs(GZ - zs[idx].reshape(GX.shape))
    valid_mask = (dist <= edge_xy_max) & (dz_nearest <= edge_z_max)
    GZ = np.where(valid_mask, GZ, np.nan)
    if np.all(np.isnan(GZ)):
        return None
    from scipy.ndimage import gaussian_filter
    valid = ~np.isnan(GZ)
    if valid.sum() >= 9:
        filled = np.where(valid, GZ, 0.0)
        sigma = 1.6
        num = gaussian_filter(filled, sigma=sigma, mode="nearest")
        den = gaussian_filter(valid.astype(float), sigma=sigma, mode="nearest")
        with np.errstate(invalid="ignore", divide="ignore"):
            smoothed = num / den
        GZ = np.where(valid, smoothed, np.nan)
    if cmap is not None:
        GV = griddata((xs, ys), vs, (GX, GY), method="linear")
        GV = np.where(valid_mask, GV, np.nan)
        norm = plt.Normalize(vmin=vmin, vmax=vmax)
        facecolors = plt.get_cmap(cmap)(norm(np.nan_to_num(GV, nan=vmin)))
        surface = ax.plot_surface(GX, GY, GZ, facecolors=facecolors,
                                  edgecolor="none", shade=False,
                                  antialiased=True, rstride=1, cstride=1)
        return plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    ax.plot_surface(GX, GY, GZ, edgecolor="none", shade=True,
                    antialiased=True, rstride=1, cstride=1, **kw)
    return None


files = sorted(glob.glob(sys.argv[1]), key=lambda p: int(re.search(r"f(\d+)\.vtk", p).group(1)))
out = sys.argv[2]
MODE = sys.argv[3]  # "triax" or "vonmises"
VIEW_ELEV = float(sys.argv[4]) if len(sys.argv) > 4 else 35.0
VIEW_AZIM = float(sys.argv[5]) if len(sys.argv) > 5 else -55.0
print("frames:", len(files), "mode=%s elev=%.0f azim=%.0f" % (MODE, VIEW_ELEV, VIEW_AZIM))

X0, X1 = 0.1735, 0.1905
Y0, Y1 = -1.892, -1.868
Z0, Z1 = -3.5e-3, 1.2e-3
BIN = 95.0e-6
MARGIN = 0.3e-3
HOLE_MIN_PTS = 200

if MODE == "triax":
    CMAP = "RdBu_r"
    VMIN, VMAX = -0.5, 0.5
    CBAR_LABEL = "Stress triaxiality  eta = sigma_m / sigma_vm"
    TITLE_COLOR = "応力三軸度"
elif MODE == "principal":
    CMAP = "turbo"
    VMIN, VMAX = -200.0, 600.0  # MPa (max principal stress, compressive can be negative)
    CBAR_LABEL = "Max principal stress  sigma_1 [MPa]"
    TITLE_COLOR = "最大主応力"
else:
    CMAP = "turbo"
    VMIN, VMAX = 0.0, 600.0  # MPa
    CBAR_LABEL = "Von Mises equivalent stress [MPa]"
    TITLE_COLOR = "Von Mises等価応力"

# 画像サイズを拡大(元8.0x7.5in@110dpi=880x825px -> 13x12in@160dpi=2080x1920px)
fig = plt.figure(figsize=(13.0, 12.0), dpi=160)
ax = fig.add_subplot(111, projection="3d")
writer = FFMpegWriter(fps=6, metadata=dict(
    title=f"PANEL4MM_P1r7 oblique ({MODE}, real OpenRadioss result)"))

with writer.saving(fig, out, dpi=160):
    for idx, path in enumerate(files):
        pts, cells, part, ero, vm, tens, t = load(path)

        mat_nodes = {}
        dead_xy = []
        for i, (c, p, e) in enumerate(zip(cells, part, ero)):
            if p != 2:
                continue
            if e < 0.5:
                xs = [pts[n][0] for n in c]
                ys = [pts[n][1] for n in c]
                dead_xy.append((sum(xs) / len(xs), sum(ys) / len(ys)))
                continue
            if MODE == "triax":
                val = triaxiality(vm[i], tens[i]) if tens is not None else 0.0
            elif MODE == "principal":
                val = (max_principal(tens[i]) / 1e6) if tens is not None else 0.0  # Pa -> MPa
            else:
                val = (vm[i] / 1e6) if vm[i] is not None else 0.0  # Pa -> MPa
            for n in c:
                x, y, z = pts[n]
                if n not in mat_nodes or z > mat_nodes[n][2]:
                    mat_nodes[n] = (x, y, z, val)
        if not mat_nodes:
            continue
        all_pts = list(mat_nodes.values())
        zmax = max(p[2] for p in all_pts)

        holes = []
        if len(dead_xy) > 10:
            for idxs in connected_blobs(dead_xy, cell=0.15e-3, min_pts=1):
                if len(idxs) < HOLE_MIN_PTS:
                    continue
                xs = [dead_xy[i][0] for i in idxs]
                ys = [dead_xy[i][1] for i in idxs]
                holes.append((min(xs) - MARGIN, max(xs) + MARGIN,
                              min(ys) - MARGIN, max(ys) + MARGIN))

        slug_pts_per_hole = [[] for _ in holes]
        sheet_src = []
        for (x, y, z, v) in all_pts:
            assigned = False
            for hi, (x0, x1, y0, y1) in enumerate(holes):
                if x0 <= x <= x1 and y0 <= y <= y1 and z < zmax - 80e-6:
                    slug_pts_per_hole[hi].append((x, y, z, v))
                    assigned = True
                    break
            if not assigned:
                sheet_src.append((x, y, z, v))

        sheet_top = top_by_bin(sheet_src, BIN)

        ax.clear()
        mappable = surf(ax, sheet_top, 150e-6, 60e-6, cmap=CMAP,
                        vmin=VMIN, vmax=VMAX)
        n_slugs = 0
        for hi, slug_pts in enumerate(slug_pts_per_hole):
            if len(slug_pts) < 15:
                continue
            slug_top = top_by_bin(slug_pts, BIN)
            surf(ax, slug_top, 130e-6, 600e-6, cmap=CMAP, vmin=VMIN, vmax=VMAX)
            n_slugs += 1

        ax.set_xlim(X0, X1)
        ax.set_ylim(Y0, Y1)
        ax.set_zlim(Z0, Z1)
        ax.view_init(elev=VIEW_ELEV, azim=VIEW_AZIM)
        ax.set_box_aspect((X1 - X0, Y1 - Y0, (Z1 - Z0) * 1.3))
        ax.set_title("OpenRadioss PANEL4MM_P1r7  t=%.4f ms (single-connected mesh)\n"
                     "color = %s" % (t * 1e3, TITLE_COLOR), fontsize=15)
        ax.set_xlabel("x [m]", fontsize=11)
        ax.set_ylabel("y [m]", fontsize=11)
        ax.set_zlabel("z [m]", fontsize=11)
        ax.tick_params(labelsize=9)
        if idx == 0 and mappable is not None:
            cbar_ax = fig.add_axes([0.90, 0.25, 0.02, 0.5])
            fig.colorbar(mappable, cax=cbar_ax, label=CBAR_LABEL)
            cbar_ax.tick_params(labelsize=10)
            cbar_ax.yaxis.label.set_size(12)
        writer.grab_frame()
        print("frame", idx, "t=%.4f holes=%d slugs_drawn=%d sheet_cols=%d"
              % (t * 1e3, len(holes), n_slugs, len(sheet_top)))

print("saved", out)
