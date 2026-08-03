import sys
if hasattr(sys.stdout, "reconfigure"):
    try: sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception: pass
import json
import tempfile
import unittest
from unittest import mock
from pathlib import Path
from scripts.lavie_mf_pipeline_monitor import atomic_write, evaluate

def write(root: Path, relative: str, value: dict) -> None:
    path = root / relative; path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")

class PipelineMonitorTests(unittest.TestCase):
    def test_success_advances_only_to_validation_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write(root, "data/workspace/moldflow_bridge/inc183_lavie_wait_status.json",
                  {"state": "submitted_or_completed", "returncode": 0, "trial_id": "r35"})
            write(root, "data/workspace/apps/growth_dashboard/k10_tri_track_cae_status.json",
                  {"running": True, "tracks": {"openfoam_lavie": {"last": {"verdict": "SUCCESS"}}}})
            write(root, "data/workspace/moldflow_bridge/mf_of_multiphysics_campaign/cool_dispatch_status.json",
                  {"state": "cancelled_by_user_sequence_change"})
            result = evaluate(root)
            self.assertEqual("ready_for_thermo_fill", result["phase"])
            self.assertTrue(result["guards"]["observation_only"])
            self.assertEqual("PROXY_GAP", result["accuracy_label"])
    def test_missing_repeat_never_advances(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual("waiting_pressure_repeat", evaluate(Path(tmp))["phase"])

    def test_atomic_write_retries_transient_windows_lock(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "status.json"
            real_replace = __import__("os").replace
            calls = {"count": 0}
            def transient_replace(source, destination):
                calls["count"] += 1
                if calls["count"] == 1:
                    raise PermissionError("transient lock")
                return real_replace(source, destination)
            with mock.patch("scripts.lavie_mf_pipeline_monitor.os.replace", side_effect=transient_replace):
                atomic_write(target, {"ok": True})
            self.assertTrue(json.loads(target.read_text(encoding="utf-8"))["ok"])
            self.assertEqual(2, calls["count"])

if __name__ == "__main__": unittest.main()
