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

def plot_tornado(params, filename):
    # Sort by contribution magnitude
    # Contribution = (f * Tol)^2 for RSS, or just f*Tol for worst case sensitivity?
    # Usually Tornado shows "Swing": +Effect and -Effect.
    # Effect = f * Tol
    
    data = []
    for p in params:
        effect = abs(p["f"] * p["tol"])
        data.append((p["name"], effect))
    
    # Sort by effect
    data.sort(key=lambda x: x[1], reverse=False) # Ascending for barh
    
    names = [x[0] for x in data]
    effects = [x[1] for x in data]
    
    plt.figure(figsize=(8, 6))
    plt.barh(names, effects, color='skyblue', edgecolor='navy', alpha=0.7)
    plt.xlabel("Effect Magnitude (± mm) [f * Tol]")
    plt.title("Tornado Chart: Sensitivity Analysis")
    plt.grid(True, linestyle='--', alpha=0.5)
    plt.axvline(0, color='k', linewidth=0.5)
    
    # Add values
    for i, v in enumerate(effects):
        plt.text(v, i, f" {v:.4f}", va='center', fontsize=9)
        
    save_plot(filename)

def plot_qq(data, filename):
    # Sample down if too large
    plot_data = np.sort(np.random.choice(data, min(len(data), 1000), replace=False))
    n = len(plot_data)
    
    # Theoretical quantiles (Standard Normal)
    # Uses statistics.NormalDist if Python 3.8+
    try:
        norm = statistics.NormalDist(0, 1)
        theoretical_q = [norm.inv_cdf((i + 0.5) / n) for i in range(n)]
    except:
        # Fallback if statistics module is too old or missing (unlikely)
        # Simple approximation or skip
        print("Warning: statistics.NormalDist not available. Skipping Q-Q plot details.")
        return

    # Normalize data
    mean = np.mean(plot_data)
    std = np.std(plot_data)
    z_scores = (plot_data - mean) / std
    
    plt.figure(figsize=(6, 6))
    plt.scatter(theoretical_q, z_scores, alpha=0.5, color='blue', edgecolor='k', s=20)
    plt.plot([-3, 3], [-3, 3], 'r--', label="Normal Reference") # y=x line
    plt.xlabel("Theoretical Quantiles (Z-score)")
    plt.ylabel("Sample Quantiles (Z-score)")
    plt.title("Normal Probability Plot (Q-Q Plot)")
    plt.grid(True)
    plt.legend()
    save_plot(filename)

def plot_range_comparison(mean, wc_tol, rss_tol, filename):
    plt.figure(figsize=(8, 4))
    
    y = [0, 1]
    labels = ["RSS (Statistical)", "Worst Case"]
    
    # RSS Range
    plt.barh(0, 2*rss_tol, left=mean-rss_tol, height=0.5, color='green', alpha=0.6, label='RSS (±3σ)')
    # WC Range
    plt.barh(1, 2*wc_tol, left=mean-wc_tol, height=0.5, color='red', alpha=0.6, label='Worst Case')
    
    plt.yticks(y, labels)
    plt.xlabel("Gap Dimension [mm]")
    plt.title("Tolerance Range Comparison: RSS vs Worst Case")
    plt.axvline(mean, color='k', linestyle=':', label='Mean')
    plt.grid(True, axis='x', linestyle='--')
    plt.legend()
    
    # Add text
    plt.text(mean-rss_tol, 0, f"{mean-rss_tol:.3f} ", va='center', ha='right', fontsize=9)
    plt.text(mean+rss_tol, 0, f" {mean+rss_tol:.3f}", va='center', ha='left', fontsize=9)
    plt.text(mean-wc_tol, 1, f"{mean-wc_tol:.3f} ", va='center', ha='right', fontsize=9)
    plt.text(mean+wc_tol, 1, f" {mean+wc_tol:.3f}", va='center', ha='left', fontsize=9)
    
    save_plot(filename)

# --- Execute Calculations ---

# Cpk (Assuming LSL=0)
lsl_spec = 0.0
usl_spec = None # One-sided
cpk_val = calculate_cpk(mean_val, rss_tol_3sigma/3, lsl_spec, usl_spec) # Sigma = Tol/3

# Generate Plots
plot_qq(res_gap, "tf_qq.png")
plot_tornado(params, "tf_tornado.png")
plot_range_comparison(mean_val, worst_case_tol, rss_tol_3sigma, "tf_range.png")

# Base64 Encode
def get_base64_image(filename):
    path = os.path.join(REPORT_DIR, filename)
    if not os.path.exists(path): return ""
    with open(path, "rb") as f:
        return f"data:image/png;base64,{base64.b64encode(f.read()).decode('utf-8')}"

