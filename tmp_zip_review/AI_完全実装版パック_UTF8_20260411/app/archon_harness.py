from __future__ import annotations
from pathlib import Path
from datetime import datetime
import hashlib
import json
import os
import difflib
from typing import Dict, List

RUN_COUNT = int(os.getenv("RUN_COUNT", "5"))
LOG_DIR = Path(os.getenv("LOG_DIR", "/logs"))
MODEL_NAME = os.getenv("MODEL_NAME", "demo-model")
STABILITY_THRESHOLD = float(os.getenv("STABILITY_THRESHOLD", "0.80"))

TASKS_PATH = Path(__file__).parent / "sample_tasks.json"

def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def simulate_model_output(prompt: str, run_index: int) -> str:
    # 実運用ではここをLiteLLM / OpenAI互換API呼び出しに置き換える
    # デモ用に少しぶれる可能性のある出力を作る
    suffix = "" if run_index % 2 == 0 else "。"
    return f"[MODEL={MODEL_NAME}] {prompt.strip()}{suffix}"

def normalize(text: str) -> str:
    return " ".join(text.replace("。", "").split()).strip().lower()

def similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, a, b).ratio()

def main() -> None:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tasks = json.loads(TASKS_PATH.read_text(encoding="utf-8"))
    summary: List[Dict] = []

    for task in tasks:
        task_id = task["task_id"]
        prompt = task["prompt"]
        input_hash = hash_text(prompt)
        outputs = []

        for i in range(1, RUN_COUNT + 1):
            raw = simulate_model_output(prompt, i)
            norm = normalize(raw)

            raw_path = LOG_DIR / f"{task_id}_run{i}_raw.txt"
            norm_path = LOG_DIR / f"{task_id}_run{i}_norm.txt"
            raw_path.write_text(raw, encoding="utf-8")
            norm_path.write_text(norm, encoding="utf-8")

            outputs.append({
                "run_index": i,
                "raw": raw,
                "norm": norm,
                "raw_path": str(raw_path),
                "norm_path": str(norm_path),
            })

        base_norm = outputs[0]["norm"]
        scores = []
        for out in outputs[1:]:
            scores.append(similarity(base_norm, out["norm"]))

        avg_score = sum(scores) / len(scores) if scores else 1.0
        label = "pass" if avg_score >= STABILITY_THRESHOLD else "review"

        task_log = {
            "task_id": task_id,
            "task_name": task["task_name"],
            "model": MODEL_NAME,
            "input_hash": input_hash,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "average_similarity": avg_score,
            "result_label": label,
            "run_count": RUN_COUNT,
        }
        (LOG_DIR / f"{task_id}_summary.json").write_text(
            json.dumps(task_log, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )
        summary.append(task_log)

    (LOG_DIR / "all_tasks_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    print("Archon harness demo completed.")
    print(json.dumps(summary, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
