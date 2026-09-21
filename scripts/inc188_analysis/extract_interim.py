# -*- coding: utf-8 -*-
"""Interim (partial-run) hotspot time series for the running P1r13-P1r16 engines.

Reads whatever VTK frames exist in <root>/<run>_vtk (frames converted from the engines' EXISTING
animation files), reuses extract_multi_run_timeseries.load()/block_eid() unchanged, and writes
interim_timeseries_<RUN>.json. Every record is a real measurement of a real frame; nothing is
interpolated or extrapolated. Frames that are not on disk are simply absent (frame numbers are kept).

usage: python extract_interim.py <vtk_root> <out_dir> [RUN ...]
"""
import glob
import json
import os
import re
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import extract_multi_run_timeseries as ex   # noqa: E402  (load, block_eid, HOTSPOTS, centroid)


def run_interim(run, vtk_dir, out_dir):
    files = sorted(glob.glob(os.path.join(vtk_dir, "f*.vtk")),
                   key=lambda p: int(re.search(r"f(\d+)\.vtk", p).group(1)))
    if not files:
        print(f"{run}: no frames in {vtk_dir}")
        return None
    first = files[0]
    if int(re.search(r"f(\d+)\.vtk", first).group(1)) != 1:
        print(f"{run}: frame f001 (t=0) is required as the element reference; have {os.path.basename(first)}")
        return None
    pts1, cells1, part1, ero1, eps1, vm1, tens1, t1 = ex.load(first)
    eid1 = ex.block_eid(first, len(cells1))
    target = {}
    for name, (hx, hy) in ex.HOTSPOTS.items():
        best_i, best_d = None, 1e9
        for i, _ in enumerate(cells1):
            if part1[i] != 2:
                continue
            cx, cy = ex.centroid(cells1, pts1, i)
            d = ((cx - hx) ** 2 + (cy - hy) ** 2) ** 0.5
            if d < best_d:
                best_d, best_i = d, i
        target[name] = (eid1[best_i], best_d)

    series = {name: [] for name in ex.HOTSPOTS}
    frames = []
    for path in files:
        fno = int(re.search(r"f(\d+)\.vtk", path).group(1))
        pts, cells, part, ero, eps, vm, tens, t = ex.load(path)
        eid = ex.block_eid(path, len(cells))
        eid2idx = {e: i for i, e in enumerate(eid)}
        frames.append({"frame": fno, "t_ms": round(t * 1e3, 4)})
        for name, (te, _) in target.items():
            i = eid2idx.get(te)
            if i is None:
                series[name].append({"frame": fno, "t": t, "status": "gone"})
            elif ero[i] < 0.5:
                series[name].append({"frame": fno, "t": t, "status": "ruptured", "eps": eps[i]})
            else:
                svm = vm[i]
                sigma1 = eta = None
                if tens is not None:
                    sxx, sxy, sxz, syx, syy, syz, szx, szy, szz = tens[i]
                    M = np.array([[sxx, sxy, sxz], [syx, syy, syz], [szx, szy, szz]])
                    sigma1 = float(np.linalg.eigvalsh((M + M.T) / 2.0)[-1]) / 1e6
                    sm = (sxx + syy + szz) / 3.0
                    eta = sm / svm if svm > 1e3 else 0.0
                series[name].append({"frame": fno, "t": t, "status": "live", "eps": eps[i],
                                     "vm_MPa": svm / 1e6, "sigma1_MPa": sigma1, "eta": eta})
    out = {"run": run, "interim": True, "frames": frames,
           "element_ids": {k: {"eid": v[0], "dist_mm": round(v[1], 4)} for k, v in target.items()},
           "series": series}
    path = os.path.join(out_dir, f"interim_timeseries_{run}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print(f"{run}: {len(files)} frames (t up to {frames[-1]['t_ms']} ms) -> {path}")
    return out


if __name__ == "__main__":
    root, out_dir = sys.argv[1], sys.argv[2]
    runs = sys.argv[3:] or ["P1r13", "P1r14", "P1r15", "P1r16"]
    os.makedirs(out_dir, exist_ok=True)
    for r in runs:
        run_interim(r, os.path.join(root, r.lower() + "_vtk"), out_dir)
