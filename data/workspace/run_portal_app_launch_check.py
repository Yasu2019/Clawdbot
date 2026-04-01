#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
STATUS_PATH = ROOT / "data" / "workspace" / "portal_app_launch_check_status.json"
SMOKE_REPORT_PATH = ROOT / "data" / "workspace" / "playwright_smoke" / "artifacts" / "portal_app_launch_check.json"
CONTAINER = "clawstack-unified-clawdbot-gateway-1"
SCRIPT_PATH = "/home/node/clawd/playwright_smoke/check_portal_apps.js"
JST = timezone(timedelta(hours=9))


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> int:
    status = {
        "startedAt": now_jst(),
        "step": "run_browser_smoke",
        "container": CONTAINER,
        "script": SCRIPT_PATH,
    }
    write_status(status)

    result = subprocess.run(
        ["docker", "exec", CONTAINER, "sh", "-lc", f"node {SCRIPT_PATH}"],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=900,
    )

    status["stdoutTail"] = result.stdout[-4000:]
    status["stderrTail"] = result.stderr[-4000:]
    status["returncode"] = result.returncode

    if result.returncode != 0:
        status["step"] = "failed_to_execute"
        status["finishedAt"] = now_jst()
        write_status(status)
        print(result.stdout)
        print(result.stderr, file=sys.stderr)
        return result.returncode

    report = json.loads(result.stdout)
    failures = [item for item in report.get("results", []) if not item.get("ok")]
    status.update(
        {
            "step": "completed",
            "finishedAt": now_jst(),
            "reportPath": str(SMOKE_REPORT_PATH),
            "total": report.get("total"),
            "passed": report.get("passed"),
            "failed": report.get("failed"),
            "failedApps": [
                {
                    "name": item.get("name"),
                    "url": item.get("url"),
                    "status": item.get("status"),
                    "error": item.get("error"),
                    "screenshot": item.get("screenshot"),
                }
                for item in failures
            ],
        }
    )
    write_status(status)
    print(json.dumps(status, ensure_ascii=True, indent=2))
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
