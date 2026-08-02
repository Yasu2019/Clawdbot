import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import tempfile
import unittest
from pathlib import Path

from scripts.openfoam_cooling_restart_builder import build_restart


CONTROL = """startFrom startTime;
startTime 0;
stopAt endTime;
endTime 1.23;
deltaT 0.0001;
maxDeltaT 0.001;
maxCo 1;
maxAlphaCo 0.5;
writeControl timeStep;
writeInterval 100;
"""


def field(patch_body: str) -> str:
    return f"""FoamFile {{ version 2.0; }}
boundaryField
{{
    inlet
    {{
        {patch_body}
    }}
    walls
    {{
        type zeroGradient;
    }}
}}
"""


class CoolingRestartBuilderTests(unittest.TestCase):
    def make_case(self, root: Path) -> Path:
        case = root / "fill"
        (case / "system").mkdir(parents=True)
        (case / "constant").mkdir()
        (case / "1.23").mkdir()
        (case / "system" / "controlDict").write_text(CONTROL, encoding="utf-8")
        for name in ("thermophysicalProperties", "thermophysicalProperties.polymer"):
            (case / "constant" / name).write_text("thermoType {}\n", encoding="utf-8")
        for name in ("U", "T", "alpha.polymer", "p_rgh"):
            (case / "1.23" / name).write_text(field("type fixedValue;\n        value uniform 1;"), encoding="utf-8")
        return case

    def test_builds_closed_gate_restart_without_modifying_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_case(root)
            source_u = (source / "1.23" / "U").read_text(encoding="utf-8")
            target = root / "cool"
            manifest = build_restart(source, target)
            control = (target / "system" / "controlDict").read_text(encoding="utf-8")
            self.assertIn("startFrom       latestTime;", control)
            self.assertIn("endTime         30.0001;", control)
            self.assertIn("maxDeltaT       0.02;", control)
            self.assertIn("fixedValue;", (target / "1.23" / "U").read_text(encoding="utf-8"))
            self.assertIn("uniform (0 0 0);", (target / "1.23" / "U").read_text(encoding="utf-8"))
            self.assertIn("uniform 323.15;", (target / "1.23" / "T").read_text(encoding="utf-8"))
            self.assertEqual(source_u, (source / "1.23" / "U").read_text(encoding="utf-8"))
            self.assertEqual("PROXY_GAP", manifest["accuracy_label"])

    def test_missing_thermal_field_fails_and_removes_partial_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_case(root)
            (source / "1.23" / "T").unlink()
            target = root / "cool"
            with self.assertRaisesRegex(ValueError, "missing field T"):
                build_restart(source, target)
            self.assertFalse(target.exists())

    def test_existing_target_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.make_case(root)
            target = root / "cool"
            target.mkdir()
            marker = target / "keep.txt"
            marker.write_text("keep", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                build_restart(source, target)
            self.assertEqual("keep", marker.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
