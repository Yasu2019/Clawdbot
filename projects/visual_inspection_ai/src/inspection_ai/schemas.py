from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field

Decision = Literal["OK", "NG", "REVIEW", "ERROR"]


class Region(BaseModel):
    x: int
    y: int
    width: int
    height: int
    area: int
    score: float = 0.0
    label: str = "anomaly"


class QualityResult(BaseModel):
    passed: bool
    blur_score: float
    brightness: float
    reasons: list[str] = Field(default_factory=list)


class MeasurementItem(BaseModel):
    name: str
    value_mm: float | None
    lower_mm: float | None = None
    upper_mm: float | None = None
    passed: bool | None = None
    confidence: float = 0.0
    method: str


class DetectionResult(BaseModel):
    anomaly_score: float
    regions: list[Region] = Field(default_factory=list)
    heatmap_path: str | None = None
    model_version: str = "unregistered"
    diagnostics: dict[str, Any] = Field(default_factory=dict)


class InspectionResult(BaseModel):
    inspection_id: str
    product_id: str
    decision: Decision
    reasons: list[str]
    anomaly_score: float
    quality: QualityResult
    measurements: list[MeasurementItem]
    regions: list[Region]
    original_image_url: str
    annotated_image_url: str
    heatmap_image_url: str | None = None
    model_version: str
    elapsed_ms: dict[str, float]
    created_at: str


class ReviewLabelRequest(BaseModel):
    decision: Literal["OK", "NG"]
    defect_mode: str = ""
    comment: str = ""
    use_for_training: bool = True
    reviewer: str = "user"


class PromoteRequest(BaseModel):
    confirm: bool
    approved_by: str = "user"
    note: str = ""
