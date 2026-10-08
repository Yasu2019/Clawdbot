# -*- coding: utf-8 -*-
"""INC-188: station-like punching sequence with per-station stripper openings (2026-10-09).

User's point (10-09): in the real progressive die, the stripper at each station only has the opening
for the punch working there, and the other punches are not there at all. The single-stroke model had
all three punches go down together (order by height) - so while the round hole was punched the rectangle
and trim punches were still stuck in their cuts, touching the trim edge at H4 - and one stripper with
all openings open.

This builds, from a fast deck (default P1r34f: GENE1 0.5, 30 um tool edges):
  * punches split into rect / trim / round (connected components of part 4, by their bottom height),
    each with its own motion: approach 15 m/s -> cut 5 m/s to 0.1 mm above the die bottom -> withdraw
    10 m/s; the next punch starts its approach when the previous one starts withdrawing;
  * a "plug" per punch (copy of the punch mesh shifted so its bottom is at the stripper bottom) that moves
    with the stripper and presses the sheet inside that opening until its punch arrives (contact Tstop);
    plugs have no contact with punches, so the punch passes through;
  * stripper released after the last withdrawal.

usage: python make_station_deck.py [--src P1r34f] [--tag P1r36f]
"""
import argparse
import os
import re

import numpy as np

W = "E:/ClawstackData/clawstack_v2_data/work"
SHEET_TOP = 1.005e-3
STRIP_BOTTOM0 = 1.2e-3
GAP = 5e-6
V_APP, V_CUT, V_WD = 15.0, 5.0, 10.0
TIP_CUT = 0.10e-3          # tip height at the end of the cut (sheet bottom 0.505 mm, die 0..0.5 mm)
TIP_WD = 1.10e-3           # tip height after withdrawal
T_CLOSE = 40e-6            # stripper closed
ORDER = ("rect", "trim", "round")


def f20(v):
    return f"{float(v):>20.7G}"


