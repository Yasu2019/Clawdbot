#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "workstudy_benchmark_scaffold_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict[str, Any]) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_labels(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("labels.json must be a list.")
    return data


def pick_segments(labels: list[dict[str, Any]], max_segments: int) -> list[dict[str, Any]]:
    preferred = [item for item in labels if not item.get("review_required")]
    source = preferred if preferred else labels
    picked: list[dict[str, Any]] = []
    for item in source[:max_segments]:
        picked.append(
            {
                "segment_id": int(item.get("segment_id", len(picked))),
                "label": item.get("label", "UNKNOWN"),
                "weight": 1.0,
                "note": item.get("label_jp") or "",
            }
        )
    return picked


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("labels_path")
    parser.add_argument("--case-id", default="workstudy_case_001")
    parser.add_argument("--output", default=str(WORKSPACE / "workstudy_benchmark_candidate.json"))
    parser.add_argument("--max-segments", type=int, default=12)
    args = parser.parse_args()

    labels_path = Path(args.labels_path)
    output_path = Path(args.output)
    status: dict[str, Any] = {
        "startedAt": now_jst_text(),
        "labelsPath": str(labels_path),
        "outputPath": str(output_path),
        "stage": "starting",
    }
    write_status(status)

    if not labels_path.exists():
        status.update({"stage": "error", "finishedAt": now_jst_text(), "message": "labels.json not found."})
        write_status(status)
        return 1

    labels = load_labels(labels_path)
    expected_segments = pick_segments(labels, args.max_segments)
    payload = {
        "cases": [
            {
                "case_id": args.case_id,
                "predicted_labels_path": str(labels_path),
                "notes": "候補として自動生成した benchmark です。label を見直して workstudy_benchmark.json へ転記してください。",
                "expected_segments": expected_segments,
            }
        ]
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    status.update(
        {
            "stage": "completed",
            "finishedAt": now_jst_text(),
            "segmentCount": len(labels),
            "selectedSegments": len(expected_segments),
        }
    )
    write_status(status)
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

