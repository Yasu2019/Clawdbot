
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os
import base64
import json
import math
import pandas as pd

# --- Configuration ---
if os.path.exists("/home/node/clawd"):
    WORKSPACE_DIR = "/home/node/clawd"
else:
    WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"

REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
MODEL_DIR = os.path.join(WORKSPACE_DIR, "report_assets", "3d_models")
REPORT_PATH = os.path.join(WORKSPACE_DIR, "gap_analysis_report.html")
THREE_JS_PATH = os.path.join(REPORT_DIR, "three.min.js")

# Font Fallback
plt.rcParams['font.family'] = 'DejaVu Sans'

# --- 1. Simulation Logic (Punch Tip vs Frame Hole) ---
# Parameters (Updated v27 - per 品質仕様書 drawing & user clarification)
# See gap_analysis_parameters.md for full source documentation
PUNCH_TIP_W = 0.95  # Horizontal X (mm)
HOLE_W = 5.00       # Horizontal X - Frame Hole Width (mm) - per drawing *5 ±0.1
PUNCH_TIP_H = 2.00  # Vertical Y (mm)
HOLE_H = 2.10       # Vertical Y - Frame Hole Height (mm)

# Tolerances (v27: corrected from drawing spec)
TOL_PUNCH     = 0.005   # Punch tip dimensional tolerance (±mm)
TOL_HOLE      = 0.1     # Frame Hole dimensional tolerance (±mm) - was 0.005, corrected per drawing
TOL_TOOL_POS  = 0.020   # Tool position error (±mm)
TOL_FEED      = 0.011   # Feed position accuracy - max variation (±mm)
TOL_PITCH     = 0.01152 # Product pitch accuracy - 3σ (±mm)
TOL_GUIDE_PLAY = 0.075  # Frame guide play in Y = strip width tol (±0.15) / 2

input_params = [
    {"name": "Punch Tip W",      "nominal": PUNCH_TIP_W, "tol": TOL_PUNCH,   "dist": "Normal"},
    {"name": "Frame Hole Width",  "nominal": HOLE_W,      "tol": TOL_HOLE,    "dist": "Normal"}, 
    {"name": "Tool Position Err", "nominal": 0.00,         "tol": TOL_TOOL_POS,"dist": "Normal"},
    {"name": "Feed Accuracy",     "nominal": 0.00,         "tol": TOL_FEED,    "dist": "Normal"}, 
    {"name": "Pitch Accuracy",    "nominal": 0.00,         "tol": TOL_PITCH,   "dist": "Normal"},
    {"name": "Frame Guide Play",  "nominal": 0.00,         "tol": TOL_GUIDE_PLAY, "dist": "Normal"},
]

N = 100000

def run_simulation(include_camber=False):
    # Dimensional Variations (Hole tolerance corrected to ±0.1 per drawing)
    s_hole_x = np.random.normal(HOLE_W, TOL_HOLE/3, N)
    s_tip_x  = np.random.normal(PUNCH_TIP_W, TOL_PUNCH/3, N)
    s_hole_y = np.random.normal(HOLE_H, TOL_HOLE/3, N)
    s_tip_y  = np.random.normal(PUNCH_TIP_H, TOL_PUNCH/3, N)
    
    # Positional Variations X (Tool + Feed + Pitch)
    s_tool_x = np.random.normal(0.00, TOL_TOOL_POS/3, N)
    s_feed_x = np.random.normal(0.00, TOL_FEED/3, N)
    s_pitch_x = np.random.normal(0.00, TOL_PITCH/3, N)
    s_total_x = s_tool_x + s_feed_x + s_pitch_x
    
    # Positional Variations Y (Tool + Frame Guide Play)
    s_tool_y = np.random.normal(0.00, TOL_TOOL_POS/3, N)
    s_guide_y = np.random.normal(0.00, TOL_GUIDE_PLAY/3, N)  # v27: Frame strip width variation
    s_total_y = s_tool_y + s_guide_y
    
    # Gap = (Hole - Tip)/2 - |Total Positional Deviation|
    gap_x = (s_hole_x - s_tip_x)/2 - np.abs(s_total_x)
    gap_y = (s_hole_y - s_tip_y)/2 - np.abs(s_total_y)
    
    return gap_x, gap_y

# Execute Simulation (v29 - with corrected tolerances)
gap_x, gap_y = run_simulation(include_camber=False)

# --- Extended Statistics ---

def get_extended_stats(data, nominal_gap):
    mean = np.mean(data)
    std = np.std(data)
    cpk = (mean - 0.0) / (3 * std) if std > 0 else 0
    fail_rate = np.sum(data < 0) / N * 100
    
    # Additional Metrics
    z_sigma = mean / std if std > 0 else 0          # Process Sigma Level
    dpmo = int(fail_rate * 10000)                      # Defects per Million
    safety_margin_pct = (mean / nominal_gap * 100) if nominal_gap > 0 else 0
    min_gap = np.min(data)
    max_gap = np.max(data)
    p01 = np.percentile(data, 0.1)                     # 0.1th percentile
    p999 = np.percentile(data, 99.9)                   # 99.9th percentile
    
    return {
        'mean': mean, 'std': std, 'cpk': cpk, 'fail_rate': fail_rate,
        'z_sigma': z_sigma, 'dpmo': dpmo, 'safety_margin_pct': safety_margin_pct,
        'min': min_gap, 'max': max_gap, 'p01': p01, 'p999': p999,
        'nominal_gap': nominal_gap
    }

