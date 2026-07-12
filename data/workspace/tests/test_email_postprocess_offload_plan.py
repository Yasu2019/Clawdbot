import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import importlib.util
import hashlib
import json
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "k10_fleet_idle_dispatch.py"
SPEC = importlib.util.spec_from_file_location("k10_fleet_idle_dispatch", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(MODULE)


class EmailPostprocessOffloadPlanTests(unittest.TestCase):
    def setUp(self):
        self.cfg = {
            "dispatch_enabled": False,
            "k10_max_cpu_percent": 70,
            "k10_max_ram_percent": 80,
            "allowed_work": ["pdf_ocr"],
            "forbidden_transfer": ["gmail_refresh_token", "raw_email_body"],
        }

    def test_recommends_lowest_load_allowlisted_node_under_pressure(self):
        plan = MODULE.build_email_offload_plan(
            self.cfg,
            {"cpu_usage_percent": 40, "ram_usage_percent": 90},
            [
                {"node_id": "lavie", "eligible": True, "load_score": 80},
                {"node_id": "vivobook", "eligible": True, "load_score": 40},
            ],
        )
        self.assertEqual(plan["decision"], "recommend")
        self.assertEqual(plan["selected_node"], "vivobook")
        self.assertFalse(plan["dispatch_enabled"])

    def test_does_not_offload_without_k10_pressure(self):
        plan = MODULE.build_email_offload_plan(
            self.cfg,
            {"cpu_usage_percent": 20, "ram_usage_percent": 30},
            [{"node_id": "vivobook", "eligible": True, "load_score": 20}],
        )
        self.assertEqual(plan["decision"], "not_needed")
        self.assertIsNone(plan["selected_node"])

    def test_fails_closed_when_no_candidate_is_eligible(self):
        plan = MODULE.build_email_offload_plan(
            self.cfg,
            {"cpu_usage_percent": 90, "ram_usage_percent": 90},
            [{"node_id": "vivobook", "eligible": False, "load_score": 20}],
        )
        self.assertEqual(plan["decision"], "no_capacity")
        self.assertIsNone(plan["selected_node"])
        self.assertIn("gmail_refresh_token", plan["forbidden_transfer"])
        self.assertFalse(plan["safety"]["raw_mail_remote_transfer"])

    def test_work_package_hash_covers_canonical_payload(self):
        envelope = MODULE.build_email_work_package("red_lavie", ["email_classification"])
        raw = MODULE.canonical_json_bytes(envelope["package"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), envelope["package_sha256"])
        serialized = json.dumps(envelope["package"], ensure_ascii=False)
        self.assertNotIn("token", serialized.lower())
        self.assertEqual(envelope["package"]["records"], [])

    def test_return_manifest_requires_matching_job_and_hash(self):
        envelope = MODULE.build_email_work_package("red_lavie", ["pdf_ocr"])
        manifest = {
            "schema": "clawstack.email_postprocess_return_manifest.v1",
            "job_id": envelope["package"]["job_id"],
            "package_sha256": envelope["package_sha256"],
            "status": "verified",
        }
        self.assertEqual(MODULE.validate_return_manifest(envelope, manifest), (True, "verified"))
        manifest["package_sha256"] = "0" * 64
        self.assertEqual(
            MODULE.validate_return_manifest(envelope, manifest),
            (False, "package_sha256_mismatch"),
        )

    def test_dispatch_cooldown_is_bounded(self):
        now = datetime.now(timezone.utc)
        state = {"last_dispatch_at": (now - timedelta(seconds=100)).isoformat()}
        remaining = MODULE.email_offload_cooldown_remaining(state, now, 3600)
        self.assertEqual(remaining, 3500)
        self.assertEqual(MODULE.email_offload_cooldown_remaining({}, now, 3600), 0)


if __name__ == "__main__":
    unittest.main()
