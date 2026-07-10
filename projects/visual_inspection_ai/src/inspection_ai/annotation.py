from __future__ import annotations

import cv2
import numpy as np

from inspection_ai.schemas import MeasurementItem, Region


def annotate(
    image: np.ndarray,
    decision: str,
    score: float,
    regions: list[Region],
    measurement_overlays: list[dict],
    measurements: list[MeasurementItem],
) -> np.ndarray:
    out = image.copy()
    # BGR: OK green, NG red, REVIEW orange
    colors = {"OK": (0, 190, 0), "NG": (0, 0, 230), "REVIEW": (0, 150, 255), "ERROR": (180, 0, 180)}
    color = colors.get(decision, (255, 255, 255))
    cv2.rectangle(out, (3, 3), (out.shape[1]-4, out.shape[0]-4), color, 4)
    cv2.putText(out, f"{decision} score={score:.4f}", (15, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, color, 2, cv2.LINE_AA)
    for i, r in enumerate(regions, 1):
        cv2.rectangle(out, (r.x, r.y), (r.x+r.width, r.y+r.height), (0, 0, 255), 2)
        cv2.putText(out, f"A{i}:{r.label}", (r.x, max(18, r.y-4)), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (0, 0, 255), 1, cv2.LINE_AA)
    for o in measurement_overlays:
        if o["type"] == "rect":
            cv2.rectangle(out, (o["x"], o["y"]), (o["x"]+o["w"], o["y"]+o["h"]), (255, 180, 0), 1)
            cv2.putText(out, o["label"], (o["x"], min(out.shape[0]-8, o["y"]+o["h"]+18)), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 180, 0), 1, cv2.LINE_AA)
        elif o["type"] == "circle":
            cv2.circle(out, (o["cx"], o["cy"]), o["r"], (255, 180, 0), 1)
            cv2.putText(out, o["label"], (o["cx"]+o["r"]+3, o["cy"]), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 180, 0), 1, cv2.LINE_AA)
    y = 55
    for m in measurements:
        val = "N/A" if m.value_mm is None else f"{m.value_mm:.4f}mm"
        state = "" if m.passed is None else ("OK" if m.passed else "NG")
        cv2.putText(out, f"{m.name}: {val} {state}", (15, y), cv2.FONT_HERSHEY_SIMPLEX, 0.43, (240, 240, 240), 1, cv2.LINE_AA)
        y += 17
    return out