# Start HTML Generation
img_hist = get_base64_image("tf_histogram.png")
img_sens = get_base64_image("tf_sensitivity.png")
img_qq = get_base64_image("tf_qq.png")
img_tornado = get_base64_image("tf_tornado.png")
img_range = get_base64_image("tf_range.png")


# --- HTML Generation ---
html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Tolerance Analysis: Tuning Fork Example</title>
    <style>
        body {{ font-family: "Segoe UI", sans-serif; background-color: #f0f2f5; color: #333; margin: 0; padding: 20px; }}
        .container {{ max-width: 1000px; margin: 0 auto; background: white; padding: 40px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); border-radius: 8px; }}
        h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
        .section {{ margin-bottom: 40px; }}
        .summary-box {{ background: #e8f4fd; padding: 20px; border-radius: 5px; border-left: 5px solid #3498db; display: flex; flex-wrap: wrap; justify-content: space-between; }}
        .summary-item {{ width: 45%; margin-bottom: 10px; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ padding: 10px; border: 1px solid #ddd; text-align: center; }}
        th {{ background: #34495e; color: white; }}
        .grid-container {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
        .img-card {{ background: white; padding: 10px; border: 1px solid #eee; border-radius: 5px; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }}
        .img-card h4 {{ margin: 0 0 10px 0; color: #555; }}
        img {{ max-width: 100%; height: auto; }}
        .badge {{ display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 0.8em; font-weight: bold; color: white; }}
        .badge-safe {{ background-color: #27ae60; }}
        .badge-risk {{ background-color: #e74c3c; }}
    </style>
</head>
<body>
<div class="container">
    <h1>Tolerance Analysis Report: Tuning Fork</h1>
    <p>Based on <strong>FCI Tolerance Training.pdf (Page 48)</strong>. Normalized Standard Output.</p>
    
    <div class="section">
        <h2>1. Executive Summary</h2>
        <div class="summary-box">
            <div class="summary-item"><strong>Mean Gap:</strong> {mean_val:.4f} mm</div>
            <div class="summary-item"><strong>RSS Tolerance (3σ):</strong> ±{rss_tol_3sigma:.4f} mm</div>
            <div class="summary-item"><strong>Worst Case Tolerance:</strong> ±{worst_case_tol:.4f} mm</div>
            <div class="summary-item"><strong>Process Capability (Cpk):</strong> {cpk_val:.2f} (LSL={lsl_spec})</div>
            <div class="summary-item"><strong>Failure Rate (Gap < 0):</strong> {fail_rate:.4f}%</div>
            <div class="summary-item"><strong>Judgment:</strong> <span class="badge { 'badge-safe' if cpk_val >= 1.33 else 'badge-risk' }">{ 'SAFE' if cpk_val >= 1.33 else 'CAUTION' }</span></div>
        </div>
    </div>

    <div class="section">
        <h2>2. Visual Analysis</h2>
        
        <div class="grid-container">
            <!-- Histogram -->
            <div class="img-card">
                <h4>Distribution & Overlay</h4>
                <img src="{img_hist}">
            </div>
            
            <!-- Range Comparison -->
            <div class="img-card">
                <h4>Interval Comparison (RSS vs WC)</h4>
                <img src="{img_range}">
            </div>
            
            <!-- Tornado -->
            <div class="img-card">
                <h4>Sensitivity (Tornado Chart)</h4>
                <img src="{img_tornado}">
            </div>
            
            <!-- Q-Q Plot -->
            <div class="img-card">
                <h4>Normality Check (Q-Q Plot)</h4>
                <img src="{img_qq}">
            </div>

            <!-- Contribution Pie -->
            <div class="img-card">
                <h4>Variance Contribution</h4>
                <img src="{img_sens}">
            </div>
        </div>
    </div>

    <div class="section">
        <h2>3. Input Parameters</h2>
        <p><strong>Equation:</strong> Gap = 0.5*Wc - 0.5*T - 0.5*K*P + 0.5*K*G + 0.5*pt</p>
        <table>
            <tr><th>Component</th><th>Nominal</th><th>Tolerance (±)</th><th>Geometric Factor (f)</th><th>Vector</th></tr>
            { "".join([f"<tr><td>{p['name']}</td><td>{p['nom']}</td><td>{p['tol']}</td><td>{p['f']:.3f}</td><td>{p['vec']}</td></tr>" for p in params]) }
        </table>
    </div>

</div>
</body>
</html>
"""

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(html)
print(f"Report generated: {REPORT_PATH}")
