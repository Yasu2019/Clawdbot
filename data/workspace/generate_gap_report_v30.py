
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os, base64, json, math

# --- Configuration ---
if os.path.exists("/home/node/clawd"):
    WORKSPACE_DIR = "/home/node/clawd"
else:
    WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"

REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html")
THREE_JS_PATH = os.path.join(REPORT_DIR, "three.min.js")
os.makedirs(REPORT_DIR, exist_ok=True)

# Japanese font setup
for f in ['MS Gothic', 'Yu Gothic', 'Meiryo', 'IPAGothic', 'DejaVu Sans']:
    try:
        matplotlib.font_manager.findfont(f, fallback_to_default=False)
        plt.rcParams['font.family'] = f
        print(f"Font: {f}")
        break
    except:
        continue

# ======================================================================
# 1. PARAMETERS
# ======================================================================
PUNCH_TIP_W = 2.00; HOLE_W = 5.00    # DXF: clearance 1.5mm each side
PUNCH_TIP_H = 1.10; HOLE_H = 2.10    # DXF: clearance 0.6mm + 0.4mm (asymmetric)
TOL_PUNCH = 0.005; TOL_HOLE = 0.1
TOL_TOOL_POS = 0.020; TOL_FEED = 0.011
TOL_PITCH = 0.01152; TOL_GUIDE_PLAY = 0.1  # DXF: 0.1mm clearance, JIS B 0405 medium
N = 100000

# Frame bending parameters
FRAME_T = 0.2          # mm
FRAME_STRIP_W = 13.15  # mm
E_NI201 = 207e3        # MPa
SY_NI201 = 103         # MPa
SUTS_NI201 = 403        # MPa
F_PUSH = 1.2           # N

# ======================================================================
# 2. SIMULATION
# ======================================================================
def run_simulation():
    s_hole_x = np.random.normal(HOLE_W, TOL_HOLE/3, N)
    s_tip_x  = np.random.normal(PUNCH_TIP_W, TOL_PUNCH/3, N)
    s_hole_y = np.random.normal(HOLE_H, TOL_HOLE/3, N)
    s_tip_y  = np.random.normal(PUNCH_TIP_H, TOL_PUNCH/3, N)
    s_tool_x = np.random.normal(0, TOL_TOOL_POS/3, N)
    s_feed_x = np.random.normal(0, TOL_FEED/3, N)
    s_pitch_x = np.random.normal(0, TOL_PITCH/3, N)
    s_tool_y = np.random.normal(0, TOL_TOOL_POS/3, N)
    s_guide_y = np.random.normal(0, TOL_GUIDE_PLAY/3, N)
    gap_x = (s_hole_x - s_tip_x)/2 - np.abs(s_tool_x + s_feed_x + s_pitch_x)
    gap_y = (s_hole_y - s_tip_y)/2 - np.abs(s_tool_y + s_guide_y)
    return gap_x, gap_y

gap_x, gap_y = run_simulation()

# ======================================================================
# 3. STATISTICS
# ======================================================================
def get_stats(data, nominal):
    m, s = np.mean(data), np.std(data)
    cpk = m / (3*s) if s > 0 else 0
    fr = np.sum(data < 0) / N * 100
    zs = m/s if s > 0 else 0
    return {'mean': m, 'std': s, 'cpk': cpk, 'fail_rate': fr,
            'z_sigma': zs, 'dpmo': int(fr*10000),
            'safety_margin_pct': m/nominal*100 if nominal > 0 else 0,
            'min': np.min(data), 'max': np.max(data),
            'p01': np.percentile(data, 0.1), 'p999': np.percentile(data, 99.9),
            'nominal': nominal}

def worst_case(h_nom, h_tol, p_nom, p_tol, pos_tols):
    mh = h_nom - h_tol; mp = p_nom + p_tol; wp = sum(pos_tols)
    return {'nominal': (h_nom-p_nom)/2, 'worst_case': (mh-mp)/2-wp,
            'min_hole': mh, 'max_punch': mp, 'worst_pos': wp}

nom_x = (HOLE_W - PUNCH_TIP_W)/2; nom_y = (HOLE_H - PUNCH_TIP_H)/2
stats_x = get_stats(gap_x, nom_x); stats_y = get_stats(gap_y, nom_y)
wc_x = worst_case(HOLE_W, TOL_HOLE, PUNCH_TIP_W, TOL_PUNCH, [TOL_TOOL_POS, TOL_FEED, TOL_PITCH])
wc_y = worst_case(HOLE_H, TOL_HOLE, PUNCH_TIP_H, TOL_PUNCH, [TOL_TOOL_POS, TOL_GUIDE_PLAY])

# ======================================================================
# 4. FRAME BENDING ANALYSIS
# ======================================================================
bridge_y = (FRAME_STRIP_W - HOLE_H) / 2
beam_b = 2 * bridge_y
beam_L = HOLE_W  # span = hole width
beam_I = beam_b * FRAME_T**3 / 12
beam_delta = F_PUSH * beam_L**3 / (48 * E_NI201 * beam_I)
beam_M = F_PUSH * beam_L / 4
beam_sigma = beam_M * (FRAME_T/2) / beam_I
beam_F_yield = SY_NI201 * beam_I * 4 / (beam_L * FRAME_T/2)
beam_F_uts = SUTS_NI201 * beam_I * 4 / (beam_L * FRAME_T/2)
beam_k = 48 * E_NI201 * beam_I / beam_L**3

print(f"Frame bending: delta={beam_delta*1000:.1f}um, sigma={beam_sigma:.1f}MPa, F_yield={beam_F_yield:.1f}N")

