"""INC-188: quasi-axisymmetric round-hole piercing model (thin hex sector) for mesh convergence.

The 3D model resolves the round hole (phi0.56, clearance 20 um) with 20-33 um tets. The literature asks
for 4-8 um in the shear zone and a convergence check in 2D/axisymmetry first. This builds a one-element
thick wedge (DTHETA deg) of hex elements with symmetry on both cut planes, so the same OpenRadioss
material, failure cards and TYPE25 contacts as the 3D deck can be used unchanged.

Geometry (m): die top z=0 (hole r=0.30 mm), blank z=[GAP, GAP+T], punch r<=0.28 mm starting GAP above
the blank, stripper hole r=0.285 mm GAP above the blank (displacement-controlled, fixed, as in 3D).
Punch moves at V (5 m/s, the 3D cutting speed). Blank r in [R0, R1].

usage: python make_axisym_sector.py TAG H_um [--fail gene1|cockcroft] [--c0 19.1e6] [--eps-s 0.5]
       [--stripper fixed|free] -> AXI_<TAG>_0000.rad / _0001.rad in --out (default the container work dir)
"""
import argparse
import math
import os

MM = 1e-3
T = 0.5 * MM          # sheet thickness
GAP = 5e-6            # tool-blank initial gap (as TOOL_GAP in the 3D builder)
RP = 0.28 * MM        # punch radius
RD = 0.30 * MM        # die hole radius (measured, clearance 20 um)
RS = 0.285 * MM       # stripper hole radius
R0 = 0.05 * MM        # inner edge of the modelled blank / punch (free: an u_r=0 BC here + wide tools gave -61 % energy error)
R1 = 1.00 * MM        # outer edge
TOOL_H = 0.15 * MM    # tool height
V = 5.0               # punch speed m/s
STROKE = 0.60 * MM    # punch travel after first contact (> T)
STEEL = (7800.0, 2.1e11, 0.28)
# tools span [-TOOL_DTH, DTHETA+TOOL_DTH] deg: with the blank's symmetry faces coplanar to the tool side
# faces, TYPE25 produced an out-of-plane (Y) punch force and an energy error of -70..-99 % (G10/G5,
# 2026-10-05). r*4deg = 7 um at R0 keeps every tool node outside the contact gap of those faces.
TOOL_DTH = 10.0


def f20(v):
    return f"{float(v):>20.7G}"


def i10(v):
    return f"{int(v):>10d}"


def graded(a, b, h_fine, fa, fb, h_max, ratio=1.15):
    """1D node coordinates on [a,b]: h_fine inside [fa,fb], geometric growth (ratio) outside, capped."""
    xs = []
    # fine band
    n = max(1, round((fb - fa) / h_fine))
    band = [fa + (fb - fa) * i / n for i in range(n + 1)]
    left = []
    x, h = fa, h_fine
    while x - h * ratio > a + 0.5 * h:
        h = min(h * ratio, h_max); x -= h; left.append(x)
    right = []
    x, h = fb, h_fine
    while x + h * ratio < b - 0.5 * h:
        h = min(h * ratio, h_max); x += h; right.append(x)
    xs = ([a] if fa > a else []) + left[::-1] + band + right + ([b] if fb < b else [])
    return sorted(set(round(v, 12) for v in xs))


