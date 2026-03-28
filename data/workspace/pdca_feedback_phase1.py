#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import json
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
PDCA_ROOT = WORKSPACE / "pdca_lab"
STATE_DIR = PDCA_ROOT / "state"
EXAMPLES_DIR = PDCA_ROOT / "examples"
MIRROR_ROOT = WORKSPACE.parents[1] / "clawstack_v2" / "data" / "work" / "pdca_lab"

STATUS_PATH = STATE_DIR / "status.json"
REGISTRY_PATH = STATE_DIR / "prompt_registry.json"
TASK_RUNS_PATH = STATE_DIR / "task_runs.jsonl"
TASK_SCORES_PATH = STATE_DIR / "task_scores.jsonl"
TASK_FEEDBACK_PATH = STATE_DIR / "task_feedback.jsonl"
PROMOTION_AUDIT_PATH = STATE_DIR / "promotion_audit.jsonl"


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def ensure_dirs() -> None:
    for path in [PDCA_ROOT, STATE_DIR, EXAMPLES_DIR, MIRROR_ROOT]:
        path.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, fallback: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    items: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            items.append(json.loads(line))
        except Exception:
            continue
    return items


def default_registry() -> dict[str, Any]:
    return {
        "updatedAt": now_jst_text(),
        "families": {
            "customer_reply": {
                "production": "customer_reply.v2026_03_29_01",
                "shadow": "customer_reply.v2026_03_29_02",
                "approval_required": True,
                "versions": [
                    {
                        "version_label": "customer_reply.v2026_03_29_01",
                        "state": "production",
                        "prompt_text": "Draft a factual, polite customer reply. Separate facts, requests, and hypotheses.",
                        "routing_policy_json": {"route": "litellm-default"},
                        "retrieval_policy_json": {"profile": "email_quality"},
                        "protected_blocks": ["external_communication_block", "citation_policy"]
                    },
                    {
                        "version_label": "customer_reply.v2026_03_29_02",
                        "state": "shadow",
                        "prompt_text": "Draft a factual customer reply with explicit open questions and next actions.",
                        "routing_policy_json": {"route": "litellm-default"},
                        "retrieval_policy_json": {"profile": "email_quality"},
                        "protected_blocks": ["external_communication_block", "citation_policy"]
                    }
                ]
            },
            "supplier_followup": {
                "production": "supplier_followup.v2026_03_29_01",
                "shadow": None,
                "approval_required": True,
                "versions": [
                    {
                        "version_label": "supplier_followup.v2026_03_29_01",
                        "state": "production",
                        "prompt_text": "Summarize supplier action items, due dates, and evidence requests in business Japanese.",
                        "routing_policy_json": {"route": "litellm-default"},
                        "retrieval_policy_json": {"profile": "supplier_email"},
                        "protected_blocks": ["external_communication_block"]
                    }
                ]
            },
            "internal_quality_summary": {
                "production": "internal_quality_summary.v2026_03_29_01",
                "shadow": None,
                "approval_required": False,
                "versions": [
                    {
                        "version_label": "internal_quality_summary.v2026_03_29_01",
                        "state": "production",
                        "prompt_text": "Summarize quality status with issue, containment, next action, and unresolved risk.",
                        "routing_policy_json": {"route": "litellm-default"},
                        "retrieval_policy_json": {"profile": "quality_issue_memory"},
                        "protected_blocks": ["legal_compliance_block"]
                    }
                ]
            }
        }
    }


def default_status() -> dict[str, Any]:
    return {
        "updatedAt": now_jst_text(),
        "latest_run_status": "setup_pending",
        "pending_review_count": 0,
        "current_production_prompt_version": "customer_reply.v2026_03_29_01",
        "current_shadow_prompt_version": "customer_reply.v2026_03_29_02",
        "latest_promotion": None,
        "latest_rollback": None,
        "latest_severe_issue": None,
        "counts": {
            "task_runs": 0,
            "task_scores": 0,
            "task_feedback": 0,
            "promotion_audit": 0
        },
        "recent_runs": [],
        "review_queue": []
    }


