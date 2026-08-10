import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import math
import shutil
import tempfile
import unittest
from pathlib import Path

import openradioss_4mmx4mm_assy_params as assy


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = (
    ROOT
    / "data"
    / "cae_te_workspace"
    / "experiments"
    / "openradioss"
    / "4mmx4mm_assy_v001"
)


class Spm80MotionTest(unittest.TestCase):
    def test_crank_endpoint(self):
        points, end_time = assy._crank_displacement_points(
            spm=80.0,
            stroke_mm=80.0,
            target_mm=2.0,
        )
        expected = math.acos(0.95) / (2.0 * math.pi * 80.0 / 60.0)
        self.assertAlmostEqual(end_time, expected, places=12)
        self.assertAlmostEqual(points[-1][1], -0.002, places=12)

    def test_deck_has_exact_displacements_and_local_contact_gap(self):
        params = {
            "spm": 80.0,
            "press_stroke_mm": 80.0,
            "punch_target_mm": 2.0,
            "stripper_target_mm": 0.099,
            "clearance_pct": 8.0,
            "friction_mu": 0.1,
            "dt_noda_min": 8.0e-9,
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            temp = Path(temp_dir)
            starter = temp / "case_0000.rad"
            engine = temp / "case_0001.rad"
            shutil.copy2(TEMPLATE / "4mmx4mm_ASSY_20260105_0000.rad", starter)
            shutil.copy2(TEMPLATE / "4mmx4mm_ASSY_20260105_0001.rad", engine)
            verify = assy.apply_assy_params(starter, engine, params)
            text = starter.read_text(encoding="utf-8")
            self.assertIn("/IMPDISP/1", text)
            self.assertIn("/IMPDISP/5", text)
            self.assertNotIn("Punch_Velocity_Z", text)
            self.assertIn("-2.000000000000E-03", text)
            self.assertIn("-9.900000000000E-05", text)
            self.assertNotIn("                 0.05                 0.05", text)
            self.assertAlmostEqual(verify["punch_target_mm"], -2.0)
            self.assertAlmostEqual(verify["stripper_target_mm"], -0.099)
            stripper_block = text.split("/FUNCT/3", 1)[1].split("/IMPDISP/1", 1)[0]
            stripper_values = [
                float(line.split()[1]) for line in stripper_block.splitlines()
                if len(line.split()) == 2 and line.split()[0][0].isdigit()
            ]
            self.assertGreater(sum(value == -9.9e-5 for value in stripper_values), 1)

    def test_rejects_stripper_overtravel_beyond_initial_gap(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            starter = Path(temp_dir) / "model_0000.rad"
            shutil.copy2(TEMPLATE / "4mmx4mm_ASSY_20260105_0000.rad", starter)
            params = {
                "spm": 800.0,
                "press_stroke_mm": 80.0,
                "punch_target_mm": 2.0,
                "stripper_target_mm": 0.19,
            }
            with self.assertRaisesRegex(ValueError, "below the 0.1 mm initial gap"):
                assy._apply_spm80_motion(starter, params)


if __name__ == "__main__":
    unittest.main()
