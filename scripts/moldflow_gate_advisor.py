# -*- coding: utf-8 -*-
"""Gate Advisor: 平板キャビティ(blockMesh)の固定3インレットに対する
ゲート組合せ7通りの決定論スコアリング(LLM不使用)。

前提(近似・UIにも明示すること):
- キャビティは bbox (length x width x height) の平板近似
- ゲート位置は length 辺上の x=0(inlet1) / L/2(inlet2) / L(inlet3), y=0 端
- 流動長=中面グリッド各点から最寄り有効ゲートへのユークリッド距離(障害物なし)
- L/t限界は一般文献の保守的目安(実測相関なし=精度L3級の一次スクリーニング)

これは Moldflow BGA 相当ではない。最終判断は人間が行う。
実行例: python scripts/moldflow_gate_advisor.py --length 100 --width 10 --height 2 --material pp_generic
"""

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import itertools
import json
import math

PATCHES = ("inlet1", "inlet2", "inlet3")

# L/t(流動長/肉厚)の保守的目安(一般的なスパイラルフロー知見ベースの丸め値。実測で校正するまで参考値)
FLOW_RATIO_LIMITS = {
    "pp_generic": 150.0,
    "abs_generic": 130.0,
    "pc_generic": 100.0,
}
DEFAULT_FLOW_RATIO_LIMIT = 120.0

# スコア重み(合計1.0・決定論)
W_FILL_MARGIN = 0.45   # L/t限界に対する余裕
W_WELD = 0.25          # ウェルドライン本数ペナルティ
W_BALANCE = 0.15       # ゲート別担当領域の均等さ
W_FLOW = 0.15          # 最大流動長の短さ(全候補内で正規化)


def gate_positions(length: float) -> dict:
    return {"inlet1": (0.0, 0.0), "inlet2": (length / 2.0, 0.0), "inlet3": (length, 0.0)}


def _grid(length: float, width: float, nx: int = 61, ny: int = 25):
    for i in range(nx):
        x = length * i / (nx - 1)
        for j in range(ny):
            y = width * j / (ny - 1)
            yield (x, y)


def evaluate_config(active, length, width, thickness, flow_limit, nx=61, ny=25) -> dict:
    """1つのゲート組合せを評価して生メトリクスを返す。"""
    pos = gate_positions(length)
    gates = [(p, pos[p]) for p in active]
    max_d = -1.0
    last_fill = (0.0, 0.0)
    coverage = {p: 0 for p in active}
    for pt in _grid(length, width, nx, ny):
        best_p, best_d = None, float("inf")
        for p, g in gates:
            d = math.hypot(pt[0] - g[0], pt[1] - g[1])
            if d < best_d:
                best_p, best_d = p, d
        coverage[best_p] += 1
        if best_d > max_d:
            max_d, last_fill = best_d, pt
    # ウェルドライン: x順で隣接する有効ゲート対の合流位置(中点)
    xs = sorted(pos[p][0] for p in active)
    welds = [{"x_mm": round((a + b) / 2.0, 2), "note": "隣接ゲート合流(推定)"}
             for a, b in zip(xs, xs[1:])]
    counts = list(coverage.values())
    mean_c = sum(counts) / len(counts)
    balance_cv = (math.sqrt(sum((c - mean_c) ** 2 for c in counts) / len(counts)) / mean_c) if mean_c else 0.0
    flow_ratio = (max_d / thickness) if thickness > 0 else float("inf")
    return {
        "gates": list(active),
        "gate_count": len(active),
        "max_flow_length_mm": round(max_d, 2),
        "last_fill_point_mm": [round(last_fill[0], 1), round(last_fill[1], 1)],
        "flow_ratio_Lt": round(flow_ratio, 1),
        "flow_ratio_limit": flow_limit,
        "fill_margin_pct": round((flow_limit - flow_ratio) / flow_limit * 100.0, 1),
        "weld_lines": welds,
        "weld_count": len(welds),
        "balance_cv": round(balance_cv, 3),
    }


def advise_gates(bbox_mm: dict, thickness_mm: float | None = None,
                 material_id: str | None = None, nx: int = 61, ny: int = 25) -> dict:
    """7通りの組合せを評価しスコア降順で返す。決定論(同一入力→同一出力)。"""
    length = float(bbox_mm.get("length", 100.0) or 100.0)
    width = float(bbox_mm.get("width", 10.0) or 10.0)
    thickness = float(thickness_mm if thickness_mm is not None else (bbox_mm.get("height", 2.0) or 2.0))
    flow_limit = FLOW_RATIO_LIMITS.get(str(material_id or ""), DEFAULT_FLOW_RATIO_LIMIT)

    configs = []
    for r in (1, 2, 3):
        for combo in itertools.combinations(PATCHES, r):
            configs.append(evaluate_config(combo, length, width, thickness, flow_limit, nx, ny))

    flows = [c["max_flow_length_mm"] for c in configs]
    fmin, fmax = min(flows), max(flows)
    for c in configs:
        margin = max(0.0, min(100.0, c["fill_margin_pct"])) / 100.0
        weld_pen = 1.0 - min(1.0, c["weld_count"] * 0.5)          # 1本=-0.5, 2本=-1.0
        balance = 1.0 - min(1.0, c["balance_cv"])
        flow_norm = 1.0 if fmax == fmin else 1.0 - (c["max_flow_length_mm"] - fmin) / (fmax - fmin)
        c["score"] = round(100.0 * (W_FILL_MARGIN * margin + W_WELD * weld_pen
                                    + W_BALANCE * balance + W_FLOW * flow_norm), 1)
        c["short_shot_risk"] = c["fill_margin_pct"] < 0

    def sort_key(c):
        # 充填不成立(short_shot_risk)は常に成立候補より下位。
        # 不成立同士は「限界に近い順」(margin降順) — ウェルド数より充填可否が優先
        if c["short_shot_risk"]:
            return (1, -c["fill_margin_pct"], c["gate_count"], c["gates"])
        return (0, -c["score"], c["gate_count"], c["gates"])

    configs.sort(key=sort_key)
    return {
        "schema": "clawstack.gate_advice.v1",
        "assumptions": [
            "平板bbox近似(障害物なし・中面2D距離)",
            f"ゲート位置: x=0 / {length/2:.0f} / {length:.0f} mm (y=0端)",
            f"L/t限界 {flow_limit}(材料 {material_id or 'default'} の一般的目安・実測未校正)",
            "Moldflow BGA相当ではない一次スクリーニング。最終判断は人間",
        ],
        "input": {"bbox_mm": {"length": length, "width": width}, "thickness_mm": thickness,
                  "material_id": material_id, "grid": [nx, ny]},
        "candidates": configs,
        "best": configs[0]["gates"],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Gate Advisor (deterministic)")
    ap.add_argument("--length", type=float, default=100.0)
    ap.add_argument("--width", type=float, default=10.0)
    ap.add_argument("--height", type=float, default=2.0)
    ap.add_argument("--thickness", type=float, default=None)
    ap.add_argument("--material", default=None)
    args = ap.parse_args()
    out = advise_gates({"length": args.length, "width": args.width, "height": args.height},
                       args.thickness, args.material)
    print(json.dumps(out, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
