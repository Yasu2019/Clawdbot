# -*- coding: utf-8 -*-
"""PLM / QMS handoff artifact for tolerance analysis (Cetol L10 integration)."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def build_plm_handoff(
    *,
    manifest: dict[str, Any],
    manifest_path: Path,
    l10_report: dict[str, Any],
    measurement_correlation: dict[str, Any] | None = None,
    freecad_loop: dict[str, Any] | None = None,
    hub_base_url: str = "http://127.0.0.1:8004",
    ecn_id: str | None = None,
) -> dict[str, Any]:
    part_id = manifest.get("source_dxf") or manifest_path.parent.name
    fk = l10_report.get("factory_kpi") or {}
    mc = l10_report.get("monte_carlo") or {}
    return {
        "schema": "clawstack.tolerance_plm_handoff.v1",
        "created_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "part_id": part_id,
        "manifest_path": str(manifest_path.resolve()),
        "step_path": manifest.get("step_path"),
        "maturity_level": l10_report.get("maturity_level"),
        "base_maturity_level": l10_report.get("base_maturity_level"),
        "factory_kpi_verdict": fk.get("verdict"),
        "six_sigma_capable": fk.get("six_sigma_capable"),
        "measurement_correlation_verdict": (measurement_correlation or {}).get("verdict"),
        "freecad_loop_closure": (freecad_loop or {}).get("loop_closure"),
        "integration": {
            "progressive_die_hub": f"{hub_base_url.rstrip('/')}/api/tolerance-stack/from-manifest",
            "growth_domain": "TOLERANCE_ANALYSIS",
            "qms_audit_template": "templates/audit_template.md",
        },
        "kpi_snapshot": {
            "Cp": mc.get("Cp"),
            "Cpk": mc.get("Cpk"),
            "yield_rate": mc.get("yield_rate"),
            "worst_case_stack_mm": l10_report.get("worst_case_stack_mm"),
        },
        "ecn_id": ecn_id,
        "capa_trigger": fk.get("verdict") == "FAIL"
        or (measurement_correlation or {}).get("verdict") == "FAIL",
    }


def write_plm_handoff(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path
