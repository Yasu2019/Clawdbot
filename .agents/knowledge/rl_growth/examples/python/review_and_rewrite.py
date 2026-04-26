"""
レビュー→改善だけを独立で試す簡易例
"""

from __future__ import annotations

import json
import os
from openai import OpenAI


def read_text(path: str) -> str:
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main() -> None:
    client = OpenAI(
        base_url=os.environ.get("LITELLM_BASE_URL"),
        api_key=os.environ.get("LITELLM_API_KEY") or os.environ.get("OPENAI_API_KEY"),
    )

    answer = "回答本文をここに入れる"
    task_text = "ユーザーはOpenClaw用の自己改善プロトコルを求めている"

    reviewer_prompt = read_text("../../templates/reviewer_prompt.txt")
    review = client.chat.completions.create(
        model=os.environ.get("REVIEW_MODEL", "gpt-4.1"),
        temperature=0,
        messages=[
            {"role": "system", "content": reviewer_prompt},
            {"role": "user", "content": f"Task:\n{task_text}\n\nAnswer:\n{answer}"},
        ],
    ).choices[0].message.content

    review_json = json.loads(review)
    print("=== REVIEW ===")
    print(json.dumps(review_json, ensure_ascii=False, indent=2))

    if review_json["verdict"] == "rewrite":
        improver_prompt = read_text("../../templates/improver_prompt.txt")
        rewritten = client.chat.completions.create(
            model=os.environ.get("IMPROVER_MODEL", "gpt-4.1"),
            temperature=0.2,
            messages=[
                {"role": "system", "content": improver_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Task:\n{task_text}\n\n"
                        f"Original answer:\n{answer}\n\n"
                        f"Review JSON:\n{json.dumps(review_json, ensure_ascii=False, indent=2)}"
                    ),
                },
            ],
        ).choices[0].message.content

        print("=== REWRITTEN ===")
        print(rewritten)


if __name__ == "__main__":
    main()
