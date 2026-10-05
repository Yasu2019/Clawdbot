"""INC-188: analyse a quasi-axisymmetric sector run (make_axisym_sector.py) for mesh convergence.

usage: python axi_analyze.py DIR TAG [TAG ...]
Per run: punch stroke (after contact) at first element failure and at full separation, max punch force
(scaled from the sector to 360 deg), and the sheet-side cut-edge profile (rollover / burnish+fracture /
burr) at the last frame.
"""
import csv
import glob
import math
import os
import re
import sys

GAP, T, V, RP, RD = 5e-6, 0.5e-3, 5.0, 0.28e-3, 0.30e-3


def read_vtk(path):
    with open(path) as f:
        lines = f.read().split("\n")
    i = 0
    time = None
    pts, cells, data = [], [], {}
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("TIME"):
            time = float(lines[i + 1]); i += 2; continue
        if ln.startswith("POINTS"):
            n = int(ln.split()[1]); i += 1
            vals = []
            while len(vals) < 3 * n:
                vals += [float(v) for v in lines[i].split()]; i += 1
            pts = [vals[3 * k:3 * k + 3] for k in range(n)]
            continue
        if ln.startswith("CELLS"):
            n = int(ln.split()[1]); i += 1
            for _ in range(n):
                cells.append([int(v) for v in lines[i].split()[1:]]); i += 1
            continue
        if ln.startswith("SCALARS"):
            name = ln.split()[1]; i += 2
            vals = []
            while i < len(lines) and lines[i] and not lines[i][0].isalpha():
                vals += lines[i].split(); i += 1
            data[name] = vals
            continue
        i += 1
    return time, pts, cells, data


