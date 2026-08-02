# -*- coding: utf-8 -*-
"""Tests for leakage-safe Moldflow/CalculiX warpage comparison."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest

from scripts.mf_calculix_warpage_scorecard import score_warpage


class TestWarpageScorecard(unittest.TestCase):
    def setUp(self) -> None:
        self.reference = {
            1: (1.0, 0.0, 0.0),
            2: (0.0, 2.0, 0.0),
            3: (0.0, 0.0, 3.0),
        }
        self.provenance = {
            "load_source": "INDEPENDENT_OPENFOAM_HISTORY",
            "source_run_id": "of-cool-independent-001",
            "global_scale_fit": False,
        }

    def test_exact_independent_prediction_passes(self):
        result = score_warpage(self.reference, dict(self.reference), self.provenance)
        self.assertEqual(result["label"], "PROXY_OK")
        self.assertEqual(result["vector_nrmse"], 0.0)
        self.assertTrue(all(result["gates"].values()))

    def test_scaled_validation_result_fails_provenance(self):
        provenance = dict(self.provenance, global_scale_fit=True)
        result = score_warpage(self.reference, dict(self.reference), provenance)
        self.assertEqual(result["label"], "PROXY_GAP")
        self.assertFalse(result["gates"]["independent_load_provenance"])

    def test_large_vector_error_fails(self):
        prediction = {node: tuple(value * 0.5 for value in vector) for node, vector in self.reference.items()}
        result = score_warpage(self.reference, prediction, self.provenance)
        self.assertEqual(result["label"], "PROXY_GAP")
        self.assertGreater(result["vector_nrmse"], 0.15)

    def test_incomplete_coverage_fails(self):
        prediction = {1: self.reference[1], 2: self.reference[2]}
        result = score_warpage(self.reference, prediction, self.provenance)
        self.assertEqual(result["label"], "PROXY_GAP")
        self.assertFalse(result["gates"]["coverage"])


if __name__ == "__main__":
    unittest.main()