# Worst-Case Analysis (simple min/max stack-up)
def worst_case_gap(hole_nom, hole_tol, punch_nom, punch_tol, pos_tols):
    """pos_tols: list of positional tolerance values (all summed as worst)"""
    min_hole = hole_nom - hole_tol
    max_punch = punch_nom + punch_tol
    worst_pos = sum(pos_tols)
    wc_gap = (min_hole - max_punch) / 2 - worst_pos
    nominal = (hole_nom - punch_nom) / 2
    return {'nominal': nominal, 'worst_case': wc_gap, 'min_hole': min_hole, 'max_punch': max_punch, 'worst_pos': worst_pos}

wc_x = worst_case_gap(HOLE_W, TOL_HOLE, PUNCH_TIP_W, TOL_PUNCH, [TOL_TOOL_POS, TOL_FEED, TOL_PITCH])
wc_y = worst_case_gap(HOLE_H, TOL_HOLE, PUNCH_TIP_H, TOL_PUNCH, [TOL_TOOL_POS, TOL_GUIDE_PLAY])

nominal_gap_x = (HOLE_W - PUNCH_TIP_W) / 2
nominal_gap_y = (HOLE_H - PUNCH_TIP_H) / 2

stats_x = get_extended_stats(gap_x, nominal_gap_x)
stats_y = get_extended_stats(gap_y, nominal_gap_y)

# --- Visuals ---
def create_hist(data, filename, title, st):
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.hist(data, bins=60, color='#3498db', alpha=0.6, edgecolor='#2980b9', linewidth=0.5)
    ax.axvline(0, color='#e74c3c', linestyle='--', linewidth=2.5, label='干渉ライン (Gap=0)')
    ax.axvline(st['mean'], color='#27ae60', linestyle='-', linewidth=2, label=f'平均 = {st["mean"]:.4f} mm')
    
    # Shade interference region
    xlim = ax.get_xlim()
    ax.axvspan(xlim[0], 0, alpha=0.1, color='red', label=f'干渉領域 ({st["fail_rate"]:.2f}%)')
    
    ax.set_xlabel('Gap (mm)', fontsize=12)
    ax.set_ylabel('Frequency', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.legend(fontsize=10, loc='upper right')
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename), dpi=150)
    plt.close()

create_hist(gap_x, "hist_x.png", "X-Axis Gap Distribution", stats_x)
create_hist(gap_y, "hist_y.png", "Y-Axis Gap Distribution", stats_y)

# --- Tornado Chart (Contribution Analysis) ---
def create_tornado(filename, axis_label, factors, title):
    """factors: list of (name, tolerance_value)"""
    variances = [(name, (tol/3)**2) for name, tol in factors]
    total_var = sum(v for _, v in variances)
    contributions = [(name, v/total_var*100) for name, v in variances]
    contributions.sort(key=lambda x: x[1])  # Ascending for horizontal bar
    
    fig, ax = plt.subplots(figsize=(10, max(4, len(contributions)*0.8)))
    names = [c[0] for c in contributions]
    vals = [c[1] for c in contributions]
    colors = ['#e74c3c' if v > 30 else '#f39c12' if v > 10 else '#3498db' for v in vals]
    
    bars = ax.barh(names, vals, color=colors, edgecolor='#333', height=0.6)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, f'{val:.1f}%', 
                va='center', fontsize=11, fontweight='bold')
    
    ax.set_xlabel('Contribution to Variance (%)', fontsize=12)
    ax.set_title(title, fontsize=14, fontweight='bold')
    ax.set_xlim(0, max(vals)*1.3)
    plt.tight_layout()
    plt.savefig(os.path.join(REPORT_DIR, filename), dpi=150)
    plt.close()
    return contributions

contrib_x = create_tornado("tornado_x.png", "X",
    [("Frame Hole Width (±0.1)", TOL_HOLE), ("Punch Tip Width (±0.005)", TOL_PUNCH),
     ("Tool Position (±0.020)", TOL_TOOL_POS), ("Feed Accuracy (±0.011)", TOL_FEED),
     ("Pitch Accuracy (±0.012)", TOL_PITCH)],
    "X-Axis: What Drives the Risk?")

contrib_y = create_tornado("tornado_y.png", "Y",
    [("Frame Hole Height (±0.1)", TOL_HOLE), ("Punch Tip Height (±0.005)", TOL_PUNCH),
     ("Tool Position (±0.020)", TOL_TOOL_POS), ("Guide Play (±0.075)", TOL_GUIDE_PLAY)],
    "Y-Axis: What Drives the Risk?")

