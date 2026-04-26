#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_PATH = WORKSPACE / "meta_harness_repo_scan_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def main() -> int:
    payload = {
        "generatedAt": now_jst_text(),
        "decision": "ADOPT_PARTIAL",
        "items": [
            {
                "location": "AGENTS.md",
                "purpose": "safety, adoption gate, benchmark promotion rule",
                "maturity": "active",
                "overlap": "high",
                "adoption": "extend_existing",
            },
            {
                "location": "data/workspace/continuous_system_improvement.py",
                "purpose": "patrol, weakness detection, safe repair loop",
                "maturity": "active",
                "overlap": "high",
                "adoption": "extend_existing",
            },
            {
                "location": "data/workspace/run_app_quality_snapshot.py",
                "purpose": "daily benchmark snapshot",
                "maturity": "active",
                "overlap": "medium",
                "adoption": "extend_existing",
            },
            {
                "location": "data/workspace/playwright_smoke/check_portal_apps.js",
                "purpose": "portal and app launch verification",
                "maturity": "active",
                "overlap": "medium",
                "adoption": "keep_current",
            },
            {
                "location": "data/workspace/meta_harness_repo_scan_checklist.md",
                "purpose": "pre-adoption repo scan checklist",
                "maturity": "new",
                "overlap": "low",
                "adoption": "adopt_partial",
            },
        ],
    }
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
