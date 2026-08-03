import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import json
import unittest

from scripts.k10_lavie_wait_dispatch_inc187_thermo import parse_trial_verdict


class ThermoWaiterVerdictTests(unittest.TestCase):
    def test_worker_success_does_not_hide_failed_trial(self):
        output = "prefix\n" + json.dumps({"trial_entry": {"verdict": "FAILED"}}) + "\nRESULT: PASS"
        self.assertEqual("FAILED", parse_trial_verdict(output))

    def test_success_is_read(self):
        output = json.dumps({"trial_entry": {"verdict": "SUCCESS"}})
        self.assertEqual("SUCCESS", parse_trial_verdict(output))


if __name__ == "__main__":
    unittest.main()
