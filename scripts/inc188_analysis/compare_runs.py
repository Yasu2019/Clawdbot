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


DECK_DIRS = ["D:/Clawdbot_Docker_20260125/clawstack_v2/data/work",
             "D:/Clawdbot_Docker_20260125/data/workspace/openradioss_inc188_trials"]
STD_CONTACT_MS = 0.795 / 5.0     # first-punch air gap 0.795 mm at 5 mm/ms


def time_offset_ms(tag):
    """0 for a standard deck; for a fast-approach deck (make_fast_approach.py) the shift that maps its
    times onto the standard punch motion (contact 0.159 ms -> 0.06 ms, i.e. +0.099 ms)."""
    for d in DECK_DIRS:
        p = f"{d}/PANEL4MM_{tag}_0000.rad"
        try:
            with open(p, encoding="utf-8", errors="replace") as f:
                lines = f.read().split("\n")
        except FileNotFoundError:
            continue
        for i, ln in enumerate(lines):
            if ln.strip() == "Punch_Stroke" and lines[i - 1].startswith("/FUNCT/"):
                pts = []
                j = i + 1
                while not lines[j].startswith("/"):
                    if not lines[j].startswith("#") and lines[j].strip():
                        pts.append((float(lines[j][:20]), float(lines[j][20:40])))
                    j += 1
                if len(pts) >= 3 and abs(pts[1][0] - 5e-5) < 1e-9:   # fast approach: (5e-5, -0.745 mm)
                    t1, d1 = pts[1][0] * 1e3, -pts[1][1] * 1e3          # ms, mm
                    fast_contact = t1 + (0.795 - d1) / 5.0
                    return round(STD_CONTACT_MS - fast_contact, 4)
                return 0.0
    return None


def summarize(tag):
    out = {"tag": tag, "hotspots": {}, "sheet": None, "round_hole": None, "offset_ms": time_offset_ms(tag)}
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
    print("| punch motion | " + " | ".join(
        "-" if r["offset_ms"] is None else ("standard" if r["offset_ms"] == 0 else f"fast approach (+{r['offset_ms']} ms = standard time)")
        for r in runs) + " |")
    for h in HOTSPOTS:
        cells = []
        for r in runs:
            d = r["hotspots"].get(h)
            off = r["offset_ms"] or 0.0
            rt = None if not d else d["rupture_ms"]
            cells.append("-" if not d else
                         (("ruptured " + (f"{rt} ms" if not off else f"{rt} ms (std {round(rt + off, 3)} ms)"))
                          if rt is not None else "live")
                         + f" (max eps {fmt(d['max_eps'])})")
        print(f"| {h} | " + " | ".join(cells) + " |")
    print("| removed volume mm3 | " + " | ".join(fmt(r["sheet"] and r["sheet"]["removed_vol_mm3"]) for r in runs) + " |")
    print("| erosion regions | " + " | ".join(fmt(r["sheet"] and r["sheet"]["n_regions"]) for r in runs) + " |")
    cells = []
    for r in runs:
        rh = r["round_hole"]
        cells.append("-" if not rh else
                     f"{'SEPARATED' if rh['separated'] else 'attached'} {rh['attached_pct']}% "
                     f"({rh['slug_in_main']}/{rh['slug_live']}) at {rh['t_ms']} ms"
                     + (f" (std {round(rh['t_ms'] + r['offset_ms'], 3)} ms)" if r.get("offset_ms") else ""))
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
