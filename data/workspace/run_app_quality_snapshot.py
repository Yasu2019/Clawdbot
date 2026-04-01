#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_PATH = WORKSPACE / "app_quality_snapshot_status.json"
JST = timezone(timedelta(hours=9))

TASKS = [
    {
        "name": "email_request_quality",
        "command": [sys.executable, str(WORKSPACE / "evaluate_email_request_quality.py")],
        "status_path": WORKSPACE / "email_request_quality_status.json",
    },
    {
        "name": "complaint_query_quality",
        "command": [sys.executable, str(WORKSPACE / "evaluate_complaint_query_quality.py")],
        "status_path": WORKSPACE / "complaint_query_quality_status.json",
    },
    {
        "name": "workstudy_benchmark",
        "command": [sys.executable, str(WORKSPACE / "evaluate_workstudy_benchmark.py")],
        "status_path": WORKSPACE / "workstudy_benchmark_status.json",
    },
    {
        "name": "workstudy_project_inventory",
        "command": [sys.executable, str(WORKSPACE / "list_workstudy_projects.py")],
        "status_path": WORKSPACE / "workstudy_project_inventory.json",
    },
    {
        "name": "app_improvement_readiness",
        "command": [sys.executable, str(WORKSPACE / "evaluate_app_improvement_readiness.py")],
        "status_path": WORKSPACE / "app_improvement_readiness_status.json",
    },
]


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def read_json(path: Path) -> dict:
    if not path.exists():
      return {}
    return json.loads(path.read_text(encoding="utf-8"))


def write_status(payload: dict) -> None:
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    summary = {
        "startedAt": now_jst_text(),
        "stage": "running",
        "results": [],
    }
    write_status(summary)

    return_code = 0
    for task in TASKS:
        result = subprocess.run(
            task["command"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=300,
        )
        payload = read_json(task["status_path"])
        entry = {
            "name": task["name"],
            "returncode": result.returncode,
            "stdoutTail": result.stdout[-2000:],
            "stderrTail": result.stderr[-2000:],
            "stage": payload.get("stage"),
            "finishedAt": payload.get("finishedAt"),
            "metrics": payload.get("metrics", {}),
            "message": payload.get("message", ""),
        }
        if result.returncode != 0:
            return_code = result.returncode
        summary["results"].append(entry)
        write_status(summary)

    summary["stage"] = "completed"
    summary["finishedAt"] = now_jst_text()
    write_status(summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return return_code


if __name__ == "__main__":
    raise SystemExit(main())
