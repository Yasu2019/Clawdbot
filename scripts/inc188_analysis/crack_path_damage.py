# -*- coding: utf-8 -*-
"""INC-188: stress state and BIQUAD-type damage along the REAL crack path (2026-10-06).

The real micro-crack (Crack_発生位置_PM7TCB.pdf) starts on the trim contour and runs toward the round
hole, i.e. across the ligament between the trim fillet and the hole. The H4 hotspot element (33 um from
the trim edge) is crushed by the trim punch (eta -0.7..-0.4) and takes no damage there, so this looks at
every blank element within BAND of the crack segment, through the thickness, frame by frame:
equivalent plastic strain, triaxiality eta = sigma_m / sigma_vm, sigma1, and the damage
D = sum(d eps_p / eps_f(eta)) for a set of BIQUAD parameter sets (eps_f at eta -1/3, 0, 1/3, 1/sqrt3, 2/3;
no damage below eta = -1/3, as in Radioss).

usage: python crack_path_damage.py <label> <vtk_dir> <first> <last> [time_offset_ms]
"""
import json
import math
import os
import re
import sys

import numpy as np

HOLE = np.array([185.657, -1882.188])                 # model mm
# real crack, drawing frame (right, down) from the round hole centre (report section 6)
ORIGIN_D = np.array([0.30, 0.84])                     # on the trim contour
TIP_D = np.array([0.47, 0.43])                        # toward the round hole
BAND = 0.06                                           # mm either side of the segment
EXT = 0.10                                            # extend past both ends [mm]
SETS = {"c2=0.6": (1.2, 0.6, 0.45, 0.35, 0.45), "c2=0.9": (1.8, 0.9, 0.45, 0.35, 0.45),
        "c2=1.2": (2.4, 1.2, 0.45, 0.35, 0.45), "c2=1.6": (3.2, 1.6, 0.45, 0.35, 0.45)}


def ef(eta, c):
    c1, c2, c3, c4, c5 = c

    def para(x, xs, ys):
        (x0, x1, x2), (y0, y1, y2) = xs, ys
        return (y0 * (x - x1) * (x - x2) / ((x0 - x1) * (x0 - x2)) + y1 * (x - x0) * (x - x2) / ((x1 - x0) * (x1 - x2))
                + y2 * (x - x0) * (x - x1) / ((x2 - x0) * (x2 - x1)))
    out = np.full(eta.shape, np.inf)
    a = (eta >= -1 / 3) & (eta <= 1 / 3)
    out[a] = np.maximum(para(eta[a], (-1 / 3, 0, 1 / 3), (c1, c2, c3)), 1e-3)
    b = (eta > 1 / 3) & (eta <= 2 / 3)
    out[b] = np.maximum(para(eta[b], (1 / 3, 1 / math.sqrt(3), 2 / 3), (c3, c4, c5)), 1e-3)
    out[eta > 2 / 3] = c5
    return out


def load(path):
    txt = open(path, encoding="utf-8", errors="replace").read()
    t = float(re.search(r"TIME 1 1 double\s+([-0-9.eE+]+)", txt).group(1))
    n = int(re.search(r"^POINTS (\d+)", txt, re.M).group(1))
    m = re.search(r"^POINTS \d+ \w+\s*\n", txt, re.M)
    pts = np.fromstring(txt[m.end():m.end() + 40 * n * 3], sep=" ", count=3 * n).reshape(n, 3) * 1e3
    nc, ns = map(int, re.search(r"^CELLS (\d+) (\d+)", txt, re.M).groups())
    m = re.search(r"^CELLS \d+ \d+\s*\n", txt, re.M)
    raw = np.fromstring(txt[m.end():m.end() + 12 * ns], sep=" ", count=ns).astype(np.int64)
    cells = raw.reshape(nc, 5)[:, 1:5]

    def scal(name):
        m = re.search(r"^SCALARS " + re.escape(name) + r" \w+ 1\s*\nLOOKUP_TABLE \w+\s*\n", txt, re.M)
        if not m:
            return None
        a = np.fromstring(txt[m.end():m.end() + 25 * nc], sep=" ", count=nc)
        return a if a.size == nc else None
    m = re.search(r"^TENSORS 3DELEM_Stress \w+\s*\n", txt, re.M)
    ten = None
    if m:
        ten = np.fromstring(txt[m.end():m.end() + 16 * 9 * nc], sep=" ", count=9 * nc)
        ten = ten.reshape(nc, 9) if ten.size == 9 * nc else None
    return t, pts, cells, scal("ELEMENT_ID"), scal("PART_ID"), scal("EROSION_STATUS"), scal("3DELEM_Plastic_Strain"), ten


