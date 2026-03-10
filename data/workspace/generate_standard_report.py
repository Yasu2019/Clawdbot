import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import os
import base64

# --- Configuration ---
WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"
REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

# Set Japanese Font
plt.rcParams['font.family'] = 'MS Gothic'

DXF_PATH = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\製品抜きガイド_exploded.dxf"
REPORT_PATH = os.path.join(WORKSPACE_DIR, "tolerance_report.html")

# --- 1. Simulation Logic (Refined) ---
N_SAMPLES = 100000

# Explicit Dimensions (Design Intent)
DIM_FRAME_WIDTH = 32.00 # 図面より読み取り (短冊フレーム内幅 - 推定)
DIM_PUNCH_WIDTH = 31.70 # パンチ幅 (片側0.15mmクリアランス設定)
DESIGN_CLEARANCE = (DIM_FRAME_WIDTH - DIM_PUNCH_WIDTH) / 2 # 0.15mm
PITCH_COUNT = 5         # 累積ピッチ数

# User Provided Data (X-axis)
val_feed_acc = 0.011
val_pitch_acc = 0.01152
step_error_3sigma = np.sqrt(val_feed_acc**2 + val_pitch_acc**2)
accum_error_3sigma = step_error_3sigma * np.sqrt(PITCH_COUNT) # Random walk assumption

# --- Define Tolerance Chains (Separated) ---

# Y Axis (Width)
chain_y_pos = [
    {"name": "ガイド取り付け位置(Y)", "nominal": 0.0, "tol": 0.05, "desc": "治具固定誤差 (位置)"}, 
    {"name": "ガイド-製品隙間(Y)",     "nominal": 0.0, "tol": 0.10, "desc": "製品のガタ・浮き (位置)"},
    {"name": "パンチ芯ズレ(Y)",       "nominal": 0.0, "tol": 0.03, "desc": "プレス機の位置決め誤差 (位置)"},
]
chain_y_size = [
    {"name": "パンチ幅公差(Y)",       "nominal": 0.0, "tol": 0.02, "desc": "パンチ寸法 (サイズ)"},
    {"name": "製品幅公差(Y)",         "nominal": 0.0, "tol": 0.05, "desc": "製品寸法 (サイズ)"},
]

# X Axis (Feed)
chain_x_pos = [
    {"name": "パンチ位置(X)",         "nominal": 0.0, "tol": 0.03, "desc": "プレス機の位置決め誤差"},
    {"name": "パイロット補正残り",   "nominal": 0.0, "tol": 0.02, "desc": "位置決めピン誤差"},
    {"name": f"順送ピッチ累積(×{PITCH_COUNT})", "nominal": 0.0, "tol": accum_error_3sigma, "desc": f"送り誤差 (精度3σ={val_feed_acc}, ピッチ3σ={val_pitch_acc})"},
]
chain_x_size = [
    {"name": "パンチ厚み公差(X)",     "nominal": 0.0, "tol": 0.02, "desc": "パンチ寸法 (サイズ)"},
]

def simulate_advanced(chain_pos, chain_size, n_samples):
    # 1. Position Deviation (Center Shift)
    pos_dev = np.zeros(n_samples)
    for c in chain_pos:
        sigma = c["tol"] / 3.0
        pos_dev += np.random.normal(c["nominal"], sigma, n_samples)
    
    # 2. Effective Clearance Calculation
    # Clearnace = DesignClearance - (SizeVariation / 2)
    # SizeVariation is derived from Width Tolerance T. 
    # If Width varies by N(0, (T/3)^2), Half-width varies by N(0, (T/6)^2)
    eff_clearance = np.full(n_samples, DESIGN_CLEARANCE)
    
    for c in chain_size:
        sigma_w = c["tol"] / 3.0
        # Random variation in full width
        width_var = np.random.normal(0, sigma_w, n_samples)
        # Impact on single-side clearance is half of width variation
        # Assuming worst direction (clearance reduction) is random
        eff_clearance -= (width_var / 2.0)
    
    return pos_dev, eff_clearance

print("Running Simulation...")
res_y_dev, res_y_clr = simulate_advanced(chain_y_pos, chain_y_size, N_SAMPLES)
res_x_dev, res_x_clr = simulate_advanced(chain_x_pos, chain_x_size, N_SAMPLES)

# Analysis
fail_y = np.sum(np.abs(res_y_dev) > res_y_clr) / N_SAMPLES * 100
fail_x = np.sum(np.abs(res_x_dev) > res_x_clr) / N_SAMPLES * 100
total_fail = np.sum((np.abs(res_x_dev) > res_x_clr) | (np.abs(res_y_dev) > res_y_clr)) / N_SAMPLES * 100

