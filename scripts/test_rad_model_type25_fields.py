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

from rad_model import RadModel, set_engine_nodal_natural


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

    def test_contact_skins_are_replaced_by_solid_external_surfaces(self) -> None:
        source = ("/PROP/SHELL/999\nSkin\n# data\n0\n"
                  "/PART/101\nPunch_Skin\n# prop mat\n999 1\n"
                  "/SURF/PART/300/0\nPunch_Skin_Surf\n101\n"
                  "/SH3N/101\n1 10 11 12\n"
                  "/GRNOD/PART/501\nAll_Nodes\n1 101\n/END\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).replace_contact_skins_with_solid_external_surfaces(
                {300: 1}, {101}, {999}
            ).write(path)
            output = path.read_text(encoding="utf-8")
            self.assertIn("/SURF/PART/EXT/300/0\nPunch_Skin_Surf\n         1", output)
            self.assertNotIn("/SH3N/101", output)
            self.assertNotIn("/PART/101", output)
            self.assertNotIn("/PROP/SHELL/999", output)
            self.assertIn("/GRNOD/PART/501\nAll_Nodes\n         1", output)
            self.assertNotIn("         1       101", output)

    def test_function_points_are_replaced_with_monotonic_curve(self) -> None:
        source = ("/FUNCT/3\nStripper\n# X Y\n0 0\n1 -1\n"
                  "/END\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).set_funct_points(
                3, [(0.0, 0.0), (5e-5, -0.2), (5.5e-4, -0.2), (6e-4, 0.0)]
            ).write(path)
            output = path.read_text(encoding="utf-8")
            self.assertIn("              0.0006                   0", output)
            self.assertNotIn("1 -1", output)

    def test_gene1_requires_effective_and_shear_conditions(self) -> None:
        source = ("/FAIL/GENE1/2\n"
                  "# Eps_min Shear fct_IDg12 fct_IDg13 fct_IDe1c\n"
                  "0.0 0.0 0 0 0\n"
                  "# Volfrac Pthickfail NCS Temp_max\n"
                  "0.0 0.0 0 0.0\n/END\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).set_fail_gene1_shear_gate(0.30, ncs=2).write(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[2].split()[:2], ["0.0", "0.3"])
            self.assertEqual(lines[4].split()[2], "2")

    def test_nodal_natural_removes_constant_mass_scaling(self) -> None:
        source = "/DT/NODA/CST/0\n                 0.9               4e-8\n/END\n"
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case_0001.rad"
            path.write_text(source, encoding="utf-8")
            set_engine_nodal_natural(path)
            lines = path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(lines[0], "/DT/NODA/0")
            self.assertEqual(lines[1].split(), ["0.9", "0"])

    def test_tetra_box_is_replaced_by_structured_bricks(self) -> None:
        source = ("/NODE\n1 0 0 0\n2 1 0 0\n3 1 1 0\n4 0 1 0\n"
                  "5 0 0 1\n6 1 0 1\n7 1 1 1\n8 0 1 1\n"
                  "/TETRA4/2\n1 1 2 3 7\n2 1 3 4 7\n3 1 5 6 7\n4 1 6 2 7\n5 1 4 8 7\n"
                  "/PROP/SOLID/2\nBlank\n# Isolid Ismstr\n1 -1\n"
                  "/GRNOD/NODE/400\nSkin\n1 2 3 4\n"
                  "/GRNOD/NODE/500\nPerimeter\n1 2 3 4\n/END\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "case.rad"
            path.write_text(source, encoding="utf-8")
            RadModel(path).replace_tetra_box_part_with_structured_bricks(2, 2, 2, 1).write(path)
            output = path.read_text(encoding="utf-8")
            self.assertNotIn("/TETRA4/2", output)
            self.assertIn("/BRICK/2", output)
            self.assertEqual(len(output.split("/BRICK/2\n", 1)[1].split("/PROP", 1)[0].splitlines()), 4)
            self.assertEqual(output.split("# Isolid Ismstr\n", 1)[1].split()[0], "14")
            self.assertNotIn("\n1 2 3 4\n", output)


if __name__ == "__main__":
    unittest.main()
