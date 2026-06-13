# -*- coding: utf-8 -*-
"""Cetol-class full path: FreeCAD 3D loop + L10 assembly + measurement correlation + PLM."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from pathlib import Path
from typing import Any

_WORKSPACE = Path(__file__).resolve().parent
_APPS = _WORKSPACE / "apps" / "dxf2step"
for p in (_APPS, _WORKSPACE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import freecad_tolerance_loop as fcl  # noqa: E402
import part_geometry_contract as pgc  # noqa: E402
import step_pmi_extract as spe  # noqa: E402
import tolerance_l10_assembly as l10  # noqa: E402
import tolerance_measurement_correlation as tmc  # noqa: E402
import tolerance_plm_handoff as tplm  # noqa: E402


MATURITY_CETOL_FULL = "L10_cetol_full"


def analyze_cetol_full(
    manifest: dict[str, Any],
    *,
    manifest_path: Path | None = None,
    measured_lot_path: Path | None = None,
    enrich_pmi: bool = True,
    run_freecad_loop: bool = True,
    nominal_target: float = 0.2,
    spec_limit: float = 0.5,
    include_gdt: bool = True,
    hub_base_url: str = "http://127.0.0.1:8004",
    ecn_id: str | None = None,
) -> dict[str, Any]:
    """Run full Cetol scaffold: PMI + FreeCAD loop + L10 + correlation + PLM."""
    if enrich_pmi and manifest_path is not None:
        manifest = spe.try_enrich_manifest_from_step(manifest, manifest_path=manifest_path, best_in_dir=True)

    freecad_loop: dict[str, Any] = {"ok": False, "skipped": True}
    step_path: Path | None = None
    if manifest_path is not None:
        step_path = spe.resolve_step_path(manifest, manifest_path)
    if run_freecad_loop and step_path and step_path.exists():
        freecad_loop = fcl.extract_freecad_3d_loop(step_path)
        manifest = fcl.merge_loop_into_manifest(manifest, freecad_loop)

    half = spec_limit / 2.0
    l10_report = l10.analyze_l10_assembly_from_manifest(
        manifest,
        nominal_target=nominal_target,
        lsl=nominal_target - half,
        usl=nominal_target + half,
        include_gdt=include_gdt,
    )

    measurement: dict[str, Any] | None = None
    if measured_lot_path and measured_lot_path.exists():
        lot = tmc.load_measured_lot(measured_lot_path)
        measurement = tmc.correlate_measured_lot(
            l10_report=l10_report,
            measured_lot=lot,
            lsl=nominal_target - half,
            usl=nominal_target + half,
            nominal_target=nominal_target,
        )

    plm = tplm.build_plm_handoff(
        manifest=manifest,
        manifest_path=manifest_path or Path("part_manifest.json"),
        l10_report=l10_report,
        measurement_correlation=measurement,
        freecad_loop=freecad_loop if freecad_loop.get("ok") else None,
        hub_base_url=hub_base_url,
        ecn_id=ecn_id,
    )

    maturity = MATURITY_CETOL_FULL
    fk_pass = l10_report.get("factory_kpi", {}).get("verdict") == "PASS"
    meas_pass = measurement is None or measurement.get("verdict") == "PASS"
    if not freecad_loop.get("ok") and not freecad_loop.get("skipped"):
        maturity = "L10_assembly_6sigma"
    if fk_pass and meas_pass and freecad_loop.get("ok"):
        maturity = MATURITY_CETOL_FULL
    elif fk_pass and meas_pass:
        maturity = "L10_assembly_6sigma"

    tol = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    tol["cetol_full_ready"] = True
    tol["maturity_level"] = maturity
    tol["plm_handoff_ready"] = True
    manifest.setdefault("physics_handoff", {})["tolerance"] = tol
    manifest["cetol_full_enrichment"] = {
        "maturity_level": maturity,
        "freecad_loop_ok": bool(freecad_loop.get("ok")),
        "measurement_correlation_verdict": (measurement or {}).get("verdict"),
        "factory_kpi_verdict": (l10_report.get("factory_kpi") or {}).get("verdict"),
    }

    return {
        "schema": "clawstack.tolerance_cetol_full.v1",
        "maturity_level": maturity,
        "manifest": manifest,
        "l10_assembly": l10_report,
        "freecad_3d_loop": freecad_loop,
        "measurement_correlation": measurement,
        "plm_handoff": plm,
    }
