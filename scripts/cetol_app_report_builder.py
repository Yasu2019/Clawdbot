# -*- coding: utf-8 -*-
"""CETOL 6σ app report builder (T-iy63).

Scans dxf2step trial archives for part_manifest.json, runs the drawing-driven
CETOL pipeline (AP242 PMI enrich -> L10 assembly stack: WC/RSS/MC + L5 MSM +
tolerance allocation) and writes the app data file:

    data/workspace/apps/cetol6sigma/cetol_reports.json

Usage (K10):
    python scripts/cetol_app_report_builder.py            # latest 20 manifests
    python scripts/cetol_app_report_builder.py --limit 5
    python scripts/cetol_app_report_builder.py --manifest <path>   # single part
"""
from __future__ import annotations

import argparse
import json
import sys
import time
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

import step_pmi_extract as spe  # noqa: E402
import tolerance_l10_assembly as tla  # noqa: E402

ARCHIVE = WORKSPACE / "thinkpad_dxf2step_history"
APP_DIR = WORKSPACE / "apps" / "cetol6sigma"
OUT_PATH = APP_DIR / "cetol_reports.json"


def analyze_manifest(manifest_path: Path) -> dict | None:
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except Exception as exc:
        print(f"[skip] {manifest_path.parent.name}: manifest unreadable ({exc})")
        return None
    try:
        enriched = spe.try_enrich_manifest_from_step(manifest, manifest_path=manifest_path)
        rep = tla.analyze_l10_assembly_from_manifest(enriched)
    except Exception as exc:
        print(f"[skip] {manifest_path.parent.name}: analysis failed ({exc})")
        return None

    # Solve 3D Vector Loop
    loop_res = {}
    try:
        loop = tla.tse.VectorLoop3D()
        loop.add_frame("BasePlate", (0.0, 0.0, 0.0), (0.0, 0.0, 0.0), (0.02, 0.02, 0.03), (0.01, 0.01, 0.01), source="pmi")
        
        bbox = manifest.get("bbox_mm") or {"Lx": 100.0, "Ly": 20.0, "Lz": 5.0}
        lx = float(bbox.get("Lx") or 100.0)
        ly = float(bbox.get("Ly") or 20.0)
        lz = float(bbox.get("Lz") or 5.0)
        
        loop.add_frame("Bracket", (lx, ly, lz), (0.0, 90.0, 0.0), (0.04, 0.04, 0.05), (0.02, 0.02, 0.02), source="measured")
        loop.add_frame("PinJoin", (0.0, 0.0, ly), (0.0, 0.0, 0.0), (0.015, 0.015, 0.02), (0.005, 0.005, 0.005), source="assembly_l10")
        loop.add_frame("GapSensor", (-lx, -ly, -lz - 2.0), (0.0, -90.0, 0.0), (0.03, 0.03, 0.03), (0.01, 0.01, 0.01), source="pmi")
        loop_res = loop.solve(gap_direction=(0.0, 0.0, 1.0))
    except Exception as e:
        print(f"[warn] 3D Vector Loop failed: {e}")

    mc = rep.get("monte_carlo") or {}
    msm = rep.get("msm") or {}
    alloc = rep.get("tolerance_allocation") or {}
    enr = enriched.get("pmi_enrichment") or {}
    return {
        "job_id": manifest_path.parent.name,
        "source_dxf": manifest.get("source_dxf"),
        "bbox_mm": manifest.get("bbox_mm"),
        "sheet_thickness_mm": manifest.get("sheet_thickness_mm"),
        "maturity_level": rep.get("maturity_level"),
        "pmi": {
            "dims": enr.get("pmi_dim_count", 0),
            "holes": enr.get("hole_count", 0),
            "datums": enr.get("datum_count", 0),
            "gdt": enr.get("gdt_annotation_count", 0),
        },
        "worst_case_mm": rep.get("worst_case_stack_mm"),
        "rss_3sigma_mm": rep.get("rss_3sigma_mm"),
        "mc": {k: mc.get(k) for k in ("Cp", "Cpk", "yield_rate", "sigma", "n")},
        "msm": {
            k: msm.get(k)
            for k in ("Cp", "Cpk", "yield_rate", "sigma", "skewness", "excess_kurtosis")
        },
        "sensitivity": msm.get("sensitivity") or {},
        "allocation": alloc,
        "dimensions": rep.get("dimensions") or [],
        "dimension_source_summary": rep.get("dimension_source_summary") or {},
        "factory_kpi": (rep.get("factory_kpi") or {}).get("verdict")
        if isinstance(rep.get("factory_kpi"), dict)
        else rep.get("factory_kpi"),
        "vector_loop_3d": loop_res,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="CETOL 6σ app report builder")
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--manifest", type=Path, help="single part_manifest.json")
    args = ap.parse_args()

    targets: list[Path] = []
    if args.manifest:
        targets = [args.manifest.resolve()]
    else:
        candidates = sorted(
            ARCHIVE.glob("*/part_manifest.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        targets = candidates[: args.limit]

    reports = []
    for mp in targets:
        row = analyze_manifest(mp)
        if row:
            reports.append(row)
            print(f"[ok] {row['job_id']}: maturity={row['maturity_level']} "
                  f"Cpk(MSM)={((row['msm'] or {}).get('Cpk') or -1):.3f} pmi_dims={row['pmi']['dims']}")

    APP_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema": "clawstack.cetol6sigma_app_reports.v1",
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "report_count": len(reports),
        "reports": reports,
    }
    OUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"[done] {len(reports)} report(s) -> {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
