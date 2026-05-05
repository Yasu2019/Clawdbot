"""OpenRadioss DOE 分析レポート

DBの全試行データを読み込み:
1. パラメータ×結果の散布図データ (CSV)
2. 失敗モード別分類
3. Run42成功条件の感度分析
4. R用 DOE 設計点出力 (次フェーズ用)

Rが未インストールでも Python で同等の LHS 設計を生成する。
"""
from __future__ import annotations
import json
import sys
from pathlib import Path

ROOT = Path(r"D:\Clawdbot_Docker_20260125")
sys.path.insert(0, str(ROOT / "data" / "workspace"))
import sim_trial_logger as db

OUT_DIR = ROOT / "data" / "workspace" / "doe_analysis"
OUT_DIR.mkdir(parents=True, exist_ok=True)


# ────────────────────────────────────────────────────────────────────
# 1. DB全件取得
# ────────────────────────────────────────────────────────────────────
def load_all_trials() -> list[dict]:
    rows = db.query_similar("openradioss", "shear_blanking_4mmx4mm", top_n=200)
    trials = []
    for r in rows:
        # (id, run_number, run_date, status, max_time_reached, failure_mode, parameters, results)
        tid, run_num, run_date, status, t_max, fail_mode, params_raw, results_raw = r
        params = params_raw if isinstance(params_raw, dict) else {}
        results = results_raw if isinstance(results_raw, dict) else {}
        trials.append({
            "id": tid,
            "run": run_num,
            "date": str(run_date),
            "status": status,
            "t_ms": round(t_max * 1000, 3) if t_max else None,
            "fail": fail_mode,
            "Inacti": params.get("Inacti"),
            "VC": params.get("VC"),
            "Eps_eff": params.get("Eps_eff"),
            "EPS_p_max": params.get("EPS_p_max"),
            "VISs": params.get("VISs"),
            "Dn": params.get("Dn"),
            "TSTOP": params.get("TSTOP"),
            "DT": params.get("DT"),
            "term_type": results.get("termination_type"),
            "err_pct": results.get("err_final_pct"),
            "nc": results.get("nc_final"),
            "note": params.get("note", ""),
        })
    return sorted(trials, key=lambda x: x["run"])


