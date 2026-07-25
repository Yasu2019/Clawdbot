# -*- coding: utf-8 -*-
"""T064-gates fix verification (standalone unittest).

Usage: python _t064_gates_verify_test.py <path_to_cae_self_growth_gates.py>
Verifies: (1) line-scoped error tags kill the permanent false hard-fail,
(2) real starter errors still tag, (3) ERR gate uses 90%-window value,
(4) mass-scaling runaway gate still fires.
"""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(sys.argv.pop(1) if len(sys.argv) > 1 else "cae_self_growth_gates.py")
spec = importlib.util.spec_from_file_location("gates_under_test", MODULE_PATH)
g = importlib.util.module_from_spec(spec)
sys.modules["gates_under_test"] = g  # dataclasses needs the module registered
spec.loader.exec_module(g)


def nc_line(nc: int, t: float, err: float, dmm: float) -> str:
    return f" NC=  {nc} T= {t:.4E} DT= 8.0000E-09 ERR= {err:.1f}% DM/M= {dmm:.4E}"


HEALTHY_LOG = "\n".join(
    [
        " INPUT UNIT SYSTEM ..............: KG  MM  MS",
        " UNIT SYSTEM FOR OUTPUT",
        nc_line(50000, 4.00e-4, -0.4, 5.5e-2),
        nc_line(52000, 4.16e-4, -0.4, 5.5e-2),
        nc_line(54000, 4.30e-4, -0.4, 5.5e-2),
        nc_line(56000, 4.48e-4, -0.5, 5.6e-2),
        nc_line(58000, 4.64e-4, -45.0, 6.9e-2),
        nc_line(59800, 4.784e-4, -98.9, 7.96e-2),
        " ENERGY ERROR SUMMARY",
        "     NORMAL TERMINATION      ",
        " TOTAL NUMBER OF CYCLES  :   59854",
    ]
)

STARTER_ERROR_LOG = "\n".join(
    [
        " INPUT UNIT SYSTEM ..............: KG  MM  MS",
        " ** ERROR 760037 : INVALID INPUT IN /UNIT CARD",
        " ** ERROR 21 : SHELL HAS NEGATIVE OR NULL SURFACE",
        "     ERROR TERMINATION      ",
    ]
)

RUNAWAY_LOG = "\n".join(
    [
        " UNIT SYSTEM",
        nc_line(30000, 4.50e-4, -0.6, 4.68e-1),
        nc_line(32000, 4.80e-4, -0.6, 4.68e-1),
        nc_line(33500, 5.02e-4, -99.4, 6.29e-1),
        "     NORMAL TERMINATION      ",
    ]
)

EARLY_COLLAPSE_LOG = "\n".join(
    [
        nc_line(10000, 1.00e-4, -0.5, 3.0e-2),
        nc_line(30000, 3.00e-4, -92.0, 6.0e-2),
        nc_line(40000, 4.00e-4, -95.0, 7.0e-2),
        nc_line(47000, 4.70e-4, -99.0, 8.0e-2),
        "     NORMAL TERMINATION      ",
    ]
)

EXP = {"assy_deck": True, "meaning_gate": {"min_t_final_ms": 0.45, "max_deleted_elements": 8000}}


class T064GatesFix(unittest.TestCase):
    def test_healthy_log_no_false_hard_tags(self):
        tags = g.tag_openradioss_log(HEALTHY_LOG)
        self.assertNotIn("radioss_unit_issue", tags)
        self.assertNotIn("radioss_contact_issue", tags)
        self.assertNotIn("radioss_error", tags)
        self.assertIn("radioss_normal_termination", tags)

    def test_starter_errors_still_tag(self):
        tags = g.tag_openradioss_log(STARTER_ERROR_LOG)
        self.assertIn("radioss_error", tags)
        self.assertIn("radioss_unit_issue", tags)

    def test_err_gate_uses_90pct_window(self):
        m = g.parse_openradioss_run_metrics(HEALTHY_LOG)
        self.assertAlmostEqual(m["last_err_pct"], -98.9)
        self.assertLessEqual(m["t_at_90_ms"], 0.9 * m["t_final_ms"] + 1e-9)
        self.assertGreater(m["err_pct_at_90"], -85.0)
        verdict, defects, reasons = g.apply_openradioss_meaning_gate(
            verdict="SUCCESS", category="press_blanking_assy", exp=EXP,
            log_text=HEALTHY_LOG, failure_tags=g.tag_openradioss_log(HEALTHY_LOG),
            defects={"shear_zone_pct": "21.7%"}, kpi_values=None,
        )
        self.assertEqual(reasons, ["shear_kpi_parametric_only"])
        self.assertEqual(verdict, "FAILED_MEANING_GATE")

    def test_early_collapse_still_fails(self):
        m = g.parse_openradioss_run_metrics(EARLY_COLLAPSE_LOG)
        self.assertLess(m["err_pct_at_90"], -85.0)
        _, _, reasons = g.apply_openradioss_meaning_gate(
            verdict="SUCCESS", category="press_blanking_assy", exp=EXP,
            log_text=EARLY_COLLAPSE_LOG, failure_tags=[], defects={}, kpi_values=None,
        )
        self.assertTrue(
            any(
                r.startswith(("forming_window_err_pct=", "err_pct_at_90="))
                for r in reasons
            ),
            reasons,
        )

    def test_mass_runaway_still_fails(self):
        _, _, reasons = g.apply_openradioss_meaning_gate(
            verdict="SUCCESS", category="press_blanking_assy", exp=EXP,
            log_text=RUNAWAY_LOG, failure_tags=[], defects={}, kpi_values=None,
        )
        self.assertTrue(any("mass_scaling_runaway" in r for r in reasons), reasons)


if __name__ == "__main__":
    unittest.main(verbosity=2)
