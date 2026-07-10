# -*- coding: utf-8 -*-
"""moldflow_gate_advisor の解析解テスト (STEP4 Gate Advisor MVP)。

実行: cd data/workspace && python -m unittest tests.test_moldflow_gate_advisor -v
"""
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_spec = importlib.util.spec_from_file_location(
    "moldflow_gate_advisor", ROOT / "scripts" / "moldflow_gate_advisor.py")
adv = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(adv)

PLATE = {"length": 100.0, "width": 10.0, "height": 2.0}


def cand(result, gates):
    key = sorted(gates)
    for c in result["candidates"]:
        if sorted(c["gates"]) == key:
            return c
    raise AssertionError(f"config {gates} not found")


class TestAnalyticFlowLength(unittest.TestCase):
    """解析解: 100x10平板・ゲートはx=0/50/100 (y=0端)。"""

    def setUp(self):
        self.r = adv.advise_gates(PLATE, material_id="pp_generic")

    def test_center_gate_max_flow(self):
        # 中央(50,0)から最遠点=(0,10)or(100,10): sqrt(50^2+10^2)=50.99
        self.assertAlmostEqual(cand(self.r, ["inlet2"])["max_flow_length_mm"], 50.99, delta=0.5)

    def test_end_gate_max_flow(self):
        # 端(0,0)から最遠点=(100,10): sqrt(100^2+10^2)=100.50
        self.assertAlmostEqual(cand(self.r, ["inlet1"])["max_flow_length_mm"], 100.50, delta=0.5)

    def test_triple_gate_max_flow(self):
        # 3点から最遠=(25,10)等: sqrt(25^2+10^2)=26.93
        self.assertAlmostEqual(
            cand(self.r, ["inlet1", "inlet2", "inlet3"])["max_flow_length_mm"], 26.93, delta=0.5)

    def test_weld_counts(self):
        self.assertEqual(cand(self.r, ["inlet2"])["weld_count"], 0)
        self.assertEqual(cand(self.r, ["inlet1", "inlet3"])["weld_count"], 1)
        self.assertEqual(cand(self.r, ["inlet1", "inlet2", "inlet3"])["weld_count"], 2)

    def test_weld_position_midpoint(self):
        welds = cand(self.r, ["inlet1", "inlet3"])["weld_lines"]
        self.assertAlmostEqual(welds[0]["x_mm"], 50.0, delta=0.1)

    def test_symmetric_balance_near_zero(self):
        self.assertLess(cand(self.r, ["inlet1", "inlet3"])["balance_cv"], 0.05)


class TestRanking(unittest.TestCase):
    def test_comfortable_fill_prefers_center_single(self):
        r = adv.advise_gates(PLATE, material_id="pp_generic")
        self.assertEqual(r["best"], ["inlet2"])

    def test_tight_fill_prefers_multi_gate(self):
        # 560mm長・t=2・PC(L/t限界100): 中央1点はL/t≈142で不成立、3点はL/t≈74で成立→3点が最良
        r = adv.advise_gates({"length": 560.0, "width": 50.0, "height": 2.0}, material_id="pc_generic")
        self.assertTrue(cand(r, ["inlet2"])["short_shot_risk"])
        self.assertFalse(cand(r, ["inlet1", "inlet2", "inlet3"])["short_shot_risk"])
        self.assertEqual(sorted(r["best"]), ["inlet1", "inlet2", "inlet3"])

    def test_infeasible_ranked_by_margin_not_weld(self):
        # 全候補が不成立の極端ケース: ウェルド数でなく限界への近さで順位が付く
        r = adv.advise_gates({"length": 2000.0, "width": 50.0, "height": 2.0}, material_id="pc_generic")
        margins = [c["fill_margin_pct"] for c in r["candidates"]]
        self.assertTrue(all(c["short_shot_risk"] for c in r["candidates"]))
        self.assertEqual(margins, sorted(margins, reverse=True))

    def test_deterministic(self):
        a = adv.advise_gates(PLATE, material_id="pp_generic")
        b = adv.advise_gates(PLATE, material_id="pp_generic")
        self.assertEqual(a, b)

    def test_all_seven_configs(self):
        r = adv.advise_gates(PLATE)
        self.assertEqual(len(r["candidates"]), 7)

    def test_unknown_material_uses_default_limit(self):
        r = adv.advise_gates(PLATE, material_id="unknown_xx")
        self.assertEqual(r["candidates"][0]["flow_ratio_limit"], adv.DEFAULT_FLOW_RATIO_LIMIT)


if __name__ == "__main__":
    unittest.main()
