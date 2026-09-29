# -*- coding: utf-8 -*-
"""What is the residual round-hole ligament? (INC-188, 2026-09-29)

For the live slug elements (t0 centroid r < R_PUNCH) that are still connected to the main sheet in the
given frame, and for the cut-ring elements (R_PUNCH-0.02 .. DIE_R+0.02 mm at t0) in the same angular
sector, report: current z (sheet top at t0 = 1.005 mm, bottom 0.505 mm, die top 0.5 mm), radial
position now vs t0, equivalent plastic strain, von Mises stress, triaxiality and max principal stress.
Answers: is the ligament bent down into the die hole, highly strained but below the failure criteria,
or simply unloaded once the punch has passed?

usage: python round_hole_ligament.py <label> <frame.vtk> <first.vtk>
"""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from round_hole_separation import HOLE, R_PUNCH, centroids, components   # noqa: E402

DIE_R = 0.300


def load_full(path):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    pi = [k for k, l in enumerate(lines) if l.startswith("POINTS ")][0]
    n = int(lines[pi].split()[1])
    pts, k = [], pi + 1
    while len(pts) < n:
        v = [float(x) for x in lines[k].split()]
        pts += [v[j:j + 3] for j in range(0, len(v), 3)]
        k += 1
    ci = [k for k, l in enumerate(lines) if l.startswith("CELLS ")][0]
    nc = int(lines[ci].split()[1])
    cells, k = [], ci + 1
    while len(cells) < nc:
        v = [int(x) for x in lines[k].split()]
        if v:
            cells.append(v[1:])
        k += 1

    def scal(name):
        idx = [k for k, l in enumerate(lines) if l.startswith("SCALARS " + name)]
        if not idx:
            return None
        out, k = [], idx[0] + 2
        while len(out) < nc and k < len(lines):
            out += [float(x) for x in lines[k].split()]
            k += 1
        return np.asarray(out[:nc])

    ten = None
    ti = [k for k, l in enumerate(lines) if l.startswith("TENSORS 3DELEM_Stress")]
    if ti:
        vals, k = [], ti[0] + 1
        while len(vals) < nc * 9 and k < len(lines):
            vals += [float(x) for x in lines[k].split()]
            k += 1
        ten = np.asarray(vals[:nc * 9]).reshape(nc, 3, 3)
    t = 0.0
    for l in lines[:40]:
        if l.startswith("TIME"):
            try:
                t = float(lines[lines.index(l) + 1].split()[0])
            except (ValueError, IndexError):
                pass
    return (pts, cells, scal("PART_ID"), scal("EROSION_STATUS"), scal("3DELEM_Plastic_Strain"),
            scal("3DELEM_Von_Mises"), ten)


def stats(a):
    a = np.asarray(a)
    if a.size == 0:
        return None
    return {"min": round(float(a.min()), 4), "p50": round(float(np.median(a)), 4),
            "p90": round(float(np.percentile(a, 90)), 4), "max": round(float(a.max()), 4)}


def main():
    label, frame, first = sys.argv[1], sys.argv[2], sys.argv[3]
    pts, cells, part, ero, eps, vm, ten = load_full(frame)
    pts0 = load_full(first)[0]
    part = part.astype(int)
    live_idx = np.where((part == 2) & (ero >= 0.5))[0]
    roots = components(cells, live_idx, len(pts))
    u, n = np.unique(roots, return_counts=True)
    main = live_idx[roots == u[np.argmax(n)]]
    cF, c0 = centroids(pts, cells), centroids(pts0, cells)
    r0 = np.hypot(c0[:, 0] - HOLE[0], c0[:, 1] - HOLE[1])
    rF = np.hypot(cF[:, 0] - HOLE[0], cF[:, 1] - HOLE[1])
    ang0 = np.degrees(np.arctan2(c0[:, 1] - HOLE[1], c0[:, 0] - HOLE[0])) % 360
    blank = part == 2
    lig = np.where(blank & (r0 < R_PUNCH) & (ero >= 0.5) & np.isin(np.arange(len(part)), main))[0]
    sectors = np.unique((ang0[lig] // 30).astype(int)) if len(lig) else []
    ring = np.where(blank & (r0 > R_PUNCH - 0.02) & (r0 < DIE_R + 0.02) & np.isin((ang0 // 30).astype(int), sectors))[0]
    ring_live = ring[ero[ring] >= 0.5]

    def principal(idx):
        if ten is None or len(idx) == 0:
            return None, None
        M = ten[idx]
        S = (M + np.transpose(M, (0, 2, 1))) / 2
        s1 = np.linalg.eigvalsh(S)[:, -1] / 1e6
        tri = (np.trace(S, axis1=1, axis2=2) / 3) / np.maximum(vm[idx], 1e3)
        return s1, tri

    out = {"label": label, "ligament_elems": int(len(lig)),
           "sectors_deg": [int(s) * 30 for s in sectors]}
    for name, idx in (("ligament", lig), ("cut_ring_live_same_sectors", ring_live)):
        s1, tri = principal(idx)
        out[name] = {
            "n": int(len(idx)),
            "z_now_mm": stats(cF[idx, 2]), "r_t0_mm": stats(r0[idx]), "r_now_mm": stats(rF[idx]),
            "eps_p": stats(eps[idx]) if eps is not None else None,
            "vm_MPa": stats(vm[idx] / 1e6) if vm is not None else None,
            "sigma1_MPa": stats(s1) if s1 is not None else None,
            "triaxiality": stats(tri) if tri is not None else None,
        }
    out["cut_ring_eroded_frac_same_sectors"] = round(float((ero[ring] < 0.5).mean()), 3) if len(ring) else None
    json.dump(out, open(f"round_hole_ligament_{label}.json", "w", encoding="utf-8"), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