def main():
    label, vdir, f0, f1 = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    off = float(sys.argv[5]) if len(sys.argv) > 5 else 0.0
    o = HOLE + np.array([-ORIGIN_D[0], ORIGIN_D[1]])
    tp = HOLE + np.array([-TIP_D[0], TIP_D[1]])
    u = (tp - o) / np.linalg.norm(tp - o)
    L = np.linalg.norm(tp - o)
    track, prev_eps, D = None, None, None
    hist = []
    for fr in range(f0, f1 + 1):
        p = os.path.join(vdir, f"f{fr:03d}.vtk")
        try:
            t, P, C, eid, part, ero, eps, ten = load(p)
        except ValueError as ex:          # truncated frame (P1r26f f012: written while E: was full)
            print(f"  skip unreadable {os.path.basename(p)}: {ex}", flush=True)
            continue
        if any(v is None for v in (eid, part, ero, eps, ten)):
            print(f"  skip incomplete {os.path.basename(p)}", flush=True)
            continue
        if track is None:          # pick elements on the first frame (undeformed positions)
            cen = P[C].mean(axis=1)[:, :2]
            rel = cen - o
            s = rel @ u
            d = np.abs(rel @ np.array([-u[1], u[0]]))
            sel = (part == 2) & (d < BAND) & (s > -EXT) & (s < L + EXT)
            track = {int(e): float(sv) for e, sv in zip(eid[sel], s[sel])}
            ids = np.array(sorted(track))
            spos = np.array([track[i] for i in ids])
            prev_eps = np.zeros(len(ids))
            D = {k: np.zeros(len(ids)) for k in SETS}
            print(f"{label}: {len(ids)} elements within {BAND} mm of the real crack path (length {L:.3f} mm)", flush=True)
        idx = {int(e): k for k, e in enumerate(eid)}
        k = np.array([idx.get(i, -1) for i in ids])
        alive = (k >= 0)
        alive[alive] &= ero[k[alive]] >= 0.5
        e_now = np.where(alive, eps[np.maximum(k, 0)], prev_eps)
        S = ten[np.maximum(k, 0)]
        sm = (S[:, 0] + S[:, 4] + S[:, 8]) / 3
        dev = S.copy(); dev[:, [0, 4, 8]] -= sm[:, None]
        vm = np.sqrt(1.5 * (dev ** 2).sum(1))
        eta = np.where(vm > 1e6, sm / np.maximum(vm, 1), 0.0)
        M3 = S.reshape(-1, 3, 3)
        s1 = np.linalg.eigvalsh((M3 + M3.transpose(0, 2, 1)) / 2)[:, -1] / 1e6
        de = np.maximum(e_now - prev_eps, 0) * alive
        for key, c in SETS.items():
            D[key] += de / ef(eta, c)
        prev_eps = np.maximum(prev_eps, e_now)
        # summary: strongest element by damage (first set) and the edge end (s < 0.1 mm)
        rec = {"t_ms": t * 1e3 + off, "n_alive": int(alive.sum()), "n_deleted": int((~alive).sum()),
               "max_eps": float(prev_eps.max())}
        hot = de > 0
        if hot.any():
            rec["eta_of_new_strain"] = float(np.average(eta[hot], weights=de[hot]))
            rec["s_of_new_strain_mm"] = float(np.average(spos[hot], weights=de[hot]))
        rec["max_sigma1_MPa"] = float(np.where(alive & (spos >= 0.03), s1, -1e9).max())
        prod = spos >= 0.03          # product side only: s < 0 is trim scrap / the trim shear band itself
        for key in SETS:
            j = int(np.argmax(np.where(prod, D[key], -1)))
            rec[f"Dmax[{key}]"] = float(D[key][j]); rec[f"s_at_Dmax[{key}]"] = float(spos[j])
        hist.append(rec)
        print(f"  {label} f{fr:03d} t={rec['t_ms']:.3f} eps_max={rec['max_eps']:.3f} "
              f"eta_new={rec.get('eta_of_new_strain', float('nan')):+.2f} @s={rec.get('s_of_new_strain_mm', float('nan')):.2f} "
              f"s1max={rec['max_sigma1_MPa']:.0f} " + " ".join(f"D[{k}]={rec[f'Dmax[{k}]']:.2f}@{rec[f's_at_Dmax[{k}]']:.2f}" for k in SETS),
              flush=True)
    out = os.path.join(vdir, "..", f"crackpath_{label}.json")
    json.dump({"label": label, "band_mm": BAND, "sets": SETS, "history": hist}, open(out, "w"), indent=1)
    print("wrote", out)


if __name__ == "__main__":
    main()