def sync_mirror(status: dict[str, Any], registry: dict[str, Any]) -> None:
    write_json(MIRROR_ROOT / "status.json", status)
    write_json(MIRROR_ROOT / "prompt_registry.json", registry)


def init_state() -> None:
    ensure_dirs()
    registry = read_json(REGISTRY_PATH, None) or default_registry()
    status = read_json(STATUS_PATH, None) or default_status()
    write_json(REGISTRY_PATH, registry)
    write_json(STATUS_PATH, status)
    for path in [TASK_RUNS_PATH, TASK_SCORES_PATH, TASK_FEEDBACK_PATH, PROMOTION_AUDIT_PATH]:
        path.touch(exist_ok=True)
    sync_mirror(status, registry)


def try_trace(payload: dict[str, Any], score: dict[str, Any]) -> None:
    try:
        from clawstack_tracing import ClawTrace

        with ClawTrace(
            name="pdca.capture",
            metadata={
                "task_type": payload.get("task_type"),
                "prompt_family": payload.get("prompt_family"),
                "prompt_version": payload.get("prompt_version"),
                "reviewer_outcome": payload.get("reviewer_outcome", "pending"),
                "pdca_phase": "phase1"
            },
            session_id=payload.get("task_run_id"),
        ) as trace:
            trace.span_n8n(
                workflow_id="pdca_capture_ingest",
                payload={"task_type": payload.get("task_type"), "prompt_version": payload.get("prompt_version")},
                result=f"overall_score={score['overall_score']}",
                status="captured",
                latency_ms=0,
            )
    except Exception:
        try:
            trace_payload = base64.urlsafe_b64encode(
                json.dumps(
                    {
                        "task_type": payload.get("task_type"),
                        "prompt_family": payload.get("prompt_family"),
                        "prompt_version": payload.get("prompt_version"),
                        "reviewer_outcome": payload.get("reviewer_outcome", "pending"),
                        "task_run_id": payload.get("task_run_id"),
                        "overall_score": score.get("overall_score"),
                    },
                    ensure_ascii=False,
                ).encode("utf-8")
            ).decode("ascii")
            script = (
                "import os,sys,base64,json; "
                "sys.path.append('/home/node/clawd'); "
                "from clawstack_tracing import ClawTrace; "
                "payload=json.loads(base64.urlsafe_b64decode(os.environ['PDCA_TRACE_B64'])); "
                "with ClawTrace(name='pdca.capture', metadata={"
                "'task_type': payload.get('task_type'), "
                "'prompt_family': payload.get('prompt_family'), "
                "'prompt_version': payload.get('prompt_version'), "
                "'reviewer_outcome': payload.get('reviewer_outcome'), "
                "'pdca_phase': 'phase1'"
                "}, session_id=payload.get('task_run_id')) as trace: "
                " trace.span_n8n(workflow_id='pdca_capture_ingest', "
                " payload={'task_type': payload.get('task_type'), 'prompt_version': payload.get('prompt_version')}, "
                " result=f\"overall_score={payload.get('overall_score')}\", status='captured', latency_ms=0)"
            )
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-e",
                    f"PDCA_TRACE_B64={trace_payload}",
                    "clawstack-unified-clawdbot-gateway-1",
                    "python3",
                    "-c",
                    script,
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            )
        except Exception:
            return


