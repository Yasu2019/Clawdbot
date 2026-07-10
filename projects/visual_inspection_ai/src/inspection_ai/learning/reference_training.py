from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.detection.reference_model import ReferenceModelTrainer, ReferenceDifferenceDetector
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.preprocessing.image_ops import apply_roi
from inspection_ai.review.service import ReviewService
from inspection_ai.utils import compact_timestamp


def _existing_paths(root: Path, rows: list[dict[str, Any]]) -> list[Path]:
    result = []
    for row in rows:
        p = root / row["original_path"]
        if p.exists():
            result.append(p)
    return result


def collect_good_images(config: AppConfig, db: Database, product_id: str) -> list[Path]:
    static_dir = config.paths.root / "data" / "internal" / product_id / "train" / "good"
    paths = sorted([p for p in static_dir.glob("**/*") if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}])
    reviewed = ReviewService(db).training_candidates(product_id, "OK")
    paths.extend(_existing_paths(config.paths.root, reviewed))
    # 内容ハッシュによる重複除外は大規模化時に行う。ここでは絶対パス重複を除く。
    return list(dict.fromkeys(p.resolve() for p in paths))


def train_reference_challenger(
    config: AppConfig,
    db: Database,
    registry: ModelRegistry,
    product_id: str,
    promote: bool = False,
    approved_by: str = "user",
) -> dict[str, Any]:
    recipe = config.recipe(product_id)
    paths = collect_good_images(config, db, product_id)
    if len(paths) < 3:
        raise ValueError(f"良品画像が不足しています: {len(paths)}枚")
    size = recipe.get("model", {}).get("input_size", [256, 256])
    size_hw = (int(size[0]), int(size[1]))
    work = config.paths.root / "models" / "work"
    work.mkdir(parents=True, exist_ok=True)
    out = work / f"{product_id}_reference_{compact_timestamp()}.npz"
    ReferenceModelTrainer().train(paths, out, size_hw, roi=recipe.get("image", {}).get("roi"))

    champion = registry.get_champion(product_id)
    version = registry.register(
        product_id=product_id,
        kind="reference_difference",
        model_path=out,
        stage="CHALLENGER",
        metrics={"training_good_images": len(paths)},
        parent_version=champion["version"] if champion else None,
        note="local reference model",
    )
    if promote:
        registry.promote(version, approved_by, "initial/manual promotion")
    return {"version": version, "training_good_images": len(paths), "promoted": promote}
