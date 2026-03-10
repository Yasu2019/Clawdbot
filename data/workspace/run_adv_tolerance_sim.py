
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 高度公差解析 (Advanced Tolerance Analysis)
# 対象: 順送これによるパンチ・フレーム干渉シミュレーション
# 考慮事項: X/Y軸独立, 順送ピッチ累積, パンチ相対位置
# ---------------------------------------------------------

N_SAMPLES = 100000

# --- パラメータ設定 (仮定値含む) ---

# 1. 共通定数
# クリアランス設計 (片側)
DESIGN_CLEARANCE = 0.15  # mm (例: パンチ19.7mm, 穴20.0mm -> 差0.3mm -> 片側0.15mm)

# 2. Y軸 (幅方向) - ガイド規制によるズレ
chain_y = [
    {"name": "ガイド取り付け位置(Y)", "nominal": 0.0, "tol": 0.05}, 
    {"name": "ガイド-製品隙間(Y)",   "nominal": 0.0, "tol": 0.10}, # センターからのズレとして扱う(±0.1)
    {"name": "パンチ芯ズレ(Y)",       "nominal": 0.0, "tol": 0.03},
    {"name": "製品幅公差(Y)",         "nominal": 0.0, "tol": 0.05},
]

# 3. X軸 (送り方向) - ピッチ累積
# 5回送り(5ピッチ目)を想定
PITCH_COUNT = 5 
chain_x_base = [
    {"name": "パンチ位置(X)", "nominal": 0.0, "tol": 0.03},
    {"name": "パイロット補正残り", "nominal": 0.0, "tol": 0.02}, # パイロットピンで補正しきれない分
]
pitch_error = {"name": "1ピッチ送り誤差", "nominal": 0.0, "tol": 0.02} # 1回あたりの送り誤差

# --- シミュレーション関数 ---
def simulate_axis(name, chain, n_samples):
    results = np.zeros(n_samples)
    print(f"--- {name} Axis Simulation ---")
    
    # Monto Carlo
    for c in chain:
        sigma = c["tol"] / 3.0
        val = np.random.normal(c["nominal"], sigma, n_samples)
        results += val
        
    # Stats
    mean = np.mean(results)
    std = np.std(results)
    worst = sum([c["tol"] for c in chain])
    
    # Interference Check (Clearance - |Deviation|)
    # Margin < 0 means Collision
    margins = DESIGN_CLEARANCE - np.abs(results)
    fail_count = np.sum(margins < 0)
    fail_rate = (fail_count / n_samples) * 100
    
    print(f"  3σ Range: ±{3*std:.3f} mm")
    print(f"  Worst Case: ±{worst:.3f} mm")
    print(f"  Fail Rate (Safety Margin < 0): {fail_rate:.3f}% (Clearance={DESIGN_CLEARANCE}mm)")
    
    return results, margins

# --- 実行 ---
# Y軸
results_y, margins_y = simulate_axis("Y (Width)", chain_y, N_SAMPLES)

# X軸 (ピッチ累積を追加)
chain_x = chain_x_base.copy()
# 単純累積 (Worst case assumption for sequential feed without perfect pilot)
# ループで追加すると項目が増えすぎるので、統計的に合成
# σ_total = sqrt(σ_base^2 + N * σ_pitch^2)
sigma_pitch = pitch_error["tol"] / 3.0
sigma_accum = np.sqrt(PITCH_COUNT) * sigma_pitch
# 追加項として扱う
chain_x.append({"name": f"ピッチ累積誤差({PITCH_COUNT}回)", "nominal": 0.0, "tol": sigma_accum * 3.0})

results_x, margins_x = simulate_axis("X (Feed)", chain_x, N_SAMPLES)

# グリッドグラフ描画 (散布図)
plt.figure(figsize=(8, 8), facecolor='black')
ax = plt.axes()
ax.set_facecolor('black')

# Plot Scatter
# 間引き表示 (重すぎて見えないため)
display_samples = 2000
idx = np.random.choice(N_SAMPLES, display_samples, replace=False)
plt.scatter(results_x[idx], results_y[idx], color='#00bcd4', alpha=0.6, s=10, label='Simulated Points')

# Draw Clearance Box (Safe Zone)
safe_rect = plt.Rectangle((-DESIGN_CLEARANCE, -DESIGN_CLEARANCE), 
                          DESIGN_CLEARANCE*2, DESIGN_CLEARANCE*2, 
                          fill=False, edgecolor='#ffeb3b', linewidth=2, linestyle='--', label='Safe Zone (Clearance)')
ax.add_patch(safe_rect)

# Labels
plt.title(f"Interference Risk Map (Pitch Count={PITCH_COUNT})", color='white')
plt.xlabel("X Deviation (Feed) [mm]", color='white')
plt.ylabel("Y Deviation (Width) [mm]", color='white')
plt.grid(True, color='#444', linestyle=':')
plt.tick_params(colors='white')
plt.legend(facecolor='#333', edgecolor='white', labelcolor='white')

# Save
result_path = r"D:\Clawdbot_Docker_20260125\data\workspace\advanced_sim_result.png"
plt.savefig(result_path, dpi=150)
print(f"Graph saved to: {result_path}")
print(f"Done.")
