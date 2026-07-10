from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable

import cv2

from inspection_ai.detection.reference_model import ReferenceDifferenceDetector
from inspection_ai.preprocessing.image_ops import apply_roi


@dataclass
class Metrics:
    total: int
    correct: int
    tp: int
    tn: int
    fp: int
    fn: int
    accuracy: float
    precision: float
    recall: float
    f1: float

    def to_dict(self):
        return asdict(self)


def evaluate_labeled_paths(
    model_path: str | Path,
    recipe: dict,
    labeled: Iterable[tuple[str | Path, str]],
) -> Metrics:
    detector = ReferenceDifferenceDetector(model_path, recipe)
    ng_t = float(recipe.get("model", {}).get("review_threshold", 0.03))
    tp = tn = fp = fn = 0
    for path, expected in labeled:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        roi, offset = apply_roi(image, recipe.get("image", {}).get("roi"))
        result, _ = detector.predict(roi, offset)
        pred = "NG" if result.anomaly_score >= ng_t else "OK"
        expected = expected.upper()
        if pred == "NG" and expected == "NG": tp += 1
        elif pred == "OK" and expected == "OK": tn += 1
        elif pred == "NG" and expected == "OK": fp += 1
        elif pred == "OK" and expected == "NG": fn += 1
    total = tp + tn + fp + fn
    correct = tp + tn
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return Metrics(total, correct, tp, tn, fp, fn, correct/total if total else 0.0, precision, recall, f1)
