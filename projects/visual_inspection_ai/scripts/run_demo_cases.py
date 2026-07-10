# -*- coding: utf-8 -*-
"""検査デモ実行: 良品+5不良種(+位置ズレ良品)を校正済みパイプラインで判定し、
アノテーション画像とヒートマップを data/demo_runs/<日付>/ に出力する。

実行: python scripts/run_demo_cases.py
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import glob
import json
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inspection_ai.detection.reference_model import ReferenceDifferenceDetector, ReferenceModelTrainer
from inspection_ai.preprocessing.image_ops import apply_roi
from inspection_ai.measurement.geometry import measure_part
from inspection_ai.annotation import annotate

DEMO = ROOT / "data" / "internal" / "demo_press_part"
OUT = ROOT / "data" / "demo_runs" / datetime.now().strftime("%Y%m%d_%H%M%S")

CASES = [
    ("case1_good", "良品", DEMO / "fixed_test" / "good", "OK期待"),
    ("case2_burr", "バリ", DEMO / "fixed_test" / "bad" / "burr", "NG期待"),
    ("case3_dent", "打痕", DEMO / "fixed_test" / "bad" / "dent", "NG期待"),
    ("case4_scratch", "傷", DEMO / "fixed_test" / "bad" / "scratch", "NG期待"),
    ("case5_short_shot", "ショートショット", DEMO / "fixed_test" / "bad" / "short_shot", "NG期待"),
    ("case6_stain", "汚れ", DEMO / "fixed_test" / "bad" / "stain", "NG期待"),
]


def decide_simple(score: float, model_cfg: dict) -> str:
    if score >= float(model_cfg["ng_threshold"]):
        return "NG"
    if score >= float(model_cfg["review_threshold"]):
        return "REVIEW"
    return "OK"


def main() -> int:
    recipe = yaml.safe_load((ROOT / "configs" / "products" / "demo_press_part.yaml").read_text(encoding="utf-8"))
    good = sorted(glob.glob(str(DEMO / "train" / "good" / "*.png")))
    size = recipe["model"]["input_size"]
    model_path = OUT / "_ref_model.npz"
    OUT.mkdir(parents=True, exist_ok=True)
    ReferenceModelTrainer().train(good, model_path, (int(size[0]), int(size[1])),
                                  roi=recipe["image"].get("roi"))
    det = ReferenceDifferenceDetector(model_path, recipe)
    results = []

    def run_one(case_id, label, img, expect):
        roi, offset = apply_roi(img, recipe["image"].get("roi"))
        detection, heat = det.predict(roi, offset=offset)
        decision = decide_simple(detection.anomaly_score, recipe["model"])
        measurements, overlays = measure_part(roi, recipe, offset=offset)
        ann = annotate(img, decision, detection.anomaly_score, detection.regions, overlays, measurements)
        cv2.imwrite(str(OUT / f"{case_id}_annotated.png"), ann)
        cv2.imwrite(str(OUT / f"{case_id}_heatmap.png"), heat)
        if "非NG" in expect:
            ok = decision in ("OK", "REVIEW")  # ズレ良品はNG誤判定回避が成功条件(REVIEW=人間確認は正しい安全動作)
        elif "NG" in expect:
            ok = decision == "NG"
        else:
            ok = decision == "OK"
        results.append({"case": case_id, "label": label, "expect": expect,
                        "decision": decision, "score": round(detection.anomaly_score, 5),
                        "regions": len(detection.regions), "judged_correctly": ok})
        mark = "✅" if ok else "❌"
        print(f"{mark} {label:10s} 期待={expect} → 判定={decision} score={detection.anomaly_score:.5f} 不良領域={len(detection.regions)}")

    for case_id, label, folder, expect in CASES:
        img = cv2.imread(sorted(glob.glob(str(folder / "*.png")))[0])
        run_one(case_id, label, img, expect)

    # ボーナス: 位置ズレ良品(6,-5px) — アライメント耐性のデモ
    img = cv2.imread(sorted(glob.glob(str(DEMO / "fixed_test" / "good" / "*.png")))[0])
    M = np.float32([[1, 0, 6], [0, 1, -5]])
    shifted = cv2.warpAffine(img, M, (img.shape[1], img.shape[0]), borderMode=cv2.BORDER_REPLICATE)
    run_one("case7_shifted_good", "位置ズレ良品", shifted, "非NG期待(ECC補正・REVIEW可)")

    summary = {"at": datetime.now().isoformat(), "out_dir": str(OUT),
               "all_correct": all(r["judged_correctly"] for r in results), "results": results}
    (OUT / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n判定成績: {sum(r['judged_correctly'] for r in results)}/{len(results)} 正解")
    print(f"出力: {OUT}")
    return 0 if summary["all_correct"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
