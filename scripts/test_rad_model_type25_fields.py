# -*- coding: utf-8 -*-
"""Regression tests for TYPE25 fixed-field mutation."""

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data" / "workspace"))

from rad_model import RadModel


TYPE25 = """/INTER/TYPE25/1/0
Contact
#  surf_ID1  surf_ID2      Istf      Igap   Irem_i2      Idel     Iedge
       300       400         4         3         3         1         0
#                 Stmin                 Stmax     Igap0    Ishape               Edge_angle
                    0.0               1.0E30         1         1                  135.0
/END
"""

TYPE25_COMPLETE = """/INTER/TYPE25/1/0
Contact
#  surf_ID1  surf_ID2      Istf      Igap   Irem_i2      Idel     Iedge
       300       400         4         3         3         1         0
#  grnd_IDs             Gap_scale           %mesh_size              Gap_max_s              Gap_max_m
         0                   1.0                  0.4                 0.01                 0.01
#                 Stmin                 Stmax     Igap0    Ishape               Edge_angle
                    0.0               1.0E30         1         1                  135.0
#                 Stfac                  Fric               Tstart                 Tstop
               5.0E-2                   0.1                  0.0               1.0E30
#      I_BC     IVIS2    Inacti                  VISs
         0         0         6                   1.0
#     Ifric    Ifiltr                 Xfreq   sens_ID   fric_ID
         0         0                   0.0         0         0
/END
"""


class Type25FieldMutationTest(unittest.TestCase):
    def test_penetration_fix_preserves_stiffness_bounds(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(TYPE25, encoding="utf-8")
            model = RadModel(path)
            model.set_inter_type25_penetration_fix(
                igap=2, irem_i2=2, igap0=0, ishape=2
            ).set_inter_type25_idel(2).write(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            contact = lines[3].split()
            stiffness = lines[5].split()
            self.assertEqual(contact[3:6], ["2", "2", "2"])
            self.assertEqual(stiffness[:4], ["0.0", "1.0E30", "0", "2"])

    def test_normalize_places_values_in_documented_columns(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(TYPE25_COMPLETE, encoding="utf-8")
            RadModel(path).normalize_inter_type25_cards().write(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            surf = lines[3]
            self.assertEqual(len(surf), 100)
            self.assertEqual(surf[30:40], " " * 10)
            self.assertEqual(int(surf[40:50]), 3)
            self.assertEqual(int(surf[50:60]), 2)
            self.assertEqual(int(surf[70:80]), 2)
            flags = lines[11]
            self.assertEqual(len(flags), 100)
            self.assertEqual(flags[10:20], " " * 10)
            self.assertEqual(int(flags[20:30]), 0)
            self.assertEqual(int(flags[30:40]), 5)

    def test_missing_solid_title_is_inserted(self) -> None:
        source = "/PROP/SOLID/2\n# Isolid Ismstr\n        14         4\n/END\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).ensure_prop_solid_titles().write(path)
            self.assertEqual(
                path.read_text(encoding="utf-8").splitlines()[1],
                "Solid_Property_2",
            )

    def test_legacy_solid_cards_are_upgraded(self) -> None:
        source = ("/PROP/SOLID/2\nSolid\n# Isolid Ismstr Dn Qa Hm\n"
                  "        14         4       0.5       0.0       1.0\n"
                  "                   0                   0                   0                   0                   0\n/END\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).normalize_prop_solid_cards().write(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines[3]), 100)
            self.assertEqual(int(lines[3][50:60]), 222)
            self.assertEqual(len(lines[5]), 100)


if __name__ == "__main__":
    unittest.main()
