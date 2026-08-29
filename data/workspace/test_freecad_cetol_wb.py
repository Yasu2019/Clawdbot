# -*- coding: utf-8 -*-
"""Portable FreeCAD CETOL workbench tests (no FreeCAD GUI required).

Run:  python data/workspace/test_freecad_cetol_wb.py
"""
from __future__ import annotations

import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

WORKSPACE = Path(__file__).resolve().parent
REPO = WORKSPACE.parent.parent
WB = REPO / "addons" / "ClawstackCetol"
sys.path.insert(0, str(WB))

from clawstack_cetol_wb.extract import (  # noqa: E402
    apply_pin_mmc_to_holes,
    cluster_holes,
    extract_joints_from_objects,
    manifest_from_shape_records,
)
from clawstack_cetol_wb.animate import _axis_from_driver, pick_animate_object, pick_animate_objects  # noqa: E402
from clawstack_cetol_wb.run_analysis import analyze_manifest  # noqa: E402


class _J:
    def __init__(self) -> None:
        self.Name = "J1"
        self.Label = "Cylindrical"
        self.JointType = "Cylindrical"
        self.Reference1 = None
        self.Reference2 = None


def main() -> int:
    holes = [
        {"name": "a", "xyz_mm": [10.0, 5.0, 0.0], "diameter_mm": 6.0, "position_tol_mm": 0.05},
        {"name": "a2", "xyz_mm": [10.1, 5.0, 0.0], "diameter_mm": 6.0, "position_tol_mm": 0.05},
        {"name": "b", "xyz_mm": [40.0, 5.0, 0.0], "diameter_mm": 6.0, "position_tol_mm": 0.05},
    ]
    c = cluster_holes(holes)
    assert len(c) == 2, c
    print("V1 hole cluster: PASS")

    joints = extract_joints_from_objects([_J()])
    assert joints and joints[0]["kind"] == "pin_hole_float", joints
    assert joints[0].get("constrained_dof") == ["Tx", "Ty"]
    print("V2 assembly joint mapping: PASS")

    man = manifest_from_shape_records(
        job_id="FC_PORTABLE_TEST",
        bbox={"Lx": 50.0, "Ly": 20.0, "Lz": 3.0},
        holes=c,
        joints=joints,
        datums=[{"name": "datum_A", "letter": "A", "flatness_tol_mm": 0.02}],
        object_names=["Pad", "Hole"],
    )
    assert man["extract_source"] == "freecad_workbench"
    model = analyze_manifest(man)
    assert model["truth_gate"]["commercial_cetol_equivalent"] is False
    assert (model.get("cross_table") or {}), model.keys()
    px = max((float((row or {}).get("pitch_x") or 0) for row in model["cross_table"].values()), default=0)
    assert px > 0.05, px
    assert model.get("freecad_assembly_joints")
    print("V3 analyze_manifest via vendor/live engine (pitch_x max %.3f): PASS" % px)

    ax, rot = _axis_from_driver("Part_hole_1_Tx")
    assert ax == "x" and rot is False
    ax, rot = _axis_from_driver("Strip_Rz")
    assert ax == "z" and rot is True
    print("V4 driver axis parse: PASS")

    vendor_eng = WB / "vendor" / "cetol_modeler.py"
    assert vendor_eng.is_file(), vendor_eng
    initgui = (WB / "InitGui.py").read_text(encoding="utf-8")
    assert "ClawstackCetolWorkbench" in initgui
    assert "docker exec" not in initgui.lower()
    assert "clawstack-unified" not in initgui.lower()
    print("V5 portable files (no Docker in InitGui): PASS")

    demo_src = (WB / "clawstack_cetol_wb" / "demo.py").read_text(encoding="utf-8")
    assert "makeBox" in demo_src and "DieBase" in demo_src
    assert "JointType" in demo_src and "Cylindrical" in demo_src
    assert (WB / "samples" / "Load_Clawstack_Demo.FCMacro").is_file()
    print("V6 demo sample files: PASS")

    mmc_holes = apply_pin_mmc_to_holes(
        [{"name": "h1", "diameter_mm": 6.2, "position_tol_mm": 0.05}],
        5.7,
        0.02,
    )
    assert mmc_holes[0]["mmc"] == "MMC"
    assert mmc_holes[0]["pin_diameter_mm"] == 5.7
    assert mmc_holes[0]["diameter_tol_mm"] == 0.05
    print("V7 pin MMC enrichment: PASS")

    class _Sh:
        Volume = 10.0
        def isNull(self):
            return False

    class _O:
        def __init__(self, name: str) -> None:
            self.Name = name
            self.Label = name
            self.Shape = _Sh()

    class _Doc:
        Objects = [_O("DieBase"), _O("Strip"), _O("Pin")]

    picked = pick_animate_object(_Doc(), "hole_1_Tx")
    assert picked is not None and picked.Name == "Pin"
    group = pick_animate_objects(_Doc(), "hole_1_Tx")
    names = [o.Name for o in group]
    assert "Pin" in names and "Strip" in names, names
    panel_src = (WB / "clawstack_cetol_wb" / "panel.py").read_text(encoding="utf-8")
    assert "no cross-partials" not in panel_src
    assert "start_many" in panel_src
    assert "DLM=" in panel_src
    assert "jointY=" in panel_src
    print("V8 animate prefers Pin for Tx + Pin+Strip group: PASS")

    assert "cetol-cannot process RSS" in panel_src
    sync_src = (REPO / "scripts" / "sync_freecad_cetol_vendor.py").read_text(encoding="utf-8")
    assert "cetol_process_physics.py" in sync_src
    print("V9 FreeCAD dock shows process physics CETOL cannot implement: PASS")

    print("ALL_FREECAD_CETOL_WB_TESTS_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
