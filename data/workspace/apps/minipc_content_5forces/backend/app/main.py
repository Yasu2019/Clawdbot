from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .schemas import ContentIdea, EvaluationResult
from .scorer import ContentFiveForcesScorer

app = FastAPI(
    title="MiniPC Content 5-Forces Gate",
    description="Portal向けの売れるテーマ判定ゲート。note/Kindle/YouTube/TikTok/ミニゲーム生成の前処理に使います。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

scorer = ContentFiveForcesScorer()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "encoding": "utf-8"}


@app.post("/evaluate", response_model=EvaluationResult)
def evaluate(idea: ContentIdea) -> EvaluationResult:
    return scorer.evaluate(idea)


@app.get("/sample")
def sample() -> dict:
    idea = ContentIdea(
        title="NEXIV測定データをExcel VBAで検査成績書へ自動転記する方法",
        target_audience="製造業の品質保証担当者",
        pain="転記ミス、成績書作成時間、属人化",
        proof="NEXIV出力、検査成績書、VBA実務",
        unique_angle="品質保証の現場で使える実装例",
        preferred_platform="note",
    )
    return scorer.evaluate(idea).model_dump()
