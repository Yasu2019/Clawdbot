# -*- coding: utf-8 -*-
"""Punching animation v2 (2026-10-06, after review comments on v1):

  * top views are rasterised (each pixel = max over the sheet thickness of the elements within
    PIX_R of it). v1 scattered element centroids, so finely meshed zones (round hole, H4, H1, H2,
    H3/H5) looked like dark blobs before the punch even touched - pure point density, not data.
  * the section lines A-A (round hole -> H4) and B-B (across the rectangle punch's cut, found
    from the eroded band of the last frame) are drawn on the top views.
  * two sections: A-A and B-B, rasterised the same way, tools in grey.

layout: row 1 = plastic strain (top), von Mises (top); row 2 = section A-A, section B-B.
usage: python render_punch_anim2.py <label> <vtk_dir> <first> <last> <time_offset_ms> <out.mp4> "<title>"
"""
import os
import subprocess
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from render_punch_anim import load, HOLE, H4, WIN_R, WIN_D   # noqa: E402  (fonts set on import)
from scan_rupture_sites import HOTSPOTS_MM                     # noqa: E402

PIX = 0.02          # top-view pixel [mm]
PIX_R = 0.075       # a pixel takes elements whose centroid is within this radius (coarse mesh 100 um)
SPIX = 0.01         # section pixel [mm]
SLAB = 0.06         # section slab half-thickness [mm]
SEC_R = 0.045       # section pixel search radius [mm]
SEC_Z = (-0.6, 1.9)
B_SEED = np.array([1.6, 0.45])   # drawing frame point near the rectangle cut edge between the A-A line and H1


def to_draw(xy):
    """model (x, y) mm -> drawing frame (right, down) about the round hole (PDF orientation)."""
    return np.stack([-(xy[..., 0] - HOLE[0]), xy[..., 1] - HOLE[1]], axis=-1)


def raster_max(pts2, vals, xs, ys, r, r_fine=None):
    """max of vals over points within r_fine of each pixel centre (fine mesh zones), falling back
    to r where none is that close (coarse mesh); NaN where none within r. Two radii keep 20 um
    elements from being drawn as 75 um discs while the 100 um mesh still has no gaps."""
    tree = cKDTree(pts2)
    gx, gy = np.meshgrid(xs, ys)
    q = np.stack([gx.ravel(), gy.ravel()], axis=1)
    out = np.full(len(q), np.nan)
    for rr in ([r_fine] if r_fine else []) + [r]:
        todo = np.where(np.isnan(out))[0]
        for i, nb in zip(todo, tree.query_ball_point(q[todo], rr)):
            if nb:
                out[i] = vals[nb].max()
    return out.reshape(gy.shape)


def slice_tets(Pd, Ct, c0, u, sx, sz):
    """exact cut of tets by the vertical plane through c0 along u: True where a pixel (s, z) lies
    inside a tet. Pd = node coordinates (right, down, z) in the drawing frame."""
    nrm = np.array([-u[1], u[0]])
    perp = (Pd[:, :2] - c0) @ nrm
    sv = (Pd[:, :2] - c0) @ u
    pc = perp[Ct]
    hit = np.where((pc.min(1) <= 0) & (pc.max(1) >= 0))[0]
    mask = np.zeros((len(sz), len(sx)), bool)
    ds, dz = sx[1] - sx[0], sz[1] - sz[0]
    for e in hit:
        nd = Ct[e]
        X = np.stack([sv[nd], perp[nd], Pd[nd, 2]], 1)          # (s, perp, z) of the 4 nodes
        i0 = max(0, int((X[:, 0].min() - sx[0]) / ds)); i1 = min(len(sx), int((X[:, 0].max() - sx[0]) / ds) + 2)
        j0 = max(0, int((X[:, 2].min() - sz[0]) / dz)); j1 = min(len(sz), int((X[:, 2].max() - sz[0]) / dz) + 2)
        if i0 >= i1 or j0 >= j1:
            continue
        T = (X[1:] - X[0]).T
        try:
            Ti = np.linalg.inv(T)
        except np.linalg.LinAlgError:
            continue
        gs, gz = np.meshgrid(sx[i0:i1], sz[j0:j1])
        q = np.stack([gs.ravel() - X[0, 0], np.full(gs.size, -X[0, 1]), gz.ravel() - X[0, 2]])
        lam = Ti @ q
        inside = (lam >= -1e-9).all(0) & (lam.sum(0) <= 1 + 1e-9)
        mask[j0:j1, i0:i1] |= inside.reshape(gs.shape)
    return mask


