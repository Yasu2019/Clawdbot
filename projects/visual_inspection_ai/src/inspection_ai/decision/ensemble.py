from __future__ import annotations

from inspection_ai.schemas import DetectionResult, MeasurementItem, QualityResult


def decide(
    detection: DetectionResult,
    quality: QualityResult,
    measurements: list[MeasurementItem],
    recipe: dict,
) -> tuple[str, list[str]]:
    model = recipe.get("model", {})
    review_t = float(model.get("review_threshold", 0.03))
    ng_t = float(model.get("ng_threshold", 0.08))
    review_cfg = recipe.get("review", {})
    reasons: list[str] = []

    if not quality.passed and review_cfg.get("require_review_on_quality_failure", True):
        reasons.extend(quality.reasons)
        return "REVIEW", reasons

    failed_measurements = [m for m in measurements if m.passed is False]
    uncertain_measurements = [m for m in measurements if m.value_mm is None]
    if failed_measurements:
        reasons.extend([f"寸法規格外: {m.name}={m.value_mm}" for m in failed_measurements])
        return "NG", reasons
    if uncertain_measurements and review_cfg.get("require_review_on_measurement_failure", True):
        reasons.extend([f"寸法測定不能: {m.name}" for m in uncertain_measurements])
        return "REVIEW", reasons

    score = detection.anomaly_score
    if score >= ng_t:
        reasons.append(f"異常スコアがNGしきい値以上: {score:.4f} >= {ng_t:.4f}")
        return "NG", reasons
    if score >= review_t:
        reasons.append(f"異常スコアが確認帯: {review_t:.4f} <= {score:.4f} < {ng_t:.4f}")
        return "REVIEW", reasons
    reasons.append(f"異常スコアがOK範囲: {score:.4f} < {review_t:.4f}")
    return "OK", reasons
