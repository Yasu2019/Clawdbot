# -*- coding: utf-8 -*-
"""CLI: STEP PMI/GD&T extract -> part_manifest enrich (module in apps/dxf2step)."""
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
APPS = ROOT / "data" / "workspace" / "apps" / "dxf2step"
if str(APPS) not in sys.path:
    sys.path.insert(0, str(APPS))

import step_pmi_extract as spe  # noqa: E402

SCHEMA = spe.SCHEMA


def main() -> int:
    parser = argparse.ArgumentParser(description="STEP PMI/GD&T extract -> part_manifest enrich")
    parser.add_argument("--manifest", required=True, help="part_manifest.json path")
    parser.add_argument("--step", help="STEP path override")
    parser.add_argument("--write", action="store_true", help="Write enriched manifest in-place")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    if manifest.get("schema") != SCHEMA:
        print(f"[NG] schema != {SCHEMA}", file=sys.stderr)
        return 2

    step_path = Path(args.step) if args.step else spe.resolve_step_path(manifest, manifest_path)
    if not step_path or not step_path.exists():
        print(f"[NG] STEP not found for manifest: {manifest_path}", file=sys.stderr)
        return 2

    pmi = spe.parse_step_pmi(step_path)
    enriched = spe.enrich_manifest_with_pmi(manifest, pmi)
    report = {"pmi": pmi, "manifest_maturity": enriched.get("pmi_enrichment")}

    if args.write:
        manifest_path.write_text(json.dumps(enriched, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        report["written"] = str(manifest_path)

    print(json.dumps(report, ensure_ascii=False, indent=2) if args.json else json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
