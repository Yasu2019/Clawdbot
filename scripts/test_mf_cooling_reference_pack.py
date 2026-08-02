# -*- coding: utf-8 -*-
"""Unit tests for Moldflow cooling reference normalization."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import unittest

from scripts.mf_cooling_reference_pack import EXCLUDED_FIELDS, _converter, _stats


class TestCoolingReferencePack(unittest.TestCase):
    def test_absolute_celsius_to_kelvin(self):
        convert = _converter("degC", "K")
        self.assertAlmostEqual(convert(25.0), 298.15, places=9)

    def test_pressure_mpa_to_pa(self):
        convert = _converter("MPa", "Pa")
        self.assertEqual(convert(1.5), 1_500_000.0)

    def test_statistics_keep_numeric_zero(self):
        stats = _stats([0.0, 1.0, 2.0])
        self.assertEqual(stats["min"], 0.0)
        self.assertEqual(stats["mean"], 1.0)

    def test_delta_temperature_anomaly_is_excluded(self):
        self.assertIn("temperature_difference_from_mold_walls", EXCLUDED_FIELDS)

    def test_unverified_conversion_is_rejected(self):
        with self.assertRaises(ValueError):
            _converter("UNVERIFIED", "SOURCE_RAW")


if __name__ == "__main__":
    unittest.main()
