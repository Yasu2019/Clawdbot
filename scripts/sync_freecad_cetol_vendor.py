# -*- coding: utf-8 -*-
"""Copy live CETOL engine into the FreeCAD workbench vendor/ folder."""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "data" / "workspace"
DST = REPO / "addons" / "ClawstackCetol" / "vendor"
FILES = (
    "tolerance_stackup_engine.py",
    "cetol_modeler.py",
    "tolerance_l10_assembly.py",
    "cetol_process_physics.py",
)


def main() -> int:
    DST.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        src = SRC / name
        if not src.is_file():
            print("[err] missing " + str(src))
            return 1
        shutil.copy2(src, DST / name)
        print("[ok] " + name)
    print("[done] vendor -> " + str(DST))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
