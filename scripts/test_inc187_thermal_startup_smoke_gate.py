# -*- coding: utf-8 -*-
import unittest

import cae_te_engine as engine


class ThermalStartupSmokeGateTests(unittest.TestCase):
    def test_flag_and_purpose_detect_smoke(self):
        self.assertTrue(engine._is_thermal_startup_smoke({"thermal_startup_smoke": True}))
        self.assertTrue(
            engine._is_thermal_startup_smoke(
                {
                    "analysis_end_time_s": 0.0001,
                    "trial_purpose": "INC-187 r16 staged thermal startup",
                }
            )
        )
        self.assertFalse(
            engine._is_thermal_startup_smoke(
                {
                    "analysis_end_time_s": 1.23,
                    "trial_purpose": "full thermo fill",
                }
            )
        )

    def test_assess_keeps_success_for_smoke_low_fill(self):
        run_result = {
            "status": "DONE",
            "log": "Time = 0.0001\nEnd\n",
            "params": {
                "thermal_startup_smoke": True,
                "analysis_end_time_s": 0.0001,
                "trial_purpose": "startup smoke",
                "polymer_nu": 0.01,
                "inlet_velocity": 6.0,
                "physics_category": "resin_fill_cool",
            },
            "kpi": {
                "values": {
                    "fill_fraction_pct": 0.2,
                    "fill_time_s": 0.0001,
                    "fill_complete": False,
                    "T_min": 313.15,
                    "T_max": 516.78,
                }
            },
            "failure_tags": [],
            "failure_evidence": {},
            "pregate": {"ok": True},
        }
        assessment = engine._assess_openfoam(run_result, {"category": "resin_fill_cad"})
        self.assertEqual(assessment["verdict"], "SUCCESS")
        self.assertTrue(assessment["defects"].get("thermal_startup_smoke"))
        self.assertTrue(assessment["defects"].get("fill_fraction_gate_skipped"))

    def test_assess_fails_nonphysical_cold_temperature(self):
        run_result = {
            "status": "DONE",
            "log": "Time = 5e-05\nEnd\n",
            "params": {
                "thermal_startup_smoke": True,
                "analysis_end_time_s": 0.0001,
                "trial_purpose": "startup smoke",
                "physics_category": "resin_fill_cool",
                "polymer_nu": 0.01,
                "inlet_velocity": 6.0,
            },
            "kpi": {
                "values": {
                    "fill_fraction_pct": 0.2,
                    "fill_time_s": 5e-05,
                    "fill_complete": False,
                    "T_min": 25.16,
                    "T_max": 512.6,
                }
            },
            "failure_tags": [],
            "failure_evidence": {},
            "pregate": {"ok": True},
        }
        assessment = engine._assess_openfoam(run_result, {"category": "resin_fill_cad"})
        self.assertEqual(assessment["verdict"], "FAILED_NONPHYSICAL")
        self.assertIn("nonphysical_temperature", assessment["defects"])


if __name__ == "__main__":
    unittest.main()