# ======================================================================
# 5. CHARTS (Japanese)
# ======================================================================
def create_hist(data, filename, title, st):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(data, bins=60, color='#3498db', alpha=0.6, edgecolor='#2980b9', linewidth=0.5)
    ax.axvline(0, color='#e74c3c', ls='--', lw=2.5, label='Gap=0 (Interference)')
    ax.axvline(st['mean'], color='#27ae60', ls='-', lw=2, label=f'Mean={st["mean"]:.4f}mm')
    xl = ax.get_xlim()
    ax.axvspan(xl[0], 0, alpha=0.1, color='red', label=f'Interference ({st["fail_rate"]:.2f}%)')
    ax.set_xlabel('Gap (mm)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename), dpi=150)
    plt.close()

create_hist(gap_x, "hist_x.png", f"X Gap (Cpk={stats_x['cpk']:.2f})", stats_x)
create_hist(gap_y, "hist_y.png", f"Y Gap (Cpk={stats_y['cpk']:.2f})", stats_y)

def create_tornado(filename, factors, title):
    variances = [(n, (t/3)**2) for n, t in factors]
    tv = sum(v for _, v in variances)
    contribs = sorted([(n, v/tv*100) for n, v in variances], key=lambda x: x[1])
    fig, ax = plt.subplots(figsize=(10, max(4, len(contribs)*0.8)))
    names = [c[0] for c in contribs]; vals = [c[1] for c in contribs]
    colors = ['#e74c3c' if v > 30 else '#f39c12' if v > 10 else '#3498db' for v in vals]
    bars = ax.barh(names, vals, color=colors, edgecolor='#333', height=0.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_width()+1, b.get_y()+b.get_height()/2, f'{v:.1f}%', va='center', fontsize=11, fontweight='bold')
    ax.set_xlabel('Contribution (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlim(0, max(vals)*1.3)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename), dpi=150)
    plt.close()
    return contribs

cx = create_tornado("tornado_x.png",
    [("Hole W (+-0.1)", TOL_HOLE), ("Punch W (+-0.005)", TOL_PUNCH),
     ("Tool Pos (+-0.020)", TOL_TOOL_POS), ("Feed (+-0.011)", TOL_FEED),
     ("Pitch (+-0.012)", TOL_PITCH)], "X-Axis Contribution")

cy = create_tornado("tornado_y.png",
    [("Hole H (+-0.1)", TOL_HOLE), ("Punch H (+-0.005)", TOL_PUNCH),
     ("Tool Pos (+-0.020)", TOL_TOOL_POS), ("Guide Play (+-0.075)", TOL_GUIDE_PLAY)],
    "Y-Axis Contribution")

# Frame bending chart
def create_bending_chart():
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
    # Left: Force comparison
    forces = [F_PUSH, beam_F_yield, beam_F_uts]
    labels = ['Push Force\n1.2N', 'Yield Force\n{:.1f}N'.format(beam_F_yield), 'Fracture Force\n{:.1f}N'.format(beam_F_uts)]
    colors = ['#3498db', '#f39c12', '#e74c3c']
    ax1.bar(labels, forces, color=colors, edgecolor='#333', width=0.5)
    ax1.set_ylabel('Force (N)', fontsize=12)
    ax1.set_title('Force Comparison', fontsize=14, fontweight='bold')
    ax1.axhline(F_PUSH, color='#3498db', ls='--', alpha=0.5)
    # Right: Deflection
    spans = np.linspace(3, 10, 50)
    deltas = [F_PUSH * L**3 / (48*E_NI201*beam_I) * 1000 for L in spans]
    ax2.plot(spans, deltas, 'b-', lw=2, label='1.2N Deflection')
    ax2.axhline(200, color='#e74c3c', ls='--', lw=1.5, label='Step Height 0.2mm')
    ax2.axvline(beam_L, color='#27ae60', ls=':', lw=1.5, label=f'Actual Span {beam_L}mm')
    ax2.set_xlabel('Span (mm)', fontsize=12)
    ax2.set_ylabel('Deflection (um)', fontsize=12)
    ax2.set_title('Frame Deflection vs Span', fontsize=14, fontweight='bold')
    ax2.legend(fontsize=10)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, "bending_chart.png"), dpi=150)
    plt.close()

create_bending_chart()

# 2D Schematic - Corrected Rectangular Geometry
def generate_schematic():
    fig, ax = plt.subplots(figsize=(12, 8))
    
    # Dimensions
    hole_w = HOLE_W  # 5.00mm
    hole_h = HOLE_H  # 2.10mm
    tip_w = PUNCH_TIP_W  # 2.00mm
    tip_h = PUNCH_TIP_H  # 1.10mm
    
    # Y Position: Shift down by 0.1mm to get 0.6mm top gap, 0.4mm bottom gap
    # Calculation: (2.1 - 1.1)/2 = 0.5 nom. 0.5 - (-0.1) = 0.6 top. 0.5 + (-0.1) = 0.4 bottom.
    tip_cy = -0.1
    
    # === Frame Hole (Solid Line) ===
    # User said: "White solid line is Frame outer edge"
    # Drawn as cyan filled rect with dark cyan outline
    ax.add_patch(patches.Rectangle((-hole_w/2, -hole_h/2), hole_w, hole_h,
        lw=3, edgecolor='#00695c', facecolor='#e0f7fa', alpha=0.3,
        zorder=1, label=f'Frame Hole ({hole_w:.2f} x {hole_h:.2f} mm)'))
    
    # === Punch Tip (Dotted/Dashed Line) ===
    # User said: "White dotted line is Punch Tip outer edge"
    # Drawn as orange filled rect with Dashed outline
    ax.add_patch(patches.Rectangle((-tip_w/2, tip_cy - tip_h/2), tip_w, tip_h,
        lw=2.5, edgecolor='#e65100', facecolor='#ffe0b2', alpha=0.9,
        linestyle='--', zorder=2, label=f'Punch Tip ({tip_w:.2f} x {tip_h:.2f} mm)'))
    
    # Center lines
    ax.axhline(0, color='#999', lw=0.5, ls='-.')
    ax.axvline(0, color='#999', lw=0.5, ls='-.')
    
    # === Dimension Lines ===
    def dim_line(x1, y1, x2, y2, label, color='#1a237e', offset_x=0, offset_y=0, fontsize=10):
        ax.annotate('', xy=(x1, y1), xytext=(x2, y2),
            arrowprops=dict(arrowstyle='<->', color=color, lw=2.0, mutation_scale=15))
        mx, my = (x1+x2)/2, (y1+y2)/2
        ax.text(mx + offset_x, my + offset_y, label,
            ha='center', va='center', color=color, fontweight='bold', fontsize=fontsize,
            bbox=dict(boxstyle='round,pad=0.2', facecolor='white', edgecolor=color, alpha=0.9))
    
    # X Gap (1.5mm) - Left
    dy = hole_h/2 + 0.5
    dim_line(-hole_w/2, dy, -tip_w/2, dy, "1.5 mm", '#1565c0')
    # Ext lines
    ax.plot([-hole_w/2, -hole_w/2], [hole_h/2, dy+0.2], 'b:', lw=1)
    ax.plot([-tip_w/2, -tip_w/2], [tip_cy+tip_h/2, dy+0.2], 'b:', lw=1)
    
    # X Gap (1.5mm) - Right
    dim_line(tip_w/2, dy, hole_w/2, dy, "1.5 mm", '#1565c0')
    ax.plot([hole_w/2, hole_w/2], [hole_h/2, dy+0.2], 'b:', lw=1)
    ax.plot([tip_w/2, tip_w/2], [tip_cy+tip_h/2, dy+0.2], 'b:', lw=1)
    
    # Y Gap Top (0.6mm)
    dx = -hole_w/2 - 0.5
    dim_line(dx, tip_cy + tip_h/2, dx, hole_h/2, "0.6 mm", '#2e7d32')
    ax.plot([-hole_w/2, dx-0.2], [hole_h/2, hole_h/2], 'g:', lw=1)
    ax.plot([-tip_w/2, dx-0.2], [tip_cy+tip_h/2, tip_cy+tip_h/2], 'g:', lw=1)
    
    # Y Gap Bottom (0.4mm) - Note: tip_cy is negative (-0.1), tip bottom is -0.1 - 0.55 = -0.65
    # hole bottom is -1.05. Gap = -0.65 - (-1.05) = 0.4.
    dx2 = hole_w/2 + 0.5
    dim_line(dx2, -hole_h/2, dx2, tip_cy - tip_h/2, "0.4 mm", '#d32f2f')
    ax.plot([hole_w/2, dx2+0.2], [-hole_h/2, -hole_h/2], 'r:', lw=1)
    ax.plot([tip_w/2, dx2+0.2], [tip_cy-tip_h/2, tip_cy-tip_h/2], 'r:', lw=1)
    
    ax.set_xlim(-4.5, 4.5)
    ax.set_ylim(-2.5, 2.5)
    ax.set_aspect('equal')
    ax.axis('off')
    ax.set_title('Punch Tip vs Frame Hole (Top View)', fontsize=14, fontweight='bold', pad=20)
    ax.legend(loc='lower center', ncol=2, fontsize=10, bbox_to_anchor=(0.5, -0.15))
    
    fn = 'schematic_v30.png'
    plt.savefig(os.path.join(REPORT_DIR, fn), bbox_inches='tight', dpi=150, facecolor='white')
    plt.close()
    return fn

