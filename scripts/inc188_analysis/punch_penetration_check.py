# -*- coding: utf-8 -*-
"""Does the round punch pass through the blank? (contact check, INC-188 2026-09-27)

Counts live blank elements whose centroid lies inside the round-punch volume
(r < 0.25 mm from the hole centre, between punch bottom + 0.01 mm and punch top) and above the
punch top. Healthy contact: ~0 inside. P1r19fc3p5 (EXT surface): 0 / 3,104 / 8,011 / 12,158 at
f006 / f007 / f008 / f010.

usage: python punch_penetration_check.py <frame.vtk> [<frame.vtk> ...]
"""
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("\\", 1)[0].rsplit("/", 1)[0])
from scan_rupture_sites import load, HOTSPOTS_MM   # noqa: E402

H = HOTSPOTS_MM["ROUND_HOLE"]
PUNCH_PART, BLANK_PART = 4, 2

for path in sys.argv[1:]:
    pts, cells, part, ero, t, _ = load(path)
    P = np.asarray(pts) * 1e3
    part, ero = np.asarray(part), np.asarray(ero)
    c = np.asarray([cc[:4] for cc in cells])
    cen = P[c].mean(axis=1)
    r = np.hypot(cen[:, 0] - H[0], cen[:, 1] - H[1])
    pz = P[np.unique(c[(part == PUNCH_PART) & (r < 0.5)]), 2]
    zb, zt = pz.min(), pz.max()
    live = (part == BLANK_PART) & (ero >= 0.5) & (r < 0.25)
    inside = int((live & (cen[:, 2] > zb + 0.01) & (cen[:, 2] < zt)).sum())
    above = int((live & (cen[:, 2] >= zt)).sum())
    print(f"{path.rsplit('/', 1)[-1]} t={t*1e3:.3f}ms punch z {zb:.3f}..{zt:.3f} | "
          f"live blank inside punch {inside:,} | above punch top {above:,}", flush=True)
