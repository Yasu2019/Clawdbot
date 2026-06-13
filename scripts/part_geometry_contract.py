# -*- coding: utf-8 -*-
"""CLI entry for Part Geometry Contract (canonical module in apps/dxf2step)."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
CANONICAL = ROOT / "data" / "workspace" / "apps" / "dxf2step" / "part_geometry_contract.py"
_spec = importlib.util.spec_from_file_location("part_geometry_contract_dxf2step", CANONICAL)
_mod = importlib.util.module_from_spec(_spec)
assert _spec.loader is not None
_spec.loader.exec_module(_mod)

if __name__ == "__main__":
    raise SystemExit(_mod.main())