schematic_file = generate_schematic()

# Tolerance Stack-Up Diagrams (Min/Max method)
def create_stackup(filename, title, components, total_label, gap_formula_min, gap_formula_max):
    """
    components: list of dict with keys: label, nominal, tol, color, direction
        direction: 'pos' (adds to gap) or 'neg' (subtracts from gap)
    """
    fig, ax = plt.subplots(figsize=(14, 7))
    ax.set_xlim(-1, 18)
    n = len(components)
    y_top = n * 1.8 + 2
    ax.set_ylim(-3, y_top + 1)
    ax.axis('off')
    
    # Title
    ax.text(8.5, y_top, title, ha='center', va='top', fontsize=16, fontweight='bold',
            color='#1a237e')
    ax.plot([0, 17], [y_top - 0.5, y_top - 0.5], color='#1a237e', lw=3)
    
    # Draw each component block
    y = y_top - 2.0
    block_h = 1.2
    for i, comp in enumerate(components):
        nom = comp['nominal']
        tol = comp['tol']
        c = comp.get('color', '#26a69a')
        lbl = comp['label']
        d = comp.get('direction', 'neg')
        mn = nom - tol
        mx = nom + tol
        
        # Component block
        bx = 1.5
        bw = 6.0
        ax.add_patch(patches.FancyBboxPatch((bx, y - block_h/2), bw, block_h,
            boxstyle='round,pad=0.1', facecolor=c, edgecolor='#333', lw=1.5, alpha=0.85))
        
        # Label inside block
        ax.text(bx + bw/2, y, lbl, ha='center', va='center', fontsize=10,
                fontweight='bold', color='white')
        
        # Min/Max dimensions with arrows
        arr_x = bx + bw + 0.5
        ax.annotate('', xy=(arr_x + 3.5, y + 0.15), xytext=(arr_x, y + 0.15),
            arrowprops=dict(arrowstyle='->', color='#d32f2f', lw=1.5))
        ax.annotate('', xy=(arr_x + 3.5, y - 0.15), xytext=(arr_x, y - 0.15),
            arrowprops=dict(arrowstyle='->', color='#1565c0', lw=1.5))
        
        ax.text(arr_x + 4.0, y + 0.25, f'{mx:.3f}', fontsize=11, color='#d32f2f',
                fontweight='bold', va='center')
        ax.text(arr_x + 4.0, y - 0.35, f'{mn:.3f}', fontsize=11, color='#1565c0',
                fontweight='bold', va='center')
        
        # Nominal with tolerance
        ax.text(arr_x + 7.5, y, f'{nom:.3f} \u00b1{tol:.3f}', fontsize=9, color='#555',
                va='center', style='italic')
        
        # Direction indicator
        dir_symbol = '\u2191 +' if d == 'pos' else '\u2193 \u2212'
        dir_color = '#2e7d32' if d == 'pos' else '#c62828'
        ax.text(0.8, y, dir_symbol, ha='center', va='center', fontsize=12,
                color=dir_color, fontweight='bold')
        
        # Connecting arrow down
        if i < n - 1:
            ax.annotate('', xy=(bx + bw/2, y - block_h/2 - 0.1),
                xytext=(bx + bw/2, y - block_h/2 - 0.45),
                arrowprops=dict(arrowstyle='->', color=c, lw=2, mutation_scale=15))
        
        y -= 1.8
    
    # Result section
    y_result = y - 0.5
    ax.plot([0, 17], [y_result + 0.8, y_result + 0.8], color='#333', lw=1, ls='--')
    
    # Min Gap
    ax.text(1, y_result, 'Min Gap =', fontsize=12, fontweight='bold', color='#d32f2f',
            va='center')
    ax.text(5, y_result, gap_formula_min, fontsize=11, color='#d32f2f', va='center',
            family='monospace')
    
    # Max Gap
    ax.text(1, y_result - 0.8, 'Max Gap =', fontsize=12, fontweight='bold', color='#1565c0',
            va='center')
    ax.text(5, y_result - 0.8, gap_formula_max, fontsize=11, color='#1565c0', va='center',
            family='monospace')
    
    # Legend
    ax.text(12, y_result, '\u25cf Max', fontsize=10, color='#d32f2f', fontweight='bold')
    ax.text(12, y_result - 0.5, '\u25cf Min', fontsize=10, color='#1565c0', fontweight='bold')
    ax.text(12, y_result - 1.0, '\u2191+ Gap increases', fontsize=9, color='#2e7d32')
    ax.text(12, y_result - 1.4, '\u2193\u2212 Gap decreases', fontsize=9, color='#c62828')
    
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename), dpi=150, bbox_inches='tight', facecolor='white')
    plt.close()