def i10(v):
    return f"{int(v):>10d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="P1r34f")
    ap.add_argument("--tag", default="P1r36f")
    a = ap.parse_args()
    src = open(os.path.join(W, f"PANEL4MM_{a.src}_0000.rad"), newline="").read()
    eng = open(os.path.join(W, f"PANEL4MM_{a.src}_0001.rad"), newline="").read()
    lines = src.split("\n")

    def block_range(head):
        i = lines.index(head)
        j = i + 1
        while j < len(lines) and not lines[j].startswith("/"):
            j += 1
        return i, j

    # nodes
    i0, i1 = block_range("/NODE")
    nid, xyz = [], []
    for ln in lines[i0 + 1:i1]:
        if len(ln) >= 70 and not ln.startswith("#"):
            nid.append(int(ln[:10])); xyz.append((float(ln[10:30]), float(ln[30:50]), float(ln[50:70])))
    nid = np.array(nid); xyz = np.array(xyz)
    pos = {n: k for k, n in enumerate(nid)}
    # punch elements
    p0, p1 = block_range("/TETRA4/4")
    pe = []
    for ln in lines[p0 + 1:p1]:
        if len(ln) >= 50 and not ln.startswith("#"):
            pe.append([int(ln[10 * q:10 * q + 10]) for q in range(5)])
    pe = np.array(pe)
    # connected components (union-find over nodes)
    par = {}

    def find(x):
        while par.get(x, x) != x:
            par[x] = par.get(par[x], par[x]); x = par[x]
        return x
    for e in pe:
        r = [find(n) for n in e[1:]]
        for q in r[1:]:
            if q != r[0]:
                par[q] = r[0]
    comp = np.array([find(e[1]) for e in pe])
    groups = {k: [] for k in ORDER}
    for c in np.unique(comp):
        sel = pe[comp == c]
        zmin = min(xyz[pos[n], 2] for n in np.unique(sel[:, 1:]))
        name = min(((abs(zmin - z), g) for g, z in (("rect", 1.8e-3), ("trim", 2.4e-3), ("round", 3.0e-3))))[1]
        groups[name].append(sel)
        print(f"punch component {c}: {len(sel)} tets, zmin {zmin*1e3:.3f} mm -> {name}")
    groups = {g: np.concatenate(v) for g, v in groups.items()}
    zmin = {g: min(xyz[pos[n], 2] for n in np.unique(v[:, 1:])) for g, v in groups.items()}

    # motion schedule
    sched, t = {}, T_CLOSE
    for g in ORDER:
        d_app = zmin[g] - (SHEET_TOP + GAP)
        t_app = t + d_app / V_APP
        d_cut = zmin[g] - TIP_CUT
        t_cut = t_app + (d_cut - d_app) / V_CUT
        d_wd = zmin[g] - TIP_WD
        t_wd = t_cut + (d_cut - d_wd) / V_WD
        sched[g] = [(0, 0), (t, 0), (t_app, -d_app), (t_cut, -d_cut), (t_wd, -d_wd), (0.006, -d_wd)]
        print(f"{g}: start {t*1e6:.1f} us, at sheet {t_app*1e6:.1f}, cut end {t_cut*1e6:.1f}, out {t_wd*1e6:.1f} us")
        sched[g + "_plug_off"] = t_app - 2e-6
        sched[g + "_end"] = t_wd
        t = t_cut                       # next punch starts its approach when this one starts withdrawing
    t_last = sched["round_end"]
    t_rel = t_last + 30e-6
    tstop = t_rel + 10e-6

    # plugs: copies of the punch meshes, bottom at the stripper bottom
    nmax, emax = int(nid.max()), 0
    for hd in ("/TETRA4/1", "/TETRA4/2", "/TETRA4/3", "/TETRA4/4"):
        b0, b1 = block_range(hd)
        for ln in lines[b0 + 1:b1]:
            if len(ln) >= 10 and not ln.startswith("#"):
                emax = max(emax, int(ln[:10]))
    new_nodes, new_blocks, plug_nodes, grp_punch = [], {}, [], {}
    off_n, off_e = 10 ** (len(str(nmax))), 10 ** (len(str(emax)))
    for k, g in enumerate(ORDER):
        el = groups[g]
        nodes_g = np.unique(el[:, 1:])
        grp_punch[g] = nodes_g
        dz = STRIP_BOTTOM0 - zmin[g]
        base_n = off_n * (k + 1)
        base_e = off_e * (k + 1)
        for n in nodes_g:
            x, y, z = xyz[pos[n]]
            new_nodes.append(f"{i10(base_n + n)}{f20(x)}{f20(y)}{f20(z + dz)}")
            plug_nodes.append(base_n + n)
        new_blocks[5 + k] = [i10(base_e + e[0]) + "".join(i10(base_n + n) for n in e[1:]) for e in el]

    out = lines[:i1] + new_nodes + lines[i1:]
    txt = "\n".join(out)
    # elements of the plugs before /MAT
    mat_i = txt.index("\n/MAT/LAW1/1\n")
    blk = "".join(f"\n/TETRA4/{pid}\n" + "\n".join(v) for pid, v in new_blocks.items())
    txt = txt[:mat_i] + blk + txt[mat_i:]
    # parts, groups, surfaces
    parts = "".join(f"/PART/{5 + k}\nPlug_{g}\n#    Prop_ID     Mat_ID\n{i10(1)}{i10(1)}\n" for k, g in enumerate(ORDER))
    txt = txt.replace("/GRNOD/NODE/100\n", parts + "/GRNOD/NODE/100\n", 1)

    def grnod(gid, name, ids):
        ids = sorted(int(v) for v in ids)
        return f"/GRNOD/NODE/{gid}\n{name}\n" + "\n".join("".join(i10(v) for v in ids[i:i + 10]) for i in range(0, len(ids), 10)) + "\n"
    g_add = "".join(grnod(101 + k, f"Punch_{g}_Nodes", grp_punch[g]) for k, g in enumerate(ORDER))
    g_add += grnod(500, "Plug_Nodes", plug_nodes)
    s_add = "".join(f"/SURF/PART/EXT/{(5 + k) * 100}/0\nSurf_Plug_{g}\n{i10(5 + k)}\n" for k, g in enumerate(ORDER))
    txt = txt.replace("/SURF/PART/EXT/100/0\n", g_add + s_add + "/SURF/PART/EXT/100/0\n", 1)
    # functions
    fn = ""
    for k, g in enumerate(ORDER):
        fn += f"/FUNCT/{11 + k}\nPunch_{g}_station\n#                  X                   Y\n" + "".join(f20(x) + f20(y) + "\n" for x, y in sched[g])
    fn += ("/FUNCT/2\nStripper_close_hold_release\n#                  X                   Y\n" + "".join(
        f20(x) + f20(y) + "\n" for x, y in [(0, 0), (T_CLOSE, -0.00019), (t_last, -0.00019), (t_rel, 0.00011), (0.006, 0.00011)]))
    f2_i = txt.index("/FUNCT/2\n"); f2_j = txt.index("\n/FUNCT/3\n")
    txt = txt[:f2_i] + fn.rstrip("\n") + txt[f2_j:]
    # punch motion: the old IMPDISP/1 (all punch nodes, FUNCT/1) -> one per punch group
    m = re.search(r"/IMPDISP/1\n.*?\n(?=/)", txt, re.S)
    imp = ""
    for k, g in enumerate(ORDER):
        imp += (f"/IMPDISP/{21 + k}\nPunch_{g}_Z\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor\n"
                f"{i10(11 + k)}         Z         0         0{i10(101 + k)}         0\n"
                "#             Ascale_x            Fscale_y              Tstart               Tstop\n"
                "                   1                   1                   0               1E+30\n")
    imp += ("/IMPDISP/24\nPlugs_Z\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor\n"
            "         2         Z         0         0       500         0\n"
            "#             Ascale_x            Fscale_y              Tstart               Tstop\n"
            "                   1                   1                   0               1E+30\n")
    for k, d in enumerate(("X", "Y")):
        imp += (f"/IMPVEL/{25 + k}\nPlugs_{d}\n#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe\n"
                f"         3         {d}         0         0       500         0         0\n"
                "#             Ascale_x            Fscale_y              Tstart               Tstop\n"
                "                   1                   1                   0               1E+30\n")
    txt = txt[:m.start()] + imp + txt[m.end():]
    # plug contacts: like the stripper contact, until the punch arrives
    m = re.search(r"/INTER/TYPE25/2/0\n.*?\n(?=/)", txt, re.S)
    tmpl = m.group(0)
    inter = ""
    for k, g in enumerate(ORDER):
        c = tmpl.replace("/INTER/TYPE25/2/0", f"/INTER/TYPE25/{4 + k}/0").replace("Stripper_Blank_Contact", f"Plug_{g}_Blank_Contact")
        c = c.replace("       300       200 ", f"{i10((5 + k) * 100)}       200 ", 1)
        c = c.replace("                   1                 0.1                                       0               1e+30",
                      "                   1                 0.1                                       0" + f20(sched[g + "_plug_off"]), 1)
        assert f"{i10((5 + k) * 100)}       200 " in c and f20(sched[g + "_plug_off"]) in c, c
        inter += c
    txt = txt.replace("/END", inter + "/END", 1) if txt.count("/END") == 1 else txt[:txt.rindex("/END")] + inter + txt[txt.rindex("/END"):]
    txt = txt.replace(a.src, a.tag)
    open(os.path.join(W, f"PANEL4MM_{a.tag}_0000.rad"), "w", newline="").write(txt)
    e2 = eng.replace(a.src, a.tag)
    e2 = re.sub(r"/RUN/(\S+)/1\n *\S+\n", lambda mm: f"/RUN/{mm.group(1)}/1\n{f20(tstop)}\n", e2, count=1)
    open(os.path.join(W, f"PANEL4MM_{a.tag}_0001.rad"), "w", newline="").write(e2)
    print(f"{a.tag}: plugs off at " + ", ".join(f"{g} {sched[g + '_plug_off']*1e6:.1f} us" for g in ORDER) +
          f"; last withdrawal {t_last*1e6:.1f} us, stripper released {t_rel*1e6:.1f} us, tstop {tstop*1e6:.1f} us; "
          f"+{len(new_nodes)} nodes, +{sum(len(v) for v in new_blocks.values())} tets")


if __name__ == "__main__":
    main()
