from __future__ import annotations

from typing import Any, Literal
from pydantic import BaseModel, Field


Platform = Literal["note", "kindle", "youtube", "tiktok", "minigame", "auto"]


class ContentIdea(BaseModel):
    title: str = Field(..., description="企画タイトル")
    target_audience: str = Field(default="", description="想定読者・視聴者")
    pain: str = Field(default="", description="読者の困りごと")
    proof: str = Field(default="", description="自分が示せる証拠・経験・サンプル")
    unique_angle: str = Field(default="", description="独自切り口")
    preferred_platform: Platform = Field(default="auto", description="希望媒体")
    confidential_level: Literal["public_sample", "internal_only", "secret"] = "public_sample"


class ForceScore(BaseModel):
    name: str
    score: int
    max_score: int
    reason: str


class EvaluationResult(BaseModel):
    title: str
    total_score: int
    decision: str
    recommended_platform: str
    force_scores: list[ForceScore]
    risks: list[str]
    next_actions: list[str]
    outline: list[str]
    safe_publication_notes: list[str]
    raw_features: dict[str, Any]
