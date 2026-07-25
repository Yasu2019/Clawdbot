# -*- coding: utf-8 -*-
"""Smoke tests for openradioss_lab_api helpers."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import openradioss_lab_api as api  # noqa: E402


class OpenRadiossLabApiTests(unittest.TestCase):
    def test_build_status_ok(self) -> None:
        st = api.build_status()
        self.assertTrue(st.get("ok"))
        self.assertIn("kpi", st)
        self.assertIn("bundle", st)
        self.assertIn("tri_track", st["bundle"])

    def test_list_videos_returns_list(self) -> None:
        self.assertIsInstance(api.list_videos(5), list)


if __name__ == "__main__":
    unittest.main()
