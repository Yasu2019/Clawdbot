# -*- coding: utf-8 -*-
"""全体スキャン: 最終フレームで消失(EROSION_STATUS<0.5)した材料要素を空間クラスタに分け、
どこで破断が起きたかを列挙する。6ホットスポットだけの追跡では、順番を変えて別の場所が
割れたときに見逃すため、その補完として使う。

使い方: python scan_rupture_sites.py <label> <final.vtk> <first_frame.vtk> [cluster_cell_mm]
出力: rupture_sites_<label>.json と要約表(標準出力)。ホットスポット座標(mm)への最短距離も付ける。
"""
import sys
import json
from collections import defaultdict

HOTSPOTS_MM = {
    "H4": (185.55, -1881.25), "H1": (183.208, -1880.745), "H2": (182.801, -1878.650),
    "H2b": (187.056, -1884.107), "H3": (179.857, -1878.233), "H5": (181.092, -1878.245),
    "ROUND_HOLE": (185.657, -1882.188),
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
        out, k = [], idx[0] + 2
        while len(out) < nc and k < len(lines):
            out += [cast(float(x)) for x in lines[k].split()]
            k += 1
        return out[:nc]

    tl = [k for k, l in enumerate(lines) if l.strip() == "TIME 1 1 double"]
    t = float(lines[tl[0] + 1]) if tl else 0.0
    return pts[:n], cells, block("PART_ID", int), block("EROSION_STATUS"), t, block("ELEMENT_ID", int)


def main():
    label, path, first = sys.argv[1], sys.argv[2], sys.argv[3]
    cell_mm = float(sys.argv[4]) if len(sys.argv) > 4 else 0.15
    # 消失判定は最終フレーム、形状(重心・体積)は必ずt=0フレームを使う。消失した要素の節点は
    # 最終フレームで飛散しており、そこから測ると体積が桁違いに(約1.6万倍)膨らむ。
    _, _, _, ero, t, eid_last = load(path)
    pts, cells, part, _, _, eid_first = load(first)
    assert eid_first == eid_last, "element order differs between first and last frame"

    dead = []          # (x_mm, y_mm) of eroded blank elements
    dvol = []          # tet volume [mm^3] (mesh-density independent measure of removed material)
    for i, c in enumerate(cells):
        if part[i] == 2 and ero[i] < 0.5:
            xs = [pts[n][0] for n in c]
            ys = [pts[n][1] for n in c]
            dead.append((sum(xs) / len(xs) * 1e3, sum(ys) / len(ys) * 1e3))
            a, b, cc, d = (pts[n] for n in c[:4])
            u = [b[k] - a[k] for k in range(3)]
            v = [cc[k] - a[k] for k in range(3)]
            w = [d[k] - a[k] for k in range(3)]
            det = (u[0] * (v[1] * w[2] - v[2] * w[1]) - u[1] * (v[0] * w[2] - v[2] * w[0])
                   + u[2] * (v[0] * w[1] - v[1] * w[0]))
            dvol.append(abs(det) / 6.0 * 1e9)   # m^3 -> mm^3

    # 単純な格子クラスタリング(8近傍の連結成分)
    occ = defaultdict(list)
    for idx, (x, y) in enumerate(dead):
        occ[(round(x / cell_mm), round(y / cell_mm))].append(idx)
    seen, comps = set(), []
    for key in occ:
        if key in seen:
            continue
        stack, comp = [key], []
        seen.add(key)
        while stack:
            kx, ky = stack.pop()
            comp.extend(occ[(kx, ky)])
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    nk = (kx + dx, ky + dy)
                    if nk in occ and nk not in seen:
                        seen.add(nk)
                        stack.append(nk)
        comps.append(comp)

    comps.sort(key=len, reverse=True)

    def summarize(comp):
        xs = [dead[i][0] for i in comp]
        ys = [dead[i][1] for i in comp]
        cx, cy = sum(xs) / len(xs), sum(ys) / len(ys)
        near = min(HOTSPOTS_MM.items(), key=lambda kv: (kv[1][0] - cx) ** 2 + (kv[1][1] - cy) ** 2)
        return {"n_elems": len(comp), "vol_mm3": round(sum(dvol[i] for i in comp), 6),
                "cx_mm": round(cx, 3), "cy_mm": round(cy, 3),
                "extent_mm": round(max(max(xs) - min(xs), max(ys) - min(ys)), 3),
                "nearest": near[0],
                "dist_hot_mm": round(((near[1][0] - cx) ** 2 + (near[1][1] - cy) ** 2) ** 0.5, 3)}

    regions = sorted((summarize(c) for c in comps), key=lambda x: -x["vol_mm3"])
    # t=0の形状で見ると、消失要素は打ち抜きの切断線に沿う大きな領域だけにまとまる。
    # 200要素未満の小領域は切断線から外れた点在の破断で、想定外の場所の候補になる。
    stray = [x for x in regions if x["n_elems"] < 200]

    out = {"label": label, "t_ms": round(t * 1e3, 4), "n_dead": len(dead),
           "removed_vol_mm3": round(sum(dvol), 6), "n_regions": len(regions),
           "secondary_count": len(regions) - 1,      # 旧キー互換(最大領域以外の数)
           "regions": regions, "stray_regions": stray}
    json.dump(out, open(f"rupture_sites_{label}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{label}: t={t*1e3:.3f}ms removed={sum(dvol):.4f} mm3 ({len(dead):,} elems, geometry @t=0) "
          f"regions={len(regions)} stray(<200 elems)={len(stray)}")
    for x in regions:
        print(f"    n={x['n_elems']:>7,} vol={x['vol_mm3']:.4f}mm3 extent={x['extent_mm']:.2f}mm "
              f"at ({x['cx_mm']:.2f},{x['cy_mm']:.2f}) nearest={x['nearest']} {x['dist_hot_mm']:.2f}mm")


if __name__ == "__main__":
    main()
