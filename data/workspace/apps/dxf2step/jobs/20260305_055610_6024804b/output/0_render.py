import FreeCAD as App
import Part
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec

shape = Part.read('/home/node/clawd/apps/dxf2step/jobs/20260305_055610_6024804b/output/0.step')
bb = shape.BoundBox
cx = (bb.XMax + bb.XMin) / 2
cy = (bb.YMax + bb.YMin) / 2
cz = (bb.ZMax + bb.ZMin) / 2

segments = []
for edge in shape.Edges:
    try:
        pts = edge.discretize(50)
        if pts:
            segments.append([(p.x - cx, p.y - cy, p.z - cz) for p in pts])
    except Exception:
        pass

def draw_view(ax, segs_2d, title, flip_y=False):
    for seg in segs_2d:
        if len(seg) >= 2:
            xs = [p[0] for p in seg]
            ys = [p[1] for p in seg]
            ax.plot(xs, ys, 'k-', linewidth=0.8, solid_capstyle='round')
    ax.set_aspect('equal', adjustable='datalim')
    ax.margins(0.12)
    # Ensure minimum visible height (for thin extruded plates)
    ax.autoscale()
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    xspan = max(xlim[1] - xlim[0], 1e-6)
    yspan = ylim[1] - ylim[0]
    if yspan < xspan * 0.08:
        mid_y = (ylim[0] + ylim[1]) / 2
        ax.set_ylim(mid_y - xspan * 0.12, mid_y + xspan * 0.12)
    ax.set_title(title, fontsize=9, pad=5)
    ax.set_facecolor('#F5F5F5')
    ax.tick_params(left=False, bottom=False, labelleft=False, labelbottom=False)
    for spine in ax.spines.values():
        spine.set_color('#AAAAAA')
        spine.set_linewidth(0.5)
    if flip_y:
        ax.invert_yaxis()

# Third-angle projection: Top=XY(flip Y), Front=XZ, Right=YZ
top_segs   = [[(p[0],  p[1]) for p in s] for s in segments]
front_segs = [[(p[0],  p[2]) for p in s] for s in segments]
right_segs = [[(p[1],  p[2]) for p in s] for s in segments]

fig = plt.figure(figsize=(14, 10), facecolor='white')
gs = gridspec.GridSpec(2, 2, figure=fig, hspace=0.4, wspace=0.3)

ax_top   = fig.add_subplot(gs[0, 0])
ax_sym   = fig.add_subplot(gs[0, 1])
ax_front = fig.add_subplot(gs[1, 0])
ax_right = fig.add_subplot(gs[1, 1])

draw_view(ax_top,   top_segs,   'Top View  (Hira-Men)', flip_y=True)
draw_view(ax_front, front_segs, 'Front View  (Sho-Men)')
draw_view(ax_right, right_segs, 'Right Side View  (Migi-Sokumen)')

ax_sym.axis('off')
ax_sym.set_facecolor('#FAFAFA')
ax_sym.text(0.5, 0.62, 'Third Angle Projection',
            ha='center', va='center', transform=ax_sym.transAxes,
            fontsize=12, fontweight='bold', color='#333333')
ax_sym.text(0.5, 0.45, 'Daisan-kakuho', ha='center', va='center',
            transform=ax_sym.transAxes, fontsize=10, color='#555555')
ax_sym.text(0.5, 0.28, 'ISO E  /  ANSI  /  JIS', ha='center', va='center',
            transform=ax_sym.transAxes, fontsize=8, color='#888888')

fig.suptitle('0  —  STEP Views', fontsize=13, fontweight='bold', y=1.01)
plt.savefig('/home/node/clawd/apps/dxf2step/jobs/20260305_055610_6024804b/output/0_views.png', dpi=150, bbox_inches='tight', facecolor='white')
plt.close()
print('PNG saved: /home/node/clawd/apps/dxf2step/jobs/20260305_055610_6024804b/output/0_views.png')
