# -*- coding: utf-8 -*-
"""PANEL4MM_P2 の全41フレームを上面図+断面図の動画にする。"""
import sys, os, subprocess, re
import numpy as np
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

WORK = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\work"
OUT = r"D:\Temp\claude\d--Clawdbot-Docker-20260125\e5a77d2e-7c2f-4183-9a32-b59e0d3ab3bf\scratchpad\frames"
CT = "clawstack-unified-openradioss-1"
XC = 185.657          # 丸パンチ軸
TSTOP = 6.0e-4
os.makedirs(OUT, exist_ok=True)


def to_vtk(name):
    subprocess.run(["docker", "exec", CT, "bash", "-c",
                    f"cd /work && /opt/openradioss/OpenRadioss/exec/anim_to_vtk_linux64_gf {name} > {name}.vtk 2>/dev/null"],
                   check=True)


def rm_vtk(name):
    subprocess.run(["docker", "exec", CT, "bash", "-c", f"rm -f /work/{name}.vtk"], check=False)


def parse(path, want_cells):
    """POINTS と CELLS(初回のみ) と CELL_DATA の PART_ID / EROSION_STATUS を読む。"""
    pts = cells = pid = ero = None
    mode = None
    with open(path, "r", errors="replace") as f:
        while True:
            l = f.readline()
            if not l:
                break
            t = l.split()
            if not t:
                continue
            if t[0] == "POINTS":
                n = int(t[1]); v = []
                while len(v) < 3 * n:
                    v += f.readline().split()
                pts = np.array(v[:3 * n], dtype=np.float32).reshape(n, 3)
            elif t[0] == "CELLS":
                nc = int(t[1]); tot = int(t[2]); v = []
                while len(v) < tot:
                    v += f.readline().split()
                if want_cells:
                    cells = np.array(v[:tot], dtype=np.int32).reshape(nc, 5)[:, 1:]
            elif t[0] == "CELL_DATA":
                mode = "c"
            elif t[0] == "POINT_DATA":
                mode = "p"
            elif t[0] == "SCALARS":
                nm = t[1]; f.readline()
                n = nc if mode == "c" else len(pts); v = []
                while len(v) < n:
                    v += f.readline().split()
                if mode == "c" and nm == "PART_ID":
                    pid = np.array(v[:n], dtype=np.int16)
                elif mode == "c" and nm == "EROSION_STATUS":
                    ero = np.array(v[:n], dtype=np.int8)
                if ero is not None and (cells is not None or not want_cells) and pid is not None:
                    break
            elif t[0] == "VECTORS":
                n = len(pts); v = []
                while len(v) < 3 * n:
                    v += f.readline().split()
    return pts, cells, pid, ero


COL = {1: ("#4477dd", "Die"), 2: ("#999999", "Blank"),
       3: ("#22aa66", "Stripper"), 4: ("#ff9900", "Punch")}
names = sorted([n for n in os.listdir(WORK) if re.fullmatch(r"PANEL4MM_P2A\d+", n)])
print(f"frames={len(names)}")
cells = pid = None
for k, nm in enumerate(names):
    to_vtk(nm)
    p, c, q, e = parse(os.path.join(WORK, nm + ".vtk"), cells is None)
    rm_vtk(nm)
    if c is not None:
        cells = c
    if q is not None:
        pid = q
    p = p * 1e3
    cen = p[cells].mean(axis=1)
    t = TSTOP * k / (len(names) - 1)
    blank = pid == 2
    fig, ax = plt.subplots(1, 2, figsize=(15, 7))
    # 上面図
    a = ax[0]
    liv = blank & (e == 1) & (cen[:, 2] > -0.5)
    ded = blank & (e == 0)
    sub = np.where(liv)[0][::3]
    a.scatter(cen[sub, 0], cen[sub, 1], s=0.5, c="#d5d5d5", lw=0)
    if ded.any():
        a.scatter(cen[ded][:, 0], cen[ded][:, 1], s=1.5, c="#d62728", lw=0,
                  label=f"ruptured {int(ded.sum()):,}")
        a.legend(fontsize=9, loc="upper right")
    a.set_xlim(176, 193); a.set_ylim(-1891, -1874)
    a.set_aspect("equal"); a.set_title("TOP VIEW  (red = ruptured)", fontsize=12)
    a.set_xlabel("X [mm]"); a.set_ylabel("Y [mm]")
    # 断面図
    b = ax[1]
    band = np.abs(cen[:, 0] - XC) < 0.35
    for pp, (cc, nn) in COL.items():
        m = band & (pid == pp) & (e == 1)
        if m.any():
            b.scatter(cen[m][:, 1], cen[m][:, 2], s=3.5, c=cc, lw=0, label=nn)
    m = band & blank & (e == 0)
    if m.any():
        b.scatter(cen[m][:, 1], cen[m][:, 2], s=5, c="#d62728", lw=0, label="ruptured")
    b.set_xlim(-1890.5, -1874.5); b.set_ylim(-3.6, 4.2)
    b.set_aspect("equal"); b.legend(fontsize=9, loc="upper right", ncol=2)
    b.set_title(f"SECTION X={XC:.2f}mm", fontsize=12)
    b.set_xlabel("Y [mm]"); b.set_ylabel("Z [mm]")
    b.axhline(0.5, color="k", lw=.5, ls=":"); b.axhline(1.005, color="k", lw=.5, ls=":")
    fig.suptitle(f"Panel 4mm ASSY - 4 punches, 3mm stroke   t = {t*1e3:.3f} ms   "
                 f"(frame {k+1}/{len(names)})", fontsize=13)
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(os.path.join(OUT, f"f{k:03d}.png"), dpi=95)
    plt.close(fig)
    print(f"  {nm} t={t*1e3:.3f}ms ruptured={int(ded.sum()):,}", flush=True)
print("frames done")
