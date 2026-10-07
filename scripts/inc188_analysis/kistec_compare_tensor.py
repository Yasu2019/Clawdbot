# -*- coding: utf-8 -*-
"""INC-188: compare top-surface stresses of a frame with the KISTEC X-ray residual stresses (Points A-H).

KISTEC (2025-06-30, AutoMATE II, AA5052-H34 part): -5.49..+9.21 MPa, origin = round hole centre,
coordinates "after rotation" (mm). Which model direction the photo's horizontal axis (= stress
direction) corresponds to is NOT settled, so every orientation hypothesis (rotation 0..345 deg in 15 deg
steps, with and without a mirror) is evaluated and listed; the best fit is only a candidate.

Per point: live blank elements whose centroid is within R (in plane) of the point and within TOP of the
local top surface; the stress tensor is averaged and the normal stress along the KISTEC x axis taken.

usage: python kistec_compare_tensor.py <frame.vtk> [R_mm=0.15] [TOP_mm=0.05]
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from crack_path_damage import load   # noqa: E402

HOLE = np.array([185.657, -1882.188])
KISTEC = {   # rotated coordinates [mm], stress [MPa], 95% limit [MPa]
    "A": ((0.008, 1.822), 7.92, 4.48), "B": ((0.673, 1.645), 0.64, 3.01),
    "C": ((0.171, 0.637), -5.49, 4.34), "D": ((0.614, 0.776), -1.36, 2.79),
    "E": ((0.679, 0.325), 4.34, 3.72), "F": ((0.330, -0.572), 9.21, 2.88),
    "G": ((0.425, -1.589), 5.94, 2.52), "H": ((1.296, -1.086), -0.65, 2.56),
}


def main():
    path = sys.argv[1]
    R = float(sys.argv[2]) if len(sys.argv) > 2 else 0.15
    TOP = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
    t, P, C, eid, part, ero, eps, ten = load(path)
    cen = P[C].mean(axis=1)
    live = (part == 2) & (ero >= 0.5)
    cen, S = cen[live], ten[live].reshape(-1, 3, 3) / 1e6
    print(f"{os.path.basename(path)} t={t*1e3:.3f} ms, R={R} mm, top {TOP} mm")
    rows = []
    for mirror in (False, True):
        for rot in range(0, 360, 15):
            th = math.radians(rot)
            Rm = np.array([[math.cos(th), -math.sin(th)], [math.sin(th), math.cos(th)]])
            Mm = np.diag([1.0, -1.0]) if mirror else np.eye(2)
            T = Rm @ Mm                        # KISTEC frame -> model frame
            ex = T @ np.array([1.0, 0.0])      # KISTEC x axis (stress direction) in the model
            res = {}
            for k, (xy, meas, ci) in KISTEC.items():
                g = HOLE + T @ np.array(xy)
                d = np.hypot(cen[:, 0] - g[0], cen[:, 1] - g[1])
                near = d < R
                if near.sum() < 3:
                    res[k] = None
                    continue
                ztop = cen[near, 2].max()
                sel = near & (cen[:, 2] > ztop - TOP)
                s = S[sel].mean(axis=0)
                s2 = s[:2, :2]
                res[k] = (float(ex @ s2 @ ex), int(sel.sum()))
            ok = [k for k in KISTEC if res[k] is not None]
            if not ok:
                continue
            err = [res[k][0] - KISTEC[k][1] for k in ok]
            rms = math.sqrt(sum(e * e for e in err) / len(err))
            hit = sum(abs(e) <= KISTEC[k][2] for e, k in zip(err, ok))
            rows.append((rms, rot, mirror, hit, len(ok), res))
    rows.sort(key=lambda r: r[0])
    for rms, rot, mirror, hit, n, res in rows[:5]:
        print(f"rot {rot:3d} mirror {str(mirror):5s}: RMS {rms:7.1f} MPa, within limit {hit}/{n}  " +
              " ".join(f"{k}:{res[k][0]:+.1f}" if res[k] else f"{k}:-" for k in KISTEC))
    print("measured:            " + " ".join(f"{k}:{v[1]:+.1f}" for k, v in KISTEC.items()))
    print("(orientation is unknown: the best rows are fit candidates, not a determination)")


if __name__ == "__main__":
    main()
