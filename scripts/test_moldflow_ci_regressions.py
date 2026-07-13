# -*- coding: utf-8 -*-
"""Focused regressions for the Moldflow continuous-improvement P0 fixes."""

import sys
import tempfile
import unittest
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(Path(__file__).resolve().parent))

import cae_self_growth_gates as gates
import cae_te_engine as engine
import moldflow_step_case_builder as builder


ALPHA_FIELD = """FoamFile { object alpha.polymer; }
internalField nonuniform List<scalar>
2
(
0.5
1
)
;
boundaryField
{
}
"""


class MoldflowCiRegressionTests(unittest.TestCase):
    def test_openfoam_trap_message_is_not_fpe(self):
        tags = gates.tag_openfoam_log(
            "Floating point exception trapping enabled (FOAM_SIGFPE).\nEnd\n"
        )
        self.assertNotIn("foam_fpe", tags)
        self.assertIn(
            "foam_fpe",
            gates.tag_openfoam_log("Floating point exception (core dumped)\n"),
        )

    def test_precise_openfoam_time_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as temp:
            time_dir = Path(temp) / "1.096174"
            time_dir.mkdir()
            (time_dir / "alpha.polymer").write_text(ALPHA_FIELD, encoding="utf-8")
            out = engine._extract_vof_fill_kpis(Path(temp))
        self.assertEqual(75.0, out["fill_fraction_pct"])
        self.assertEqual(1.096174, out["fill_time_s"])
        self.assertFalse(out["fill_complete"])
        self.assertEqual(1.0, out["alpha_max"])

    def test_corner_vent_moves_center_far_face_to_wall(self):
        full = builder.blockmesh_dict_text(100, 60, 2)
        corner = builder.blockmesh_dict_text(
            100, 60, 2, vent_layout="corner_far_edge"
        )
        full_outlet = full.split("outlet", 1)[1].split("walls", 1)[0]
        corner_outlet = corner.split("outlet", 1)[1].split("walls", 1)[0]
        corner_walls = corner.split("walls", 1)[1].split("frontAndBack", 1)[0]
        self.assertIn("(3 11 13 5)", full_outlet)
        self.assertNotIn("(3 11 13 5)", corner_outlet)
        self.assertIn("(3 11 13 5)", corner_walls)

if __name__ == "__main__":
    unittest.main()
