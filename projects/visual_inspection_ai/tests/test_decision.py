from inspection_ai.decision.ensemble import decide
from inspection_ai.schemas import DetectionResult, QualityResult


def recipe():
    return {
        "model": {"review_threshold": 0.01, "ng_threshold": 0.05},
        "review": {"require_review_on_quality_failure": True, "require_review_on_measurement_failure": True},
    }


def test_decision_thresholds():
    quality = QualityResult(passed=True, blur_score=100, brightness=100)
    assert decide(DetectionResult(anomaly_score=0.001), quality, [], recipe())[0] == "OK"
    assert decide(DetectionResult(anomaly_score=0.02), quality, [], recipe())[0] == "REVIEW"
    assert decide(DetectionResult(anomaly_score=0.08), quality, [], recipe())[0] == "NG"


def test_quality_failure_is_review():
    quality = QualityResult(passed=False, blur_score=1, brightness=100, reasons=["blur"])
    decision, reasons = decide(DetectionResult(anomaly_score=0), quality, [], recipe())
    assert decision == "REVIEW"
    assert "blur" in reasons