# --- 2. Generate 2D Schematic (Top View with Camber Concept) ---
def generate_schematic():
    fig, ax = plt.subplots(figsize=(10, 8))
    
    # 1. Frame Hole (Cyan / Light Blue) - Centered at Y=0
    hole_color = '#00bcd4' # Cyan
    ax.add_patch(patches.Rectangle((-HOLE_W/2, -HOLE_H/2), HOLE_W, HOLE_H, 
                                  linewidth=2, edgecolor='#00838f', facecolor=hole_color, alpha=0.3, label='Frame Hole (Cyan)'))
    
    # 2. Two-Block Punch Tip (Yellow) - Centered at Y=0
    punch_color = '#f1c40f' # Yellow
    # VISUAL ONLY for schematic clarity
    bw = 0.70 
    bh = 0.70 
    bg = 0.35 
    
    # Top Block
    ax.add_patch(patches.Rectangle((-bw/2, bg/2), bw, bh, 
                                 linewidth=1.5, edgecolor='#d4ac0d', facecolor=punch_color, alpha=0.9))
    # Bottom Block
    ax.add_patch(patches.Rectangle((-bw/2, -bg/2 - bh), bw, bh, 
                                 linewidth=1.5, edgecolor='#d4ac0d', facecolor=punch_color, alpha=0.9, label='Punch Head (Yellow 2-Blocks)'))
    
    # 3. Gap Markers
    def arrow_dim(x1, y1, x2, y2, text, color='blue', ha='left', va='center', dy=0):
        ax.annotate('', xy=(x1, y1), xytext=(x2, y2), 
                    arrowprops=dict(arrowstyle='<->', color=color, lw=2, mutation_scale=15))
        ax.text((x1+x2)/2, (y1+y2)/2 + dy, text, 
                ha=ha, va=va, color=color, fontweight='bold', fontsize=9, backgroundcolor='white')

    # X-Axis Gap (Extended to touch boundaries, Label lowered to avoid overlap)
    arrow_dim(-HOLE_W/2, bg/2 + bh/2, -bw/2, bg/2 + bh/2, "Gap X", ha='center', va='top', dy=-0.1)
    # Y-Axis Gap (Top edge clearance)
    arrow_dim(0, bg/2 + bh, 0, HOLE_H/2, "Gap Y", color='green', ha='center', va='bottom', dy=0.05)

    ax.set_xlim(-1.2, 1.2)
    ax.set_ylim(-1.5, 1.5)
    ax.set_aspect('equal')
    ax.axis('off')
    plt.title("v21: Final Schematic - Corrected Dimension Placements", fontsize=12)
    plt.legend(loc='lower left', fontsize=8)
    
    filename = "schematic_v21_final.png"
    plt.savefig(os.path.join(REPORT_DIR, filename), bbox_inches='tight', dpi=150)
    plt.close()
    return filename
    plt.title("v16: Top View - Functional Gap (Two-Block Punch Interface)", fontsize=12)
    plt.legend(loc='lower left', fontsize=8)
    
    filename = "schematic_v16_twoblock.png"
    plt.savefig(os.path.join(REPORT_DIR, filename), bbox_inches='tight', dpi=150)
    plt.close()
    return filename

schematic_file = generate_schematic()

# Calculation Basis Table (Documentation)
def generate_dim_table():
    rows = []
    for p in input_params:
        rows.append(f"""
            <tr>
                <td>{p['name']}</td>
                <td>{p['nominal']:.3f}</td>
                <td>±{p['tol']:.3f}</td>
                <td>{p['dist']}</td>
                <td>{'Provisional / 仮' if p['tol'] == 0.005 or p['name'] == 'Camber (Y)' else 'Standard'}</td>
            </tr>
        """)
    return f"""
    <div class="fci-table-box">
        <h3>Simulation Dimension & Tolerance List (管理寸法表)</h3>
        <table class="fci-table">
            <thead>
                <tr>
                    <th>Parameter Name</th>
                    <th>Nominal (mm)</th>
                    <th>Tolerance (mm)</th>
                    <th>Distribution</th>
                    <th>Source / Status</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows)}
            </tbody>
        </table>
    </div>
    """

dim_table_html = generate_dim_table()

# Tables Generation - REMOVED (replaced by dashboard in v29)

# Nominal Gap comment
# X = (5.00 - 0.95)/2 = 2.025  Y = (2.10 - 2.00)/2 = 0.050

