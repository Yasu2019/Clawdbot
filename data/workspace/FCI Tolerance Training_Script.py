import numpy as np
import matplotlib.pyplot as plt
import os
import base64

# --- Configuration ---
WORKSPACE_DIR = r"D:\Clawdbot_Docker_20260125\data\workspace"
REPORT_DIR = os.path.join(WORKSPACE_DIR, "report_assets")
if not os.path.exists(REPORT_DIR):
    os.makedirs(REPORT_DIR)

# Set Japanese Font
plt.rcParams['font.family'] = 'MS Gothic'

REPORT_PATH = os.path.join(WORKSPACE_DIR, "tuning_fork_report.html")

# --- 1. Simulation Logic (Tuning Fork Example) ---
N_SAMPLES = 100000

# Constants
K_FACTOR = 1.217 # Tip movement ratio

# Parameters (from PDF Pg.48)
# Name, Nominal, Tol(±), GeometricFactor(f), Vector(+/-)
params = [
    {"name": "Wc (Housing Width)",   "nom": 1.635, "tol": 0.025, "f": 0.5,         "vec": 1,  "desc": "Case Width"},
    {"name": "T (Fork Thickness)",   "nom": 1.000, "tol": 0.050, "f": 0.5,         "vec": -1, "desc": "Fork Thickness"},
    {"name": "G (Gap / Position)",   "nom": 0.200, "tol": 0.050, "f": 0.5*K_FACTOR, "vec": 1,  "desc": "Gap pos (amplified by K)"},
    {"name": "P (Pin Position)",     "nom": 0.495, "tol": 0.015, "f": 0.5*K_FACTOR, "vec": -1, "desc": "Pin pos (amplified by K)"},
    {"name": "pt (Post Position?)",  "nom": 0.000, "tol": 0.050, "f": 0.5,         "vec": 1,  "desc": "Tab Position (Dev Only)"},
]

def simulate_tuning_fork():
    # Gap = Sum ( Vec * f * Val )
    # Val ~ N(Nom, (Tol/3)^2)
    
    gap_samples = np.zeros(N_SAMPLES)
    
    # Validation Calculation (Mean)
    calc_mean = 0.0
    
    for p in params:
        sigma = p["tol"] / 3.0
        val = np.random.normal(p["nom"], sigma, N_SAMPLES)
        
        term = p["vec"] * p["f"] * val
        gap_samples += term
        
        calc_mean += p["vec"] * p["f"] * p["nom"]

    return gap_samples, calc_mean

print("Running Simulation (Tuning Fork)...")
res_gap, mean_val = simulate_tuning_fork()

# PDF Result for Comparison
# Nominal Gap = 0.138
# Worst Case = ±0.1021 (Sum of f*T)
# RSS = ±0.049 (Sqrt of Sum (f*T)^2 ? No, PDF says SqRt=0.049. let's check)

# My Calculation Check
print(f"Calculated Mean: {mean_val:.4f}")
worst_case_tol = sum([p["f"] * p["tol"] for p in params])
rss_tol_3sigma = np.sqrt(sum([(p["f"] * p["tol"])**2 for p in params])) # Note: PDF might use Tol as 3sigma directly?
# PDF Table: (fT)^2 sums to 0.002. Sqrt(0.002) = 0.0447. Close to 0.049?
# Wait, PDF says SqRt = 0.049. 0.049^2 = 0.0024.
# Let's re-read PDF table.
# Wc: fT=0.0125, sq=0.000156. Table says 2E-04 (0.0002). Rounding?
# T: fT=0.025, sq=0.000625. Table says 6E-04.
# G: fT=0.0304, sq=0.000924. Table says 9E-04.
# pt: fT=0.025, sq=0.000625. Table says 6E-04.
# P: fT=0.0091, sq=0.000082. Table says 8E-05.
# Sum Sq = 0.0002+0.0006+0.0009+0.0006+0.00008 = 0.00238.
# Sqrt(0.00238) = 0.0487 ~ 0.049.
# Matches! So my assumption of fT is correct.
# And RSS Tol = 0.049.

print(f"Worst Case Tol (±): {worst_case_tol:.4f}")
print(f"RSS Tol (±3σ): {rss_tol_3sigma:.4f}")

# Stats
# Failure condition: Gap < 0 ? 
# PDF says "The contact will not protrude in the window to stub against the pin."
# Implies Gap > 0 is GOOD.
fail_rate = np.sum(res_gap < 0) / N_SAMPLES * 100
min_gap = np.min(res_gap)
max_gap = np.max(res_gap)

