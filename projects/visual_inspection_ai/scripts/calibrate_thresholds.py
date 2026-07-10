# -*- coding: utf-8 -*-
"""しきい値校正(決定論): 良品/不良スコア分布からreview/ng_thresholdを提案・適用する。

方式(LLM不使用・全て統計量):
  review_threshold = max(良品score) + 3*MAD(良品score)   ※下限1e-4
  ng_threshold     = sqrt(review_threshold * median(不良score))  (幾何中点)
                     不良未指定時は review*3
  ガード: min(不良) <= review なら「分離不足」を警告しapplyを拒否(--force必要)

使い方:
  python scripts/calibrate_thresholds.py --product demo_press_part \
      --good data/internal/demo_press_part/fixed_test/good \
      --bad  data/internal/demo_press_part/fixed_test/bad --apply
適用時は recipe yaml をバックアップ(.bak_thcal)し、旧→新値をレポートJSONに記録する。
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import glob
import json
import shutil
import statistics
from datetime import datetime, timezone
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inspection_ai.detection.reference_model import (  # noqa: E402
    ReferenceDifferenceDetector,
    ReferenceModelTrainer,
)
from inspection_ai.preprocessing.image_ops import apply_roi  # noqa: E402


def collect_scores(det, folder: Path, recipe: dict, augment_shift_px: int = 0) -> list[float]:
    """pipeline.pyと同一の前処理(ROI切り出し)でスコア収集する。

    augment_shift_px>0 の場合、±shiftの平行移動変種も良品分布に含める
    (実治具の位置ズレを校正に織り込む=ズレ良品の偽REVIEW防止)。"""
    import numpy as np
    scores = []
    for p in sorted(glob.glob(str(folder / "**" / "*.png"), recursive=True)):
        img = cv2.imread(p)
        if img is None:
            continue
        variants = [img]
        if augment_shift_px > 0:
            s = augment_shift_px
            for dx, dy in ((s, 0), (-s, 0), (0, s), (s, -s)):
                M = np.float32([[1, 0, dx], [0, 1, dy]])
                variants.append(cv2.warpAffine(img, M, (img.shape[1], img.shape[0]),
                                               borderMode=cv2.BORDER_REPLICATE))
        for v in variants:
            roi, offset = apply_roi(v, recipe.get("image", {}).get("roi"))
            scores.append(float(det.predict(roi, offset=offset)[0].anomaly_score))
    return scores


def mad(values: list[float]) -> float:
    med = statistics.median(values)
    return statistics.median([abs(v - med) for v in values]) * 1.4826


def main() -> int:
    ap = argparse.ArgumentParser(description="threshold calibration (deterministic)")
    ap.add_argument("--product", required=True)
    ap.add_argument("--good", required=True, help="良品画像フォルダ(学習に使っていない検証用)")
    ap.add_argument("--bad", default=None, help="不良画像フォルダ(再帰)")
    ap.add_argument("--model", default=None, help="基準モデルnpz。省略時は--goodで一時学習(検証用途)")
    ap.add_argument("--train-good", default=None, help="一時学習に使う良品フォルダ(省略時=--good)")
    ap.add_argument("--augment-shift-px", type=int, default=0, help="良品に±Npxズレ変種を加えて校正(治具ズレ耐性)")
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--force", action="store_true", help="分離不足でも適用(非推奨)")
    args = ap.parse_args()

    recipe_path = ROOT / "configs" / "products" / f"{args.product}.yaml"
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))

    if args.model:
        model_path = Path(args.model)
    else:
        train_dir = Path(args.train_good or args.good)
        paths = sorted(glob.glob(str(train_dir / "*.png")))
        sample = cv2.imread(paths[0], 0)
        model_path = ROOT / "data" / "reports" / "_thcal_tmp_model.npz"
        size = recipe.get("model", {}).get("input_size") or list(sample.shape)
        ReferenceModelTrainer().train(paths, model_path, (int(size[0]), int(size[1])),
                                      roi=recipe.get("image", {}).get("roi"))
    det = ReferenceDifferenceDetector(model_path, recipe)

    good_scores = collect_scores(det, Path(args.good), recipe, augment_shift_px=args.augment_shift_px)
    if len(good_scores) < 5:
        print(f"[NG] 良品検証画像が{len(good_scores)}枚(最低5枚)"); return 2
    bad_scores = collect_scores(det, Path(args.bad), recipe) if args.bad else []

    # 10%安全マージン+6桁切り上げ(境界同値での取り零し防止)
    import math
    review_t = max((max(good_scores) + 3 * mad(good_scores)) * 1.10, 1e-4)
    review_t = math.ceil(review_t * 1e6) / 1e6
    if bad_scores:
        med_bad = statistics.median(bad_scores)
        ng_t = (review_t * med_bad) ** 0.5 if med_bad > review_t else review_t * 1.5
        separated = min(bad_scores) > review_t
    else:
        ng_t = review_t * 3.0
        separated = None

    old = {k: recipe.get("model", {}).get(k) for k in ("review_threshold", "ng_threshold")}
    report = {
        "schema": "clawstack.threshold_calibration.v1",
        "product": args.product,
        "calibrated_at": datetime.now(timezone.utc).isoformat(),
        "good_n": len(good_scores), "bad_n": len(bad_scores),
        "good_stats": {"max": max(good_scores), "median": statistics.median(good_scores), "mad": mad(good_scores)},
        "bad_stats": ({"min": min(bad_scores), "median": statistics.median(bad_scores)} if bad_scores else None),
        "separated": separated,
        "old": old,
        "proposed": {"review_threshold": review_t, "ng_threshold": round(ng_t, 6)},
        "applied": False,
    }

    if separated is False and not args.force:
        print("[WARN] 良品/不良のスコア分布が重なっています。適用拒否(--forceで強行可)。")
        args.apply = False

    if args.apply:
        shutil.copy(recipe_path, str(recipe_path) + ".bak_thcal")
        recipe.setdefault("model", {})["review_threshold"] = float(review_t)
        recipe["model"]["ng_threshold"] = float(round(ng_t, 6))
        recipe_path.write_text(yaml.safe_dump(recipe, allow_unicode=True, sort_keys=False), encoding="utf-8")
        report["applied"] = True

    out = ROOT / "data" / "reports" / f"threshold_calibration_{args.product}_{datetime.now().strftime('%Y%m%dT%H%M%S')}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"[report] {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
