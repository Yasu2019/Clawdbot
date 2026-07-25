# -*- coding: utf-8 -*-
"""Smoke tests for openradioss_lab_api helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openradioss_lab_api as api  # noqa: E402
import k10_red_lavie_urgent_assy_pipeline as urgent  # noqa: E402


class OpenRadiossLabApiTests(unittest.TestCase):
    def test_build_status_ok(self) -> None:
        st = api.build_status()
        self.assertTrue(st.get("ok"))
        self.assertIn("kpi", st)
        self.assertIn("bundle", st)
        self.assertIn("tri_track", st["bundle"])

    def test_list_videos_returns_list(self) -> None:
        self.assertIsInstance(api.list_videos(5), list)

    @patch.object(urgent, "urlopen")
    def test_urgent_pipeline_uses_stdlib_http(self, mock_urlopen: MagicMock) -> None:
        response = MagicMock()
        response.read.return_value = b'{"cpu_usage_percent": 12.5}'
        mock_urlopen.return_value.__enter__.return_value = response
        self.assertEqual(urgent.read_worker_cpu_percent(), 12.5)


if __name__ == "__main__":
    unittest.main()
