from __future__ import annotations

import cv2
import numpy as np


def ensure_bgr(image: np.ndarray) -> np.ndarray:
    if image is None:
        raise ValueError("画像を読み込めません")
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    return image


def apply_roi(image: np.ndarray, roi: list[int] | None) -> tuple[np.ndarray, tuple[int, int]]:
    if not roi:
        return image, (0, 0)
    if len(roi) != 4:
        raise ValueError("roiは[x1,y1,x2,y2]です")
    x1, y1, x2, y2 = map(int, roi)
    h, w = image.shape[:2]
    x1, x2 = max(0, x1), min(w, x2)
    y1, y2 = max(0, y1), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        raise ValueError("ROIが画像範囲外です")
    return image[y1:y2, x1:x2].copy(), (x1, y1)


def resize_exact(image: np.ndarray, size_hw: tuple[int, int]) -> np.ndarray:
    h, w = size_hw
    return cv2.resize(image, (w, h), interpolation=cv2.INTER_AREA)