# X-axis stack-up
x_comps = [
    {'label': 'Frame Hole W', 'nominal': HOLE_W, 'tol': TOL_HOLE, 'color': '#00897b', 'direction': 'pos'},
    {'label': 'Punch Tip W', 'nominal': PUNCH_TIP_W, 'tol': TOL_PUNCH, 'color': '#f9a825', 'direction': 'neg'},
    {'label': 'Tool Pos Err (X)', 'nominal': 0.0, 'tol': TOL_TOOL_POS, 'color': '#5c6bc0', 'direction': 'neg'},
    {'label': 'Feed Accuracy', 'nominal': 0.0, 'tol': TOL_FEED, 'color': '#7e57c2', 'direction': 'neg'},
    {'label': 'Pitch Accuracy', 'nominal': 0.0, 'tol': TOL_PITCH, 'color': '#ab47bc', 'direction': 'neg'},
]
min_gap_x = (HOLE_W - TOL_HOLE - PUNCH_TIP_W - TOL_PUNCH)/2 - (TOL_TOOL_POS + TOL_FEED + TOL_PITCH)
max_gap_x = (HOLE_W + TOL_HOLE - PUNCH_TIP_W + TOL_PUNCH)/2
x_min_str = f"({HOLE_W-TOL_HOLE:.3f} - {PUNCH_TIP_W+TOL_PUNCH:.3f})/2 - {TOL_TOOL_POS+TOL_FEED+TOL_PITCH:.4f} = {min_gap_x:.4f} mm"
x_max_str = f"({HOLE_W+TOL_HOLE:.3f} - {PUNCH_TIP_W-TOL_PUNCH:.3f})/2 = {max_gap_x:.4f} mm"
create_stackup("stackup_x.png", "X-Axis Tolerance Stack-Up (Min/Max)", x_comps,
               "Gap X", x_min_str, x_max_str)

# Y-axis stack-up
y_comps = [
    {'label': 'Frame Hole H', 'nominal': HOLE_H, 'tol': TOL_HOLE, 'color': '#00897b', 'direction': 'pos'},
    {'label': 'Punch Tip H', 'nominal': PUNCH_TIP_H, 'tol': TOL_PUNCH, 'color': '#f9a825', 'direction': 'neg'},
    {'label': 'Tool Pos Err (Y)', 'nominal': 0.0, 'tol': TOL_TOOL_POS, 'color': '#5c6bc0', 'direction': 'neg'},
    {'label': 'Guide Play (Y)', 'nominal': 0.0, 'tol': TOL_GUIDE_PLAY, 'color': '#ef5350', 'direction': 'neg'},
]
min_gap_y = (HOLE_H - TOL_HOLE - PUNCH_TIP_H - TOL_PUNCH)/2 - (TOL_TOOL_POS + TOL_GUIDE_PLAY)
max_gap_y = (HOLE_H + TOL_HOLE - PUNCH_TIP_H + TOL_PUNCH)/2
y_min_str = f"({HOLE_H-TOL_HOLE:.3f} - {PUNCH_TIP_H+TOL_PUNCH:.3f})/2 - {TOL_TOOL_POS+TOL_GUIDE_PLAY:.4f} = {min_gap_y:.4f} mm"
y_max_str = f"({HOLE_H+TOL_HOLE:.3f} - {PUNCH_TIP_H-TOL_PUNCH:.3f})/2 = {max_gap_y:.4f} mm"
create_stackup("stackup_y.png", "Y-Axis Tolerance Stack-Up (Min/Max)", y_comps,
               "Gap Y", y_min_str, y_max_str)

print("Stack-up diagrams generated.")

# ======================================================================
# 6. LOAD ASSETS
# ======================================================================

def get_b64(fn):
    p = os.path.join(REPORT_DIR, fn)
    if not os.path.exists(p): return ""
    with open(p, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode()}"

img_x = get_b64("hist_x.png"); img_y = get_b64("hist_y.png")
img_sch = get_b64(schematic_file)
img_tx = get_b64("tornado_x.png"); img_ty = get_b64("tornado_y.png")
img_bend = get_b64("bending_chart.png")
img_su_x = get_b64("stackup_x.png"); img_su_y = get_b64("stackup_y.png")

# OBJ Parser
ASSY_PATH = os.path.join(WORKSPACE_DIR, "ASSY_Guide.obj")
def parse_obj(fp):
    objs = {}; cur = None; gv = []
    if not os.path.exists(fp): return {}
    with open(fp) as f:
        for line in f:
            line = line.strip()
            if not line or line[0] in '#mu': continue
            p = line.split()
            if p[0]=='o': cur=p[1]; objs[cur]={"vl":[],"i":[],"vo":len(gv)}
            elif p[0]=='v' and cur:
                c=[float(x) for x in p[1:4]]; gv.append(c); objs[cur]["vl"].extend(c)
            elif p[0]=='f' and cur:
                poly=[]
                for x in p[1:]:
                    idx=int(x.split('/')[0])-1; poly.append(idx-objs[cur]["vo"])
                for i in range(1,len(poly)-1): objs[cur]["i"].extend([poly[0],poly[i],poly[i+1]])
    return {n:{"v":d["vl"],"i":d["i"]} for n,d in objs.items()}

models = parse_obj(ASSY_PATH)
d_guide = models.get("Guide_for_3D_001",{"v":[],"i":[]})
d_punch = models.get("Punch_for_3D_001",{"v":[],"i":[]})
d_frame = models.get("Scrap_for_3D_001",{"v":[],"i":[]})
d_strip = models.get("Product_for_3D_001",{"v":[],"i":[]})

three_js = ""
if os.path.exists(THREE_JS_PATH):
    with open(THREE_JS_PATH, "r", encoding="utf-8") as f: three_js = f.read()

# Traffic lights
def tl(cpk, fr):
    if cpk >= 1.33 and fr < 0.01: return ("&#x1F7E2;","Safe","#27ae60","Interference risk is extremely low.")
    elif cpk >= 1.0 and fr < 1.0: return ("&#x1F7E1;","Caution","#f39c12","Some conditions may cause interference.")
    elif cpk >= 0.5 and fr < 10: return ("&#x1F7E0;","Warning","#e67e22","Interference occurs in some products.")
    else: return ("&#x1F534;","Danger","#e74c3c","High probability of interference.")

tl_x = tl(stats_x['cpk'], stats_x['fail_rate'])
tl_y = tl(stats_y['cpk'], stats_y['fail_rate'])

print("All calculations and charts complete. Generating HTML...")

# ======================================================================
# 7. HTML REPORT (v30 - Full Japanese)
# ======================================================================

bending_safe = "safe" if beam_delta < 0.01 else "danger"
wc_x_cls = "safe" if wc_x['worst_case'] > 0 else "danger"
wc_y_cls = "safe" if wc_y['worst_case'] > 0 else "danger"

