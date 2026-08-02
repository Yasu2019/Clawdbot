# -*- coding: utf-8 -*-
"""Unit tests for Moldflow -> OpenFOAM handoff param mapping."""
from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mf_to_of_handoff as m2o  # noqa: E402

HANDOFF = (
    ROOT
    / "data"
    / "workspace"
    / "moldflow_bridge"
    / "mf_to_of_handoff_box_xplus_d2_20260720.json"
)


class TestMfToOfHandoff(unittest.TestCase):
    def test_gate_velocity_from_volume(self):
        u = m2o.compute_gate_inlet_velocity_m_s(4.1330997e-05, 1.0772605, 2.7e-06)
        self.assertAlmostEqual(u, 14.21, places=2)

    def test_box_handoff_params(self):
        self.assertTrue(HANDOFF.is_file(), f"missing {HANDOFF}")
        handoff = m2o.load_handoff(HANDOFF)
        params = m2o.of_params_from_handoff(handoff)
        # mfalign-v3 calibrated U (was volumetric ~14.21 / v2 ~10.55); keep PROXY_GAP
        expected_u = float((handoff.get("of_target") or {}).get("inlet_velocity") or 6.51)
        self.assertAlmostEqual(params["inlet_velocity"], expected_u, places=3)
        self.assertLessEqual(params["analysis_end_time_s"], 2.0)
        self.assertEqual(params["mf_to_of_proxy_label"], "PROXY_GAP")
        self.assertGreaterEqual(params["T_melt"], 500.0)
        self.assertEqual(params["max_global_cells"], 120000)
        self.assertEqual(params.get("power_law_n"), 0.275)

    def test_apply_preserves_explicit(self):
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        merged = m2o.apply_handoff_to_params(
            {"inlet_velocity": 99.0, "mf_to_of_handoff_path": str(HANDOFF)},
            handoff=handoff,
            overwrite=False,
        )
        self.assertEqual(merged["inlet_velocity"], 99.0)
        self.assertIn("analysis_end_time_s", merged)

    def test_apply_overwrite(self):
        handoff = json.loads(HANDOFF.read_text(encoding="utf-8"))
        expected_u = float((handoff.get("of_target") or {}).get("inlet_velocity") or 6.51)
        merged = m2o.apply_handoff_to_params(
            {"inlet_velocity": 99.0},
            handoff=handoff,
            overwrite=True,
        )
        self.assertAlmostEqual(merged["inlet_velocity"], expected_u, places=3)

    def test_density_g_cm3_to_kg_m3(self):
        self.assertAlmostEqual(m2o.mf_density_to_kg_m3(0.895), 895.0, places=3)
        self.assertAlmostEqual(m2o.mf_density_to_kg_m3(900.0), 900.0, places=3)

    def test_viscosity_ceiling_not_usable_as_nu(self):
        self.assertFalse(m2o.viscosity_absmax_usable_as_nu(1.0e6))
        self.assertTrue(m2o.viscosity_absmax_usable_as_nu(32.4))

    def test_warp_v2_eval_handoff_pack_kpis(self):
        path = (
            ROOT
            / "data"
            / "workspace"
            / "moldflow_bridge"
            / "mf_to_of_handoff_warp_v2_eval_20260730.json"
        )
        if not path.is_file():
            self.skipTest("warp_v2 handoff missing")
        handoff = m2o.load_handoff(path)
        params = m2o.of_params_from_handoff(handoff)
        self.assertAlmostEqual(params["pack_pressure_MPa"], 17.6064, places=3)
        expected_fill = float((handoff.get("mf_kpis") or {}).get("fill_time_s"))
        self.assertAlmostEqual(params["mf_fill_time_s"], expected_fill, places=6)
        self.assertAlmostEqual(params["T_melt"], 516.78, places=1)
        self.assertEqual(params["mf_to_of_proxy_label"], "PROXY_GAP")
        self.assertAlmostEqual(params["power_law_k"], 10.576058, places=6)


if __name__ == "__main__":
    unittest.main()
