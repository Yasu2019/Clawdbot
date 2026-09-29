# -*- coding: utf-8 -*-
"""Round-hole separation check (live-element flood fill on the final frame).

Live blank elements (PART_ID 2, EROSION_STATUS >= 0.5) are joined into components through shared nodes.
The largest component is the main sheet. If the round hole is punched out, the main sheet must not
reach the hole centre: its nearest element centroid should sit near the die-hole radius (~0.28-0.30 mm).
Distances are reported in both the final (deformed) frame and the t=0 geometry.
The slug (elements whose t=0 centroid lies inside the punch radius) is checked for membership in
the main component: slug connected to main sheet = not separated.

usage: python round_hole_separation.py <label> <final.vtk> <first_frame.vtk>
output: round_hole_sep_<label>.json + one-line summary
"""
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from scan_rupture_sites import load, HOTSPOTS_MM   # noqa: E402

HOLE = HOTSPOTS_MM["ROUND_HOLE"]
R_PUNCH = 0.280   # mm (STEP: round punch R=0.280, die hole R=0.300)
CORE_MARGIN = 0.040   # mm = two 20 um round-hole elements inside the punch edge


def centroids(pts, cells):
    p = np.asarray(pts) * 1e3
    c = np.asarray([cc[:4] for cc in cells])
    return p[c].mean(axis=1)             # (nc, 3) mm


def components(cells, live_idx, n_nodes):
    parent = np.arange(n_nodes)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for i in live_idx:
        c = cells[i]
        r0 = find(c[0])
        for n in c[1:4]:
            r = find(n)
            if r != r0:
                parent[r] = r0
    return np.array([find(cells[i][0]) for i in live_idx])


def main():
    label, final, first = sys.argv[1], sys.argv[2], sys.argv[3]
    ptsF, cellsF, partF, eroF, t, eidF = load(final)
    pts0, cells0, _, _, _, eid0 = load(first)
    assert eidF == eid0, "element order differs between first and last frame"

    part = np.asarray(partF)
    ero = np.asarray(eroF)
    live_idx = np.where((part == 2) & (ero >= 0.5))[0]
    roots = components(cellsF, live_idx, len(ptsF))
    uniq, counts = np.unique(roots, return_counts=True)
    main_root = uniq[np.argmax(counts)]
    main = live_idx[roots == main_root]

    cF = centroids(ptsF, cellsF)
    c0 = centroids(pts0, cellsF)
    dF = np.hypot(cF[main, 0] - HOLE[0], cF[main, 1] - HOLE[1])
    d0 = np.hypot(c0[main, 0] - HOLE[0], c0[main, 1] - HOLE[1])

    blank = np.where(part == 2)[0]
    slug = blank[np.hypot(c0[blank, 0] - HOLE[0], c0[blank, 1] - HOLE[1]) < R_PUNCH]
    slug_live = slug[ero[slug] >= 0.5]
    slug_in_main = np.isin(slug_live, main)

    # 2026-09-29: in P1r20 every slug element still attached to the main sheet lay within 25 um of
    # the punch edge (t0 r 0.255-0.280 mm), squeezed into the 20 um punch-die clearance under
    # compression (burr-like rim), while the slug body was already detached. 'core' = slug elements
    # at least two 20 um elements inside the punch edge; core_separated is reported next to the
    # strict 'separated' (any slug element attached), which is kept unchanged.
    core = slug_live[np.hypot(c0[slug_live, 0] - HOLE[0], c0[slug_live, 1] - HOLE[1]) < R_PUNCH - CORE_MARGIN]
    core_in_main = int(np.isin(core, main).sum())
    rim_attached = slug_live[slug_in_main]
    rim_r0 = np.hypot(c0[rim_attached, 0] - HOLE[0], c0[rim_attached, 1] - HOLE[1])

    out = {
        "label": label, "t_ms": round(t * 1e3, 4),
        "n_live_blank": int(len(live_idx)), "n_components": int(len(uniq)),
        "main_component_elems": int(len(main)),
        "main_min_dist_to_hole_centre_final_mm": round(float(dF.min()), 4),
        "main_min_dist_to_hole_centre_t0_mm": round(float(d0.min()), 4),
        "slug_elems_t0": int(len(slug)), "slug_live": int(len(slug_live)),
        "slug_live_in_main": int(slug_in_main.sum()),
        "separated": bool(slug_in_main.sum() == 0 and d0.min() > R_PUNCH * 0.9),
        "core_r_mm": round(R_PUNCH - CORE_MARGIN, 3),
        "core_live": int(len(core)), "core_live_in_main": core_in_main,
        "core_separated": bool(len(core) > 0 and core_in_main == 0),
        "attached_min_r0_mm": round(float(rim_r0.min()), 4) if len(rim_r0) else None,
    }
    json.dump(out, open(f"round_hole_sep_{label}.json", "w", encoding="utf-8"), indent=1)
    print(f"{label}: t={out['t_ms']}ms comps={out['n_components']} main={out['main_component_elems']:,} "
          f"main->hole min dist final={out['main_min_dist_to_hole_centre_final_mm']}mm "
          f"t0={out['main_min_dist_to_hole_centre_t0_mm']}mm | slug t0={out['slug_elems_t0']:,} "
          f"live={out['slug_live']:,} in_main={out['slug_live_in_main']:,} -> separated={out['separated']} | "
          f"core r<{out['core_r_mm']} in_main={out['core_live_in_main']:,}/{out['core_live']:,} "
          f"-> core_separated={out['core_separated']} (attached from r0={out['attached_min_r0_mm']})")


if __name__ == "__main__":
    main()
