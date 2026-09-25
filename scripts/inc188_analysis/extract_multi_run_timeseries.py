# -*- coding: utf-8 -*-
"""P1r8/P1r9/P1r10/P1r11/P1r12の各VTKフレーム群から、6箇所(H1,H2,H2b,H3,H4,H5)の
Von Mises・応力三軸度・等価塑性ひずみの時系列を抽出する(extract_timeseries.pyの多Run版)。
座標は全RunでP1r7と同一幾何(P1r12はメッシュサイズのみ異なるため最近接要素で再特定)。
"""
import glob
import re
import json
import sys
import numpy as np

HOTSPOTS = {
    "H4": (185.55, -1881.25),
    "H1": (183.208, -1880.745),
    "H2": (182.801, -1878.650),
    "H2b": (187.056, -1884.107),
    "H3": (179.857, -1878.233),
    "H5": (181.092, -1878.245),
}

RUNS = {
    "P1r8": r"p1r8_vtk",
    "P1r9": r"p1r9_vtk",
    "P1r10": r"p1r10_vtk",
    "P1r11": r"p1r11_vtk",
    "P1r12": r"p1r12_vtk",
    # six-order punch study (rect,round,trim / round,rect,trim / trim,round,rect / round,trim,rect)
    "P1r13": r"p1r13_vtk",
    "P1r14": r"p1r14_vtk",
    "P1r15": r"p1r15_vtk",
    "P1r16": r"p1r16_vtk",
    "P1r17": r"p1r17_vtk",   # stroke 4 mm (tstop 0.8 ms), round-hole penetration test
    "P1r18": r"p1r18_vtk",   # P1r8 + COCKCROFT C0 = 19.1 MPa from the MR536 tensile curve
}


def load(path):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
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
            block("3DELEM_Plastic_Strain"), block("3DELEM_Von_Mises"), tens, t)


def block_eid(path, nc):
    lines = open(path, encoding="utf-8", errors="replace").read().split("\n")
    idx = [k for k, l in enumerate(lines) if l.startswith("SCALARS ELEMENT_ID")][0]
    out, k = [], idx + 2
    while len(out) < nc and k < len(lines):
        out += [int(float(x)) for x in lines[k].split()]
        k += 1
    return out[:nc]


def centroid(cells, pts, i):
    xs = [pts[n][0] for n in cells[i]]
    ys = [pts[n][1] for n in cells[i]]
    return sum(xs) / len(xs) * 1000, sum(ys) / len(ys) * 1000


def run_one(run_name, vtk_dir):
    files = sorted(glob.glob(vtk_dir + "/f*.vtk"),
                    key=lambda p: int(re.search(r"f(\d+)\.vtk", p).group(1)))
    if not files:
        print(f"{run_name}: NO VTK FILES FOUND in {vtk_dir}, skipping")
        return None
    print(f"{run_name}: {len(files)} frames")

    pts1, cells1, part1, ero1, eps1, vm1, tens1, t1 = load(files[0])
    eid1 = block_eid(files[0], len(cells1))

    target_eid = {}
    for name, (hx, hy) in HOTSPOTS.items():
        best_i, best_d = None, 1e9
        for i, c in enumerate(cells1):
            if part1[i] != 2:
                continue
            cx, cy = centroid(cells1, pts1, i)
            d = ((cx - hx) ** 2 + (cy - hy) ** 2) ** 0.5
            if d < best_d:
                best_d, best_i = d, i
        target_eid[name] = eid1[best_i]
        print(f"  {name}: nearest element_id={eid1[best_i]} dist={best_d:.4f}mm")

    series = {name: [] for name in HOTSPOTS}
    for fi, path in enumerate(files):
        pts, cells, part, ero, eps, vm, tens, t = load(path)
        eid = block_eid(path, len(cells))
        eid2idx = {e: i for i, e in enumerate(eid)}
        for name, target in target_eid.items():
            i = eid2idx.get(target)
            if i is None:
                series[name].append({"t": t, "status": "gone"})
                continue
            if ero[i] < 0.5:
                series[name].append({"t": t, "status": "ruptured", "eps": eps[i]})
                continue
            svm = vm[i]
            if tens is not None:
                sxx, sxy, sxz, syx, syy, syz, szx, szy, szz = tens[i]
                M = np.array([[sxx, sxy, sxz], [syx, syy, syz], [szx, szy, szz]])
                eigvals = np.linalg.eigvalsh((M + M.T) / 2.0)
                sigma1 = eigvals[-1]
                sm = (sxx + syy + szz) / 3.0
                eta = sm / svm if svm > 1e3 else 0.0
            else:
                sigma1, eta = None, None
            series[name].append({
                "t": t, "status": "live", "eps": eps[i],
                "vm_MPa": svm / 1e6, "sigma1_MPa": (sigma1 / 1e6 if sigma1 is not None else None),
                "eta": eta,
            })
    out_path = f"timeseries_{run_name}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(series, f, ensure_ascii=False, indent=1)
    print(f"  saved {out_path}")
    return series


if __name__ == "__main__":
    targets = sys.argv[1:] if len(sys.argv) > 1 else list(RUNS.keys())
    for run_name in targets:
        run_one(run_name, RUNS[run_name])
