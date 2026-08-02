# -*- coding: utf-8 -*-
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import csv
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import mf_coolflowwarp_to_openfoam_pack as packer  # noqa: E402


class TestCoolFlowWarpPack(unittest.TestCase):
    def test_association_cover(self) -> None:
        geometry = {"NODE": {1: (0, 0, 0)}, "TRI3": {2: (0, 0, 0)}, "1DET": {3: (0, 0, 0)}}
        self.assertEqual(packer.choose_associations({1}, geometry), ("NODE",))
        self.assertEqual(packer.choose_associations({2, 3}, geometry), ("TRI3", "1DET"))

    def test_build_scalar_node_and_circuit(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            geometry = base / "geometry.csv"
            with geometry.open("w", encoding="utf-8", newline="") as fh:
                writer = csv.writer(fh)
                writer.writerow(("entity_id", "entity_type", "centroid_x_mm", "centroid_y_mm", "centroid_z_mm", "node_connectivity"))
                writer.writerow((1, "NODE", 100, 0, 0, 1))
                writer.writerow((2, "TRI3", 50, 0, 0, "1;4;5"))
                writer.writerow((3, "1DET", 0, 25, 0, "6;7"))
            for suffix, field, rows in (
                ("pressure_end_of_fill", "pressure_end_of_fill", [(1, 2.0)]),
                ("frozen_pressure", "frozen_pressure", [(2, 3.0), (3, 4.0)]),
            ):
                path = base / f"{packer.STUDY_PREFIX}{suffix}.csv"
                with path.open("w", encoding="utf-8", newline="") as fh:
                    writer = csv.writer(fh)
                    writer.writerow(("NodeID", "value", "indp", "data_id", "field"))
                    for entity_id, value in rows:
                        writer.writerow((entity_id, value, 0, 1, field))
            out = base / "pack"
            manifest = packer.build(base, geometry, out)
            self.assertEqual(manifest["field_count"], 2)
            self.assertTrue(manifest["all_fields_fully_joined"])
            self.assertEqual(manifest["fields"]["frozen_pressure"]["associations"], ["TRI3", "1DET"])
            values = (out / "pressure_end_of_fill" / "values").read_text(encoding="utf-8")
            self.assertIn("2000000", values)
            points = (out / "pressure_end_of_fill" / "points").read_text(encoding="utf-8")
            self.assertIn("(0.1 0 0)", points)


if __name__ == "__main__":
    unittest.main()
