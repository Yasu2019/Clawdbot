# -*- coding: utf-8 -*-
"""P1r7基準(20um clearance, 標準抜き順番, 25um全ホットスポット細分化, GENE1単独)と
P1r8-P1r12の各結果を比較する4種の分析(理論考察はレポート側で実施、ここは数値抽出のみ)。

1) COCKCROFT: P1r8 vs P1r7           -- H1-H5破断有無・タイミングの差
2) クリアランス: P1r9(10um)/P1r7(20um)/P1r10(30um) -- H4破断タイミング、丸穴分離
3) 抜き順番: P1r11 vs P1r7            -- H4のepsサチュレーションタイミング
4) メッシュ収束性: P1r12(50um) vs P1r7(25um)     -- H4(フィレット) vs H1(鋭角)の収束性
"""
import json

TSTOP = 6.0e-4


def load(name):
    with open(f"timeseries_{name}.json", encoding="utf-8") as f:
        return json.load(f)


def rupture_time(series):
    for pt in series:
        if pt.get("status") == "ruptured":
            return pt["t"], pt.get("eps")
    return None, None


def eps_at_progress(series, frac):
    """tstop*fracに最も近いフレームのeps(破断前)を返す。"""
    target = TSTOP * frac
    best = None
    best_d = 1e9
    for pt in series:
        d = abs(pt["t"] - target)
        if d < best_d and pt.get("status") == "live":
            best_d, best = d, pt.get("eps")
    return best


def summarize(name, series):
    rt, reps = rupture_time(series)
    last = series[-1]
    return {
        "run": name,
        "rupture_t_ms": None if rt is None else round(rt * 1e3, 4),
        "rupture_pct_tstop": None if rt is None else round(rt / TSTOP * 100, 1),
        "eps_at_rupture": reps,
        "final_status": last.get("status"),
        "final_eps": last.get("eps"),
        "eps_30pct": eps_at_progress(series, 0.30),  # ~矩形フェーズ終盤相当
        "eps_50pct": eps_at_progress(series, 0.50),
        "eps_70pct": eps_at_progress(series, 0.70),
    }


def print_table(rows, hotspots):
    for h in hotspots:
        print(f"\n=== {h} ===")
        print(f"{'run':8s} {'rupt_ms':>9s} {'rupt_%tstop':>11s} {'eps@rupt':>9s} "
              f"{'final':>10s} {'eps30%':>8s} {'eps50%':>8s} {'eps70%':>8s}")
        for r in rows:
            s = summarize(r["name"], r["data"][h])
            def f(v):
                return "-" if v is None else f"{v:.4f}" if isinstance(v, float) else str(v)
            print(f"{r['name']:8s} {f(s['rupture_t_ms']):>9s} {f(s['rupture_pct_tstop']):>11s} "
                  f"{f(s['eps_at_rupture']):>9s} {s['final_status']:>10s} "
                  f"{f(s['eps_30pct']):>8s} {f(s['eps_50pct']):>8s} {f(s['eps_70pct']):>8s}")


HOTSPOTS = ["H4", "H1", "H2", "H2b", "H3", "H5"]

baseline = load("6hotspots")  # P1r7

print("#" * 70)
print("# 1) COCKCROFT: P1r8 (GENE1+COCKCROFT) vs P1r7 (GENE1 only, baseline)")
print("#" * 70)
p1r8 = load("P1r8")
print_table([{"name": "P1r7", "data": baseline}, {"name": "P1r8", "data": p1r8}], HOTSPOTS)

print("\n" + "#" * 70)
print("# 2) クリアランス感度: P1r9(10um) / P1r7(20um) / P1r10(30um)  -- H4中心")
print("#" * 70)
p1r9 = load("P1r9")
p1r10 = load("P1r10")
print_table(
    [{"name": "P1r9_10um", "data": p1r9}, {"name": "P1r7_20um", "data": baseline},
     {"name": "P1r10_30um", "data": p1r10}],
    ["H4"])

print("\n" + "#" * 70)
print("# 3) 抜き順番: P1r11(矩形/トリム入替) vs P1r7(標準順番)  -- H4中心")
print("#" * 70)
p1r11 = load("P1r11")
print_table([{"name": "P1r7_std", "data": baseline}, {"name": "P1r11_swap", "data": p1r11}], ["H4"])

print("\n" + "#" * 70)
print("# 4) メッシュ収束性: P1r12(50um) vs P1r7(25um)  -- 鋭角アーティファクト仮説の検証")
print("#" * 70)
p1r12 = load("P1r12")
print_table([{"name": "P1r7_25um", "data": baseline}, {"name": "P1r12_50um", "data": p1r12}], HOTSPOTS)

print("\n" + "#" * 70)
print("# メッシュ収束性の判定基準:")
print("#  - H4(フィレット): 25um->50umで破断有無/タイミングが大きく変わらなければ収束(妥当な物理予測)")
print("#  - H1/H2/H3/H5(鋭角): 25um->50umで破断有無/タイミングが大きく変わる=メッシュサイズ依存")
print("#    -> 鋭角側の破断はメッシュアーティファクトである仮説を支持")
print("#" * 70)
