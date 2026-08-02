# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mf_of_pressure_calibration as calibration  # noqa: E402


class TestPressureCalibration(unittest.TestCase):
    def test_pa_to_mpa_prevents_kpa_label_error(self) -> None:
        self.assertAlmostEqual(calibration.pa_to_mpa(65240.0), 0.06524, places=8)

    def test_r32_first_order_k(self) -> None:
        result = calibration.first_order_power_law_k(
            current_k=0.05,
            of_pressure_pa=65170.0,
            mf_pressure_mpa=13.784831,
        )
        self.assertAlmostEqual(result["proposed_k"], 10.576058, places=5)
        self.assertGreater(result["pressure_ratio"], 200.0)

    def test_rejects_nonphysical_input(self) -> None:
        with self.assertRaises(ValueError):
            calibration.first_order_power_law_k(
                current_k=0.05, of_pressure_pa=0.0, mf_pressure_mpa=13.8
            )


if __name__ == "__main__":
    unittest.main()

