# -*- coding: utf-8 -*-
"""Regression tests for physically scoped OpenRadioss blanking gates."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
import unittest

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cae_self_growth_gates as gates


HEALTHY_BLANKING_LOG = """
NC= 61250 T= 4.9000E-04 DT= 8.0000E-09 ERR= -0.6% DM/M= 5.5100E-02
NC= 62000 T= 4.9600E-04 DT= 8.0000E-09 ERR= -0.6% DM/M= 5.5100E-02
FAILURE START AT TIME: 4.9868E-04
NC= 63000 T= 5.0400E-04 DT= 8.0000E-09 ERR=-98.7% DM/M= 8.1000E-02
WARNING: NODAL VELOCITY MAY BE TOO HIGH FOR INTERFACE 1
NC= 70000 T= 5.6000E-04 DT= 8.0000E-09 ERR=-98.4% DM/M= 8.8558E-02
NORMAL TERMINATION
"""


class OpenRadiossBlankingGateRegressionTest(unittest.TestCase):
    def test_warning_is_not_velocity_hard_failure(self) -> None:
        self.assertNotIn("radioss_velocity_too_high", gates.tag_openradioss_log(HEALTHY_BLANKING_LOG))
        self.assertNotIn("radioss_time_step_issue", gates.tag_openradioss_log("TIME-STEP\\nDT=8.0E-09"))

    def test_energy_is_measured_before_first_failure(self) -> None:
        metrics = gates.parse_openradioss_run_metrics(HEALTHY_BLANKING_LOG)
        self.assertAlmostEqual(metrics["err_pct_pre_failure"], -0.6)
        self.assertAlmostEqual(metrics["first_failure_time_ms"], 0.49868)

    def test_cycle_table_format_is_parsed(self) -> None:
        log = """
 61250  0.4900E-03  0.8000E-08 NODE 101 -0.6% 0 0 0 0 0.5510E-01 0.4360E-03 0.2277E-04
 62000  0.4960E-03  0.8000E-08 NODE 101 -0.6% 0 0 0 0 0.5510E-01 0.4360E-03 0.2277E-04
 FAILURE START AT TIME: 4.9868E-04
 70000  0.5600E-03  0.8000E-08 NODE 101 -98.4% 0 0 0 0 0.88558E-01 0.4498E-03 0.3658E-04
 NORMAL TERMINATION
"""
        metrics = gates.parse_openradioss_run_metrics(log)
        self.assertEqual(metrics["nc_final"], 70000)
        self.assertAlmostEqual(metrics["t_final_ms"], 0.56)
        self.assertAlmostEqual(metrics["last_dm_m"], 0.088558)
        self.assertAlmostEqual(metrics["err_pct_pre_failure"], -0.6)

    def test_completed_run_passes_physics_gate(self) -> None:
        verdict, defects, reasons = gates.apply_openradioss_meaning_gate(
            verdict="SUCCESS",
            category="press_blanking_assy",
            exp={
                "assy_deck": True,
                "meaning_gate": {"min_t_final_ms": 0.532},
            },
            log_text=HEALTHY_BLANKING_LOG,
            failure_tags=gates.tag_openradioss_log(HEALTHY_BLANKING_LOG),
            defects={"shear_zone_pct": "37.0%"},
            kpi_values={"theta1_deg": 0.1},
        )
        self.assertEqual(verdict, "SUCCESS")
        self.assertEqual(reasons, [])
        self.assertEqual(defects["kpi_source"], "solver_or_geometry")


if __name__ == "__main__":
    unittest.main()
