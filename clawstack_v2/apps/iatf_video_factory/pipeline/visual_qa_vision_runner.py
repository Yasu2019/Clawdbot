# -*- coding: utf-8 -*-
"""Optional AI vision_checks batch for IATF visual QA (consent-gated, fail-closed)."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import visual_qa_checklist as vqc


def vision_qa_enabled() -> bool:
    return os.getenv("IATF_VISION_QA_ENABLED", "0").strip() == "1"


def vision_qa_consent() -> bool:
    return os.getenv("IATF_VISION_QA_CONSENT", "0").strip() == "1"


def run_vision_checks(
    *,
    contact_sheet: Path,
    report_dir: Path,
    mode: str = "render",
    stage: str = "pre_mp4",
) -> dict:
    """Run checklist vision_checks via ai_visual_reviewer when consent is set."""
    report_dir.mkdir(parents=True, exist_ok=True)
    out_path = report_dir / "visual_qa_vision_report.json"

    if not vision_qa_enabled():
        stub = {
            "ok": True,
            "skipped": True,
            "reason": "IATF_VISION_QA_ENABLED=0",
            "stage": stage,
        }
        out_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
        return stub

    if not vision_qa_consent():
        stub = {
            "ok": True,
            "skipped": True,
            "reason": "IATF_VISION_QA_CONSENT=0 (cloud vision requires explicit consent)",
            "stage": stage,
        }
        out_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
        return stub

    checklist = vqc.load_checklist()
    vision_checks = vqc.vision_checks_for_mode(checklist, mode)
    if not vision_checks:
        stub = {"ok": True, "skipped": True, "reason": "no vision_checks for mode", "mode": mode}
        out_path.write_text(json.dumps(stub, ensure_ascii=False, indent=2), encoding="utf-8")
        return stub

    reviewer = Path(__file__).resolve().parent / "ai_visual_reviewer.py"
    request = {
        "task": f"IATF {mode} visual QA vision_checks batch ({stage})",
        "contact_sheet": str(contact_sheet),
        "vision_checks": vision_checks,
        "mode": mode,
        "required_decision": {"approved": "boolean", "reason": "string"},
    }
    req_path = report_dir / "visual_qa_vision_request.json"
    req_path.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")

    cmd = os.getenv("IATF_VIDEO_AI_REVIEW_CMD", "").strip()
    if not cmd:
        cmd = f"{sys.executable} {reviewer}"

    timeout = int(os.getenv("IATF_VISION_QA_TIMEOUT_SEC", "120"))
    proc = subprocess.run(
        [*cmd.split(), str(req_path)],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(reviewer.parent),
    )
    if proc.returncode != 0:
        result = {
            "ok": False,
            "approved": False,
            "reason": f"vision_reviewer exit {proc.returncode}: {(proc.stderr or '')[-400:]}",
            "stage": stage,
        }
        out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        return result

    try:
        payload = json.loads((proc.stdout or "").strip().splitlines()[-1])
    except json.JSONDecodeError:
        payload = {"approved": False, "reason": "invalid JSON from vision reviewer"}

    approved = bool(payload.get("approved"))
    result = {
        "ok": approved,
        "approved": approved,
        "reason": payload.get("reason", ""),
        "checks": payload.get("checks", []),
        "_method": payload.get("_method"),
        "mode": mode,
        "stage": stage,
        "vision_check_count": len(vision_checks),
    }
    out_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