def compute_score(payload: dict[str, Any]) -> dict[str, Any]:
    output_text = str(payload.get("output_snapshot") or "")
    corrected = str(payload.get("human_corrected_output") or output_text)
    edit_distance_score = round(SequenceMatcher(None, output_text, corrected).ratio(), 4)
    format_score = 1.0 if len(output_text.strip()) >= 30 else 0.5
    factual_issue_count = len(payload.get("factual_issues") or [])
    domain_rule_violations = len(payload.get("domain_rule_violations") or [])
    domain_rule_score = max(0.0, round(1.0 - (0.2 * domain_rule_violations), 4))
    acceptance_score = 1.0 if str(payload.get("reviewer_outcome") or "").lower() in {"accepted", "approved"} else 0.4
    overall = round(
        (acceptance_score * 0.35)
        + (edit_distance_score * 0.2)
        + (format_score * 0.15)
        + (domain_rule_score * 0.2)
        + (max(0.0, 1.0 - (0.2 * factual_issue_count)) * 0.1),
        4,
    )
    return {
        "acceptance_score": acceptance_score,
        "edit_distance_score": edit_distance_score,
        "format_score": format_score,
        "factual_issue_count": factual_issue_count,
        "domain_rule_score": domain_rule_score,
        "overall_score": overall
    }


def refresh_status() -> dict[str, Any]:
    registry = read_json(REGISTRY_PATH, default_registry())
    status = read_json(STATUS_PATH, default_status())
    task_runs = load_jsonl(TASK_RUNS_PATH)
    task_scores = load_jsonl(TASK_SCORES_PATH)
    task_feedback = load_jsonl(TASK_FEEDBACK_PATH)
    promotions = load_jsonl(PROMOTION_AUDIT_PATH)
    pending = [run for run in task_runs if run.get("status") == "pending_review"]
    severe_feedback = [fb for fb in task_feedback if str(fb.get("severity") or "").lower() == "high"]

    status["updatedAt"] = now_jst_text()
    status["counts"] = {
        "task_runs": len(task_runs),
        "task_scores": len(task_scores),
        "task_feedback": len(task_feedback),
        "promotion_audit": len(promotions)
    }
    status["pending_review_count"] = len(pending)
    status["latest_run_status"] = task_runs[-1]["status"] if task_runs else "setup_pending"
    status["review_queue"] = [
        {
            "task_run_id": run.get("task_run_id"),
            "task_type": run.get("task_type"),
            "prompt_version": run.get("prompt_version"),
            "created_at": run.get("created_at")
        }
        for run in pending[-10:]
    ]
    status["recent_runs"] = [
        {
            "task_run_id": run.get("task_run_id"),
            "task_type": run.get("task_type"),
            "prompt_version": run.get("prompt_version"),
            "status": run.get("status"),
            "created_at": run.get("created_at")
        }
        for run in task_runs[-10:]
    ]
    customer = registry["families"]["customer_reply"]
    status["current_production_prompt_version"] = customer.get("production")
    status["current_shadow_prompt_version"] = customer.get("shadow")
    status["latest_promotion"] = promotions[-1] if promotions else None
    rollback_items = [item for item in promotions if item.get("action") == "rollback"]
    status["latest_rollback"] = rollback_items[-1] if rollback_items else None
    status["latest_severe_issue"] = severe_feedback[-1] if severe_feedback else None
    write_json(STATUS_PATH, status)
    sync_mirror(status, registry)
    return status


def capture(input_path: Path) -> dict[str, Any]:
    init_state()
    payload = read_json(input_path, {})
    task_run_id = payload.get("task_run_id") or f"pdca-{uuid.uuid4().hex[:12]}"
    created_at = now_jst_text()
    run_record = {
        "task_run_id": task_run_id,
        "task_type": payload.get("task_type", "customer_reply_draft"),
        "prompt_family": payload.get("prompt_family", "customer_reply"),
        "input_snapshot": payload.get("input_snapshot", {}),
        "output_snapshot": payload.get("output_snapshot", ""),
        "model_route": payload.get("model_route", "litellm-default"),
        "prompt_version": payload.get("prompt_version", "customer_reply.v2026_03_29_01"),
        "retrieval_profile": payload.get("retrieval_profile", "email_quality"),
        "source_refs": payload.get("source_refs", []),
        "status": "pending_review" if not payload.get("reviewer_outcome") else str(payload.get("reviewer_outcome")).lower(),
        "created_at": created_at
    }
    score_record = {"task_run_id": task_run_id, "created_at": created_at, **compute_score(payload)}

    append_jsonl(TASK_RUNS_PATH, run_record)
    append_jsonl(TASK_SCORES_PATH, score_record)
    for feedback in payload.get("feedback", []):
        append_jsonl(
            TASK_FEEDBACK_PATH,
            {
                "task_run_id": task_run_id,
                "feedback_type": feedback.get("feedback_type", "human_review"),
                "label": feedback.get("label", "general"),
                "feedback_text": feedback.get("feedback_text", ""),
                "severity": feedback.get("severity", "medium"),
                "created_at": created_at
            },
        )

    try_trace({**payload, "task_run_id": task_run_id}, score_record)
    status = refresh_status()
    return {"task_run_id": task_run_id, "score": score_record, "status": status["latest_run_status"]}


