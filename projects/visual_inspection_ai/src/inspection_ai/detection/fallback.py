from __future__ import annotations

import cv2
import numpy as np

from inspection_ai.schemas import DetectionResult, Region


class FallbackEdgeDetector:
    """モデル未学習時のデモ用。強い局所エッジを異常候補として返す。"""

    version = "fallback-edge-v1"

    def __init__(self, recipe: dict):
        self.cfg = recipe.get("model", {})

    def predict(self, image_bgr: np.ndarray, offset: tuple[int, int] = (0, 0)) -> tuple[DetectionResult, np.ndarray]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 80, 180)
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: list[Region] = []
        ox, oy = offset
        for c in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            area = int(cv2.contourArea(c))
            if area < 25:
                continue
            x, y, w, h = cv2.boundingRect(c)
            regions.append(Region(x=x+ox, y=y+oy, width=w, height=h, area=area, score=0.2, label="edge_candidate"))
        score = min(1.0, float(edges.mean() / 255.0 * 2.0))
        heat = cv2.applyColorMap(edges, cv2.COLORMAP_JET)
        return DetectionResult(anomaly_score=score, regions=regions, model_version=self.version), heat
