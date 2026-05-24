# -*- coding: utf-8 -*-
"""FreeCAD headless DXF to STEP converter. Usage: FreeCADCmd scripts/freecad_dxf_to_step.py input.dxf output.step"""
import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
import FreeCAD, Import

def convert(input_dxf: Path, output_step: Path):
    if not input_dxf.exists(): raise FileNotFoundError(input_dxf)
    doc = FreeCAD.newDocument("DXF_TO_STEP")
    Import.insert(str(input_dxf), doc.Name); doc.recompute()
    objects = [obj for obj in doc.Objects if hasattr(obj, "Shape") and not obj.Shape.isNull()]
    if not objects: raise RuntimeError("No valid shapes imported from DXF.")
    Import.export(objects, str(output_step)); print(f"STEP exported: {output_step}")

def main():
    if len(sys.argv) < 3:
        print("Usage: FreeCADCmd freecad_dxf_to_step.py input.dxf output.step"); return 1
    convert(Path(sys.argv[-2]), Path(sys.argv[-1])); return 0
if __name__ == "__main__": raise SystemExit(main())
