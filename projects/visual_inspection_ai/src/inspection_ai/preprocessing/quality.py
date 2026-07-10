from __future__ import annotations

import cv2
import numpy as np

from inspection_ai.schemas import QualityResult


def evaluate_quality(image: np.ndarray, recipe: dict) -> QualityResult:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if image.ndim == 3 else image
    blur = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(gray.mean())
    cfg = recipe.get("quality", {})
    blur_min = float(cfg.get("blur_min_laplacian_var", 0))
    bmin = float(cfg.get("brightness_min", 0))
    bmax = float(cfg.get("brightness_max", 255))
    reasons: list[str] = []
    if blur < blur_min:
        reasons.append(f"画像がぼけています: {blur:.1f} < {blur_min:.1f}")
    if brightness < bmin:
        reasons.append(f"画像が暗すぎます: {brightness:.1f} < {bmin:.1f}")
    if brightness > bmax:
        reasons.append(f"画像が明るすぎます: {brightness:.1f} > {bmax:.1f}")
    return QualityResult(passed=not reasons, blur_score=blur, brightness=brightness, reasons=reasons)