print(f"Failure Rate (Gap < 0): {fail_rate:.2f}%")

# --- 2. Generate Graphs ---

def save_plot(filename, facecolor='white'):
    path = os.path.join(REPORT_DIR, filename)
    plt.savefig(path, dpi=100, bbox_inches='tight', facecolor=facecolor)
    plt.close()

# Histogram
plt.figure(figsize=(8, 5))
plt.hist(res_gap, bins=100, color='#9b59b6', alpha=0.7, edgecolor='black', label='Gap Distribution')
plt.axvline(0, color='r', linestyle='--', linewidth=2, label='Interference Limit (0.0)')
plt.axvline(mean_val, color='g', linestyle='-', linewidth=2, label=f'Mean ({mean_val:.3f})')
plt.xlabel("Gap [mm]")
plt.ylabel("Frequency")
plt.title(f"Tuning Fork Gap Analysis\nRSS(3σ)=±{rss_tol_3sigma:.3f}, WC=±{worst_case_tol:.3f}")
plt.legend()
plt.grid(True, alpha=0.3)
save_plot("tf_histogram.png")

# Sensitivity
labels = [p['name'] for p in params]
sizes = [(p["f"] * p["tol"])**2 for p in params] # Contribution based on variance (RSS)
plt.figure(figsize=(6, 6))
plt.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90, colors=plt.cm.Pastel1.colors)
plt.title("Contribution to Variation (Variance)")
save_plot("tf_sensitivity.png")

# Base64 Encode
def get_base64_image(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

img_hist = get_base64_image("tf_histogram.png")
img_sens = get_base64_image("tf_sensitivity.png")

# --- HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="en"> <!-- English as generic sample -->
<head>
    <meta charset="UTF-8">
    <title>Tolerance Analysis: Tuning Fork Example</title>
    <style>
        body {{ font-family: "Segoe UI", sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 900px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-radius: 8px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .summary-box {{ background: #e8f4fd; padding: 20px; border-radius: 5px; border-left: 5px solid #3498db; margin: 20px 0; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: center; }}
        th {{ background: #34495e; color: white; }}
        .img-container {{ text-align: center; margin: 30px 0; }}
        img {{ max-width: 100%; box-shadow: 0 2px 5px rgba(0,0,0,0.2); }}
    </style>
</head>
<body>
<div class="container">
    <h1>Tolerance Analysis Report: Tuning Fork</h1>
    <p>Based on <strong>FCI Tolerance Training.pdf (Page 48)</strong>.</p>
    
    <div class="summary-box">
        <h3>Analysis Result</h3>
        <p><strong>Mean Gap:</strong> {mean_val:.4f} mm</p>
        <p><strong>RSS Tolerance (3σ):</strong> ±{rss_tol_3sigma:.4f} mm</p>
        <p><strong>Worst Case Tolerance:</strong> ±{worst_case_tol:.4f} mm</p>
        <p><strong>Theoretical Min Gap (RSS):</strong> {mean_val - rss_tol_3sigma:.4f} mm</p>
        <p><strong>Failure Rate (Gap < 0):</strong> {fail_rate:.4f}%</p>
    </div>

    <h2>1. Parameters (Input)</h2>
    <p><strong>Equation:</strong> Gap = 0.5*Wc - 0.5*T - 0.5*K*P + 0.5*K*G + 0.5*pt</p>
    <p>(Where K = {K_FACTOR})</p>
    <table>
        <tr><th>Component</th><th>Nominal</th><th>Tolerance (±)</th><th>Geometric Factor (f)</th><th>Vector</th></tr>
        { "".join([f"<tr><td>{p['name']}</td><td>{p['nom']}</td><td>{p['tol']}</td><td>{p['f']:.3f}</td><td>{p['vec']}</td></tr>" for p in params]) }
    </table>

    <h2>2. Distributions & Risk</h2>
    <div class="img-container">
        <img src="{img_hist}">
    </div>
    <div class="img-container">
        <img src="{img_sens}">
    </div>

    <h2>3. Conclusion</h2>
    <p>The Monte Carlo simulation confirms the PDF's analytical result (RSS Gap ≈ 0.138 ± 0.049).</p>
    <p>With a minimum gap of approx. {mean_val - rss_tol_3sigma:.3f}mm (RSS limit), the assembly is <strong>SAFE</strong> from interference.</p>

</div>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Report generated: {REPORT_PATH}")
