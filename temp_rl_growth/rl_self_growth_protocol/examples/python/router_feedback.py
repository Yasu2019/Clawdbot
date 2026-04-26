"""
モデル別の履歴スコアを見て、簡単な優先順位を決める例。
本番では Langfuse / DB 集計結果を使う想定です。
"""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable


def choose_model(task_type: str, records: Iterable[dict]) -> str:
    bucket = defaultdict(list)
    for r in records:
        if r.get("task_type") != task_type:
            continue
        bucket[r.get("model", "unknown")].append(float(r.get("score", 0)))

    if not bucket:
        return "gemini-2.5-flash"

    model_avgs = {
        model: sum(scores) / len(scores)
        for model, scores in bucket.items()
        if scores
    }
    return max(model_avgs, key=model_avgs.get)


if __name__ == "__main__":
    sample = [
        {"task_type": "email_editing", "model": "gemini-2.5-flash", "score": 4.4},
        {"task_type": "email_editing", "model": "claude-opus-4.6", "score": 4.7},
        {"task_type": "technical_protocol", "model": "gemini-2.5-pro", "score": 4.6},
        {"task_type": "technical_protocol", "model": "qwen2.5-coder:14b", "score": 3.8},
    ]
    print(choose_model("technical_protocol", sample))