def analyze(d, tag):
    deck = open(os.path.join(d, f"AXI_{tag}_0000.rad")).read()
    m = re.search(r"h=([\d.]+) um", deck)
    h = float(m.group(1)) if m else float("nan")
    global GAP
    mg = re.search(r"gap=([\d.]+) um", deck)
    GAP = float(mg.group(1)) * 1e-6 if mg else 5e-6
    dth = float(re.search(r"sector ([\d.]+) deg", deck).group(1))
    frames = sorted(glob.glob(os.path.join(d, f"vtk_{tag}", "f*.vtk")))
    first_fail = None
    for ln in open(os.path.join(d, f"engine_{tag}.log"), errors="replace"):
        if "RUPTURE OF SOLID" in ln:
            first_fail = float(ln.split("TIME :")[1]); break
    sep_t, last = None, None
    for fp in frames:
        t, pts, cells, data = read_vtk(fp)
        part = [int(v) for v in data["PART_ID"]]
        ero = [int(v) for v in data["EROSION_STATUS"]]
        # blank elements alive; build node->elements adjacency (shared nodes on the theta=0 face)
        alive = [k for k in range(len(cells)) if part[k] == 2 and ero[k] != 0] if any(e == 0 for e in ero) \
            else [k for k in range(len(cells)) if part[k] == 2]
        # EROSION_STATUS: 1 = alive, 0 = eroded (checked on the first frame where failures exist)
        node_el = {}
        for k in alive:
            for n in cells[k]:
                node_el.setdefault(n, []).append(k)
        # initial radius from the element centroid in the first frame is not available here; use the
        # current centroid: slug = centroid r < RP - 20 um, sheet = centroid r > RD + 40 um
        def rc(k):
            xs = [pts[n] for n in cells[k]]
            return math.hypot(sum(p[0] for p in xs) / 8, sum(p[1] for p in xs) / 8)
        slug = [k for k in alive if rc(k) < RP - 20e-6]
        seen, stack = set(slug), list(slug)
        connected = False
        while stack:
            k = stack.pop()
            if rc(k) > RD + 40e-6:
                connected = True; break
            for n in cells[k]:
                for k2 in node_el[n]:
                    if k2 not in seen:
                        seen.add(k2); stack.append(k2)
        if not connected and sep_t is None:
            sep_t = t
        last = (t, pts, cells, alive, rc)
    # punch force: /TH/INTER gives cumulative impulses (FNX FNY FNZ FTX FTY FTZ); force = d(impulse)/dt
    # of the z components, scaled from the sector to 360 deg. Energy check: the TH internal energy
    # misses the plastic part on fine meshes (IE < plastic work, 2026-10-05), so the balance uses
    # external work vs plastic work + kinetic + contact energy.
    fmax, s_fmax, ebal = None, None, None
    curve = []
    th = os.path.join(d, f"AXI_{tag}T01.csv")
    if os.path.exists(th):
        rows = list(csv.reader(open(th)))
        hdr = rows[0]
        cols = [i for i, c in enumerate(hdr) if "Punch_Blank_Contact" in c]
        if len(cols) >= 6:
            prev = None
            for r in rows[1:]:
                if len(r) <= cols[5]:
                    continue
                tt = float(r[0]); imp = float(r[cols[2]]) + float(r[cols[5]])
                if prev and tt > prev[0]:
                    f = abs(imp - prev[1]) / (tt - prev[0]) * 360.0 / dth
                    curve.append(((V * tt - GAP) * 1e6, f))
                prev = (tt, imp)
            if curve:
                # smooth over 5 samples (1 us) before taking the max: contact chatter
                sm = [sum(c[1] for c in curve[max(0, k - 2):k + 3]) / len(curve[max(0, k - 2):k + 3]) for k in range(len(curve))]
                k = max(range(len(sm)), key=lambda q: sm[q])
                fmax, s_fmax = sm[k], curve[k][0]
        r = rows[-1]
        g = lambda name: float(r[hdr.index(name)])
        ew = g("EXTERNAL WORK")
        if ew > 0:
            ebal = (g("PLASTIC WORK") + g("KINETIC ENERGY") + g("CONTACT ENERGY")) / ew * 100
    with open(os.path.join(d, f"force_{tag}.tsv"), "w") as fo:
        fo.write("stroke_um\tF_N\n" + "".join(f"{a:.2f}\t{b:.2f}\n" for a, b in curve))
    # sheet = surviving blank elements connected to the far field (r > 0.8 mm) at the last frame
    t, pts, cells, alive, rc = last
    node_el = {}
    for k in alive:
        for n in cells[k]:
            node_el.setdefault(n, []).append(k)
    seed = [k for k in alive if rc(k) > 0.8e-3]
    sheet, stack = set(seed), list(seed)
    while stack:
        k = stack.pop()
        for n in cells[k]:
            for k2 in node_el[n]:
                if k2 not in sheet:
                    sheet.add(k2); stack.append(k2)
    face = [pts[n] for k in sheet for n in cells[k] if abs(pts[n][1]) < 1e-9]   # theta=0 face nodes
    top_far = max(p[2] for p in face if p[0] > 0.8e-3)
    rmin = min(p[0] for p in face)
    # cut-edge profile: innermost radius per 5 um z-bin
    prof = {}
    for p in face:
        b = int(math.floor(p[2] * 1e6 / 5.0))
        prof[b] = min(prof.get(b, 1.0), p[0])
    with open(os.path.join(d, f"edge_{tag}.tsv"), "w") as fo:
        fo.write("z_um\tr_um\n" + "".join(f"{b*5+2.5:.1f}\t{prof[b]*1e6:.2f}\n" for b in sorted(prof)))
    near = [p for p in face if p[0] < rmin + 20e-6]
    top_edge = max(p[2] for p in near)
    burnish = sum(5.0 for b in prof if prof[b] < rmin + 5e-6)   # wall within 5 um of the innermost radius
    burr = max(0.0, -min(p[2] for p in near) * 1e6)                # below the die top (z=0)
    return {
        "tag": tag, "h_um": h,
        "fail1_stroke_um": None if first_fail is None else (V * first_fail - GAP) * 1e6,
        "sep_stroke_um": None if sep_t is None else (V * sep_t - GAP) * 1e6,
        "Fmax_N": fmax, "stroke_at_Fmax_um": s_fmax,
        "rollover_um": (top_far - top_edge) * 1e6,
        "burnish_um": burnish, "burr_um": burr, "hole_r_um": rmin * 1e6,
        "energy_bal_pct": ebal, "n_frames": len(frames),
    }

if __name__ == "__main__":
    d = sys.argv[1]
    keys = ["tag", "h_um", "fail1_stroke_um", "sep_stroke_um", "Fmax_N", "stroke_at_Fmax_um", "rollover_um", "burnish_um", "burr_um", "hole_r_um", "energy_bal_pct", "n_frames"]
    print("\t".join(keys))
    for tag in sys.argv[2:]:
        r = analyze(d, tag)
        print("\t".join("-" if r[k] is None else (f"{r[k]:.1f}" if isinstance(r[k], float) else str(r[k])) for k in keys))