def find_bb(vdir, last):
    """direction of the rectangle cut near B_SEED from the eroded elements of the last frame."""
    t, P, C, part, ero, eps, vm = load(os.path.join(vdir, f"f{last:03d}.vtk"))
    cen = P[C].mean(axis=1)
    d = to_draw(cen[:, :2])
    gone = (part == 2) & (ero < 0.5)
    near = gone & (np.linalg.norm(d - B_SEED, axis=1) < 0.35)
    pts = d[near]
    if len(pts) < 10:
        raise SystemExit(f"B-B: only {len(pts)} eroded elements near {B_SEED}; pick another seed")
    c0 = pts.mean(axis=0)
    w, v = np.linalg.eigh(np.cov((pts - c0).T))
    edge = v[:, -1]                       # along the cut
    normal = np.array([-edge[1], edge[0]])
    return c0, normal                     # B-B runs along the normal through c0


def main():
    label, vdir, f0, f1, off, out, title = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]), sys.argv[6], sys.argv[7]
    tmp = out + "_frames2"
    os.makedirs(tmp, exist_ok=True)
    a_dir = to_draw(H4[None, :])[0]
    a_dir = a_dir / np.linalg.norm(a_dir)               # A-A: hole centre -> H4
    b_c, b_dir = find_bb(vdir, f1)
    secs = {"A": (np.zeros(2), a_dir, (-0.9, 1.7), "A-A：丸穴中心 → H4"),
            "B": (b_c, b_dir, (-1.0, 1.0), "B-B：矩形パンチの切断線を横切る")}
    print("B-B centre (right, down) =", b_c.round(3), "dir =", b_dir.round(3), flush=True)
    xs = np.arange(WIN_R[0], WIN_R[1], PIX) + PIX / 2
    ys = np.arange(WIN_D[0], WIN_D[1], PIX) + PIX / 2
    hot = {k: to_draw(np.array(HOTSPOTS_MM[k])[None, :])[0] for k in ("H4", "H1", "H2")}
    for i, fr in enumerate(range(f0, f1 + 1)):
        png = os.path.join(tmp, f"{i:04d}.png")
        if os.path.exists(png):
            continue
        try:
            t, P, C, part, ero, eps, vm = load(os.path.join(vdir, f"f{fr:03d}.vtk"))
        except Exception as ex:      # truncated frame (P1r26f f012)
            print(label, fr, "skip unreadable:", ex, flush=True); continue
        if any(v is None or len(v) < len(C) for v in (part, ero, eps, vm)):
            print(label, fr, "skip incomplete frame", flush=True); continue   # P1r26f f010/f012 (E: full on 10-05)
        cen = P[C].mean(axis=1)
        d = to_draw(cen[:, :2])
        Pd = np.concatenate([to_draw(P[:, :2]), P[:, 2:3]], 1)
        live = (part == 2) & (ero >= 0.5)
        win = live & (d[:, 0] > WIN_R[0] - PIX_R) & (d[:, 0] < WIN_R[1] + PIX_R) & (d[:, 1] > WIN_D[0] - PIX_R) & (d[:, 1] < WIN_D[1] + PIX_R)
        fig, ax = plt.subplots(2, 2, figsize=(16, 13), dpi=90)
        for a, val, vmax, cm, lab in ((ax[0, 0], eps, 0.8, "turbo", "相当塑性ひずみ（上から、板厚方向の最大値）"),
                                      (ax[0, 1], vm / 1e6, 600, "inferno", "von Mises [MPa]（上から、板厚方向の最大値）")):
            img = raster_max(d[win], val[win], xs, ys, PIX_R, 0.03)
            cmap = plt.get_cmap(cm).copy(); cmap.set_bad("white")
            im = a.imshow(np.ma.masked_invalid(img), extent=(WIN_R[0], WIN_R[1], WIN_D[1], WIN_D[0]),
                          cmap=cmap, vmin=0, vmax=vmax, interpolation="nearest")
            a.set_xlim(*WIN_R); a.set_ylim(WIN_D[1], WIN_D[0]); a.set_aspect("equal")
            a.set_xlabel("右 [mm]"); a.set_ylabel("下 [mm]"); a.set_title(lab, fontsize=11)
            plt.colorbar(im, ax=a, fraction=0.046, pad=0.02)
            for k, h in hot.items():
                a.plot(h[0], h[1], "+", color="k", ms=11, mew=2)
                a.text(h[0] + 0.1, h[1] - 0.1, k, color="k", fontsize=11, weight="bold")
            for key, (c0, u, rng, _) in secs.items():
                p0, p1 = c0 + u * rng[0], c0 + u * rng[1]
                a.plot([p0[0], p1[0]], [p0[1], p1[1]], "-", color="magenta", lw=1.6)
                a.text(p0[0], p0[1], key, color="magenta", fontsize=13, weight="bold", ha="center", va="center",
                       bbox=dict(fc="white", ec="magenta", pad=1.5))
                a.text(p1[0], p1[1], key, color="magenta", fontsize=13, weight="bold", ha="center", va="center",
                       bbox=dict(fc="white", ec="magenta", pad=1.5))
        for a, key in ((ax[1, 0], "A"), (ax[1, 1], "B")):
            c0, u, rng, ttl = secs[key]
            rel = d - c0
            s = rel @ u
            perp = rel @ np.array([-u[1], u[0]])
            z = cen[:, 2]
            box = (s > rng[0] - 0.1) & (s < rng[1] + 0.1) & (z > SEC_Z[0]) & (z < SEC_Z[1])
            sx = np.arange(rng[0], rng[1], SPIX) + SPIX / 2
            sz = np.arange(SEC_Z[0], SEC_Z[1], SPIX) + SPIX / 2
            tl = box & (part != 2) & (np.abs(perp) < 0.4)
            if tl.any():
                tm = slice_tets(Pd, C[tl], c0, u, sx, sz)
                a.imshow(np.ma.masked_where(~tm, tm.astype(float)), extent=(rng[0], rng[1], SEC_Z[0], SEC_Z[1]), origin="lower",
                         cmap="Greys", vmin=0, vmax=3, interpolation="nearest")
            bl = box & live & (np.abs(perp) < SLAB)
            img = raster_max(np.stack([s[bl], z[bl]], 1), eps[bl], sx, sz, SEC_R, 0.02)
            cmap = plt.get_cmap("turbo").copy(); cmap.set_bad((0, 0, 0, 0))
            im = a.imshow(np.ma.masked_invalid(img), extent=(rng[0], rng[1], SEC_Z[0], SEC_Z[1]), origin="lower",
                          cmap=cmap, vmin=0, vmax=0.8, interpolation="nearest")
            if key == "A":
                a.axvline(0.28, color="k", ls=":", lw=0.8)
                a.text(0.28, SEC_Z[1] - 0.12, " 丸パンチ刃先", fontsize=9)
                a.axvline(np.linalg.norm(to_draw(H4[None, :])[0]), color="magenta", ls="--", lw=1)
            a.set_xlim(*rng); a.set_ylim(*SEC_Z); a.set_aspect("equal")
            a.set_xlabel(f"断面 {key}-{key} に沿った距離 [mm]"); a.set_ylabel("z [mm]")
            a.set_title(f"{ttl}（色＝相当塑性ひずみ、灰色＝パンチ・ダイ・ストリッパー）", fontsize=11)
            plt.colorbar(im, ax=a, fraction=0.046, pad=0.02)
        tstd = t * 1e3 + off
        fig.suptitle(f"{title}    t = {t*1e3:.3f} ms" + (f"（標準時刻 {tstd:.3f} ms）" if off else ""), fontsize=14)
        fig.tight_layout(rect=(0, 0, 1, 0.96))
        fig.savefig(png); plt.close(fig)
        print(label, fr, f"t={t*1e3:.3f}", flush=True)
    ff = os.environ.get("FFMPEG", "ffmpeg")
    import glob, shutil
    seq = tmp + "_seq"                      # skipped frames leave gaps; ffmpeg needs a contiguous sequence
    shutil.rmtree(seq, ignore_errors=True); os.makedirs(seq)
    for k, pth in enumerate(sorted(glob.glob(os.path.join(tmp, "*.png")))):
        shutil.copy(pth, os.path.join(seq, f"{k:04d}.png"))
    subprocess.run([ff, "-y", "-loglevel", "error", "-framerate", "4", "-i", os.path.join(seq, "%04d.png"),
                    "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                    "-crf", "26", "-movflags", "+faststart", out], check=True)
    print("wrote", out, os.path.getsize(out))


if __name__ == "__main__":
    main()
