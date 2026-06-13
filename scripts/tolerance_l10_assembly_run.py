# -*- coding: utf-8 -*-
"""CLI: L10 assembly tolerance + factory KPI from part_manifest.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
DXF2STEP = ROOT / "data" / "workspace" / "apps" / "dxf2step"
WORKSPACE = ROOT / "data" / "workspace"
for p in (DXF2STEP, WORKSPACE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import part_geometry_contract as pgc  # noqa: E402
import step_pmi_extract as spe  # noqa: E402
import tolerance_l10_assembly as l10  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="L10 assembly tolerance + factory KPI")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--enrich-pmi", action="store_true", help="L4 PMI from co-located STEP files")
    parser.add_argument("--write-manifest", action="store_true", help="Write PMI-enriched manifest")
    parser.add_argument("--write-report", type=Path, default=None, help="Write L10 JSON report path")
    parser.add_argument("--nominal-gap", type=float, default=0.2)
    parser.add_argument("--spec-limit", type=float, default=0.5)
    parser.add_argument("--no-gdt", action="store_true")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = pgc.load_part_manifest(manifest_path)
    if not manifest:
        print("[NG] invalid manifest", file=sys.stderr)
        return 2
    if args.enrich_pmi:
        manifest = spe.try_enrich_manifest_from_step(manifest, manifest_path=manifest_path, best_in_dir=True)
        if args.write_manifest:
            manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    nominal = args.nominal_gap
    half = args.spec_limit / 2.0
    report = l10.analyze_l10_assembly_from_manifest(
        manifest,
        nominal_target=nominal,
        lsl=nominal - half,
        usl=nominal + half,
        include_gdt=not args.no_gdt,
    )
    tol = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    tol["l10_ready"] = True
    tol["maturity_level"] = report.get("maturity_level")
    tol["factory_kpi_verdict"] = (report.get("factory_kpi") or {}).get("verdict")
    manifest.setdefault("physics_handoff", {})["tolerance"] = tol
    report["manifest_maturity"] = pgc.detect_maturity_level(manifest, include_gdt=not args.no_gdt)
    report["pmi_enrichment"] = manifest.get("pmi_enrichment")

    out_path = args.write_report or (manifest_path.parent / "tolerance_l10_assembly.json")
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.write_manifest:
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    fk = report.get("factory_kpi") or {}
    return 0 if fk.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
