"""INC-188: plot the theta=0 face of a sector run (deformed mesh, plastic strain, eroded elements).
usage: python axi_plot.py DIR TAG FRAME[,FRAME...] OUT.png [rmin_um rmax_um zmin_um zmax_um]"""
import sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.collections import PolyCollection
from axi_analyze import read_vtk

d, tag, frames, out = sys.argv[1], sys.argv[2], sys.argv[3].split(","), sys.argv[4]
win = [float(v) for v in sys.argv[5:9]] if len(sys.argv) >= 9 else [0.2, 0.4, -0.15, 0.56]
fig, axs = plt.subplots(1, len(frames), figsize=(5 * len(frames), 6), squeeze=False)
for ax, fr in zip(axs[0], frames):
    t, pts, cells, data = read_vtk(f"{d}/vtk_{tag}/f{int(fr):03d}.vtk")
    part = [int(v) for v in data["PART_ID"]]
    ero = [int(v) for v in data["EROSION_STATUS"]]
    ep = [float(v) for v in data.get("3DELEM_Plastic_Strain", ["0"] * len(cells))]
    polys, cols, ec = [], [], []
    for k, c in enumerate(cells):
        q = [pts[n] for n in c[:4]]           # theta=0 face (first 4 nodes)
        polys.append([(p[0] * 1e3, p[2] * 1e3) for p in q])
        cols.append(ep[k] if part[k] == 2 else -1)
        ec.append(ero[k])
    pc = PolyCollection([p for p, e in zip(polys, ec) if e == 1], array=[c for c, e in zip(cols, ec) if e == 1],
                        cmap="jet", clim=(0, 2), edgecolors="k", linewidths=0.1)
    pc.cmap.set_under("lightgray")
    ax.add_collection(pc)
    ax.add_collection(PolyCollection([p for p, e in zip(polys, ec) if e == 0], facecolors="none",
                                     edgecolors="r", linewidths=0.3))
    ax.set_xlim(win[0], win[1]); ax.set_ylim(win[2], win[3]); ax.set_aspect("equal")
    ax.set_title(f"{tag} f{fr} t={t*1e6:.1f}us stroke={(5*t-5e-6)*1e6:.0f}um")
    ax.set_xlabel("r [mm]"); ax.set_ylabel("z [mm]")
fig.colorbar(pc, ax=axs[0].tolist(), label="plastic strain (gray=tool, red=eroded)")
fig.savefig(out, dpi=130)
print(out)
