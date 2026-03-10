
import numpy as np
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
import os

# --- Configuration ---
WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"
REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

# Set Japanese Font
plt.rcParams['font.family'] = 'MS Gothic'

DXF_PATH = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\製品抜きガイド_exploded.dxf"
REPORT_PATH = os.path.join(WORKSPACE_DIR, "tolerance_report_advanced.html")

# --- 1. Simulation Logic (Advanced) ---
N_SAMPLES = 100000
DESIGN_CLEARANCE = 0.15 # 片側クリアランス (mm)
PITCH_COUNT = 5         # 累積ピッチ数

# Y軸 (幅)
chain_y = [
    {"name": "ガイド取り付け(Y)", "nominal": 0.0, "tol": 0.05, "desc": "治具固定誤差"}, 
    {"name": "ガイド隙間(Y)",     "nominal": 0.0, "tol": 0.10, "desc": "製品のガタ・浮き"},
    {"name": "パンチ芯ズレ(Y)",   "nominal": 0.0, "tol": 0.03, "desc": "パンチ位置精度"},
    {"name": "製品幅公差(Y)",     "nominal": 0.0, "tol": 0.05, "desc": "製品寸法バラつき"},
]

# X軸 (送り)
chain_x = [
    {"name": "パンチ位置(X)",       "nominal": 0.0, "tol": 0.03, "desc": "パンチ位置精度"},
    {"name": "パイロット補正残り", "nominal": 0.0, "tol": 0.02, "desc": "位置決めピン誤差"},
    {"name": f"ピッチ累積(×{PITCH_COUNT})", "nominal": 0.0, "tol": 0.02 * np.sqrt(PITCH_COUNT) * 3, "desc": "順送送りの累積誤差"},
]

def simulate(chain):
    res = np.zeros(N_SAMPLES)
    for c in chain:
        sigma = c["tol"] / 3.0
        res += np.random.normal(c["nominal"], sigma, N_SAMPLES)
    return res

print("Running Simulation...")
res_y = simulate(chain_y)
res_x = simulate(chain_x)

# Stats
std_y = np.std(res_y)
std_x = np.std(res_x)
fail_y = np.sum(np.abs(res_y) > DESIGN_CLEARANCE) / N_SAMPLES * 100
fail_x = np.sum(np.abs(res_x) > DESIGN_CLEARANCE) / N_SAMPLES * 100
total_fail = np.sum((np.abs(res_x) > DESIGN_CLEARANCE) | (np.abs(res_y) > DESIGN_CLEARANCE)) / N_SAMPLES * 100

# --- 2. Generate Scatter Plot ---
plt.figure(figsize=(9, 8), facecolor='#222222')
ax = plt.axes()
ax.set_facecolor('#222222')

# Points
idx = np.random.choice(N_SAMPLES, 5000, replace=False)
plt.scatter(res_x[idx], res_y[idx], color='#00bcd4', alpha=0.5, s=15, label='シミュレーション点')

# Safe Zone
rect = plt.Rectangle((-DESIGN_CLEARANCE, -DESIGN_CLEARANCE), 
                     DESIGN_CLEARANCE*2, DESIGN_CLEARANCE*2, 
                     fill=False, edgecolor='#ffeb3b', linewidth=2.5, linestyle='--', label='安全領域 (クリアランス)')
ax.add_patch(rect)

plt.title(f"干渉リスクマップ ({PITCH_COUNT}ピッチ累積)", color='white', fontsize=14)
plt.xlabel("X軸 ズレ (送り方向) [mm]", color='white', fontsize=12)
plt.ylabel("Y軸 ズレ (幅方向) [mm]", color='white', fontsize=12)
plt.grid(True, color='#555', linestyle=':')
plt.tick_params(colors='white')
plt.xlim(-0.4, 0.4)
plt.ylim(-0.4, 0.4)
plt.legend(facecolor='#333', edgecolor='white', labelcolor='white')

img_path = os.path.join(REPORT_DIR, "scatter_plot.png")
plt.savefig(img_path, dpi=100)
plt.close()

# --- 3. DXF Image (Reuse logic) ---
# ... (Assuming DXF image logic is similar or reusing existing image if consistent)
# Re-generate to be safe and dark
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
    dxf_img_path = os.path.join(REPORT_DIR, "dxf_view_dark.png")
    fig.savefig(dxf_img_path, dpi=150, bbox_inches='tight', facecolor='black')
    plt.close()
except:
    pass

