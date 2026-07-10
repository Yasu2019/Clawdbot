# -*- coding: utf-8 -*-
"""self_heal_loops.decide_actions の単体テスト(決定ロジックのみ・副作用なし)。"""
import importlib.util
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_s = importlib.util.spec_from_file_location("shl", ROOT / "scripts" / "self_heal_loops.py")
shl = importlib.util.module_from_spec(_s)
_s.loader.exec_module(shl)

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 7, 10, 15, 0, tzinfo=JST)


def ts(hours_ago):
    return (NOW - timedelta(hours=hours_ago)).isoformat()


class TestDecideActions(unittest.TestCase):
    def test_all_healthy_no_action(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(0.5)},
                               {"updated_at": ts(1), "state": "training"}, True, {})
        self.assertEqual(a, [])

    def test_tritrack_stale_restarts(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(50)}, None, True, {})
        self.assertEqual(a[0]["action"], "restart_tritrack")

    def test_tritrack_unreadable_restarts(self):
        a = shl.decide_actions(NOW, None, None, True, {})
        self.assertEqual(a[0]["action"], "restart_tritrack")

    def test_supervisor_stale_but_trainer_alive_no_action(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(0.1)},
                               {"updated_at": ts(9), "state": "training"}, True, {})
        self.assertEqual(a, [])

    def test_supervisor_stale_trainer_dead_resets(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(0.1)},
                               {"updated_at": ts(9), "state": "training"}, False, {})
        self.assertEqual(a[0]["action"], "reset_supervisor")

    def test_supervisor_escalated_not_touched(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(0.1)},
                               {"updated_at": ts(30), "state": "escalated"}, False, {})
        self.assertEqual(a, [])

    def test_rate_limit_escalates_to_human(self):
        a = shl.decide_actions(NOW, {"updated_at": ts(50)}, None, True,
                               {"restart_tritrack": 2})
        self.assertEqual(a[0]["action"], "escalate_human")

    def test_age_parse_z_suffix(self):
        self.assertAlmostEqual(
            shl.age_hours("2026-07-10T05:00:00Z", NOW), 1.0, delta=0.01)


if __name__ == "__main__":
    unittest.main()
