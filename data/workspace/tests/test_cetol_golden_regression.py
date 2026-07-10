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


def hub_resp(wc, rss, mc_std):
    """Hub実レスポンス形(server.py準拠)のモック。"""
    return {"worst_case": {"cum_upper": wc}, "rss": {"cum_upper": rss},
            "monte_carlo": {"std": mc_std}}


class TestAnalytic(unittest.TestCase):
    def test_two_plates(self):
        wc, rss, mc_std = cgr.analytic([(10.0, 0.1), (20.0, 0.2)])
        self.assertAlmostEqual(wc, 0.3)
        self.assertAlmostEqual(rss, math.sqrt(0.01 + 0.04))
        self.assertAlmostEqual(mc_std, math.sqrt(0.05 / 3.0))

    def test_five_stack(self):
        wc, rss, mc_std = cgr.analytic([(5.0, 0.05)] * 5)
        self.assertAlmostEqual(wc, 0.25)
        self.assertAlmostEqual(rss, 0.05 * math.sqrt(5))


class TestEvaluate(unittest.TestCase):
    def test_exact_match_passes(self):
        case = cgr.GOLDEN_CASES[0]
        wc, rss, mc_std = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, hub_resp(wc, rss, mc_std * 1.03))
        self.assertTrue(r["wc_ok"] and r["rss_ok"] and r["mc_ok"])
        self.assertLessEqual(r["max_err_pct"], 10.0)

    def test_wrong_wc_fails(self):
        case = cgr.GOLDEN_CASES[0]
        wc, rss, mc_std = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, hub_resp(wc * 1.10, rss, mc_std))
        self.assertFalse(r["wc_ok"])

    def test_mc_std_out_of_band_fails(self):
        case = cgr.GOLDEN_CASES[1]
        wc, rss, mc_std = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, hub_resp(wc, rss, mc_std * 1.20))
        self.assertFalse(r["mc_ok"], "MC stdは±10%要求")

    def test_missing_field_fails_not_skips(self):
        case = cgr.GOLDEN_CASES[0]
        wc, rss, mc_std = cgr.analytic(case["dims"])
        r = cgr.evaluate(case, {"worst_case": {"cum_upper": wc}, "rss": {}, "monte_carlo": {}})
        self.assertFalse(r["rss_ok"] and r["mc_ok"], "欠落フィールドは偽PASSさせない")


if __name__ == "__main__":
    unittest.main()