def build(tag, h, fail, c0, eps_s, stripper, dtheta_deg, out, tstop=None, isolid=24, stfac=1.0, pmesh=0.4, gapmax=None, tool_dth=None, inner_bc=True, gap0=None):
    # initial tool-blank distance must be inside the contact gap (0.4 x element size): with 5 um and
    # h<=10 um the blank started outside every contact, floated free and hit the die (energy error
    # -65..-99 %, 2026-10-05). G20 (gap 8 um > 5 um) was fine.
    global GAP
    GAP = gap0 if gap0 else min(5e-6, 0.15 * h)
    th = math.radians(dtheta_deg)
    c, s = math.cos(th), math.sin(th)
    nodes = []           # (id, x, y, z)
    nid = [0]

    def node(r, z, a):
        nid[0] += 1
        nodes.append((nid[0], r * math.cos(a), r * math.sin(a), z))
        return nid[0]

    def block(rs, zs, a0=0.0, a1=None):
        """hex block on radial nodes rs x axial nodes zs between angles a0..a1; returns (bricks, ids[k][i][j])."""
        a1 = th if a1 is None else a1
        ids = [[[node(r, z, a) for z in zs] for r in rs] for a in (a0, a1)]
        br = []
        for i in range(len(rs) - 1):
            for j in range(len(zs) - 1):
                a = [ids[0][i][j], ids[0][i][j + 1], ids[0][i + 1][j + 1], ids[0][i + 1][j]]
                b = [ids[1][i][j], ids[1][i][j + 1], ids[1][i + 1][j + 1], ids[1][i + 1][j]]
                br.append(a + b)
        return br, ids

    hmax = max(25e-6, h)
    # blank: fine band around the cutting gap, also fine through the full thickness
    rb = graded(R0, R1, h, RP - 60e-6, RD + 60e-6, hmax)
    nz = max(1, round(T / h))
    zb = [GAP + T * j / nz for j in range(nz + 1)]
    blank, bid = block(rb, zb)
    # punch (r <= RP), die (r >= RD), stripper (r >= RS): tool meshes fine only near the edge
    hz_t = max(h, 10e-6)
    zp = graded(GAP + T + GAP, GAP + T + GAP + TOOL_H, hz_t, GAP + T + GAP, GAP + T + GAP + 40e-6, 50e-6)
    rp = graded(R0, RP, hz_t, RP - 40e-6, RP, 50e-6)
    ew = math.radians(TOOL_DTH if tool_dth is None else tool_dth)
    punch, pid_ = block(rp, zp, -ew, th + ew)
    zd = graded(-TOOL_H, 0.0, hz_t, -40e-6, 0.0, 50e-6)
    rd = graded(RD, R1, hz_t, RD, RD + 40e-6, 50e-6)
    die, did = block(rd, zd, -ew, th + ew)
    zs_ = graded(GAP + T + GAP, GAP + T + GAP + TOOL_H, hz_t, GAP + T + GAP, GAP + T + GAP + 40e-6, 50e-6)
    rs_ = graded(RS, R1, hz_t, RS, RS + 40e-6, 50e-6)
    strip, sid = block(rs_, zs_, -ew, th + ew)

    def allids(ids):
        return sorted({n for k in ids for col in k for n in col})

    def plane(ids, k):
        return sorted({n for col in ids[k] for n in col})

    # inner edge r=R0 stands in for the axis: no radial motion (a free inner face let the slug squeeze
    # inward like a ring and the punch 'ate' through it, 2026-10-05 G10/G20)
    inner0 = set(bid[0][0]) if inner_bc else set(); inner1 = set(bid[1][0]) if inner_bc else set()
    sym0 = [n for n in plane(bid, 0) if n not in inner0]   # punch: IMPVEL X/Y=0 already
    sym1 = [n for n in plane(bid, 1) if n not in inner1]
    punch_n, die_n, strip_n = allids(pid_), allids(did), allids(sid)
    lines = []
    w = lines.append
    w("#RADIOSS STARTER"); w("/BEGIN"); w(f"AXI_{tag}"); w("      2022         0")
    w("                  kg                   m                   s")
    w("                  kg                   m                   s")
    w("/TITLE"); w(f"INC-188 round hole quasi-axisymmetric sector {dtheta_deg} deg, h={h*1e6:.1f} um, gap={GAP*1e6:.3f} um, {fail}")
    w("/ANALY"); w("#    N2D3D             IPARITH"); w("         0                   1")
    w("/NODE")
    for n, x, y, z in nodes:
        w(f"{i10(n)}{f20(x)}{f20(y)}{f20(z)}")
    eid = 0
    for part, br in ((2, blank), (4, punch), (1, die), (3, strip)):
        w(f"/BRICK/{part}")
        for b in br:
            eid += 1
            w(i10(eid) + "".join(i10(v) for v in b))
    w("/MAT/LAW1/1"); w("S185_Steel"); w("#              RHO_I"); w(f20(STEEL[0]))
    w("#                  E                  NU"); w(f20(STEEL[1]) + f20(STEEL[2]))
    w("/MAT/LAW2/2"); w("MR536_H34_AA5052_measured"); w("#              RHO_I"); w("           2700.0")
    w("#                  E                  NU"); w("          6.9E+10               0.33")
    w("#                  a                   b                   n           EPS_p_max               Xmax")
    w("       1.9640E+08        5.2473E+08              0.7183              10.0                 0")
    for _ in range(3):
        w("                 0.0                 0.0                 0.0                 0.0                 0.0")
    if fail == "gene1":
        w("/FAIL/GENE1/2")
        w("#               Pmin                Pmax           SigP1_max            Time_max               dtmin")
        w("                 0.0                 0.0                 0.0                 0.0                 0.0")
        w("# fct_IDsm                    Eps_dot_sm             Sig_max                Sigr                   K")
        w("         0                         0.0                 0.0                 0.0                 0.0")
        w("# fct_IDps                    Eps_dot_ps             Eps_max             Eps_eff             Eps_vol")
        w("         0                   0                   0                 100                   0")
        w("#            Eps_min               Eps_s fct_IDg12 fct_IDg13 fct_IDe1c")
        w("                   0" + f20(eps_s) + "         0         0         0")
        w("#tab_IDfld      Itab         Eps_dot_fld     Nstep   Ismooth   Istrain                      Thinning")
        w("         0         0                   0        10         0         0                   0")
        w("#            Volfrac          Pthickfail       NCS                      Temp_max")
        w("                 0.0                 0.0         1                         0.0")
        w("# fct_IDel                     Fscale_el              El_ref")
        w("         0                         0.0                 0.0")
    else:
        w("/FAIL/COCKCROFT/2"); w(f20(c0) + "                   1"); w("")
    w("/PROP/SOLID/1"); w("Tool_Solid"); w("#    Isolid    Ismstr")
    w("        24         0")
    w("                   0                   0                   0                   0                   0")
    w("                   0                   0                   0                   0                   0")
    w("/PROP/SOLID/2"); w("Blank_Solid"); w("#    Isolid    Ismstr")
    w(i10(isolid) + "         0")
    w("                   0                   0                   0                   0                   0")
    w("                   0                   0                   0                   0                   0")
    for p, name, prop, mat in ((1, "Die", 1, 1), (2, "Blank", 2, 2), (3, "Stripper", 1, 1), (4, "Punch", 1, 1)):
        w(f"/PART/{p}"); w(name); w("#    Prop_ID     Mat_ID"); w(i10(prop) + i10(mat))

    def grnod(gid, name, ids):
        w(f"/GRNOD/NODE/{gid}"); w(name)
        for i in range(0, len(ids), 10):
            w("".join(i10(v) for v in ids[i:i + 10]))

    grnod(100, "Punch_Nodes", punch_n)
    grnod(300, "Die_Nodes", die_n)
    grnod(400, "Stripper_Nodes", strip_n)
    grnod(500, "Sym_theta0", sym0)
    grnod(501, "Sym_theta1", sym1)
    if inner_bc:
        grnod(502, "Inner_theta0", sorted(inner0))
        grnod(503, "Inner_theta1", sorted(inner1))
    w("/SKEW/FIX/1"); w("theta1_plane")
    w("#                 OX                  OY                  OZ"); w(f20(0) + f20(0) + f20(0))
    w("#                 X1                  Y1                  Z1"); w(f20(c) + f20(s) + f20(0))
    w("#                 X2                  Y2                  Z2"); w(f20(-s) + f20(c) + f20(0))
    # symmetry: no motion normal to the cut planes (theta=0: global Y; theta=dtheta: local Y of skew 1)
    w("/BCS/1"); w("sym_theta0"); w("#  Tra rot   skew_ID  grnd_ID"); w("   010 000         0       500")
    w("/BCS/2"); w("sym_theta1"); w("#  Tra rot   skew_ID  grnd_ID"); w("   010 000         1       501")
    if inner_bc:
      w("/BCS/5"); w("inner_theta0"); w("#  Tra rot   skew_ID  grnd_ID"); w("   110 000         0       502")
      w("/BCS/6"); w("inner_theta1"); w("#  Tra rot   skew_ID  grnd_ID"); w("   110 000         1       503")
    w("/BCS/3"); w("die_fixed"); w("#  Tra rot   skew_ID  grnd_ID"); w("   111 000         0       300")
    if stripper == "fixed":
        w("/BCS/4"); w("stripper_fixed"); w("#  Tra rot   skew_ID  grnd_ID"); w("   111 000         0       400")
    for sid_, ids in ((100, 1), (200, 2), (300, 3), (400, 4)):
        w(f"/SURF/PART/EXT/{sid_}/0"); w(f"Surf_Part_{ids}"); w(i10(ids))
    w("/SURF/PART/ALL/201/0"); w("Surf_Part_2_all_faces"); w(i10(2))
    tend = (2 * GAP + STROKE) / V
    w("/FUNCT/1"); w("Punch_Vz"); w("#                  X                   Y")
    w(f20(0) + f20(-V)); w(f20(1.0) + f20(-V))
    w("/IMPVEL/1"); w("Punch_Z")
    w("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
    w("         1         Z         0         0       100         0         0")
    w("#             Ascale_x            Fscale_y              Tstart               Tstop")
    w("                   1                   1                   0               1E+30")
    w("/FUNCT/3"); w("Zero"); w("#                  X                   Y"); w(f20(0) + f20(0)); w(f20(1.0) + f20(0))
    for k, d in enumerate(("X", "Y")):
        w(f"/IMPVEL/{2 + k}"); w(f"Punch_{d}")
        w("#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe")
        w(f"         3         {d}         0         0       100         0         0")
        w("#             Ascale_x            Fscale_y              Tstart               Tstop")
        w("                   1                   1                   0               1E+30")
    gap_max = gapmax if gapmax else min(15e-6, 0.8 * h + 2e-6)
    for i, (s1, s2, idel, name) in enumerate(((100, 200, 2, "Die_Blank_Contact"),
                                              (300, 200, 2, "Stripper_Blank_Contact"),
                                              (400, 201, 1, "Punch_Blank_Contact")), start=1):
        w(f"/INTER/TYPE25/{i}/0"); w(name)
        w("#  surf_ID1  surf_ID2      Istf      Igap   Irem_i2      Idel     Iedge")
        w(f"{i10(s1)}{i10(s2)}         4                   3         2          {i10(idel)}         0          ")
        w("#  grnd_IDs             Gap_scale           %mesh_size              Gap_max_s              Gap_max_m")
        w(f"         0                             1{f20(pmesh)}{f20(gap_max)}{f20(gap_max)}")
        w("#                 Stmin                 Stmax     Igap0    Ishape               Edge_angle")
        w("                   0               1e+30         0         2                 135                    ")
        w("#                 Stfac                  Fric               Tstart                 Tstop")
        w(f20(stfac) + "                 0.1                                       0               1e+30")
        w("#      I_BC     IVIS2    Inacti                  VISs")
        w("         0                   0         5                0.05                                        ")
        w("#     Ifric    Ifiltr                 Xfreq   sens_ID   fric_ID")
        w("         0         0                   0                   0                             0                    ")
    # time history: contact forces (punch force = cutting force) and punch node displacement
    w("/TH/INTER/1"); w("contact_forces"); w("#     var1      var2"); w("DEF")
    w("         1         2         3")
    w("/TH/NODE/2"); w("punch_node"); w("#     var1"); w("DEF"); w(f"{i10(punch_n[0])}")
    w("/END")
    os.makedirs(out, exist_ok=True)
    root = os.path.join(out, f"AXI_{tag}")
    with open(root + "_0000.rad", "w", newline="\n") as f:
        f.write("\n".join(lines) + "\n")
    ts = tstop if tstop else tend
    eng = [f"/RUN/AXI_{tag}/1", f20(ts), "/DT/NODA/0", "                 0.9                   0",
           "/DT/BRICK/DEL", "                 0.9               1E-12", "/RFILE", "     20000",
           "/TFILE/4", "               2E-07", "/ANIM/DT", f20(0) + f20(ts / 60),
           "/ANIM/ELEM/EPSP", "/ANIM/ELEM/VONM", "/ANIM/BRICK/TENS/STRESS", "/ANIM/VECT/DISP", "/END"]
    with open(root + "_0001.rad", "w", newline="\n") as f:
        f.write("\n".join(eng) + "\n")
    print(f"AXI_{tag}: h={h*1e6:.1f}um nodes={len(nodes)} bricks={eid} (blank {len(blank)}) "
          f"blank r-nodes={len(rb)} z-layers={nz} tstop={ts:.3e}s")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("h_um", type=float)
    ap.add_argument("--fail", default="gene1", choices=["gene1", "cockcroft"])
    ap.add_argument("--c0", type=float, default=19.1e6)
    ap.add_argument("--eps-s", type=float, default=0.5)
    ap.add_argument("--stripper", default="fixed", choices=["fixed", "free"])
    ap.add_argument("--dtheta", type=float, default=5.0)
    ap.add_argument("--tstop", type=float, default=None)
    ap.add_argument("--isolid", type=int, default=24)
    ap.add_argument("--stfac", type=float, default=1.0)
    ap.add_argument("--pmesh", type=float, default=0.4)
    ap.add_argument("--gapmax", type=float, default=None)
    ap.add_argument("--tool-dth", type=float, default=None)
    ap.add_argument("--inner", action="store_true")
    ap.add_argument("--gap0", type=float, default=None)
    ap.add_argument("--out", default="D:/Clawdbot_Docker_20260125/clawstack_v2/data/work")
    a = ap.parse_args()
    build(a.tag, a.h_um * 1e-6, a.fail, a.c0, a.eps_s, a.stripper, a.dtheta, a.out, a.tstop, a.isolid, a.stfac, a.pmesh, a.gapmax, a.tool_dth, a.inner, a.gap0)