html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gap Analysis Report v30</title>
<style>
*{{box-sizing:border-box}}
body{{font-family:'Segoe UI','Meiryo',sans-serif;background:#eaeded;margin:0;padding:20px;line-height:1.7;color:#2c3e50}}
.container{{max-width:1400px;margin:0 auto;background:#fff;padding:30px;box-shadow:0 4px 15px rgba(0,0,0,.1);border-radius:8px}}
.header{{text-align:center;margin-bottom:20px}}
.header h1{{font-size:1.6em;margin-bottom:5px}}
.stitle{{border-bottom:2px solid #546e7a;color:#2c3e50;padding-bottom:5px;margin-top:40px;font-size:1.3em}}
.exec{{background:linear-gradient(135deg,#2c3e50,#34495e);color:#fff;padding:25px;border-radius:12px;margin:20px 0}}
.exec h2{{margin-top:0;color:#fff;border:none;font-size:1.3em}}
.tgrid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:15px}}
.tcard{{background:rgba(255,255,255,.1);padding:20px;border-radius:8px;text-align:center}}
.ticon{{font-size:3em;margin-bottom:5px}}
.tlabel{{font-size:1.3em;font-weight:bold}}
.tdesc{{font-size:.9em;opacity:.9;margin-top:5px}}
.dash{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:15px 0}}
.dc{{padding:15px;border-radius:8px;text-align:center;border:1px solid #eee;background:#fafafa}}
.dc .mv{{font-size:1.8em;font-weight:bold;margin:5px 0}}
.dc .mn{{font-size:.82em;color:#666}}
.dc .me{{font-size:.72em;color:#999;margin-top:3px}}
.wt{{width:100%;border-collapse:collapse;margin:15px 0}}
.wt th,.wt td{{border:1px solid #ddd;padding:10px 15px;text-align:center}}
.wt th{{background:#34495e;color:#fff}}
.wt .safe{{background:#d5f5e3;color:#27ae60;font-weight:bold}}
.wt .danger{{background:#fadbd8;color:#e74c3c;font-weight:bold}}
.ib{{background:#f8f9fa;border-left:4px solid #3498db;padding:15px 20px;margin:15px 0;border-radius:0 8px 8px 0}}
.ib.warn{{border-left-color:#e74c3c;background:#fef5f5}}
.ib.green{{border-left-color:#27ae60;background:#f0fff0}}
.ib h4{{margin:0 0 8px 0;color:#2c3e50}}
.ib p{{margin:0;color:#555}}
.glos{{background:#f0f3f5;padding:20px;border-radius:8px;margin-top:20px}}
.glos dt{{font-weight:bold;color:#2c3e50;margin-top:12px}}
.glos dd{{margin-left:20px;color:#555}}
.cgrid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin:20px 0}}
.cbox{{text-align:center;background:#fafafa;padding:15px;border-radius:8px;border:1px solid #eee}}
.cbox img{{max-width:100%;border-radius:4px}}
.sgrid{{display:flex;gap:20px;margin-top:20px;flex-wrap:wrap}}
.scard{{flex:1;min-width:250px;padding:15px;border:1px solid #eee;text-align:center;background:#fff;border-radius:8px}}
.vbox{{width:100%;height:400px;background:#e0e0e0;position:relative;overflow:hidden;border-radius:4px;border:1px solid #ccc}}
.schbox{{text-align:center;margin:20px 0;padding:20px;background:#fafafa;border:1px dashed #ccc}}
.schbox img{{max-width:80%;box-shadow:0 2px 5px rgba(0,0,0,.1)}}
.pt{{width:100%;border-collapse:collapse;margin:15px 0;font-size:.9em}}
.pt th,.pt td{{border:1px solid #ddd;padding:8px 12px;text-align:center}}
.pt th{{background:#546e7a;color:#fff}}
.pt tr:nth-child(even){{background:#f9f9f9}}
.bend-grid{{display:grid;grid-template-columns:1fr 1fr;gap:15px;margin:15px 0}}
.bend-card{{padding:15px;border-radius:8px;text-align:center;border:1px solid #eee}}
.bend-card .bv{{font-size:1.6em;font-weight:bold;margin:3px 0}}
.bend-card .bn{{font-size:.82em;color:#666}}
.footer{{text-align:center;color:#888;margin-top:40px;font-size:.85em;padding-top:20px;border-top:1px solid #eee}}
</style>
<script>{three_js}</script>
</head>
<body>
<div class="container">
<div class="header">
<h1>&#x1F50D; パンチ・フレーム穴 干渉リスク分析レポート v30</h1>
<p>Punch Tip vs Frame (Scrap) Hole &mdash; 材質: Ni201 / 板厚: 0.2mm</p>
</div>

<!-- EXECUTIVE SUMMARY -->
<div class="exec">
<h2>&#x1F4CA; 総合評価 (Executive Summary)</h2>
<p>パンチ先端がフレーム穴を通過する際の隙間（ギャップ）を分析した結果です。<br>
ギャップがゼロ以下になると、パンチとフレーム穴が接触（干渉）し、製品不良や工具破損の原因になります。</p>
<div class="tgrid">
<div class="tcard">
<div class="ticon">{tl_x[0]}</div>
<div class="tlabel">X軸（送り方向）</div>
<div style="color:{tl_x[2]};font-size:1.2em;font-weight:bold">{tl_x[1]}</div>
<div class="tdesc">{tl_x[3]}</div>
<div class="tdesc">設計ギャップ: {nom_x:.3f} mm</div>
</div>
<div class="tcard">
<div class="ticon">{tl_y[0]}</div>
<div class="tlabel">Y軸（幅方向）&#x26A0;&#xFE0F;</div>
<div style="color:{tl_y[2]};font-size:1.2em;font-weight:bold">{tl_y[1]}</div>
<div class="tdesc">{tl_y[3]}</div>
<div class="tdesc">設計ギャップ: {nom_y:.3f} mm</div>
</div>
</div>
</div>

<!-- SECTION 1: WORST CASE -->
<h2 class="stitle">1. ワーストケース分析（最悪条件の重ね合わせ）</h2>
<div class="ib">
<h4>&#x1F4A1; この分析は何を示していますか？</h4>
<p>すべての寸法が同時に「最も悪い方向」に振れた場合のギャップを計算します。
実際にすべてが同時に最悪になることは稀ですが、<strong>物理的に起こりうる最悪の状態</strong>を把握できます。
例えると「すべてのサイコロが同時に1を出す」ような極端な状況です。</p>
</div>
<table class="wt">
<thead><tr><th>項目</th><th>X軸（送り方向）</th><th>Y軸（幅方向）</th></tr></thead>
<tbody>
<tr><td>基本ギャップ（設計値）</td><td><strong>{wc_x['nominal']:.3f} mm</strong></td><td><strong>{wc_y['nominal']:.3f} mm</strong></td></tr>
<tr><td>穴の最小寸法</td><td>{wc_x['min_hole']:.3f} mm</td><td>{wc_y['min_hole']:.3f} mm</td></tr>
<tr><td>パンチの最大寸法</td><td>{wc_x['max_punch']:.3f} mm</td><td>{wc_y['max_punch']:.3f} mm</td></tr>
<tr><td>位置ずれ（合計最大）</td><td>{wc_x['worst_pos']:.4f} mm</td><td>{wc_y['worst_pos']:.4f} mm</td></tr>
<tr><td><strong>ワーストケース ギャップ</strong></td>
<td class="{wc_x_cls}"><strong>{wc_x['worst_case']:.4f} mm</strong></td>
<td class="{wc_y_cls}"><strong>{wc_y['worst_case']:.4f} mm</strong></td></tr>
</tbody></table>

<h3>公差スタックアップ図（寸法の積み上げ）</h3>
<div class="ib">
<h4>&#x1F4A1; スタックアップ図の読み方</h4>
<p>各部品の寸法が最小・最大になった場合にギャップがどう変化するかを視覚的に示します。<br>
<strong style="color:#d32f2f">赤い数値 = 最大</strong>、<strong style="color:#1565c0">青い数値 = 最小</strong>。
&#x2191;+ はギャップを広げる方向、&#x2193;&#x2212; はギャップを狭める方向です。</p>
</div>
<div class="cgrid">
<div class="cbox"><h4>X軸 スタックアップ</h4><img src="{img_su_x}" style="max-width:100%"></div>
<div class="cbox"><h4>Y軸 スタックアップ &#x26A0;&#xFE0F;</h4><img src="{img_su_y}" style="max-width:100%"></div>
</div>
{"<div class='ib warn'><h4>&#x26A0;&#xFE0F; Y軸ワーストケースで干渉が発生します</h4><p>すべての公差が最悪方向に重なった場合、Y軸ギャップは <strong>" + f"{wc_y['worst_case']:.4f}" + " mm</strong>（マイナス = 干渉）になります。</p></div>" if wc_y['worst_case'] < 0 else ""}

<!-- SECTION 2: STATISTICAL DASHBOARD -->
<h2 class="stitle">2. 統計的分析ダッシュボード（Monte Carlo N={N:,}）</h2>
<div class="ib">
<h4>&#x1F4A1; 統計的分析とは？</h4>
<p>実際の生産では、すべてが同時に最悪になることは稀です。モンテカルロ法では、各寸法がランダムに変動する状況を
<strong>{N:,}回</strong>シミュレーションし、<strong>実際に近い条件下</strong>での干渉リスクを評価します。
例えると「工場で{N:,}個の製品を仮想的に作ってみて、何個に問題があるか数える」方法です。</p>
</div>
<h3>X軸（送り方向）&mdash; {tl_x[0]} {tl_x[1]}</h3>
<div class="dash">
<div class="dc" style="border-left:4px solid {tl_x[2]}"><div class="mn">干渉発生率</div><div class="mv" style="color:{tl_x[2]}">{stats_x['fail_rate']:.2f}%</div><div class="me">100個中 約{stats_x['fail_rate']:.1f}個</div></div>
<div class="dc"><div class="mn">DPMO</div><div class="mv">{stats_x['dpmo']:,}</div><div class="me">100万個中の不良数</div></div>
<div class="dc"><div class="mn">平均ギャップ</div><div class="mv">{stats_x['mean']:.4f}</div><div class="me">mm（ゼロ以上で安全）</div></div>
<div class="dc"><div class="mn">Cpk</div><div class="mv" style="color:{tl_x[2]}">{stats_x['cpk']:.2f}</div><div class="me">1.33以上が管理基準</div></div>
<div class="dc"><div class="mn">プロセスシグマ</div><div class="mv">{stats_x['z_sigma']:.1f}&sigma;</div><div class="me">高いほど安定</div></div>
<div class="dc"><div class="mn">安全余裕度</div><div class="mv">{stats_x['safety_margin_pct']:.0f}%</div><div class="me">設計値に対する余裕</div></div>
</div>
<h3>Y軸（幅方向）&mdash; {tl_y[0]} {tl_y[1]}</h3>
<div class="dash">
<div class="dc" style="border-left:4px solid {tl_y[2]}"><div class="mn">干渉発生率</div><div class="mv" style="color:{tl_y[2]}">{stats_y['fail_rate']:.2f}%</div><div class="me">100個中 約{stats_y['fail_rate']:.1f}個</div></div>
<div class="dc"><div class="mn">DPMO</div><div class="mv">{stats_y['dpmo']:,}</div><div class="me">100万個中の不良数</div></div>
<div class="dc"><div class="mn">平均ギャップ</div><div class="mv">{stats_y['mean']:.4f}</div><div class="me">mm（ゼロ以上で安全）</div></div>
<div class="dc"><div class="mn">Cpk</div><div class="mv" style="color:{tl_y[2]}">{stats_y['cpk']:.2f}</div><div class="me">1.33以上が管理基準</div></div>
<div class="dc"><div class="mn">プロセスシグマ</div><div class="mv">{stats_y['z_sigma']:.1f}&sigma;</div><div class="me">高いほど安定</div></div>
<div class="dc"><div class="mn">安全余裕度</div><div class="mv">{stats_y['safety_margin_pct']:.0f}%</div><div class="me">設計値に対する余裕</div></div>
</div>

<!-- SECTION 3: HISTOGRAMS -->
<h2 class="stitle">3. ギャップ分布（ヒストグラム）</h2>
<div class="ib">
<h4>&#x1F4A1; ヒストグラムの読み方</h4>
<p>横軸がギャップ値（mm）、縦軸が出現頻度です。<strong style="color:#e74c3c">赤い縦線</strong>が干渉ライン（Gap=0）です。
分布が赤い線の左側にはみ出すほど、干渉リスクが高いことを意味します。</p>
</div>
<div class="sgrid">
<div class="scard"><h4>X軸 ギャップ分布</h4><img src="{img_x}" style="max-width:100%"></div>
<div class="scard"><h4>Y軸 ギャップ分布 &#x26A0;&#xFE0F;</h4><img src="{img_y}" style="max-width:100%"></div>
</div>

<!-- SECTION 4: CONTRIBUTION -->
<h2 class="stitle">4. リスク要因分析（トルネードチャート）</h2>
<div class="ib">
<h4>&#x1F4A1; 寄与率チャートの読み方</h4>
<p>各公差がギャップのばらつきにどれだけ影響しているかを示します。
<strong style="color:#e74c3c">赤色のバー</strong>は最も影響が大きい要因です。改善効果が最も高い箇所を特定できます。</p>
</div>
<div class="cgrid">
<div class="cbox"><h4>X軸 寄与率</h4><img src="{img_tx}" style="max-width:100%"></div>
<div class="cbox"><h4>Y軸 寄与率 &#x26A0;&#xFE0F;</h4><img src="{img_ty}" style="max-width:100%"></div>
</div>

<!-- SECTION 5: FRAME BENDING -->
<h2 class="stitle">5. フレーム曲げ検証（パンチ押し込み時の変形解析）</h2>
<div class="ib">
<h4>&#x1F4A1; この検証は何を示していますか？</h4>
<p>パンチがProductを下方向に押し込む際、Frame（Scrap）が弓状に変形するかを検証します。<br>
Frameは Guideの段差（0.2mm）のみで支持されており、1.2Nの打ち抜き抵抗で変形するかを<strong>単純支持梁モデル</strong>で計算しました。</p>
</div>
<div class="ib {"green" if beam_delta < 0.01 else "warn"}">
<h4>{"&#x2705; 結論: Productが先にFrameから抜け落ちます" if beam_delta < 0.01 else "&#x26A0;&#xFE0F; 注意: Frameの変形が大きい可能性があります"}</h4>
<p>押し込み力 1.2N に対して、Frameの降伏力は <strong>{beam_F_yield:.1f}N</strong>（約{beam_F_yield/F_PUSH:.0f}倍）です。<br>
Frameのたわみ量は <strong>{beam_delta*1000:.1f} &mu;m</strong>（段差0.2mm = 200&mu;m の <strong>{beam_delta/0.2*100:.2f}%</strong>）で、ほぼ無視できるレベルです。</p>
</div>
<div class="bend-grid">
<div class="bend-card"><div class="bn">押込み力</div><div class="bv" style="color:#3498db">{F_PUSH} N</div></div>
<div class="bend-card"><div class="bn">降伏力</div><div class="bv" style="color:#f39c12">{beam_F_yield:.1f} N</div></div>
<div class="bend-card"><div class="bn">破断力</div><div class="bv" style="color:#e74c3c">{beam_F_uts:.1f} N</div></div>
<div class="bend-card"><div class="bn">たわみ量</div><div class="bv">{beam_delta*1000:.1f} &mu;m</div></div>
<div class="bend-card"><div class="bn">最大応力</div><div class="bv">{beam_sigma:.1f} MPa</div><div class="me">降伏応力の {beam_sigma/SY_NI201*100:.0f}%</div></div>
<div class="bend-card"><div class="bn">ばね定数</div><div class="bv">{beam_k:.0f} N/mm</div></div>
</div>
<div class="cgrid">
<div class="cbox"><img src="{img_bend}" style="max-width:100%"></div>
</div>
<table class="pt">
<thead><tr><th>パラメータ</th><th>値</th><th>備考</th></tr></thead>
<tbody>
<tr><td>材質</td><td>Ni201（純ニッケル）</td><td>ヤング率 207 GPa, 降伏103 MPa</td></tr>
<tr><td>板厚</td><td>{FRAME_T} mm</td><td>Frame / Product共通</td></tr>
<tr><td>梁幅 (有効断面)</td><td>{beam_b:.2f} mm</td><td>穴の両側のブリッジ幅の合計</td></tr>
<tr><td>スパン (支持間距離)</td><td>{beam_L} mm</td><td>穴幅 = Guide支持間距離</td></tr>
<tr><td>解析モデル</td><td>単純支持梁・中央集中荷重</td><td>Euler-Bernoulli梁理論</td></tr>
</tbody></table>

<!-- SECTION 6: 2D SCHEMATIC -->
<h2 class="stitle">6. 断面図（2Dスキマティック）</h2>
<div class="schbox">
<img src="{img_sch}" alt="2D Schematic">
<p><small>パンチ先端（黄色）とフレーム穴（水色）の位置関係 — 単位: mm</small></p>
</div>

<!-- SECTION 7: 3D VIEWS -->
<h2 class="stitle">7. 3Dモデル（インタラクティブ）</h2>
<div class="sgrid">
<div class="scard"><h4>アセンブリ全体</h4><div id="v_main" class="vbox"></div></div>
<div class="scard"><h4>パンチ部品</h4><div id="v_punch" class="vbox"></div></div>
<div class="scard"><h4>ガイド部品</h4><div id="v_guide" class="vbox"></div></div>
</div>
<p style="text-align:center;color:#666"><small>左ドラッグ: 回転 | ホイール: ズーム | 右ドラッグ: パン</small></p>

<!-- SECTION 8: INPUT PARAMS -->
<h2 class="stitle">8. 計算条件（入力パラメータ一覧）</h2>
<div class="ib">
<h4>&#x1F4A1; この表の読み方</h4>
<p>レポート内の全計算に使用した入力値です。「公差」は図面で許容されたばらつきの範囲です。「分布」は正規分布（ベル型のカーブ）で、公差 = 3&sigma;（99.7%の製品がこの範囲に収まる）として設定しています。</p>
</div>
<table class="pt">
<thead><tr><th>パラメータ名</th><th>基準値 (mm)</th><th>公差 (&plusmn;mm)</th><th>分布</th><th>適用軸</th><th>出典・備考</th></tr></thead>
<tbody>
<tr><td>フレーム穴 幅</td><td>{HOLE_W:.2f}</td><td>&plusmn;{TOL_HOLE}</td><td>正規</td><td>X</td><td>品質仕様書 *5&plusmn;0.1</td></tr>
<tr><td>フレーム穴 高さ</td><td>{HOLE_H:.2f}</td><td>&plusmn;{TOL_HOLE}</td><td>正規</td><td>Y</td><td>品質仕様書</td></tr>
<tr><td>パンチ先端 幅</td><td>{PUNCH_TIP_W:.2f}</td><td>&plusmn;{TOL_PUNCH}</td><td>正規</td><td>X</td><td>DXF図面</td></tr>
<tr><td>パンチ先端 高さ</td><td>{PUNCH_TIP_H:.2f}</td><td>&plusmn;{TOL_PUNCH}</td><td>正規</td><td>Y</td><td>DXF図面</td></tr>
<tr><td>工具位置誤差</td><td>0.000</td><td>&plusmn;{TOL_TOOL_POS}</td><td>正規</td><td>X, Y</td><td>加工機精度</td></tr>
<tr><td>送り精度</td><td>0.000</td><td>&plusmn;{TOL_FEED}</td><td>正規</td><td>X</td><td>最大変動量</td></tr>
<tr><td>ピッチ精度</td><td>0.000</td><td>&plusmn;{TOL_PITCH}</td><td>正規</td><td>X</td><td>3&sigma; = 0.01152</td></tr>
<tr><td>フレームガイドプレイ</td><td>0.000</td><td>&plusmn;{TOL_GUIDE_PLAY}</td><td>正規</td><td>Y</td><td>ストリップ幅公差&plusmn;0.15/2</td></tr>
</tbody></table>

<!-- SECTION 9: GLOSSARY -->
<h2 class="stitle">9. 用語解説（初めてこのレポートを読む方へ）</h2>
<div class="glos"><dl>
<dt>&#x1F4CC; ギャップ (Gap)</dt>
<dd>パンチ先端とフレーム穴の間の隙間。この値がゼロ以下になると「干渉」（接触・衝突）が発生します。</dd>
<dt>&#x1F4CC; 干渉 (Interference)</dt>
<dd>パンチとフレーム穴が接触してしまう状態。製品不良や工具破損の原因になります。</dd>
<dt>&#x1F4CC; ワーストケース分析</dt>
<dd>すべての寸法が「同時に最も悪い方向」に振れた場合を想定する評価方法です。実際にこうなる確率は非常に低いですが、理論上の最悪状態を確認できます。</dd>
<dt>&#x1F4CC; モンテカルロ・シミュレーション</dt>
<dd>各寸法の公差範囲でランダムに値を変えながら、{N:,}回の仮想生産をコンピュータで実行します。例えると「工場で{N:,}個の製品を仮想的に作り、何個に問題があるか数える」方法です。</dd>
<dt>&#x1F4CC; Cpk（工程能力指数）</dt>
<dd>製造プロセスの安定性を示す指標です。<br>
&bull; <strong>Cpk &ge; 1.33</strong> &#x1F7E2; 十分に安定（一般的な管理基準）<br>
&bull; <strong>1.00 &le; Cpk &lt; 1.33</strong> &#x1F7E1; やや不安定（改善検討）<br>
&bull; <strong>Cpk &lt; 1.00</strong> &#x1F534; 不安定（改善必要）<br>
駐車場に例えると、Cpkが高い = 車が駐車枠の真ん中にきちんと停まっている状態です。</dd>
<dt>&#x1F4CC; DPMO（百万個あたり不良数）</dt>
<dd>100万個の製品を作った場合に、何個で干渉が発生するかの推定値です。</dd>
<dt>&#x1F4CC; プロセスシグマ (Z&sigma;)</dt>
<dd>平均ギャップが干渉ラインから何個分の「標準偏差」離れているか。6&sigma;が最高品質、3&sigma;が一般的水準です。</dd>
<dt>&#x1F4CC; 安全余裕度 (%)</dt>
<dd>設計上のギャップに対して、実際のギャップ（平均値）がどれだけ維持されているか。100%に近いほど設計通りです。</dd>
<dt>&#x1F4CC; 寄与率 (Contribution %)</dt>
<dd>各公差がギャップのばらつきに占める割合。寄与率が高い要因を改善すると、最も効率的にリスクを低減できます。</dd>
<dt>&#x1F4CC; 単純支持梁モデル</dt>
<dd>フレームをGuide段差の2点で支持された「梁」として近似し、中央に集中荷重がかかる場合の変形量と応力を計算する方法です。工学では最も基本的な構造解析手法の一つです。</dd>
</dl></div>

<div class="footer">
<p>Generated: 2026-02-15 | Gap Analysis Report v30 | Monte Carlo N={N:,} | Ni201 t=0.2mm</p>
</div>
</div>

<script type="application/json" id="dg">{json.dumps(d_guide)}</script>
<script type="application/json" id="df">{json.dumps(d_frame)}</script>
<script type="application/json" id="ds">{json.dumps(d_strip)}</script>
<script type="application/json" id="dp">{json.dumps(d_punch)}</script>

<script>
function sv(cid, ms) {{
    if (typeof THREE==='undefined') return;
    var c=document.getElementById(cid), sc=new THREE.Scene();
    sc.background=new THREE.Color(0xd0d0d0);
    var a=c.clientWidth/c.clientHeight, fs=100;
    var cam=new THREE.OrthographicCamera(-fs*a/2,fs*a/2,fs/2,-fs/2,0.1,100000);
    var r=new THREE.WebGLRenderer({{antialias:true,alpha:true}});
    r.setSize(c.clientWidth,c.clientHeight); c.appendChild(r.domElement);
    var fb=new THREE.Box3(), hd=false;
    ms.forEach(function(m){{
        var el=document.getElementById(m.id); if(!el)return;
        var j=JSON.parse(el.textContent); if(!j.v||j.v.length===0)return;
        var g=new THREE.BufferGeometry();
        g.setAttribute('position',new THREE.Float32BufferAttribute(j.v,3));
        if(j.i&&j.i.length>0){{g.setIndex(j.i);g.computeVertexNormals();}}
        var mo={{color:m.color,side:THREE.DoubleSide}};
        if(m.op!==undefined){{mo.transparent=true;mo.opacity=m.op;mo.depthWrite=false;}}
        var mt=new THREE.MeshBasicMaterial(mo);
        var mesh=new THREE.Mesh(g,mt); mesh.rotation.x=-Math.PI/2;
        if(m.op!==undefined)mesh.renderOrder=1; sc.add(mesh);
        if(m.edges!==false){{var eg=new THREE.EdgesGeometry(g,30);
        var em=new THREE.LineBasicMaterial({{color:0x333333,linewidth:1}});
        var ed=new THREE.LineSegments(eg,em); ed.rotation.x=-Math.PI/2; sc.add(ed);}}
        mesh.updateMatrixWorld(); fb.expandByObject(mesh); hd=true;
    }});
    var tgt=new THREE.Vector3(), th=Math.PI/4, ph=Math.PI/3;
    if(hd){{fb.getCenter(tgt);var sz=new THREE.Vector3();fb.getSize(sz);
    fs=Math.max(sz.x,sz.y,sz.z)*1.8;
    cam.left=-fs*a/2;cam.right=fs*a/2;cam.top=fs/2;cam.bottom=-fs/2;cam.updateProjectionMatrix();}}
    var cd=fs*3;
    function uc(){{cam.position.x=tgt.x+cd*Math.sin(ph)*Math.sin(th);
    cam.position.y=tgt.y+cd*Math.cos(ph);cam.position.z=tgt.z+cd*Math.sin(ph)*Math.cos(th);cam.lookAt(tgt);}}
    uc();
    function an(){{requestAnimationFrame(an);r.render(sc,cam);}} an();
    var dr=false,px=0,py=0;
    c.onmousedown=function(e){{dr=true;px=e.clientX;py=e.clientY;e.preventDefault();}};
    window.onmouseup=function(){{dr=false;}};
    c.onmousemove=function(e){{if(!dr)return;var dx=e.clientX-px,dy=e.clientY-py;
    px=e.clientX;py=e.clientY;th-=dx*0.01;ph-=dy*0.01;ph=Math.max(0.1,Math.min(Math.PI-0.1,ph));uc();}};
    c.onwheel=function(e){{var zf=e.deltaY>0?1.1:0.9;fs*=zf;
    cam.left=-fs*a/2;cam.right=fs*a/2;cam.top=fs/2;cam.bottom=-fs/2;cam.updateProjectionMatrix();e.preventDefault();}};
}}
window.onload=function(){{
    sv('v_main',[{{id:'dp',color:0xf1c40f}},{{id:'dg',color:0x00bcd4}},{{id:'df',color:0xbdc3c7}},{{id:'ds',color:0x2ecc71}}]);
    sv('v_punch',[{{id:'dp',color:0xf1c40f,edges:true}}]);
    sv('v_guide',[{{id:'dg',color:0x00bcd4,edges:true}}]);
}};
</script>
</body></html>"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"v30 Report exported: {REPORT_PATH}")
