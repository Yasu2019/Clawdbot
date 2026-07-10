# -*- coding: utf-8 -*-
"""寸法スケール校正CLI: 既知長の2点指定から mm_per_pixel を算出しrecipeへ適用する。

例(基準ゲージの両端が画素(100,240)-(540,240)で実長8.80mmの場合):
  python scripts/calibrate_scale.py --product demo_press_part \
      --image data/internal/demo_press_part/fixed_test/good/normal_0000.png \
      --ax 100 --ay 240 --bx 540 --by 240 --known-mm 8.80 --apply

注意: これはアルゴリズム校正であり、光学系(テレセントリックレンズ・照明・治具)
確立前の値は本番の寸法保証に使えない(README/MSA注記参照)。
"""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import cv2
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from inspection_ai.measurement.calibration import estimate_scale  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="mm/pixel scale calibration")
    ap.add_argument("--product", required=True)
    ap.add_argument("--image", required=True)
    ap.add_argument("--ax", type=float, required=True)
    ap.add_argument("--ay", type=float, required=True)
    ap.add_argument("--bx", type=float, required=True)
    ap.add_argument("--by", type=float, required=True)
    ap.add_argument("--known-mm", type=float, required=True)
    ap.add_argument("--apply", action="store_true")
    args = ap.parse_args()

    img = cv2.imread(args.image)
    if img is None:
        print(f"[NG] 画像を読めません: {args.image}"); return 2
    cal_id = f"scale_{args.product}_{datetime.now().strftime('%Y%m%dT%H%M%S')}"
    cal = estimate_scale(img, (args.ax, args.ay), (args.bx, args.by), args.known_mm, cal_id,
                         note=f"CLI校正 {Path(args.image).name}")
    recipe_path = ROOT / "configs" / "products" / f"{args.product}.yaml"
    recipe = yaml.safe_load(recipe_path.read_text(encoding="utf-8"))
    old = (recipe.get("measurement") or {}).get("mm_per_pixel")
    print(json.dumps({
        "calibration_id": cal_id,
        "measured_length_px": cal.measured_length_px,
        "known_length_mm": cal.known_length_mm,
        "mm_per_pixel_old": old,
        "mm_per_pixel_new": round(cal.mm_per_pixel, 6),
        "applied": bool(args.apply),
    }, ensure_ascii=False, indent=2))
    cal_dir = ROOT / "data" / "calibrations"
    cal.save(cal_dir / f"{cal_id}.json")
    if args.apply:
        shutil.copy(recipe_path, str(recipe_path) + ".bak_scale")
        recipe.setdefault("measurement", {})["mm_per_pixel"] = float(round(cal.mm_per_pixel, 6))
        recipe["measurement"]["calibration_id"] = cal_id
        recipe_path.write_text(yaml.safe_dump(recipe, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
