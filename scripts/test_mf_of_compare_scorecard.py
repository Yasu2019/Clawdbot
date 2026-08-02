# -*- coding: utf-8 -*-
"""Boundary tests for MF/OpenFOAM promotion verdicts."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest

from scripts.mf_of_compare_scorecard import scorecard


class TestScorecardPromotionGate(unittest.TestCase):
    def setUp(self) -> None:
        self.mf = {
            "fill_time_s": 1.0,
            "fill_fraction_pct": 100.0,
            "pressure_end_of_fill_MPa": 100.0,
        }
        self.band = {
            "fill_time_rel_tol": 0.05,
            "fill_fraction_min_pct": 99.0,
            "pressure_rel_tol": 0.10,
            "independent_repeat_runs_min": 2,
        }

    def evaluate(self, pressure: float | None) -> dict:
        return scorecard(
            self.mf,
            {
                "fill_time_s": 1.0,
                "fill_fraction_pct": 100.0,
                "fill_complete": True,
                "peak_pressure_MPa": pressure,
                "independent_repeat_runs": 2,
            },
            self.band,
        )

    def test_exact_match_is_valid_zero_error(self):
        result = self.evaluate(100.0)
        pressure = next(row for row in result["rows"] if row["kpi"] == "pressure_end_of_fill_MPa")
        self.assertEqual(pressure["rel_err"], 0.0)
        self.assertTrue(pressure["pass"])
        self.assertEqual(result["label"], "PROXY_OK")

    def test_exact_tolerance_boundary_passes(self):
        self.assertEqual(self.evaluate(90.0)["label"], "PROXY_OK")

    def test_just_over_tolerance_fails(self):
        self.assertEqual(self.evaluate(89.999)["label"], "PROXY_GAP")

    def test_missing_pressure_never_promotes(self):
        result = self.evaluate(None)
        pressure = next(row for row in result["rows"] if row["kpi"] == "pressure_end_of_fill_MPa")
        self.assertIsNone(pressure["pass"])
        self.assertEqual(result["label"], "PROXY_GAP")

    def test_fill_pass_cannot_override_pressure_failure(self):
        self.assertEqual(self.evaluate(50.0)["label"], "PROXY_GAP")

    def test_single_run_cannot_promote(self):
        result = scorecard(
            self.mf,
            {
                "fill_time_s": 1.0,
                "fill_fraction_pct": 100.0,
                "fill_complete": True,
                "peak_pressure_MPa": 100.0,
                "independent_repeat_runs": 1,
            },
            self.band,
        )
        self.assertEqual(result["label"], "PROXY_GAP")
        repeat = next(row for row in result["rows"] if row["kpi"] == "independent_repeat_runs")
        self.assertFalse(repeat["pass"])


if __name__ == "__main__":
    unittest.main()