# Data for Plotting (Scatter uses deviations)
res_x = res_x_dev
res_y = res_y_dev
chain_y = chain_y_pos + chain_y_size
chain_x = chain_x_pos + chain_x_size

# --- 2. Generate Graphs ---

def save_plot(filename, facecolor='white'):
    path = os.path.join(REPORT_DIR, filename)
    plt.savefig(path, dpi=100, bbox_inches='tight', facecolor=facecolor)
    plt.close()

# Scatter Plot
plt.figure(figsize=(9, 8), facecolor='#222222')
ax = plt.axes()
ax.set_facecolor('#222222')
idx = np.random.choice(N_SAMPLES, 5000, replace=False)
plt.scatter(res_x[idx], res_y[idx], color='#00bcd4', alpha=0.5, s=15, label='シミュレーション点 (ズレ量)')
# Note: Since clearance varies, we show the MEAN clearance as the box
rect = plt.Rectangle((-DESIGN_CLEARANCE, -DESIGN_CLEARANCE), 
                     DESIGN_CLEARANCE*2, DESIGN_CLEARANCE*2, 
                     fill=False, edgecolor='#ffeb3b', linewidth=2.5, linestyle='--', label=f'設計クリアランス (±{DESIGN_CLEARANCE}mm)')
ax.add_patch(rect)
plt.title(f"干渉リスクマップ ({PITCH_COUNT}ピッチ累積)", color='white', fontsize=14)
plt.xlabel("X軸 位置ズレ [mm]", color='white', fontsize=12)
plt.ylabel("Y軸 位置ズレ [mm]", color='white', fontsize=12)
plt.grid(True, color='#555', linestyle=':')
plt.tick_params(colors='white')
plt.xlim(-0.4, 0.4)
plt.ylim(-0.4, 0.4)
plt.legend(facecolor='#333', edgecolor='white', labelcolor='white', loc='upper right')
save_plot("scatter_plot.png", facecolor='#222222')

# Histogram Y
plt.figure(figsize=(6, 4))
plt.hist(res_y, bins=50, color='#3498db', alpha=0.7, edgecolor='black', label='位置ズレ分布')
plt.axvline(DESIGN_CLEARANCE, color='r', linestyle='--', label='設計クリアランス')
plt.axvline(-DESIGN_CLEARANCE, color='r', linestyle='--')
plt.title(f"Y軸(幅) ズレ分布 - 不良率 {fail_y:.2f}%")
plt.legend()
save_plot("histogram_y.png")

# Sensitivity Y (Use Squared Sigma for Contribution)
labels_y = [c['name'] for c in chain_y]
sizes_y = [(c['tol']/3.0)**2 for c in chain_y]
plt.figure(figsize=(5, 5))
plt.pie(sizes_y, labels=labels_y, autopct='%1.1f%%', startangle=90)
plt.title("Y軸 寄与率 (分散比)")
save_plot("sensitivity_y.png")

# Histogram X
plt.figure(figsize=(6, 4))
plt.hist(res_x, bins=50, color='#e74c3c', alpha=0.7, edgecolor='black', label='位置ズレ分布')
plt.axvline(DESIGN_CLEARANCE, color='r', linestyle='--', label='設計クリアランス')
plt.axvline(-DESIGN_CLEARANCE, color='r', linestyle='--')
plt.title(f"X軸(送り) ズレ分布 - 不良率 {fail_x:.2f}%")
plt.legend()
save_plot("histogram_x.png")

# Sensitivity X
labels_x = [c['name'] for c in chain_x]
sizes_x = [(c['tol']/3.0)**2 for c in chain_x]
plt.figure(figsize=(5, 5))
plt.pie(sizes_x, labels=labels_x, autopct='%1.1f%%', startangle=90)
plt.title("X軸 寄与率 (分散比)")
save_plot("sensitivity_x.png")

