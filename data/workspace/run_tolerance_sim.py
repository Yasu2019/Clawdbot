
import numpy as np
import matplotlib.pyplot as plt

# ---------------------------------------------------------
# 公差解析シミュレーション (Monte Carlo Method)
# 対象: 製品抜きガイド - 石井様懸念事項 (位置ズレ・クリアランス)
# ---------------------------------------------------------

N_SAMPLES = 100000

# 定義: 寸法チェーン (単位: mm)
# [公称値, 公差(±)]
chain = [
    {"name": "ガイド位置基準", "nominal": 0.0, "tol": 0.0},      # 基準
    {"name": "ガイド取り付け位置", "nominal": 100.0, "tol": 0.1}, # 治具精度 (推定)
    {"name": "ガイド-製品隙間", "nominal": 0.2, "tol": 0.1},    # 懸念点: 両端の浮き/ガタ
    {"name": "製品穴ピッチ誤差", "nominal": 0.0, "tol": 0.05},   # 製品精度
]

# シミュレーション実行
results = []
details = { c["name"]: [] for c in chain }

print(f"--- Simulation Start ({N_SAMPLES} samples) ---")

for _ in range(N_SAMPLES):
    stackup = 0.0
    for c in chain:
        # 正規分布近似 (3σ = 公差)
        sigma = c["tol"] / 3.0
        val = np.random.normal(c["nominal"], sigma)
        stackup += val
        details[c["name"]].append(val)
    results.append(stackup)

results = np.array(results)

# 統計量
mean_val = np.mean(results)
std_dev = np.std(results)
min_val = np.min(results)
max_val = np.max(results)
range_val = max_val - min_val

nominal_sum = sum([c["nominal"] for c in chain])
worst_case_tol = sum([c["tol"] for c in chain])

print(f"\n--- Analysis Result ---")
print(f"Nominal Sum (Design): {nominal_sum:.3f} mm")
print(f"Worst Case (Arithmetic): {nominal_sum:.3f} ± {worst_case_tol:.3f} mm")
print(f"RSS (Root Sum Squares, 3σ): {nominal_sum:.3f} ± {3*std_dev:.3f} mm")
print(f"Simulation Mean: {mean_val:.4f} mm")
print(f"Simulation Range: {min_val:.3f} to {max_val:.3f} mm")
print(f"Standard Deviation (σ): {std_dev:.4f} mm")
print(f"Cp (Process Capability, considering ±{worst_case_tol}): {worst_case_tol / (3*std_dev):.2f}")

# 判定
target_limit = 0.5 # 仮の許容ズレ量
fail_count = np.sum(np.abs(results - nominal_sum) > target_limit)
fail_rate = (fail_count / N_SAMPLES) * 100
print(f"\nTarget Limit: ±{target_limit} mm")
print(f"Failure Rate (Probability of exceeding limit): {fail_rate:.2f}%")

# グラフ生成
plt.figure(figsize=(10, 6))
plt.hist(results, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
plt.axvline(nominal_sum, color='green', linestyle='dashed', linewidth=2, label='Nominal')
plt.axvline(nominal_sum + 3*std_dev, color='red', linestyle='dashed', linewidth=2, label='+3σ')
plt.axvline(nominal_sum - 3*std_dev, color='red', linestyle='dashed', linewidth=2, label='-3σ')
plt.title(f"Tolerance Stackup Simulation (N={N_SAMPLES})")
plt.xlabel("Total Dimension (mm)")
plt.ylabel("Frequency")
plt.legend()
plt.grid(True)
plt.savefig(r"D:\Clawdbot_Docker_20260125\data\workspace\tolerance_result.png")
print("\nGraph saved to: tolerance_result.png")

# 感度分析 (寄与率)
print("\n--- Sensitivity Analysis (Contribution %) ---")
total_variance = sum([(c["tol"] / 3.0)**2 for c in chain])
for c in chain:
    if c["tol"] > 0:
        variance = (c["tol"] / 3.0)**2
        contribution = (variance / total_variance) * 100
        print(f"{c['name']}: {contribution:.1f}%")
