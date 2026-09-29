# -*- coding: utf-8 -*-
"""Side-by-side summary of finished INC-188 runs (real solver output only).

Per run: for each tracked hotspot the rupture time (first frame whose status is not 'live') and the
max equivalent plastic strain; the whole-sheet erosion scan (removed volume, number of regions);
the round-hole separation check on the last frame (slug still attached to the main sheet).

Inputs (F:/clawstack_data/inc188/vtk): timeseries_<TAG>.json, rupture_sites_<TAG>.json,
round_hole_sep_<TAG>.json or the newest round_hole_sep_<TAG>_fNNN.json.
usage: python compare_runs.py TAG [TAG ...]   -> markdown table on stdout + compare_<TAGS>.json
"""
import glob
import json
import os
import sys

VTK = "F:/clawstack_data/inc188/vtk"
HOTSPOTS = ["H4", "H1", "H2", "H2b", "H3", "H5"]


def load(path):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None


def round_hole(tag):
    cands = glob.glob(f"{VTK}/round_hole_sep_{tag}_f[0-9][0-9][0-9].json")
    if cands:
        return load(max(cands, key=lambda p: int(p[-8:-5])))
    return load(f"{VTK}/round_hole_sep_{tag}.json")


def summarize(tag):
    out = {"tag": tag, "hotspots": {}, "sheet": None, "round_hole": None}
    ts = load(f"{VTK}/timeseries_{tag}.json")
    if ts:
        for h in HOTSPOTS:
            rows = ts.get(h) or []
            dead = [r["t"] for r in rows if r.get("status") != "live"]
            out["hotspots"][h] = {
                "rupture_ms": round(dead[0] * 1e3, 3) if dead else None,
                "max_eps": round(max((r.get("eps") or 0.0) for r in rows), 3) if rows else None,
            }
    rs = load(f"{VTK}/rupture_sites_{tag}.json")
    if rs:
        out["sheet"] = {"removed_vol_mm3": rs.get("removed_vol_mm3"), "n_regions": rs.get("n_regions"),
                        "t_ms": rs.get("t_ms")}
    rh = round_hole(tag)
    if rh:
        live = rh.get("slug_live") or 0
        out["round_hole"] = {"t_ms": rh.get("t_ms"), "separated": rh.get("separated"),
                             "slug_in_main": rh.get("slug_live_in_main"), "slug_live": live,
                             "attached_pct": round(100.0 * rh.get("slug_live_in_main", 0) / live, 1) if live else None,
                             "main_min_dist_t0_mm": rh.get("main_min_dist_to_hole_centre_t0_mm"),
                             "core_separated": rh.get("core_separated"),
                             "attached_min_r0_mm": rh.get("attached_min_r0_mm")}
    return out


def fmt(v):
    return "-" if v is None else str(v)


def main():
    tags = sys.argv[1:]
    if not tags:
        print(__doc__)
        return 2
    runs = [summarize(t) for t in tags]
    head = "| item | " + " | ".join(tags) + " |"
    sep = "|---|" + "---|" * len(tags)
    print(head)
    print(sep)
    for h in HOTSPOTS:
        cells = []
        for r in runs:
            d = r["hotspots"].get(h)
            cells.append("-" if not d else
                         (f"ruptured {d['rupture_ms']} ms" if d["rupture_ms"] is not None else "live")
                         + f" (max eps {fmt(d['max_eps'])})")
        print(f"| {h} | " + " | ".join(cells) + " |")
    print("| removed volume mm3 | " + " | ".join(fmt(r["sheet"] and r["sheet"]["removed_vol_mm3"]) for r in runs) + " |")
    print("| erosion regions | " + " | ".join(fmt(r["sheet"] and r["sheet"]["n_regions"]) for r in runs) + " |")
    cells = []
    for r in runs:
        rh = r["round_hole"]
        cells.append("-" if not rh else
                     f"{'SEPARATED' if rh['separated'] else 'attached'} {rh['attached_pct']}% "
                     f"({rh['slug_in_main']}/{rh['slug_live']}) at {rh['t_ms']} ms")
    print("| round hole (last frame) | " + " | ".join(cells) + " |")
    cells = []
    for r in runs:
        rh = r["round_hole"]
        cs = None if not rh else rh.get("core_separated")
        cells.append("-" if cs is None else
                     ("core SEPARATED" if cs else "core attached")
                     + (f", attached from r0={rh['attached_min_r0_mm']} mm" if rh.get("attached_min_r0_mm") is not None else ""))
    print("| round hole core r<0.24 mm | " + " | ".join(cells) + " |")
    missing = [r["tag"] for r in runs if not r["hotspots"] or not r["sheet"] or not r["round_hole"]]
    if missing:
        print(f"\nmissing inputs for: {', '.join(missing)} (run finalize_runs.sh / round_hole_separation.py first)")
    dst = os.path.join(VTK, "compare_" + "_".join(tags) + ".json")
    with open(dst, "w", encoding="utf-8") as f:
        json.dump(runs, f, indent=1, ensure_ascii=False)
    print(f"\njson: {dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