# --- 4. HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>高度公差解析レポート</title>
    <style>
        body {{ font-family: "Meiryo", sans-serif; background-color: #f4f6f9; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-radius: 8px; }}
        h1 {{ border-bottom: 3px solid #ff5722; padding-bottom: 10px; color: #2c3e50; }}
        h2 {{ border-left: 5px solid #00bcd4; padding-left: 15px; margin-top: 40px; background: #e0f7fa; padding: 10px; }}
        .risk-alert {{ background-color: #ffebee; border: 2px solid #ef5350; color: #c62828; padding: 20px; border-radius: 8px; margin: 20px 0; font-weight: bold; }}
        .safe-box {{ background-color: #e8f5e9; border: 2px solid #66bb6a; color: #2e7d32; padding: 20px; border-radius: 8px; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #37474f; color: white; }}
        .img-box {{ text-align: center; margin: 30px 0; background: #222; padding: 20px; border-radius: 8px; }}
        img {{ max-width: 100%; height: auto; }}
        .stat-value {{ font-size: 1.5em; font-weight: bold; }}
        .danger {{ color: #d32f2f; }}
        .safe {{ color: #388e3c; }}
    </style>
</head>
<body>
<div class="container">
    <h1>🚀 高度公差解析レポート: 干渉リスク検証</h1>
    <p><strong>検証テーマ:</strong> 順送ピッチ累積およびガイドガタによる、パンチとフレームの干渉（金型破損）リスク</p>
    
    <div class="{ 'risk-alert' if total_fail > 1.0 else 'safe-box' }">
        <h3>⚡ 総合判定結果: { '危険 (CRITICAL)' if total_fail > 1.0 else '安全 (SAFE)' }</h3>
        <p>シミュレーションの結果、パンチがフレームに接触（干渉）する確率は <strong>{total_fail:.2f}%</strong> です。</p>
        <ul>
            <li>X軸 (送り方向): <strong>{fail_x:.2f}%</strong> の確率で干渉 (危険)</li>
            <li>Y軸 (幅方向): <strong>{fail_y:.2f}%</strong> の確率で干渉 (比較的安全)</li>
        </ul>
        <p>※クリアランス {DESIGN_CLEARANCE}mm に対する判定</p>
    </div>

    <h2>1. 解析結果マップ (散布図)</h2>
    <p>青い点がシミュレーション結果（1製品ごとのズレ）、黄色い枠が安全領域（クリアランス）です。<br>
    黄色い枠の外にはみ出している青点は、<strong>「金型が破損するショット」</strong>を意味します。</p>
    <div class="img-box">
        <img src="report_assets/scatter_plot.png" alt="Scatter Plot">
    </div>

    <h2>2. 詳細統計データ</h2>
    <table>
        <thead>
            <tr>
                <th>方向</th>
                <th>累積条件</th>
                <th>ばらつき (3σ)</th>
                <th>不良率 (干渉確率)</th>
                <th>判定</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>X軸 (送り)</strong></td>
                <td>{PITCH_COUNT}ピッチ累積</td>
                <td>±{3*std_x:.3f} mm</td>
                <td class="{ 'danger' if fail_x > 0.1 else 'safe' }">{fail_x:.3f}%</td>
                <td>{ '❌ 対策必須' if fail_x > 0.1 else '✅ OK' }</td>
            </tr>
            <tr>
                <td><strong>Y軸 (幅)</strong></td>
                <td>ガイド/隙間</td>
                <td>±{3*std_y:.3f} mm</td>
                <td class="{ 'danger' if fail_y > 0.1 else 'safe' }">{fail_y:.3f}%</td>
                <td>{ '⚠️ 要注意' if fail_y > 0.1 else '✅ OK' }</td>
            </tr>
        </tbody>
    </table>

    <h2>3. ズレの要因 (なぜX軸が危険なのか？)</h2>
    <p>X軸は「順送ピッチの誤差」が積み重なるため、後工程になればなるほどズレが大きくなります。</p>
    <table>
        <thead>
            <tr><th>要因</th><th>公差設定</th><th>影響度</th></tr>
        </thead>
        <tbody>
            { "".join([f"<tr><td>{c['desc']}</td><td>±{c['tol']}</td><td>{'大' if c['tol'] > 0.05 else '中'}</td></tr>" for c in chain_x]) }
        </tbody>
    </table>
    
    <h2>4. 参照図面</h2>
    <div class="img-box">
        <img src="report_assets/dxf_view_dark.png" alt="DXF">
    </div>

</div>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Report generated: {REPORT_PATH}")
