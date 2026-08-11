# -*- coding: utf-8 -*-
"""Fail-closed promotion gate for user-facing engineering and AI results."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path
from typing import Any


BASE_CHECKS = (
    "execution_integrity",
    "domain_validity",
    "numerical_or_statistical_validity",
    "uncertainty_reported",
    "provenance_complete",
)

VALIDATED_CHECKS = BASE_CHECKS + (
    "reference_validity",
    "reproducibility",
    "independent_review",
)

PROHIBITED_ABSOLUTE_TERMS = (
    "proved",
    "proof",
    "complete match",
    "perfect",
    "exact",
    "commercial-quality",
    "commercial quality",
    "production-ready",
    "production ready",
    "完全一致",
    "完全証明",
    "完璧",
)


def evaluate(payload: dict[str, Any]) -> dict[str, Any]:
    claim_level = str(payload.get("claim_level", "unvalidated")).lower()
    user_facing = bool(payload.get("user_facing", False))
    checks = payload.get("checks") if isinstance(payload.get("checks"), dict) else {}
    violations = [str(v) for v in payload.get("violations", []) if str(v).strip()]
    claim_text = str(payload.get("claim_text", "")).lower()

    required = BASE_CHECKS if user_facing else ()
    if claim_level in {"validated", "production_ready"}:
        required = VALIDATED_CHECKS

    missing = [name for name in required if checks.get(name) is not True]
    absolute_terms = [term for term in PROHIBITED_ABSOLUTE_TERMS if term in claim_text]

    reasons = []
    if missing:
        reasons.append("missing_or_failed_checks=" + ",".join(missing))
    if violations:
        reasons.append("declared_violations=" + " | ".join(violations))
    if absolute_terms and claim_level != "production_ready":
        reasons.append("absolute_claim_requires_production_ready=" + ",".join(absolute_terms))
    if not payload.get("app_domain"):
        reasons.append("app_domain_missing")
    if user_facing and claim_level in {"executed", "unvalidated", "hold"}:
        reasons.append("user_facing_claim_not_validated")

    allowed = not reasons
    return {
        "allowed": allowed,
        "verdict": "PASS" if allowed else "BLOCK",
        "declared_claim_level": claim_level,
        "required_checks": list(required),
        "reasons": reasons,
        "safe_status": claim_level.upper() if allowed else "INSUFFICIENT_EVIDENCE",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("evidence_json", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    try:
        payload = json.loads(args.evidence_json.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("top-level JSON must be an object")
        result = evaluate(payload)
    except Exception as exc:
        result = {
            "allowed": False,
            "verdict": "BLOCK",
            "safe_status": "INSUFFICIENT_EVIDENCE",
            "reasons": [f"invalid_evidence:{type(exc).__name__}:{exc}"],
        }

    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    return 0 if result["allowed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
