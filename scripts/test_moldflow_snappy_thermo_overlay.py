import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
import tempfile
import unittest
from pathlib import Path
from unittest import mock

SCRIPTS = Path(__file__).resolve().parent
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))
import moldflow_step_case_builder as builder


class SnappyThermoOverlayTests(unittest.TestCase):
    def test_cool_overlay_adds_required_thermo_files_and_mfalign_patches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            run = root / "run"
            for rel in (
                "constant/thermophysicalProperties", "constant/thermophysicalProperties.air",
                "constant/thermophysicalProperties.polymer", "system/controlDict",
                "system/controlDict.ascii", "system/fvSchemes", "system/fvSchemes.ascii",
                "system/fvSolution", "system/fvSolution.ascii",
            ):
                path = source / rel; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(rel, encoding="utf-8")
            run.mkdir()
            with mock.patch.dict(builder.PHYSICS_TEMPLATES, {"resin_fill_cool": source}):
                builder.overlay_snappy_thermo_physics(run, {"physics_category": "resin_fill_cool"})
            self.assertTrue((run / "constant/thermophysicalProperties").is_file())
            self.assertIn("gate {", (run / "0/T").read_text(encoding="utf-8"))
            self.assertIn("moldflow {", (run / "0/p").read_text(encoding="utf-8"))

    def test_non_thermo_case_is_untouched(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            builder.overlay_snappy_thermo_physics(run, {"physics_category": "resin_fill_vof"})
            self.assertFalse((run / "0/T").exists())

    def test_missing_thermo_source_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "incomplete_source"
            run = root / "run"
            source.mkdir()
            run.mkdir()
            with mock.patch.dict(builder.PHYSICS_TEMPLATES, {"resin_fill_cool": source}):
                with self.assertRaisesRegex(ValueError, "thermo overlay source missing"):
                    builder.overlay_snappy_thermo_physics(
                        run, {"physics_category": "resin_fill_cool"}
                    )

    def test_time_output_updates_runtime_and_ascii_restore_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = Path(tmp)
            system = run / "system"
            system.mkdir()
            originals = {
                "controlDict": "endTime 30;\nwriteControl timeStep;\nwriteInterval 1;\n",
                "controlDict.ascii": (
                    "endTime COOL_END_TIME_PLACEHOLDER;\n"
                    "writeControl timeStep;\nwriteInterval 1;\n"
                ),
            }
            for name, original in originals.items():
                (system / name).write_text(original, encoding="utf-8")
            builder.apply_mfalign_control_overrides(
                run, {"analysis_end_time_s": 1.230131, "write_interval_s": 0.05}
            )
            for name in ("controlDict", "controlDict.ascii"):
                text = (system / name).read_text(encoding="utf-8")
                self.assertIn("writeControl    adjustableRunTime;", text)
                self.assertIn("writeInterval   0.05;", text)
                self.assertIn("endTime         1.230131;", text)


if __name__ == "__main__":
    unittest.main()