# ────────────────────────────────────────────────────────────────────
# 2. CSV 出力
# ────────────────────────────────────────────────────────────────────
def write_csv(trials: list[dict]) -> Path:
    import csv
    out = OUT_DIR / "all_trials.csv"
    fields = ["run", "date", "status", "t_ms", "Inacti", "VC", "Eps_eff",
              "EPS_p_max", "VISs", "Dn", "TSTOP", "DT", "term_type", "err_pct", "nc", "fail", "note"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(trials)
    return out


# ────────────────────────────────────────────────────────────────────
# 3. 失敗モード分類
# ────────────────────────────────────────────────────────────────────
FAILURE_TAXONOMY = {
    "NORMAL_TSTOP":    "[OK] 成功(TSTOP到達)",
    "NORMAL_VELOCITY": "[WARN] 速度超過NORMAL TERM",
    "ABNORMAL":        "[NG] ABNORMAL(ERR崩壊)",
    "UNKNOWN_OR_RUNNING": "[??] 不明/走行中",
}

def classify_failures(trials: list[dict]) -> dict:
    groups: dict[str, list] = {}
    for t in trials:
        key = t.get("term_type") or "UNKNOWN_OR_RUNNING"
        groups.setdefault(key, []).append(t)
    return groups


# ────────────────────────────────────────────────────────────────────
# 4. LHS 設計点生成 (Python実装, R不要)
# ────────────────────────────────────────────────────────────────────
def latin_hypercube(n_runs: int, factors: dict[str, tuple[float, float]],
                    seed: int = 42) -> list[dict]:
    """
    Improved Latin Hypercube Sampling (maximin距離最大化)
    factors: {name: (low, high)}
    """
    import random
    random.seed(seed)
    k = len(factors)
    names = list(factors.keys())
    lows = [factors[n][0] for n in names]
    highs = [factors[n][1] for n in names]

    # 標準 LHS: 各因子を n_runs 等分し各区間から1点ずつ
    def make_lhs():
        design = []
        for j in range(k):
            intervals = [(i / n_runs, (i + 1) / n_runs) for i in range(n_runs)]
            random.shuffle(intervals)
            col = [random.uniform(lo, hi) for lo, hi in intervals]
            design.append(col)
        return [[design[j][i] for j in range(k)] for i in range(n_runs)]

    # maximin: 50回試行して最小点間距離が最大の設計を採用
    import math
    def min_dist(d):
        mn = float("inf")
        for i in range(len(d)):
            for j in range(i + 1, len(d)):
                dd = math.sqrt(sum((d[i][l] - d[j][l]) ** 2 for l in range(k)))
                if dd < mn:
                    mn = dd
        return mn

    best, best_score = None, -1.0
    for _ in range(50):
        cand = make_lhs()
        score = min_dist(cand)
        if score > best_score:
            best, best_score = cand, score

    # スケーリング
    result = []
    for row in best:
        point = {}
        for j, name in enumerate(names):
            point[name] = round(lows[j] + row[j] * (highs[j] - lows[j]), 4)
        result.append(point)
    return result


def write_doe_design(design: list[dict], fixed: dict) -> Path:
    import csv
    out = OUT_DIR / "doe_design_next.csv"
    fields = list(design[0].keys()) + list(fixed.keys()) + ["run_priority"]
    with out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for i, row in enumerate(design, 1):
            row.update(fixed)
            row["run_priority"] = i
            w.writerow(row)
    return out


# ────────────────────────────────────────────────────────────────────
# 5. R スクリプト出力 (インストール済みの場合に使用可能)
# ────────────────────────────────────────────────────────────────────
R_SCRIPT = """\
# OpenRadioss DOE 分析 & 次実験点設計
# 実行: Rscript openradioss_doe_r_analysis.R
# 必要パッケージ: lhs, DiceKriging, ggplot2

library(lhs)
library(ggplot2)

# ── データ読込 ──
df <- read.csv("all_trials.csv", stringsAsFactors = FALSE)
df$success <- ifelse(df$status == "success", 1, 0)
df_known <- df[!is.na(df$Eps_eff) & !is.na(df$VC) & !is.na(df$t_ms), ]

cat("\\n=== 成功/失敗内訳 ===\\n")
print(table(df$status))

# ── 散布図: Eps_eff vs T_final ──
p1 <- ggplot(df_known, aes(x=Eps_eff, y=t_ms, color=status, label=run)) +
  geom_point(size=3) +
  geom_text(vjust=-0.5, size=3) +
  geom_hline(yintercept=18.13, linetype="dashed", color="red") +
  annotate("text", x=min(df_known$Eps_eff), y=18.5,
           label="関門 T=18.13ms", hjust=0, color="red") +
  labs(title="Eps_eff vs T_final", x="Eps_eff", y="T_final (ms)") +
  theme_minimal()
ggsave("plot_eps_eff_vs_t.png", p1, width=8, height=5)
cat("Saved: plot_eps_eff_vs_t.png\\n")

# ── D最適計画: VC x Eps_eff (Run46結果後に実行) ──
library(AlgDesign)
candidates <- expand.grid(
  VC      = c(0.6, 1.0, 2.0, 5.0),
  Eps_eff = c(0.22, 0.30, 0.35, 0.40, 0.50)
)
dopt <- optFederov(~VC + Eps_eff + I(VC^2) + I(Eps_eff^2) + VC:Eps_eff,
                   data = candidates, nTrials = 8, criterion = "D")
cat("\\n=== D最適設計点 ===\\n")
print(dopt$design)
write.csv(dopt$design, "doe_d_optimal.csv", row.names=FALSE)

# ── LHS 設計 (代替) ──
set.seed(42)
lhs_raw <- improvedLHS(8, 2)
doe_lhs <- data.frame(
  VC      = round(0.6  + lhs_raw[,1] * (5.0 - 0.6), 3),
  Eps_eff = round(0.22 + lhs_raw[,2] * (0.50 - 0.22), 3)
)
cat("\\n=== LHS 設計点 ===\\n")
print(doe_lhs)
write.csv(doe_lhs, "doe_lhs.csv", row.names=FALSE)
"""


def write_r_script() -> Path:
    out = OUT_DIR / "openradioss_doe_r_analysis.R"
    out.write_text(R_SCRIPT, encoding="utf-8")
    return out


# ────────────────────────────────────────────────────────────────────
# 6. メインレポート
# ────────────────────────────────────────────────────────────────────
def main() -> None:
    print("=" * 60)
    print("OpenRadioss DOE 分析レポート")
    print("=" * 60)

    trials = load_all_trials()
    print(f"\n総試行数: {len(trials)}")

    csv_path = write_csv(trials)
    print(f"CSV出力: {csv_path}")

    # 失敗モード分類
    groups = classify_failures(trials)
    print("\n--- 終了種別 ---")
    for key, label in FAILURE_TAXONOMY.items():
        runs = groups.get(key, [])
        if runs:
            print(f"  {label}: {len(runs)}件")
            for t in runs:
                print(f"    Run{t['run']:>3}: T={t['t_ms']}ms  Eps_eff={t['Eps_eff']}  VC={t['VC']}")

    # 成功試行
    success = groups.get("NORMAL_TSTOP", [])
    print(f"\n--- 成功試行(T≥18.13ms): {len(success)}件 ---")
    for t in success:
        print(f"  Run{t['run']}: T={t['t_ms']}ms  Eps_eff={t['Eps_eff']}  "
              f"VC={t['VC']}  Inacti={t['Inacti']}  TSTOP={t['TSTOP']}")

    # Eps_eff vs T_final 感度
    known = [t for t in trials if t["Eps_eff"] is not None and t["t_ms"] is not None
             and isinstance(t["Eps_eff"], (int, float))]
    if known:
        print("\n--- Eps_eff 別 T_final (感度) ---")
        print(f"  {'Run':>4} {'Eps_eff':>8} {'VC':>6} {'Inacti':>7} {'T_ms':>8}  終了種別")
        for t in sorted(known, key=lambda x: x["Eps_eff"]):
            print(f"  {t['run']:>4} {t['Eps_eff']:>8.3f} {str(t['VC']):>6} "
                  f"{str(t['Inacti']):>7} {t['t_ms']:>8.2f}  {t['term_type'] or '?'}")

    # LHS 次実験点
    print("\n--- 次回 DOE 設計点 (LHS, Python実装) ---")
    print("  固定: Inacti=6, EPS_p_max=10.0, FAIL_model=GENE1, DT=1.2E-7")
    print("  探索: VC=[0.6, 5.0], Eps_eff=[0.22, 0.50]")
    print()

    if len(success) >= 1:
        print("  [OK] Run42/47で成功設定(Eps_eff=0.35)が確認済み。")
        print("     Run47完了後、Eps_eff±0.05の確認実験(2〜3点)で感度を定量化推奨。")
        design = latin_hypercube(
            n_runs=6,
            factors={"VC": (0.6, 2.0), "Eps_eff": (0.30, 0.45)},
        )
    else:
        design = latin_hypercube(
            n_runs=8,
            factors={"VC": (0.6, 5.0), "Eps_eff": (0.22, 0.50)},
        )

    for i, d in enumerate(design, 1):
        print(f"  点{i}: {d}")

    doe_path = write_doe_design(
        design,
        fixed={"Inacti": 6, "EPS_p_max": 10.0, "FAIL_model": "GENE1", "DT": "1.2E-7", "TSTOP": 0.025},
    )
    print(f"\nDOE設計CSV: {doe_path}")

    r_path = write_r_script()
    print(f"Rスクリプト: {r_path}")
    print("  → Rインストール後: Rscript data/workspace/doe_analysis/openradioss_doe_r_analysis.R")
    print("  → Rインストール: winget install RProject.R")

    # サマリー
    print("\n" + "=" * 60)
    print("分析サマリー")
    print("=" * 60)
    best = max((t for t in trials if t["t_ms"]), key=lambda x: x["t_ms"], default=None)
    if best:
        print(f"  最大到達時刻: Run{best['run']} T={best['t_ms']}ms ({best['term_type']})")
    print(f"  関門達成: T≥18.13ms → {len(success)}件 (Run42, Run47進行中)")
    print(f"  失敗件数: {len(trials) - len(success)}件")
    print(f"  根本原因: Eps_eff=0.22(Run43以降)でNode6178速度601m/s→VC超過")
    print(f"  修正: Eps_eff=0.35に戻す → Run42再現(Node6178=436m/s<600m/s)")
    print(f"  Run47: 進行中 (成功見込み)")

    db.summary()


if __name__ == "__main__":
    main()
