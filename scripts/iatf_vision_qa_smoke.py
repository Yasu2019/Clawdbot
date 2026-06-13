# -*- coding: utf-8 -*-
"""Smoke-test IATF vision_checks consent path (loads .env, runs vision runner)."""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
PIPELINE = ROOT / "clawstack_v2" / "apps" / "iatf_video_factory" / "pipeline"

try:
    from dotenv import load_dotenv

    load_dotenv(ROOT / ".env", override=False)
except ImportError:
    pass

sys.path.insert(0, str(PIPELINE))
import visual_qa_vision_runner as vqr  # noqa: E402


def main() -> int:
    sample = ROOT / "1.jpg"
    if not sample.exists():
        sample = next(ROOT.glob("*.jpg"), None)
    if not sample or not sample.exists():
        print(json.dumps({"ok": False, "error": "no sample jpg in repo root"}))
        return 2

    with tempfile.TemporaryDirectory(prefix="iatf_vision_smoke_") as td:
        report_dir = Path(td)
        result = vqr.run_vision_checks(
            contact_sheet=sample,
            report_dir=report_dir,
            mode="render",
            stage="smoke",
        )
        payload = {
            "enabled": vqr.vision_qa_enabled(),
            "consent": vqr.vision_qa_consent(),
            "result": result,
            "report_dir": str(report_dir),
        }
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if result.get("skipped"):
            return 0 if result.get("ok") else 1
        return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
