# -*- coding: utf-8 -*-
"""growth_loop_audit.py の単体テスト (ネットワーク・LLM不使用)。

実行: cd data/workspace && python -m unittest tests.test_growth_loop_audit -v
"""

import json
import random
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

import growth_loop_audit as gla


def _spec(**over):
    spec = {
        "name": "test_loop",
        "kpi": {"fields": ["defects_detected.fill_fraction_pct"],
                "physical_min": 0.0, "physical_max": 110.0,
                "violation_tol_pct": 20.0},
        "params": ["params.x", "params.y"],
        "stagnation": {"window": 40, "min_rel_change_pct": 2.0},
        "golden": {"error_log_path": "some/path.json"},
    }
    spec.update(over)
    return spec


def _trial(kpi, x, y, verdict="SUCCESS", i=0):
    return {"verdict": verdict, "timestamp": f"2026-07-07T00:{i:02d}:00",
            "defects_detected": {"fill_fraction_pct": kpi},
            "params": {"x": x, "y": y}}


class TestGetPath(unittest.TestCase):
    def test_nested(self):
        t = {"a": {"b": {"c": 5}}}
        self.assertEqual(gla.get_path(t, "a.b.c"), 5)
        self.assertIsNone(gla.get_path(t, "a.z"))

    def test_first_kpi_percent_string(self):
        t = {"defects_detected": {"fill_fraction_pct": "98.5%"}}
        self.assertEqual(gla.first_kpi(t, ["defects_detected.fill_fraction_pct"]), 98.5)


class TestG1Validity(unittest.TestCase):
    def test_nonphysical_majority_fails(self):
        # 2026-07-07インシデント再現: SUCCESSの50%が界外
        trials = [_trial(125.0, 1, 1, i=i) for i in range(10)] + \
                 [_trial(95.0, 1, 1, i=i) for i in range(10)]
        g = gla.check_g1_validity(trials, _spec())
        self.assertFalse(g["ok"])
        self.assertEqual(g["nonphysical_pct"], 50.0)

    def test_physical_passes(self):
        trials = [_trial(90.0 + i * 0.5, 1, 1, i=i) for i in range(20)]
        self.assertTrue(gla.check_g1_validity(trials, _spec())["ok"])

    def test_failed_trials_not_counted(self):
        # 界外でも FAILED 判定済みなら G1違反ではない (正しく弾いている証拠)
        trials = [_trial(180.0, 1, 1, verdict="FAILED", i=i) for i in range(10)] + \
                 [_trial(95.0, 1, 1, i=i) for i in range(10)]
        g = gla.check_g1_validity(trials, _spec())
        self.assertTrue(g["ok"])
        self.assertEqual(g["samples"], 10)


class TestG2Information(unittest.TestCase):
    def test_stagnant_flat_kpi(self):
        # KPI完全横ばい + 成功率<100% = 停滞
        trials = [_trial(125.0, 1, 1, verdict="SUCCESS" if i % 2 else "ERROR", i=i)
                  for i in range(40)]
        g = gla.check_g2_information(trials, _spec())
        self.assertFalse(g["ok"])

    def test_improving_kpi_ok(self):
        trials = [_trial(60.0 + i, 1, 1, i=i) for i in range(40)]
        self.assertTrue(gla.check_g2_information(trials, _spec())["ok"])

    def test_all_success_flat_is_ok(self):
        # 全成功で横ばいは「習熟済み」でありG2違反にしない
        trials = [_trial(99.0, 1, 1, i=i) for i in range(40)]
        self.assertTrue(gla.check_g2_information(trials, _spec())["ok"])

    def test_insufficient_data_held(self):
        g = gla.check_g2_information([_trial(99, 1, 1)], _spec())
        self.assertTrue(g["ok"])
        self.assertIn("不足", g["note"])


class TestG4Learning(unittest.TestCase):
    def test_uniform_resampling_detected(self):
        # 一様乱数再抽選 (前半後半で分布同一) = 学習不在
        rng = random.Random(7)
        trials = [_trial(100, rng.uniform(0, 1), rng.uniform(5, 25), i=i % 60)
                  for i in range(120)]
        g = gla.check_g4_learning(trials, _spec())
        self.assertFalse(g["ok"])

    def test_adapted_params_ok(self):
        # 後半で探索範囲が移動 = 学習の証拠
        rng = random.Random(7)
        trials = [_trial(100, rng.uniform(0, 1), rng.uniform(5, 25), i=i) for i in range(60)]
        trials += [_trial(100, rng.uniform(2, 3), rng.uniform(5, 25), i=i) for i in range(60)]
        self.assertTrue(gla.check_g4_learning(trials, _spec())["ok"])

    def test_fixed_param_is_no_shift(self):
        trials = [_trial(100, 1.0, 2.0, i=i) for i in range(40)]
        g = gla.check_g4_learning(trials, _spec())
        self.assertFalse(g["ok"])  # 完全固定も学習不在


