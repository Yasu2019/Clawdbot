"""INC-188: tiny tetra block in simple shear to read back the element length that /FAIL/GENE1 uses for
its element-size factor (fct_IDel / El_ref) - 2026-10-08.

A block of side B is cut into cubes of edge a, each split into 6 tets (same Kuhn split as a
structured tet mesh). Bottom face fixed, top face moved in +x (simple shear), all with the PANEL4MM
blank material and solid property. GENE1 with Eps_s = EPS and fct_IDel = f(x) = x, El_ref = 1 um, so
the effective threshold is EPS * L_el[um]: the shear strain at the first deletion gives L_el.

usage: python make_tet_shear_block.py TAG a_um [--eps 0.01] [--elreg-lin] [--out DIR]
"""
import argparse
import os

B = 0.2e-3
V = 5.0


def f20(v):
    return f"{float(v):>20.7G}"


def i10(v):
    return f"{int(v):>10d}"


def build(tag, a, eps, lin, out, fx=None):
    n = max(1, round(B / a))
    h = B / n
    nid = {}
    nodes = []
    for k in range(n + 1):
        for j in range(n + 1):
            for i in range(n + 1):
                nid[(i, j, k)] = len(nodes) + 1
                nodes.append((i * h, j * h, k * h))
    tets = []
    for k in range(n):
        for j in range(n):
            for i in range(n):
                c = [nid[(i + di, j + dj, k + dk)] for dk in (0, 1) for dj in (0, 1) for di in (0, 1)]
                # cube corners c0..c7 (x fastest); Kuhn split along the 0-7 diagonal
                for p in ((0, 1, 3, 7), (0, 3, 2, 7), (0, 2, 6, 7), (0, 6, 4, 7), (0, 4, 5, 7), (0, 5, 1, 7)):
                    tets.append([c[q] for q in p])
    L = ["#RADIOSS STARTER", "/BEGIN", f"TET_{tag}", "      2022         0",
         "                  kg                   m                   s",
         "                  kg                   m                   s",
         "/TITLE", f"tet shear block a={a*1e6:.0f} um", "/NODE"]
    L += [f"{i10(i + 1)}{f20(x)}{f20(y)}{f20(z)}" for i, (x, y, z) in enumerate(nodes)]
    L.append("/TETRA4/1")
    import numpy as np
    P = np.array(nodes)
    for e, t in enumerate(tets):
        x = P[[q - 1 for q in t]]
        vol = np.dot(np.cross(x[1] - x[0], x[2] - x[0]), x[3] - x[0])
        if vol < 0:
            t = [t[0], t[2], t[1], t[3]]
        L.append(i10(e + 1) + "".join(i10(q) for q in t))
    L += ["/MAT/LAW2/1", "MR536", "#              RHO_I", "           2700.0", "#                  E                  NU",
          "          6.9E+10               0.33",
          "#                  a                   b                   n           EPS_p_max               Xmax",
          "       1.9640E+08        5.2473E+08              0.7183              10.0                 0"]
    L += ["                 0.0                 0.0                 0.0                 0.0                 0.0"] * 3
    L += ["/FAIL/GENE1/1",
          "                 0.0                 0.0                 0.0                 0.0                 0.0",
          "         0                         0.0                 0.0                 0.0                 0.0",
          "         0                   0                   0                 100                   0",
          "                   0" + f20(eps) + "         0         0         0",
          "         0         0                   0        10         0         0                   0",
          "                 0.0                 0.0         1                         0.0",
          ("         9          " + f20(1.0) + f20(1e-6)) if (lin or fx) else "         0                         0.0                 0.0"]
    L += ["/PROP/SOLID/1", "Blank_Solid", "#    Isolid    Ismstr", "         4"]
    L += ["/PART/1", "Block", "#    Prop_ID     Mat_ID", i10(1) + i10(1)]
    bot = [nid[(i, j, 0)] for j in range(n + 1) for i in range(n + 1)]
    top = [nid[(i, j, n)] for j in range(n + 1) for i in range(n + 1)]
    for gid, name, ids in ((1, "bottom", bot), (2, "top", top)):
        L += [f"/GRNOD/NODE/{gid}", name] + ["".join(i10(v) for v in ids[i:i + 10]) for i in range(0, len(ids), 10)]
    L += ["/BCS/1", "fix_bottom", "#  Tra rot   skew_ID  grnd_ID", "   111 000         0         1",
          "/BCS/2", "top_yz", "#  Tra rot   skew_ID  grnd_ID", "   011 000         0         2"]
    if fx:
        L += ["/FUNCT/9", "size_factor", "#                  X                   Y"] + [f20(x) + f20(y) for x, y in fx]
    elif lin:
        L += ["/FUNCT/9", "size_factor_equals_x", "#                  X                   Y", f20(0) + f20(0), f20(1000) + f20(1000)]
    L += ["/FUNCT/1", "vx", "#                  X                   Y", f20(0) + f20(V), f20(1) + f20(V),
          "/IMPVEL/1", "top_x", "#   Funct_ID    Dir   Skew_ID   Sens_ID   Gnod_ID     Icoor    Iframe",
          "         1         X         0         0         2         0         0",
          "#             Ascale_x            Fscale_y              Tstart               Tstop",
          "                   1                   1                   0               1E+30", "/END"]
    os.makedirs(out, exist_ok=True)
    open(os.path.join(out, f"TET_{tag}_0000.rad"), "w", newline="\n").write("\n".join(L) + "\n")
    tstop = 1.5 * B / V          # top displacement 1.5 B -> engineering shear strain 1.5
    open(os.path.join(out, f"TET_{tag}_0001.rad"), "w", newline="\n").write("\n".join(
        [f"/RUN/TET_{tag}/1", f20(tstop), "/DT/NODA/0", "                 0.9                   0", "/TFILE/4", f20(tstop / 300), "/END"]) + "\n")
    print(f"TET_{tag}: a={a*1e6:.0f} um, {len(tets)} tets, tstop {tstop:.2e}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("tag"); ap.add_argument("a_um", type=float)
    ap.add_argument("--eps", type=float, default=0.01)
    ap.add_argument("--elreg-lin", action="store_true")
    ap.add_argument("--fx", default=None, help="x:y,... factor vs L_el/1um")
    ap.add_argument("--out", default="D:/Temp/axi")
    a = ap.parse_args()
    build(a.tag, a.a_um * 1e-6, a.eps, a.elreg_lin, a.out, None if not a.fx else [tuple(map(float, q.split(":"))) for q in a.fx.split(",")])