def promote(family: str, candidate: str, approved_by: str, rationale: str) -> dict[str, Any]:
    init_state()
    registry = read_json(REGISTRY_PATH, default_registry())
    family_info = registry["families"][family]
    previous = family_info.get("production")
    family_info["production"] = candidate
    if family_info.get("shadow") == candidate:
        family_info["shadow"] = None
    for version in family_info.get("versions", []):
        if version["version_label"] == candidate:
            version["state"] = "production"
        elif version["version_label"] == previous:
            version["state"] = "superseded"
    registry["updatedAt"] = now_jst_text()
    write_json(REGISTRY_PATH, registry)
    audit = {
        "action": "promotion",
        "prompt_family": family,
        "from_version": previous,
        "to_version": candidate,
        "approved_by": approved_by,
        "approved_at": now_jst_text(),
        "rationale": rationale,
        "rollback_version": previous
    }
    append_jsonl(PROMOTION_AUDIT_PATH, audit)
    status = refresh_status()
    return {"audit": audit, "status": status}


def rollback(family: str, rollback_version: str, approved_by: str, rationale: str) -> dict[str, Any]:
    init_state()
    registry = read_json(REGISTRY_PATH, default_registry())
    family_info = registry["families"][family]
    previous = family_info.get("production")
    family_info["production"] = rollback_version
    registry["updatedAt"] = now_jst_text()
    for version in family_info.get("versions", []):
        if version["version_label"] == rollback_version:
            version["state"] = "production"
        elif version["version_label"] == previous:
            version["state"] = "rolled_back"
    write_json(REGISTRY_PATH, registry)
    audit = {
        "action": "rollback",
        "prompt_family": family,
        "from_version": previous,
        "to_version": rollback_version,
        "approved_by": approved_by,
        "approved_at": now_jst_text(),
        "rationale": rationale,
        "rollback_version": rollback_version
    }
    append_jsonl(PROMOTION_AUDIT_PATH, audit)
    status = refresh_status()
    return {"audit": audit, "status": status}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="PDCA Feedback Loop Phase 1 harness")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    capture_parser = sub.add_parser("capture")
    capture_parser.add_argument("--input-json", required=True)
    promote_parser = sub.add_parser("promote")
    promote_parser.add_argument("--family", required=True)
    promote_parser.add_argument("--candidate", required=True)
    promote_parser.add_argument("--approved-by", required=True)
    promote_parser.add_argument("--rationale", required=True)
    rollback_parser = sub.add_parser("rollback")
    rollback_parser.add_argument("--family", required=True)
    rollback_parser.add_argument("--rollback-version", required=True)
    rollback_parser.add_argument("--approved-by", required=True)
    rollback_parser.add_argument("--rationale", required=True)
    sub.add_parser("refresh")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.command == "init":
        init_state()
        result = {"status": "initialized", "updatedAt": now_jst_text()}
    elif args.command == "capture":
        result = capture(Path(args.input_json))
    elif args.command == "promote":
        result = promote(args.family, args.candidate, args.approved_by, args.rationale)
    elif args.command == "rollback":
        result = rollback(args.family, args.rollback_version, args.approved_by, args.rationale)
    else:
        init_state()
        result = refresh_status()
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
