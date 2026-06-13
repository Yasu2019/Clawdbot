# -*- coding: utf-8 -*-
"""CLI: Cetol full path (FreeCAD loop + L10 + measurement correlation + PLM)."""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
DXF2STEP = WORKSPACE / "apps" / "dxf2step"
for p in (DXF2STEP, WORKSPACE):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import part_geometry_contract as pgc  # noqa: E402
import tolerance_cetol_full as tcf  # noqa: E402
import tolerance_plm_handoff as tplm  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Cetol full: FreeCAD loop + L10 + correlation + PLM")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--measured-lot", type=Path, help="clawstack.measured_lot.v1 JSON")
    parser.add_argument("--no-freecad", action="store_true")
    parser.add_argument("--no-pmi", action="store_true")
    parser.add_argument("--write-manifest", action="store_true")
    parser.add_argument("--nominal-gap", type=float, default=0.2)
    parser.add_argument("--spec-limit", type=float, default=0.5)
    parser.add_argument("--hub-url", default=os.environ.get("PROGRESSIVE_DIE_HUB_URL", "http://127.0.0.1:8004"))
    parser.add_argument("--ecn-id", default="")
    args = parser.parse_args()

    manifest_path = args.manifest.resolve()
    manifest = pgc.load_part_manifest(manifest_path)
    if not manifest:
        print("[NG] invalid manifest", file=sys.stderr)
        return 2

    lot_path = args.measured_lot
    if lot_path is None:
        default_lot = manifest_path.parent / "measured_lot_golden.json"
        if default_lot.exists():
            lot_path = default_lot

    report = tcf.analyze_cetol_full(
        manifest,
        manifest_path=manifest_path,
        measured_lot_path=lot_path,
        enrich_pmi=not args.no_pmi,
        run_freecad_loop=not args.no_freecad,
        nominal_target=args.nominal_gap,
        spec_limit=args.spec_limit,
        hub_base_url=args.hub_url,
        ecn_id=args.ecn_id or None,
    )

    out_dir = manifest_path.parent
    l10_path = out_dir / "tolerance_cetol_full_report.json"
    plm_path = out_dir / "tolerance_plm_handoff.json"
    l10_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tplm.write_plm_handoff(plm_path, report["plm_handoff"])

    if args.write_manifest:
        manifest_path.write_text(
            json.dumps(report["manifest"], ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    summary = {
        "maturity_level": report.get("maturity_level"),
        "freecad_loop_ok": (report.get("freecad_3d_loop") or {}).get("ok"),
        "factory_kpi": (report.get("l10_assembly") or {}).get("factory_kpi", {}).get("verdict"),
        "measurement_correlation": (report.get("measurement_correlation") or {}).get("verdict"),
        "plm_path": str(plm_path),
        "report_path": str(l10_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    fk = (report.get("l10_assembly") or {}).get("factory_kpi") or {}
    return 0 if fk.get("verdict") == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
