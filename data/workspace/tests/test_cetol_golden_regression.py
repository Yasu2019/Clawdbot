# -*- coding: utf-8 -*-
"""cetol_golden_regression の解析解・判定ロジックテスト(API不要)。"""
import importlib.util
import math
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_s = importlib.util.spec_from_file_location("cgr", ROOT / "scripts" / "cetol_golden_regression.py")
cgr = importlib.util.module_from_spec(_s)
_s.loader.exec_module(cgr)


class TestAnalytic(unittest.TestCase):
    def test_two_plates(self):
        wc, rss = cgr.analytic([(10.0, 0.1), (20.0, 0.2)])
        self.assertAlmostEqual(wc, 0.3)
        self.assertAlmostEqual(rss, math.sqrt(0.01 + 0.04))

    def test_five_stack(self):
        wc, rss = cgr.analytic([(5.0, 0.05)] * 5)
        self.assertAlmostEqual(wc, 0.25)
        self.assertAlmostEqual(rss, 0.05 * math.sqrt(5))


class TestEvaluate(unittest.TestCase):
    def test_exact_match_passes(self):
        case = cgr.GOLDEN_CASES[0]
        wc, rss = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, {"wc": wc, "rss": rss, "mc": rss * 1.05})
        self.assertTrue(r["wc_ok"] and r["rss_ok"] and r["mc_ok"])
        self.assertLessEqual(r["max_err_pct"], 15.0)

    def test_wrong_wc_fails(self):
        case = cgr.GOLDEN_CASES[0]
        wc, rss = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, {"wc": wc * 1.10, "rss": rss, "mc": rss})
        self.assertFalse(r["wc_ok"])

    def test_mc_sampling_slack(self):
        case = cgr.GOLDEN_CASES[1]
        wc, rss = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, {"wc": wc, "rss": rss, "mc": rss * 1.12})
        self.assertTrue(r["mc_ok"], "MCは±15%許容")


if __name__ == "__main__":
    unittest.main()
