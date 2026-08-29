# -*- coding: utf-8 -*-
"""Run vendored / live CETOL-class engine on a manifest."""
from __future__ import annotations

import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .paths import add_engine_paths


def analyze_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    add_engine_paths()
    import cetol_modeler as ctm  # noqa: E402

    model = ctm.build_cetol_model(manifest, job_id=str(manifest.get("job_id") or "FreeCADDoc"))
    model["freecad_assembly_joints"] = manifest.get("freecad_assembly_joints") or []
    model["truth_gate"] = {
        "commercial_cetol_equivalent": False,
        "status": "UNVALIDATED",
        "host": "freecad_workbench",
        "note": "CETOL-class engine in FreeCAD. Not Sigmetrix CETOL 6-sigma.",
    }
    return model
