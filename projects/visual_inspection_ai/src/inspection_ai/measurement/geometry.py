from __future__ import annotations

import cv2
import numpy as np

from inspection_ai.schemas import MeasurementItem


def _spec(recipe: dict, name: str) -> dict:
    return recipe.get("measurement", {}).get("expected", {}).get(name, {})


def _item(name: str, value: float | None, spec: dict, confidence: float, method: str) -> MeasurementItem:
    lo = spec.get("lower")
    hi = spec.get("upper")
    passed = None if value is None or lo is None or hi is None else float(lo) <= value <= float(hi)
    return MeasurementItem(
        name=name,
        value_mm=None if value is None else round(float(value), 5),
        lower_mm=None if lo is None else float(lo),
        upper_mm=None if hi is None else float(hi),
        passed=passed,
        confidence=float(np.clip(confidence, 0, 1)),
        method=method,
    )


def measure_part(image_bgr: np.ndarray, recipe: dict, offset: tuple[int, int] = (0, 0)) -> tuple[list[MeasurementItem], list[dict]]:
    cfg = recipe.get("measurement", {})
    if not cfg.get("enabled", True):
        return [], []
    mm_per_px = float(cfg.get("mm_per_pixel", 1.0))
    threshold = int(cfg.get("object_threshold", 100))
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    _, binary = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY)
    binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    items: list[MeasurementItem] = []
    overlays: list[dict] = []
    if not contours:
        for name in ("width_mm", "height_mm", "hole_diameter_mm"):
            items.append(_item(name, None, _spec(recipe, name), 0.0, "contour_not_found"))
        return items, overlays

    part = max(contours, key=cv2.contourArea)
    x, y, w, h = cv2.boundingRect(part)
    confidence = min(1.0, cv2.contourArea(part) / max(w * h, 1))
    items.append(_item("width_mm", w * mm_per_px, _spec(recipe, "width_mm"), confidence, "threshold_bounding_rect"))
    items.append(_item("height_mm", h * mm_per_px, _spec(recipe, "height_mm"), confidence, "threshold_bounding_rect"))
    ox, oy = offset
    overlays.append({"type": "rect", "x": x+ox, "y": y+oy, "w": w, "h": h, "label": f"W={w*mm_per_px:.3f} H={h*mm_per_px:.3f} mm"})

    # 部品領域内部の暗い円を穴候補とする。実機ではテレセントリック/サブピクセルフィットへ置換。
    roi = gray[y:y+h, x:x+w]
    inv = cv2.threshold(roi, max(5, threshold // 3), 255, cv2.THRESH_BINARY_INV)[1]
    hole_contours, _ = cv2.findContours(inv, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    for c in hole_contours:
        area = cv2.contourArea(c)
        if area < 20:
            continue
        perimeter = cv2.arcLength(c, True)
        if perimeter <= 0:
            continue
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        (cx, cy), radius = cv2.minEnclosingCircle(c)
        if 0.55 <= circularity <= 1.2 and radius < min(w, h) * 0.3:
            candidates.append((circularity, cx, cy, radius))
    if candidates:
        circularity, cx, cy, radius = max(candidates, key=lambda v: v[0])
        diameter = 2 * radius * mm_per_px
        items.append(_item("hole_diameter_mm", diameter, _spec(recipe, "hole_diameter_mm"), circularity, "min_enclosing_circle"))
        overlays.append({"type": "circle", "cx": int(x+cx)+ox, "cy": int(y+cy)+oy, "r": int(radius), "label": f"D={diameter:.3f} mm"})
    else:
        items.append(_item("hole_diameter_mm", None, _spec(recipe, "hole_diameter_mm"), 0.0, "hole_not_found"))
    return items, overlays
