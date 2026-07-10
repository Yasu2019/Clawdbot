# -*- coding: utf-8 -*-
"""self_heal_diagnose_llm の材料収集・プロンプト構築テスト(Ollama不要)。"""
import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
_s = importlib.util.spec_from_file_location("dg", ROOT / "scripts" / "self_heal_diagnose_llm.py")
dg = importlib.util.module_from_spec(_s)
_s.loader.exec_module(dg)


class TestDiagnose(unittest.TestCase):
    def test_context_collects_without_crash(self):
        ctx = dg.build_context()
        self.assertIn("collected_at", ctx)
        self.assertIn("self_heal_status", ctx)

    def test_prompt_mentions_constraints_and_escalations(self):
        ctx = {"self_heal_status": {"actions": [
            {"action": "escalate_human", "target": "track:openradioss_red_lavie",
             "reason": "意味ゲート水準の連敗(streak=8)"}]}}
        p = dg.build_prompt(ctx)
        self.assertIn("escalate_human", p)
        self.assertIn("実行もしない", p)
        self.assertIn("T050-T056", p)
        self.assertLess(len(p), 8000, "コンテキストはローカルLLMの実用長に収める")

    def test_offline_returns_none(self):
        old = dg.OLLAMA_URL
        dg.OLLAMA_URL = "http://127.0.0.1:9/nothing"
        try:
            self.assertIsNone(dg.call_ollama("test"))
        finally:
            dg.OLLAMA_URL = old

    def test_tail_jsonl_skips_broken(self):
        import tempfile
        f = Path(tempfile.mkdtemp()) / "l.jsonl"
        f.write_text('{"a":1}\n{"broken\n{"b":2}\n', encoding="utf-8")
        rows = dg.read_tail_jsonl(f)
        self.assertEqual(len(rows), 2)


if __name__ == "__main__":
    unittest.main()