class TestVerdict(unittest.TestCase):
    def test_fake_growth_on_g1(self):
        trials = [_trial(150.0, 1, 1, i=i) for i in range(30)]
        r = gla.audit_loop(trials, _spec())
        self.assertEqual(r["verdict"], "FAKE_GROWTH")

    def test_fake_growth_on_g2_plus_g4(self):
        # KPI横ばい(成功率<100%) + パラメータ固定
        trials = [_trial(100.0, 1.0, 2.0, verdict="SUCCESS" if i % 2 else "ERROR", i=i)
                  for i in range(60)]
        r = gla.audit_loop(trials, _spec())
        self.assertEqual(r["verdict"], "FAKE_GROWTH")

    def test_suspect_on_golden_missing(self):
        trials = [_trial(60.0 + i, 1.0 + i * 0.1, 2.0 + i * 0.2, i=i) for i in range(40)]
        r = gla.audit_loop(trials, _spec(golden={"error_log_path": None}))
        self.assertEqual(r["verdict"], "SUSPECT")


    def test_g3_strict_missing_log_fails(self):
        trials = [_trial(60.0 + i * 0.8, 1.0 + i * 0.1, 2.0 + i * 0.2, i=i) for i in range(40)]
        r = gla.audit_loop(trials, _spec(golden={"error_log_path": "no/such/log.jsonl", "verify_log": True}))
        self.assertEqual(r["verdict"], "SUSPECT")

    def test_g3_strict_within_threshold_ok(self):
        import json as _j, tempfile, os
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write(_j.dumps({"max_err_pct": 12.5}) + "\n"); f.close()
        trials = [_trial(60.0 + i * 0.8, 1.0 + i * 0.1, 2.0 + i * 0.2, i=i) for i in range(40)]
        r = gla.audit_loop(trials, _spec(golden={"error_log_path": f.name, "verify_log": True, "max_err_pct": 25.0}))
        self.assertEqual(r["verdict"], "HEALTHY")
        os.unlink(f.name)

    def test_g3_strict_over_threshold_fails(self):
        import json as _j, tempfile, os
        f = tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8")
        f.write(_j.dumps({"max_err_pct": 40.0}) + "\n"); f.close()
        trials = [_trial(60.0 + i * 0.8, 1.0 + i * 0.1, 2.0 + i * 0.2, i=i) for i in range(40)]
        r = gla.audit_loop(trials, _spec(golden={"error_log_path": f.name, "verify_log": True, "max_err_pct": 25.0}))
        self.assertEqual(r["verdict"], "SUSPECT")
        os.unlink(f.name)

    def test_healthy(self):
        trials = [_trial(60.0 + i * 0.8, 1.0 + i * 0.1, 2.0 + i * 0.2, i=i)
                  for i in range(40)]
        r = gla.audit_loop(trials, _spec())
        self.assertEqual(r["verdict"], "HEALTHY")


class TestLogLoading(unittest.TestCase):
    def test_truncated_cae_te_log_prefix_parsed(self):
        # 書き込み途中でも完全なレコード分は監査対象になる
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "log.json"
            t1 = json.dumps(_trial(95, 1, 1, i=1))
            t2 = json.dumps(_trial(96, 1, 1, i=2))
            p.write_text('{"trials": [' + t1 + "," + t2 + ', {"verdict": "SUC',
                         encoding="utf-8")
            spec = {"log": {"path": "log.json", "format": "cae_te_log",
                            "categories": [""]}}
            # categories はトライアルの category="" に一致させる
            out = gla.load_trials_cae_te_log(p, [""])
            self.assertEqual(len(out), 2)

    def test_report_text(self):
        reports = [
            {"name": "ok_loop", "verdict": "HEALTHY", "trials": 10, "gates": []},
            {"name": "bad_loop", "verdict": "FAKE_GROWTH", "trials": 30,
             "gates": [{"gate": "G1", "ok": False, "note": "界外 15/30 (50.0%)"}]},
        ]
        txt = gla.build_report_text(reports, "now")
        self.assertIn("bad_loop", txt)
        self.assertIn("G1", txt)
        self.assertIn("48h", txt)
        self.assertNotIn("ok_loop =", txt)


class TestManifestIntegrity(unittest.TestCase):
    def test_real_manifest(self):
        mf = ROOT / "data" / "workspace" / "growth_loop_manifest.json"
        d = json.loads(mf.read_text(encoding="utf-8"))
        self.assertGreaterEqual(len(d["loops"]), 2)
        for lp in d["loops"]:
            self.assertIn("kpi", lp)
            self.assertIn("physical_max", lp["kpi"])
            self.assertIn("params", lp)
            self.assertIn("stagnation", lp)


if __name__ == "__main__":
    unittest.main(verbosity=2)
