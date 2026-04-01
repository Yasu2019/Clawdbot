#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
DEFAULT_BENCHMARK = WORKSPACE / "complaint_query_benchmark.json"
STATUS_PATH = WORKSPACE / "complaint_query_quality_status.json"
EMAIL_QUERY_SCRIPT = WORKSPACE / "email_search_query.py"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def pct(num: float, den: float) -> float:
    return round((num / den) * 100.0, 1) if den else 0.0


def run_query(query: str, limit: int) -> dict[str, Any]:
    result = subprocess.run(
        [sys.executable, str(EMAIL_QUERY_SCRIPT), "complaint-context", query, "--limit", str(limit)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
        check=True,
    )
    return json.loads(result.stdout)


def contains_any(blob: str, values: list[str]) -> bool:
    lowered = blob.casefold()
    return any(value.casefold() in lowered for value in values)


def evaluate_query(case: dict[str, Any]) -> dict[str, Any]:
    payload = run_query(case["query"], int(case.get("limit", 5)))
    rows = payload.get("results", [])
    subjects = [str(row.get("normalized_subject") or row.get("subject") or "") for row in rows]

    include_terms = list(case.get("must_include_subject_terms", []))
    exclude_terms = list(case.get("must_exclude_subject_terms", []))

    include_hits = sum(1 for subject in subjects if contains_any(subject, include_terms)) if include_terms else 0
    exclude_hits = sum(1 for subject in subjects if contains_any(subject, exclude_terms)) if exclude_terms else 0

    return {
        "query": case["query"],
        "limit": int(case.get("limit", 5)),
        "result_count": len(rows),
        "include_hit_rate": pct(include_hits, len(rows)) if include_terms else 0.0,
        "exclude_clean_rate": pct(len(rows) - exclude_hits, len(rows)) if exclude_terms else 100.0,
        "top_subjects": subjects[:5],
        "raw": payload,
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
                "message": "Benchmark file not found. Copy complaint_query_benchmark_template.json to complaint_query_benchmark.json and fill expected include/exclude terms.",
            }
        )
        write_status(status)
        return 0

    benchmark = json.loads(benchmark_path.read_text(encoding="utf-8"))
    queries = benchmark.get("queries", [])
    if not queries:
        status.update(
            {
                "stage": "pending",
                "finishedAt": now_jst_text(),
                "message": "Benchmark file exists but has no queries.",
            }
        )
        write_status(status)
        return 0

    status["stage"] = "evaluating"
    write_status(status)

    query_results = [evaluate_query(query) for query in queries]
    include_rates = [item["include_hit_rate"] for item in query_results if item["include_hit_rate"] > 0]
    exclude_rates = [item["exclude_clean_rate"] for item in query_results]

    status.update(
        {
            "stage": "completed",
            "finishedAt": now_jst_text(),
            "queryCount": len(query_results),
            "metrics": {
                "avg_include_hit_rate": round(sum(include_rates) / len(include_rates), 1) if include_rates else 0.0,
                "avg_exclude_clean_rate": round(sum(exclude_rates) / len(exclude_rates), 1) if exclude_rates else 0.0,
            },
            "queries": [
                {
                    "query": item["query"],
                    "result_count": item["result_count"],
                    "include_hit_rate": item["include_hit_rate"],
                    "exclude_clean_rate": item["exclude_clean_rate"],
                    "top_subjects": item["top_subjects"],
                }
                for item in query_results
            ],
        }
    )
    write_status(status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
