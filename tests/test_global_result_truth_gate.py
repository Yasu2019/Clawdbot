# -*- coding: utf-8 -*-
"""Tests for the fail-closed global result truth gate."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest

from scripts.global_result_truth_gate import evaluate


def _valid_payload() -> dict:
    return {
        "app_domain": "openradioss_fem",
        "claim_level": "validated",
        "user_facing": True,
        "claim_text": "Validated within the declared load case and tolerance.",
        "checks": {
            "execution_integrity": True,
            "domain_validity": True,
            "numerical_or_statistical_validity": True,
            "uncertainty_reported": True,
            "provenance_complete": True,
            "reference_validity": True,
            "reproducibility": True,
            "independent_review": True,
        },
        "violations": [],
    }


class GlobalResultTruthGateTests(unittest.TestCase):
    def test_validated_result_passes(self) -> None:
        result = evaluate(_valid_payload())
        self.assertTrue(result["allowed"])
        self.assertEqual(result["verdict"], "PASS")

    def test_execution_success_alone_is_blocked(self) -> None:
        payload = {
            "app_domain": "visual_inspection",
            "claim_level": "executed",
            "user_facing": True,
            "checks": {"execution_integrity": True},
        }
        result = evaluate(payload)
        self.assertFalse(result["allowed"])
        self.assertIn("user_facing_claim_not_validated", result["reasons"])

    def test_nonphysical_violation_is_blocked_even_with_all_checks(self) -> None:
        payload = _valid_payload()
        payload["violations"] = ["phase_fraction_max=18.7 exceeds 1.0"]
        result = evaluate(payload)
        self.assertFalse(result["allowed"])
        self.assertTrue(any(reason.startswith("declared_violations=") for reason in result["reasons"]))

    def test_absolute_claim_requires_production_ready(self) -> None:
        payload = _valid_payload()
        payload["claim_text"] = "This is a complete match and perfect result."
        result = evaluate(payload)
        self.assertFalse(result["allowed"])
        self.assertTrue(any(reason.startswith("absolute_claim_requires_production_ready=") for reason in result["reasons"]))

    def test_missing_domain_fails_closed(self) -> None:
        payload = _valid_payload()
        payload.pop("app_domain")
        result = evaluate(payload)
        self.assertFalse(result["allowed"])
        self.assertIn("app_domain_missing", result["reasons"])


if __name__ == "__main__":
    unittest.main()
