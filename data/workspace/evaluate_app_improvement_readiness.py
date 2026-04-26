#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "app_improvement_readiness_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def evaluate() -> dict[str, Any]:
    email_quality = load_json(WORKSPACE / "email_request_quality_status.json")
    complaint_quality = load_json(WORKSPACE / "complaint_query_quality_status.json")
    workstudy_quality = load_json(WORKSPACE / "workstudy_benchmark_status.json")

    checks: list[dict[str, Any]] = []

    deadline = float((email_quality.get("metrics") or {}).get("deadline_detection_rate", 0.0))
    checks.append(
        {
            "key": "email_deadline_quality",
            "passed": deadline >= 80.0,
            "value": deadline,
            "target": 80.0,
            "detail": f"deadline_detection_rate={deadline}%",
        }
    )

    complaint_include = float((complaint_quality.get("metrics") or {}).get("avg_include_hit_rate", 0.0))
    complaint_clean = float((complaint_quality.get("metrics") or {}).get("avg_exclude_clean_rate", 0.0))
    checks.append(
        {
            "key": "complaint_retrieval_quality",
            "passed": complaint_include >= 80.0 and complaint_clean >= 95.0,
            "value": {"include": complaint_include, "clean": complaint_clean},
            "target": {"include": 80.0, "clean": 95.0},
            "detail": f"include={complaint_include}% clean={complaint_clean}%",
        }
    )

    workstudy_stage = workstudy_quality.get("stage")
    workstudy_exact = float((workstudy_quality.get("metrics") or {}).get("exact_match_rate", 0.0))
    checks.append(
        {
            "key": "workstudy_benchmark",
            "passed": workstudy_stage == "completed" and workstudy_exact >= 85.0,
            "value": {"stage": workstudy_stage, "exact_match_rate": workstudy_exact},
            "target": {"stage": "completed", "exact_match_rate": 85.0},
            "detail": f"stage={workstudy_stage} exact_match_rate={workstudy_exact}%",
        }
    )

    passed = sum(1 for item in checks if item["passed"])
    readiness = "ready" if passed == len(checks) else "partial"
    return {
        "generatedAt": now_jst_text(),
        "readiness": readiness,
        "passedChecks": passed,
        "totalChecks": len(checks),
        "checks": checks,
        "promotionRule": "Promote a new harness only if primary KPI improves without material safety regression.",
        "successCriteria": [
            "better task completion quality",
            "better retrieval relevance",
            "lower hallucination or noise",
            "lower unnecessary retries",
            "lower human editing effort",
            "strong traceability and rollback safety",
        ],
    }


def main() -> int:
    payload = evaluate()
    write_status(payload)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