def get_b64(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_x = get_b64("hist_x.png")
img_y = get_b64("hist_y.png")
img_schematic = get_b64(schematic_file)
img_tornado_x = get_b64("tornado_x.png")
img_tornado_y = get_b64("tornado_y.png")

# 3. Model Loading - Multi-Object OBJ Parser (ASSY_Guide.obj)
ASSY_OBJ_PATH = os.path.join(WORKSPACE_DIR, "ASSY_Guide.obj")

def parse_multi_obj(filepath):
    """Parse a multi-object OBJ file, returning a dict of {object_name: {v:[], i:[]}}"""
    objects = {}
    current_obj = None
    global_vertices = []  # OBJ vertex indices are global across the file
    
    if not os.path.exists(filepath):
        print(f"WARNING: {filepath} not found")
        return {}
    
    with open(filepath, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or line.startswith('mtllib') or line.startswith('usemtl'):
                continue
            parts = line.split()
            if parts[0] == 'o':
                current_obj = parts[1]
                objects[current_obj] = {"v_local": [], "i": [], "v_offset": len(global_vertices)}
            elif parts[0] == 'v':
                try:
                    coords = [float(x) for x in parts[1:4]]
                    global_vertices.append(coords)
                    if current_obj:
                        objects[current_obj]["v_local"].extend(coords)
                except:
                    pass
            elif parts[0] == 'f' and current_obj:
                poly = []
                for p in parts[1:]:
                    idx_str = p.split('/')[0]
                    if idx_str:
                        global_idx = int(idx_str) - 1  # OBJ is 1-indexed
                        local_idx = global_idx - objects[current_obj]["v_offset"]
                        poly.append(local_idx)
                for i in range(1, len(poly) - 1):
                    objects[current_obj]["i"].extend([poly[0], poly[i], poly[i+1]])
    
    result = {}
    for name, data in objects.items():
        result[name] = {"v": data["v_local"], "i": data["i"]}
        print(f"  Component '{name}': {len(data['v_local'])//3} vertices, {len(data['i'])//3} faces")
    return result

print(f"Parsing ASSY_Guide.obj...")
assy_models = parse_multi_obj(ASSY_OBJ_PATH)

data_guide = assy_models.get("Guide_for_3D_001", {"v":[], "i":[]})
data_punch = assy_models.get("Punch_for_3D_001", {"v":[], "i":[]})
data_frame = assy_models.get("Scrap_for_3D_001", {"v":[], "i":[]})
data_strip = assy_models.get("Product_for_3D_001", {"v":[], "i":[]})

three_js_content = ""
if os.path.exists(THREE_JS_PATH):
    with open(THREE_JS_PATH, "r", encoding="utf-8") as f: three_js_content = f.read()

# Helper: traffic light based on Cpk
def traffic_light(cpk, fail_rate):
    if cpk >= 1.33 and fail_rate < 0.01:
        return ("🟢", "安全 (Safe)", "#27ae60", "問題なし — 干渉リスクは極めて低いです。")
    elif cpk >= 1.0 and fail_rate < 1.0:
        return ("🟡", "注意 (Caution)", "#f39c12", "管理が必要 — 一部条件で干渉の可能性があります。")
    elif cpk >= 0.5 and fail_rate < 10.0:
        return ("🟠", "警告 (Warning)", "#e67e22", "改善推奨 — 生産品の一部で干渉が発生します。")
    else:
        return ("🔴", "危険 (Danger)", "#e74c3c", "改善必須 — 高い確率で干渉が発生します。")

tl_x = traffic_light(stats_x['cpk'], stats_x['fail_rate'])
tl_y = traffic_light(stats_y['cpk'], stats_y['fail_rate'])

# Overall verdict
if stats_y['fail_rate'] > 5 or stats_x['fail_rate'] > 5:
    overall_tl = ("🔴", "要改善", "#e74c3c")
elif stats_y['fail_rate'] > 1 or stats_x['fail_rate'] > 1:
    overall_tl = ("🟠", "注意", "#e67e22")
else:
    overall_tl = ("🟢", "良好", "#27ae60")

# 4. HTML Generation (v29: Dashboard format with explanations)
html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gap Analysis Report v29</title>
    <style>
        body {{ font-family: 'Segoe UI', 'Meiryo', sans-serif; background: #eaeded; margin: 0; padding: 20px; line-height: 1.6; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 30px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        .header {{ text-align: center; margin-bottom: 20px; }}
        .section-title {{ border-bottom: 2px solid #546e7a; color: #2c3e50; padding-bottom: 5px; margin-top: 40px; font-size: 1.3em; }}

        /* Executive Summary */
        .exec-summary {{ background: linear-gradient(135deg, #2c3e50, #34495e); color: white; padding: 25px; border-radius: 12px; margin: 20px 0; }}
        .exec-summary h2 {{ margin-top: 0; color: white; border: none; }}
        .traffic-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 15px; }}
        .traffic-card {{ background: rgba(255,255,255,0.1); padding: 20px; border-radius: 8px; text-align: center; }}
        .traffic-icon {{ font-size: 3em; margin-bottom: 5px; }}
        .traffic-label {{ font-size: 1.3em; font-weight: bold; }}
        .traffic-desc {{ font-size: 0.9em; opacity: 0.9; margin-top: 5px; }}

        /* Dashboard Cards */
        .dashboard {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 20px 0; }}
        .dash-card {{ padding: 15px; border-radius: 8px; text-align: center; border: 1px solid #eee; }}
        .dash-card .metric-value {{ font-size: 2em; font-weight: bold; margin: 5px 0; }}
        .dash-card .metric-name {{ font-size: 0.85em; color: #666; }}
        .dash-card .metric-explain {{ font-size: 0.75em; color: #999; margin-top: 5px; }}

        /* Worst Case Table */
        .wc-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
        .wc-table th, .wc-table td {{ border: 1px solid #ddd; padding: 10px 15px; text-align: center; }}
        .wc-table th {{ background: #34495e; color: white; }}
        .wc-table .safe {{ background: #d5f5e3; color: #27ae60; font-weight: bold; }}
        .wc-table .danger {{ background: #fadbd8; color: #e74c3c; font-weight: bold; }}

        /* Info Box */
        .info-box {{ background: #f8f9fa; border-left: 4px solid #3498db; padding: 15px 20px; margin: 15px 0; border-radius: 0 8px 8px 0; }}
        .info-box.warning {{ border-left-color: #e74c3c; background: #fef5f5; }}
        .info-box h4 {{ margin-top: 0; color: #2c3e50; }}
        .info-box p {{ margin-bottom: 0; color: #555; }}

        /* Glossary */
        .glossary {{ background: #f0f3f5; padding: 20px; border-radius: 8px; margin-top: 20px; }}
        .glossary dt {{ font-weight: bold; color: #2c3e50; margin-top: 12px; }}
        .glossary dd {{ margin-left: 20px; color: #555; }}

        /* Contribution charts */
        .chart-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin: 20px 0; }}
        .chart-box {{ text-align: center; background: #fafafa; padding: 15px; border-radius: 8px; border: 1px solid #eee; }}
        .chart-box img {{ max-width: 100%; border-radius: 4px; }}

        /* Stats Grid */
        .stats-grid {{ display: flex; gap: 20px; margin-top: 20px; }}
        .stat-card {{ flex: 1; padding: 15px; border: 1px solid #eee; text-align: center; background: #fff; border-radius: 8px; }}

        /* Viewer */
        .viewer-box {{ width: 100%; height: 600px; background: #e0e0e0; position: relative; overflow: hidden; border-radius: 4px; border: 1px solid #ccc; }}
        .schematic-box {{ text-align: center; margin: 20px 0; padding: 20px; background: #fafafa; border: 1px dashed #ccc; }}
        .schematic-box img {{ max-width: 80%; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}

        /* Input Params Table */
        .param-table {{ width: 100%; border-collapse: collapse; margin: 15px 0; font-size: 0.9em; }}
        .param-table th, .param-table td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: center; }}
        .param-table th {{ background: #546e7a; color: white; }}
    </style>
    <script>{three_js_content}</script>
</head>
<body>

<div class="container">
    <div class="header">
        <h1>🔍 パンチ・フレーム穴 干渉リスク分析レポート v29</h1>
        <p>Punch Tip vs Frame (Scrap) Hole — Gap Analysis Report</p>
    </div>

    <!-- ==================== SECTION 1: EXECUTIVE SUMMARY ==================== -->
    <div class="exec-summary">
        <h2>📊 総合評価 (Executive Summary)</h2>
        <p style="font-size:1.1em;">パンチ先端がフレーム穴を通過する際の隙間（ギャップ）を分析した結果です。<br>
        ギャップがゼロ以下になると、パンチとフレーム穴が接触（干渉）し、製品不良や工具破損の原因になります。</p>
        
        <div class="traffic-grid">
            <div class="traffic-card">
                <div class="traffic-icon">{tl_x[0]}</div>
                <div class="traffic-label">X軸（送り方向）</div>
                <div style="color:{tl_x[2]}; font-size:1.2em; font-weight:bold;">{tl_x[1]}</div>
                <div class="traffic-desc">{tl_x[3]}</div>
                <div class="traffic-desc">Nominal Gap: {nominal_gap_x:.3f} mm</div>
            </div>
            <div class="traffic-card">
                <div class="traffic-icon">{tl_y[0]}</div>
                <div class="traffic-label">Y軸（幅方向）⚠️ 重要</div>
                <div style="color:{tl_y[2]}; font-size:1.2em; font-weight:bold;">{tl_y[1]}</div>
                <div class="traffic-desc">{tl_y[3]}</div>
                <div class="traffic-desc">Nominal Gap: {nominal_gap_y:.3f} mm</div>
            </div>
        </div>
    </div>

    <!-- ==================== SECTION 2: WORST CASE ==================== -->
    <h2 class="section-title">1. ワーストケース分析（最悪条件の重ね合わせ）</h2>
    <div class="info-box">
        <h4>💡 この分析は何を示していますか？</h4>
        <p>すべての寸法が同時に「最も悪い方向」に振れた場合のギャップを計算します。<br>
        実際にすべてが同時に最悪になることは稀ですが、<strong>物理的に起こりうる最悪の状態</strong>を把握できます。</p>
    </div>
    <table class="wc-table">
        <thead>
            <tr>
                <th>項目</th>
                <th>X軸（送り方向）</th>
                <th>Y軸（幅方向）</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>基本ギャップ（設計値）</td>
                <td><strong>{wc_x['nominal']:.3f} mm</strong></td>
                <td><strong>{wc_y['nominal']:.3f} mm</strong></td>
            </tr>
            <tr>
                <td>穴の最小寸法</td>
                <td>{wc_x['min_hole']:.3f} mm</td>
                <td>{wc_y['min_hole']:.3f} mm</td>
            </tr>
            <tr>
                <td>パンチの最大寸法</td>
                <td>{wc_x['max_punch']:.3f} mm</td>
                <td>{wc_y['max_punch']:.3f} mm</td>
            </tr>
            <tr>
                <td>位置ずれ（合計最大）</td>
                <td>{wc_x['worst_pos']:.4f} mm</td>
                <td>{wc_y['worst_pos']:.4f} mm</td>
            </tr>
            <tr>
                <td><strong>ワーストケース ギャップ</strong></td>
                <td class="{'safe' if wc_x['worst_case'] > 0 else 'danger'}"><strong>{wc_x['worst_case']:.4f} mm</strong></td>
                <td class="{'safe' if wc_y['worst_case'] > 0 else 'danger'}"><strong>{wc_y['worst_case']:.4f} mm</strong></td>
            </tr>
        </tbody>
    </table>
    {'<div class="info-box warning"><h4>⚠️ Y軸ワーストケースで干渉が発生します</h4><p>すべての公差が最悪方向に重なった場合、Y軸ギャップは <strong>' + f"{wc_y['worst_case']:.4f}" + ' mm</strong>（マイナス = 干渉）になります。改善策の検討が必要です。</p></div>' if wc_y['worst_case'] < 0 else ''}

    <!-- ==================== SECTION 3: STATISTICAL DASHBOARD ==================== -->
    <h2 class="section-title">2. 統計的分析ダッシュボード（Monte Carlo N={N:,}）</h2>
    <div class="info-box">
        <h4>💡 統計的分析とは？</h4>
        <p>実際の生産では、すべてが同時に最悪になることは稀です。モンテカルロ法では、各寸法がランダムに変動する状況を <strong>{N:,}回</strong> シミュレーションし、<strong>実際に近い条件下</strong>での干渉リスクを評価します。</p>
    </div>

    <h3>X軸（送り方向）— {tl_x[0]} {tl_x[1]}</h3>
    <div class="dashboard">
        <div class="dash-card" style="border-left: 4px solid {tl_x[2]};">
            <div class="metric-name">干渉発生率</div>
            <div class="metric-value" style="color:{tl_x[2]};">{stats_x['fail_rate']:.2f}%</div>
            <div class="metric-explain">100個中 約{stats_x['fail_rate']:.1f}個で干渉</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">DPMO</div>
            <div class="metric-value">{stats_x['dpmo']:,}</div>
            <div class="metric-explain">100万個中の不良数</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">平均ギャップ</div>
            <div class="metric-value">{stats_x['mean']:.4f}</div>
            <div class="metric-explain">mm（ゼロ以上で安全）</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">Cpk</div>
            <div class="metric-value" style="color:{tl_x[2]};">{stats_x['cpk']:.2f}</div>
            <div class="metric-explain">1.33以上が管理基準</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">プロセスシグマ</div>
            <div class="metric-value">{stats_x['z_sigma']:.1f}σ</div>
            <div class="metric-explain">高いほど安定</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">安全余裕度</div>
            <div class="metric-value">{stats_x['safety_margin_pct']:.0f}%</div>
            <div class="metric-explain">設計ギャップに対する余裕</div>
        </div>
    </div>

    <h3>Y軸（幅方向）— {tl_y[0]} {tl_y[1]}</h3>
    <div class="dashboard">
        <div class="dash-card" style="border-left: 4px solid {tl_y[2]};">
            <div class="metric-name">干渉発生率</div>
            <div class="metric-value" style="color:{tl_y[2]};">{stats_y['fail_rate']:.2f}%</div>
            <div class="metric-explain">100個中 約{stats_y['fail_rate']:.1f}個で干渉</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">DPMO</div>
            <div class="metric-value">{stats_y['dpmo']:,}</div>
            <div class="metric-explain">100万個中の不良数</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">平均ギャップ</div>
            <div class="metric-value">{stats_y['mean']:.4f}</div>
            <div class="metric-explain">mm（ゼロ以上で安全）</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">Cpk</div>
            <div class="metric-value" style="color:{tl_y[2]};">{stats_y['cpk']:.2f}</div>
            <div class="metric-explain">1.33以上が管理基準</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">プロセスシグマ</div>
            <div class="metric-value">{stats_y['z_sigma']:.1f}σ</div>
            <div class="metric-explain">高いほど安定</div>
        </div>
        <div class="dash-card">
            <div class="metric-name">安全余裕度</div>
            <div class="metric-value">{stats_y['safety_margin_pct']:.0f}%</div>
            <div class="metric-explain">設計ギャップに対する余裕</div>
        </div>
    </div>

    <!-- ==================== SECTION 4: HISTOGRAMS ==================== -->
    <h2 class="section-title">3. ギャップ分布（ヒストグラム）</h2>
    <div class="info-box">
        <h4>💡 ヒストグラムの読み方</h4>
        <p>横軸がギャップ値（mm）、縦軸が出現頻度です。<strong>赤い縦線</strong>が干渉ライン（Gap=0）です。<br>
        分布が赤い線の左側にはみ出すほど、干渉リスクが高いことを意味します。 赤く色付けされた領域が干渉が発生する範囲です。</p>
    </div>
    <div class="stats-grid">
        <div class="stat-card" style="flex:1;">
            <h4>X軸 ギャップ分布</h4>
            <img src="{img_x}" style="max-width:100%">
        </div>
        <div class="stat-card" style="flex:1;">
            <h4>Y軸 ギャップ分布 ⚠️</h4>
            <img src="{img_y}" style="max-width:100%">
        </div>
    </div>

    <!-- ==================== SECTION 5: CONTRIBUTION ==================== -->
    <h2 class="section-title">4. リスク要因分析（何が干渉リスクを引き起こすか？）</h2>
    <div class="info-box">
        <h4>💡 寄与率チャートの読み方</h4>
        <p>各公差がギャップのばらつきにどれだけ影響しているかを示します。<br>
        <strong style="color:#e74c3c;">赤色のバー</strong>は最も影響が大きい要因です。改善効果が最も高い箇所を特定できます。</p>
    </div>
    <div class="chart-grid">
        <div class="chart-box">
            <h4>X軸 寄与率</h4>
            <img src="{img_tornado_x}" style="max-width:100%">
        </div>
        <div class="chart-box">
            <h4>Y軸 寄与率 ⚠️</h4>
            <img src="{img_tornado_y}" style="max-width:100%">
        </div>
    </div>

    <!-- ==================== SECTION 6: 2D SCHEMATIC ==================== -->
    <h2 class="section-title">5. 断面図（2Dスキマティック）</h2>
    <div class="schematic-box">
        <img src="{img_schematic}" alt="2D Schematic Top View">
        <p><small>パンチ先端（黄色）とフレーム穴（水色）の位置関係を示します。単位: mm</small></p>
    </div>

    <!-- ==================== SECTION 7: 3D VIEWS ==================== -->
    <h2 class="section-title">6. 3Dモデル（インタラクティブ）</h2>
    <div class="stats-grid">
        <div class="stat-card" style="flex:1;">
            <h4>アセンブリ全体</h4>
            <div id="viewer_main" class="viewer-box" style="height:400px;"></div>
        </div>
        <div class="stat-card" style="flex:1;">
            <h4>パンチ部品</h4>
            <div id="viewer_punch" class="viewer-box" style="height:400px;"></div>
        </div>
        <div class="stat-card" style="flex:1;">
            <h4>ガイド部品</h4>
            <div id="viewer_guide" class="viewer-box" style="height:400px;"></div>
        </div>
    </div>
    <p style="text-align:center; color:#666;"><small>左ドラッグ: 回転 | ホイール: ズーム | 右ドラッグ: パン</small></p>

    <!-- ==================== SECTION 8: INPUT PARAMS ==================== -->
    <h2 class="section-title">7. 計算条件（入力パラメータ一覧）</h2>
    <table class="param-table">
        <thead>
            <tr>
                <th>パラメータ名</th>
                <th>基準値 (mm)</th>
                <th>公差 (±mm)</th>
                <th>分布</th>
                <th>備考</th>
            </tr>
        </thead>
        <tbody>
            <tr><td>Frame Hole Width (X)</td><td>{HOLE_W:.2f}</td><td>±{TOL_HOLE}</td><td>Normal</td><td>品質仕様書 *5±0.1</td></tr>
            <tr><td>Frame Hole Height (Y)</td><td>{HOLE_H:.2f}</td><td>±{TOL_HOLE}</td><td>Normal</td><td>品質仕様書</td></tr>
            <tr><td>Punch Tip Width (X)</td><td>{PUNCH_TIP_W:.2f}</td><td>±{TOL_PUNCH}</td><td>Normal</td><td>DXF</td></tr>
            <tr><td>Punch Tip Height (Y)</td><td>{PUNCH_TIP_H:.2f}</td><td>±{TOL_PUNCH}</td><td>Normal</td><td>DXF</td></tr>
            <tr><td>Tool Position Error</td><td>0.000</td><td>±{TOL_TOOL_POS}</td><td>Normal</td><td>X, Y両方向</td></tr>
            <tr><td>Feed Accuracy (X only)</td><td>0.000</td><td>±{TOL_FEED}</td><td>Normal</td><td>最大変動量</td></tr>
            <tr><td>Pitch Accuracy (X only)</td><td>0.000</td><td>±{TOL_PITCH}</td><td>Normal</td><td>3σ = 0.01152</td></tr>
            <tr><td>Frame Guide Play (Y only)</td><td>0.000</td><td>±{TOL_GUIDE_PLAY}</td><td>Normal</td><td>ストリップ幅公差±0.15/2</td></tr>
        </tbody>
    </table>

    <!-- ==================== SECTION 9: GLOSSARY ==================== -->
    <h2 class="section-title">8. 用語解説（初めてこのレポートを読む方へ）</h2>
    <div class="glossary">
        <dl>
            <dt>📌 ギャップ (Gap)</dt>
            <dd>パンチ先端とフレーム穴の間の隙間。この値がゼロ以下になると「干渉」（接触・衝突）が発生します。</dd>

            <dt>📌 干渉 (Interference)</dt>
            <dd>パンチとフレーム穴が接触してしまう状態。製品不良や工具破損の原因になります。</dd>

            <dt>📌 ワーストケース分析</dt>
            <dd>すべての寸法が「同時に最も悪い方向」に振れた場合を想定する、最も厳しい評価方法です。<br>
            例えると「すべてのサイコロが同時に1を出す」ような極端な状況です。実際にこうなる確率は低いですが、理論上の最悪状態を確認できます。</dd>

            <dt>📌 モンテカルロ・シミュレーション</dt>
            <dd>各寸法の公差範囲内でランダムに値を変えながら、{N:,}回の仮想生産をコンピュータで実行します。<br>
            例えると「工場で{N:,}個の製品を仮想的に作ってみて、何個に問題があるか数える」方法です。実際の生産条件に最も近い結果が得られます。</dd>

            <dt>📌 Cpk（工程能力指数）</dt>
            <dd>製造プロセスの安定性を示す指標です。<br>
            ・<strong>Cpk ≥ 1.33</strong> 🟢 十分に安定（一般的な管理基準）<br>
            ・<strong>1.00 ≤ Cpk &lt; 1.33</strong> 🟡 やや不安定（改善検討）<br>
            ・<strong>Cpk &lt; 1.00</strong> 🔴 不安定（改善必要）<br>
            駐車場に例えると、Cpkが高い = 車が駐車枠の真ん中にきちんと停まっている状態。Cpkが低い = 車がふらつき、枠線に接触しそうな状態です。</dd>

            <dt>📌 DPMO（百万個あたり不良数）</dt>
            <dd>100万個の製品を作った場合に、何個で干渉が発生するかを推定した値です。<br>
            ・DPMO = 3,400 → 1,000個中 約3.4個の不良<br>
            ・DPMO = 100,000 → 10個中 1個の不良</dd>

            <dt>📌 プロセスシグマ (Zσ)</dt>
            <dd>平均ギャップが干渉ラインから何個分の「標準偏差（ばらつきの指標）」離れているかを示します。<br>
            ・6σ: 極めて高品質（不良率: 0.00034%）<br>
            ・3σ: 一般的な品質水準（不良率: 0.27%）<br>
            ・1σ以下: 高い不良リスク</dd>

            <dt>📌 安全余裕度 (%)</dt>
            <dd>設計上のギャップに対して、実際のギャップ（平均値）がどれだけ維持されているかを示します。<br>
            100%に近いほど設計通り。低いほど公差やズレで余裕を消費しています。</dd>

            <dt>📌 寄与率 (Contribution %)</dt>
            <dd>各公差がギャップのばらつきに占める割合です。寄与率が高い要因を改善すると、最も効率的にリスクを低減できます。</dd>
        </dl>
    </div>
</div>

<script type="application/json" id="d-guide">{json.dumps(data_guide)}</script>
<script type="application/json" id="d-frame">{json.dumps(data_frame)}</script>
<script type="application/json" id="d-strip">{json.dumps(data_strip)}</script>
<script type="application/json" id="d-punch">{json.dumps(data_punch)}</script>

<script>
    function setupViewer(containerId, models) {{
        if (typeof THREE === 'undefined') return;
        const container = document.getElementById(containerId);
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xd0d0d0);

        const aspect = container.clientWidth / container.clientHeight;
        let frustumSize = 100;
        const camera = new THREE.OrthographicCamera(
            -frustumSize * aspect / 2, frustumSize * aspect / 2,
            frustumSize / 2, -frustumSize / 2,
            0.1, 100000
        );

        const renderer = new THREE.WebGLRenderer({{ antialias: true, alpha: true }});
        renderer.setSize(container.clientWidth, container.clientHeight);
        container.appendChild(renderer.domElement);

        const fullBox = new THREE.Box3();
        let hasData = false;

        models.forEach(m => {{
            const el = document.getElementById(m.id);
            if (!el) return;
            const json = JSON.parse(el.textContent);
            if (!json.v || json.v.length === 0) return;
            const geo = new THREE.BufferGeometry();
            geo.setAttribute('position', new THREE.Float32BufferAttribute(json.v, 3));
            if (json.i && json.i.length > 0) {{ geo.setIndex(json.i); geo.computeVertexNormals(); }}

            const matOpts = {{ color: m.color, side: THREE.DoubleSide }};
            if (m.opacity !== undefined) {{
                matOpts.transparent = true;
                matOpts.opacity = m.opacity;
                matOpts.depthWrite = false;
            }}
            const mat = new THREE.MeshBasicMaterial(matOpts);
            const mesh = new THREE.Mesh(geo, mat);
            mesh.rotation.x = -Math.PI / 2;
            if (m.opacity !== undefined) mesh.renderOrder = 1;
            scene.add(mesh);

            const edgesGeo = new THREE.EdgesGeometry(geo, 30);
            const edgesMat = new THREE.LineBasicMaterial({{ color: 0x333333, linewidth: 1 }});
            const edges = new THREE.LineSegments(edgesGeo, edgesMat);
            edges.rotation.x = -Math.PI / 2;
            scene.add(edges);

            mesh.updateMatrixWorld(); fullBox.expandByObject(mesh); hasData = true;
        }});

        const target = new THREE.Vector3();
        let theta = Math.PI / 4, phi = Math.PI / 3;

        if(hasData) {{
            fullBox.getCenter(target);
            const size = new THREE.Vector3(); fullBox.getSize(size);
            frustumSize = Math.max(size.x, size.y, size.z) * 1.8;
            camera.left = -frustumSize * aspect / 2;
            camera.right = frustumSize * aspect / 2;
            camera.top = frustumSize / 2;
            camera.bottom = -frustumSize / 2;
            camera.updateProjectionMatrix();
        }}

        let camDist = frustumSize * 3;

        function updateCamera() {{
            camera.position.x = target.x + camDist * Math.sin(phi) * Math.sin(theta);
            camera.position.y = target.y + camDist * Math.cos(phi);
            camera.position.z = target.z + camDist * Math.sin(phi) * Math.cos(theta);
            camera.lookAt(target);
        }}
        updateCamera();

        function animate() {{ requestAnimationFrame(animate); renderer.render(scene, camera); }}
        animate();

        let isDragging = false, px = 0, py = 0;
        container.onmousedown = e => {{ isDragging = true; px = e.clientX; py = e.clientY; e.preventDefault(); }};
        window.onmouseup = () => isDragging = false;
        container.onmousemove = e => {{
            if(!isDragging) return;
            const dx = e.clientX - px; const dy = e.clientY - py;
            px = e.clientX; py = e.clientY;
            theta -= dx * 0.01;
            phi -= dy * 0.01;
            phi = Math.max(0.1, Math.min(Math.PI - 0.1, phi));
            updateCamera();
        }};
        container.onwheel = e => {{
            const zoomFactor = e.deltaY > 0 ? 1.1 : 0.9;
            frustumSize *= zoomFactor;
            camera.left = -frustumSize * aspect / 2;
            camera.right = frustumSize * aspect / 2;
            camera.top = frustumSize / 2;
            camera.bottom = -frustumSize / 2;
            camera.updateProjectionMatrix();
            e.preventDefault();
        }};
    }}

    window.onload = () => {{
        setupViewer('viewer_main', [
            {{id: 'd-punch', color: 0xf1c40f}},
            {{id: 'd-guide', color: 0x00bcd4}},
            {{id: 'd-frame', color: 0xbdc3c7}},
            {{id: 'd-strip', color: 0x2ecc71}}
        ]);
        setupViewer('viewer_punch', [{{id: 'd-punch', color: 0xf1c40f}}]);
        setupViewer('viewer_guide', [{{id: 'd-guide', color: 0x00bcd4}}]);
    }};
</script>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"v29 Report Successfully Exported: {REPORT_PATH}")

