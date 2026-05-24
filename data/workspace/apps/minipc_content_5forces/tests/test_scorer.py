from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.schemas import ContentIdea
from app.scorer import ContentFiveForcesScorer


def test_quality_vba_scores_high():
    scorer = ContentFiveForcesScorer(config_dir=ROOT / "configs")
    result = scorer.evaluate(ContentIdea(
        title="NEXIV測定データをExcel VBAで検査成績書へ自動転記する方法",
        target_audience="製造業の品質保証担当者",
        pain="転記ミスと工数が大きい",
        proof="NEXIV出力と検査成績書の実務経験",
        unique_angle="品質保証の現場でそのまま使える",
        preferred_platform="note",
    ))
    assert result.total_score >= 65


def test_generic_ai_get_rich_scores_lower():
    scorer = ContentFiveForcesScorer(config_dir=ROOT / "configs")
    result = scorer.evaluate(ContentIdea(
        title="ChatGPTで誰でも簡単に月100万円稼ぐ方法",
        target_audience="副業初心者",
        pain="お金を稼ぎたい",
        proof="一般情報",
        unique_angle="一般論",
        preferred_platform="note",
    ))
    assert result.total_score < 65