# DXF (Annotated) - Reuse previous logic logic or simple one
print("Generating Annotated DXF...")
try:
    doc = ezdxf.readfile(DXF_PATH)
    msp = doc.modelspace()
    fig = plt.figure(figsize=(10, 6), facecolor='black')
    ax = fig.add_axes([0, 0, 1, 1], facecolor='black')
    ctx = RenderContext(doc)
    out = MatplotlibBackend(ax)
    Frontend(ctx, out).draw_layout(msp, finalize=True)
    ax.autoscale()
    ax.set_aspect('equal')
    plt.axis('off')
    xlim = ax.get_xlim()
    ylim = ax.get_ylim()
    w = xlim[1] - xlim[0]
    h = ylim[1] - ylim[0]
    center_x = (xlim[0] + xlim[1]) / 2
    center_y = (ylim[0] + ylim[1]) / 2
    props = dict(boxstyle='round', facecolor='#ffeb3b', alpha=0.9)
    ax.annotate('X軸: 順送ピッチ累積', xy=(center_x, center_y), xytext=(center_x, ylim[1] - h*0.1),
                arrowprops=dict(facecolor='#ffeb3b', width=2, headwidth=8, shrink=0.05),
                color='black', fontsize=11, ha='center', bbox=props)
    ax.annotate('Y軸: ガイド幅 / 隙間', xy=(xlim[1] - w*0.2, center_y), xytext=(xlim[1] - w*0.05, center_y),
                arrowprops=dict(facecolor='#ffeb3b', width=2, headwidth=8, shrink=0.05),
                color='black', fontsize=11, ha='left', bbox=props)
    save_plot("dxf_annotated.png", facecolor='black')
except Exception as e:
    print(f"DXF Error: {e}")

import statistics

# --- Additional Calculations ---

def calculate_cpk(mean, sigma, lsl, usl):
    # Cp = (USL - LSL) / (6 * sigma)
    # Cpk = min((USL - mean) / (3 * sigma), (mean - LSL) / (3 * sigma))
    
    cpu = (usl - mean) / (3 * sigma) if usl is not None else float('inf')
    cpl = (mean - lsl) / (3 * sigma) if lsl is not None else float('inf')
    cpk = min(cpu, cpl)
    return cpk

# --- Plotting Functions ---

def plot_tornado(chains, filename, title="Sensitivity Analysis"):
    # Flatten chains
    all_items = []
    for chain in chains:
        all_items.extend(chain)
        
    data = []
    for item in all_items:
        # Effect = Tol (assuming f=1, vec=1 for worst case add-up or sensitivity study)
        effect = item["tol"] 
        data.append((item["name"], effect))
    
    # Sort
    data.sort(key=lambda x: x[1], reverse=False)
    
    names = [x[0] for x in data]
    effects = [x[1] for x in data]
    
    plt.figure(figsize=(8, len(names)*0.5 + 2))
    plt.barh(names, effects, color='skyblue', edgecolor='navy', alpha=0.7)
    plt.xlabel("Effect (Tolerance Magnitude)")
    plt.title(f"Tornado Chart: {title}")
    plt.grid(True, linestyle='--', alpha=0.5)
    
    for i, v in enumerate(effects):
        plt.text(v, i, f" {v:.4f}", va='center', fontsize=9)
        
    save_plot(filename)

def plot_qq(data, filename):
    plot_data = np.sort(np.random.choice(data, min(len(data), 1000), replace=False))
    n = len(plot_data)
    try:
        norm = statistics.NormalDist(0, 1)
        theoretical_q = [norm.inv_cdf((i + 0.5) / n) for i in range(n)]
    except:
        return

    mean = np.mean(plot_data)
    std = np.std(plot_data)
    if std == 0: std = 1e-9
    z_scores = (plot_data - mean) / std
    
    plt.figure(figsize=(6, 6))
    plt.scatter(theoretical_q, z_scores, alpha=0.5, color='blue', edgecolor='k', s=20)
    plt.plot([-3, 3], [-3, 3], 'r--', label="Normal Reference")
    plt.xlabel("Theoretical Quantiles")
    plt.ylabel("Sample Quantiles")
    plt.title("Normal Q-Q Plot")
    plt.grid(True)
    plt.legend()
    save_plot(filename)

# --- Execute Analysis ---

# Cpk for Y (Width/Clearance)
# LSL = -DESIGN_CLEARANCE, USL = DESIGN_CLEARANCE (relative to deviation 0)
mean_y = np.mean(res_y)
std_y = np.std(res_y)
cpk_y = calculate_cpk(mean_y, std_y, -DESIGN_CLEARANCE, DESIGN_CLEARANCE)

# Plots
plot_qq(res_y, "qq_y.png")
plot_tornado([chain_y_pos, chain_y_size], "tornado_y.png", "Y-Axis Contributors")
# Range comparison? For standard report, we have complex chains. Maybe skip for now or sum tolerances manually.
# Let's sum tolerances for Worst Case Y
wc_y = sum([c['tol'] for c in chain_y_pos + chain_y_size])
rss_y = np.sqrt(sum([(c['tol']/3)**2 for c in chain_y_pos + chain_y_size])) * 3
# Range plot
def plot_range(mean, wc, rss, filename):
    plt.figure(figsize=(8, 3))
    plt.barh(0, 2*rss, left=mean-rss, height=0.5, color='green', alpha=0.6, label='RSS')
    plt.barh(1, 2*wc, left=mean-wc, height=0.5, color='red', alpha=0.6, label='Worst Case')
    plt.yticks([0, 1], ["RSS", "Worst Case"])
    plt.xlabel("Deviation [mm]")
    plt.title("Range Comparison")
    plt.grid(True, axis='x')
    plt.legend()
    save_plot(filename)

