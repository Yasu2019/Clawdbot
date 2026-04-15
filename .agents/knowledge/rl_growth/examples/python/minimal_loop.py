"""
最小の自己改善ループ実装例
- 初回回答生成
- レビュー
- 必要時リライト
- Qdrantへ保存

実運用では、OpenClaw の応答後フックや orchestrator に組み込む想定です。
"""

from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass
from typing import Any

from openai import OpenAI


@dataclass
class Task:
    task_type: str
    user_input: str
    user_goal: str


def get_client() -> OpenAI:
    base_url = os.environ.get("LITELLM_BASE_URL")
    api_key = os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY")
    return OpenAI(base_url=base_url, api_key=api_key)


def chat_completion(model: str, system_prompt: str, user_prompt: str) -> str:
    client = get_client()
    response = client.chat.completions.create(
        model=model,
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )
    return response.choices[0].message.content or ""


def load_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def solve_task(task: Task) -> str:
    system_prompt = (
        "You are a practical assistant."
        " Produce accurate, usable answers with explicit assumptions when needed."
    )
    user_prompt = f"Task type: {task.task_type}\nGoal: {task.user_goal}\nInput:\n{task.user_input}"
    model = os.environ.get("TASK_MODEL", "gpt-4.1")
    return chat_completion(model, system_prompt, user_prompt)


def review_answer(task: Task, answer: str) -> dict[str, Any]:
    prompt = load_text("../../templates/reviewer_prompt.txt")
    user_prompt = (
        f"Task type: {task.task_type}\n"
        f"Goal: {task.user_goal}\n"
        f"User input:\n{task.user_input}\n\n"
        f"Assistant answer:\n{answer}"
    )
    model = os.environ.get("REVIEW_MODEL", "gpt-4.1")
    raw = chat_completion(model, prompt, user_prompt)
    return json.loads(raw)


def improve_answer(task: Task, answer: str, review: dict[str, Any]) -> str:
    prompt = load_text("../../templates/improver_prompt.txt")
    user_prompt = (
        f"Task type: {task.task_type}\n"
        f"Goal: {task.user_goal}\n"
        f"User input:\n{task.user_input}\n\n"
        f"Original answer:\n{answer}\n\n"
        f"Review JSON:\n{json.dumps(review, ensure_ascii=False, indent=2)}"
    )
    model = os.environ.get("IMPROVER_MODEL", "gpt-4.1")
    return chat_completion(model, prompt, user_prompt)


def main() -> None:
    task = Task(
        task_type="technical_protocol",
        user_input="OpenClaw + LiteLLM + Langfuse + Qdrant の自己成長ループを設計したい",
        user_goal="現場で試せる最小構成を出したい",
    )

    started = time.time()
    task_id = str(uuid.uuid4())

    first_answer = solve_task(task)
    review = review_answer(task, first_answer)

    threshold = 4.0
    final_answer = first_answer
    if float(review.get("total_score", 0)) < threshold or review.get("verdict") == "rewrite":
        final_answer = improve_answer(task, first_answer, review)

    elapsed_ms = int((time.time() - started) * 1000)

    result = {
        "task_id": task_id,
        "task_type": task.task_type,
        "input_summary": task.user_input[:200],
        "user_goal": task.user_goal,
        "initial_answer": first_answer,
        "final_answer": final_answer,
        "review": review,
        "latency_ms": elapsed_ms,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
