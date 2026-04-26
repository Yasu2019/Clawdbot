#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DEFAULT_BENCHMARK = WORKSPACE / "workstudy_benchmark.json"
STATUS_PATH = WORKSPACE / "workstudy_benchmark_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def pct(num: float, den: float) -> float:
    return round((num / den) * 100.0, 1) if den else 0.0


def normalize_label(label: str) -> str:
    mapping = {
        "GET": "G",
        "PUT": "P",
        "MOVE": "TE",
        "WAIT": "ADe",
        "INSPECT": "I",
        "POSITION": "P",
        "USE_TOOL": "U",
    }
    upper = (label or "").strip().upper()
    return mapping.get(upper, upper)


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    predicted_path = Path(case["predicted_labels_path"])
    labels = load_json(predicted_path)
    labels_by_id = {int(item.get("segment_id", -1)): item for item in labels}

    matches = 0
    total = 0
    weighted_matches = 0.0
    weighted_total = 0.0

    for expected in case.get("expected_segments", []):
        segment_id = int(expected["segment_id"])
        predicted = labels_by_id.get(segment_id)
        weight = float(expected.get("weight", 1.0))
        total += 1
        weighted_total += weight
        if predicted and normalize_label(predicted.get("label", "")) == normalize_label(expected.get("label", "")):
            matches += 1
            weighted_matches += weight

    review_required_ratio = pct(
        sum(1 for item in labels if item.get("review_required")),
        len(labels),
    )
    unknown_ratio = pct(
        sum(1 for item in labels if normalize_label(item.get("label", "")) == "UNKNOWN"),
        len(labels),
    )

    return {
        "case_id": case["case_id"],
        "predicted_labels_path": str(predicted_path),
        "segment_count": len(labels),
        "benchmark_segment_count": total,
        "exact_match_rate": pct(matches, total),
        "weighted_match_rate": pct(weighted_matches, weighted_total),
        "review_required_ratio": review_required_ratio,
        "unknown_ratio": unknown_ratio,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", default=str(DEFAULT_BENCHMARK))
    args = parser.parse_args()

    benchmark_path = Path(args.benchmark)
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "benchmarkPath": str(benchmark_path),
        "stage": "starting",
    }
    write_status(status)

    if not benchmark_path.exists():
        status.update(
            {
                "stage": "pending",
                "finishedAt": now_jst_text(),
                "message": "Benchmark file not found. Copy workstudy_benchmark_template.json to workstudy_benchmark.json and fill expected segments.",
            }
        )
        write_status(status)
        return 0

    benchmark = load_json(benchmark_path)
    cases = benchmark.get("cases", [])
    if not cases:
        status.update(
            {
                "stage": "pending",
                "finishedAt": now_jst_text(),
                "message": "Benchmark file exists but has no cases.",
            }
        )
        write_status(status)
        return 0

    status["stage"] = "evaluating"
    write_status(status)

    case_results = [evaluate_case(case) for case in cases]
    exact_avg = sum(item["exact_match_rate"] for item in case_results) / max(len(case_results), 1)
    weighted_avg = sum(item["weighted_match_rate"] for item in case_results) / max(len(case_results), 1)
    review_avg = sum(item["review_required_ratio"] for item in case_results) / max(len(case_results), 1)
    unknown_avg = sum(item["unknown_ratio"] for item in case_results) / max(len(case_results), 1)

    status.update(
        {
            "stage": "completed",
            "finishedAt": now_jst_text(),
            "caseCount": len(case_results),
            "metrics": {
                "exact_match_rate": round(exact_avg, 1),
                "weighted_match_rate": round(weighted_avg, 1),
                "review_required_ratio": round(review_avg, 1),
                "unknown_ratio": round(unknown_avg, 1),
            },
            "cases": case_results,
        }
    )
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