plot_range(mean_y, wc_y, rss_y, "range_y.png")


# Base64 Encode
def get_base64_image(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_scatter = get_base64_image("scatter_plot.png")
img_hist_x = get_base64_image("histogram_x.png")
img_sens_x = get_base64_image("sensitivity_x.png")
img_hist_y = get_base64_image("histogram_y.png")
img_sens_y = get_base64_image("sensitivity_y.png")
img_dxf = get_base64_image("dxf_annotated.png")
img_qq_y = get_base64_image("qq_y.png")
img_tornado_y = get_base64_image("tornado_y.png")
img_range_y = get_base64_image("range_y.png")

# --- HTML Generation with Q&A ---
html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>公差解析レポート (詳細版)</title>
    <style>
        body {{ font-family: "Meiryo", sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        h1 {{ border-bottom: 3px solid #ff5722; padding-bottom: 10px; color: #2c3e50; }}
        h2 {{ border-left: 5px solid #00bcd4; padding-left: 15px; margin-top: 40px; background: #e0f7fa; padding: 10px; }}
        h3 {{ margin-top: 20px; color: #455a64; border-bottom: 1px solid #ddd; padding-bottom: 5px; }}
        .risk-alert {{ background-color: #ffebee; border: 2px solid #ef5350; color: #c62828; padding: 20px; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
        .safe-box {{ background-color: #e8f5e9; border: 2px solid #66bb6a; color: #2e7d32; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 0.9em; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #37474f; color: white; }}
        .img-box {{ text-align: center; margin: 20px 0; padding: 10px; border: 1px solid #eee; }}
        .dark-bg {{ background: #222; }}
        img {{ max-width: 100%; height: auto; }}
        .row {{ display: flex; gap: 20px; flex-wrap: wrap; align-items: flex-start; }}
        .col {{ flex: 1; min-width: 300px; }}
        .math-box {{ background: #f8f9fa; padding: 15px; border-left: 4px solid #607d8b; font-family: "Consolas", monospace; margin: 10px 0; }}
        .grid-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .img-card {{ background: white; padding: 10px; border: 1px solid #eee; border-radius: 5px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 公差解析レポート (標準版)</h1>
    <p><strong>検証テーマ:</strong> 順送ピッチ累積およびガイドガタによる干渉リスク</p>
    
    <div class="{ 'risk-alert' if total_fail > 1.0 else 'safe-box' }">
        <h3>⚡ 総合判定: { '危険 (CRITICAL)' if total_fail > 1.0 else '安全 (SAFE)' }</h3>
        <p>不良率: <strong>{total_fail:.2f}%</strong> (Cpk_Y: {cpk_y:.2f})</p>
        <p>※設計クリアランス: <strong>±{DESIGN_CLEARANCE}mm</strong></p>
    </div>

    <h2>1. 詳細分析 (Y軸: 幅/ガタ)</h2>
    <div class="grid-container">
        <div class="img-card">
            <h4>ヒストグラム & 規格</h4>
            <img src="{img_hist_y}">
        </div>
        <div class="img-card">
            <h4>感度分析 (トルネード)</h4>
            <img src="{img_tornado_y}">
        </div>
        <div class="img-card">
            <h4>正規性確認 (Q-Qプロット)</h4>
            <img src="{img_qq_y}">
        </div>
        <div class="img-card">
            <h4>レンジ比較 (RSS vs WC)</h4>
            <img src="{img_range_y}">
        </div>
    </div>

    <h2>2. X軸・散布図</h2>
    <div class="row">
        <div class="col">
            <h3>X軸 (送り方向)</h3>
            <img src="{img_hist_x}">
        </div>
        <div class="col">
            <h3>総合リスクマップ</h3>
            <div class="img-box dark-bg">
                <img src="{img_scatter}">
            </div>
        </div>
    </div>

    <h2>3. 参照図面</h2>
    <div class="img-box dark-bg">
        <img src="{img_dxf}">
    </div>

    <h2>4. 設計審査 Q&A</h2>
    <div class="math-box" style="border-left-color: #2ecc71;">
        <strong>Q. Cpkが低い場合の対策は？</strong><br>
        A. トルネードチャートで最も影響の大きい項目（一番上のバー）を確認し、その公差を厳しくするか、あるいは設計クリアランス（平均値）をシフトさせることで改善できます。
    </div>
</div>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Report generated: {REPORT_PATH}")
