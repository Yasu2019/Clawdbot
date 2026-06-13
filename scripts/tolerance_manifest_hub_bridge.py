# -*- coding: utf-8 -*-
"""Build progressive_die_hub /api/tolerance-stack body from part_manifest.json."""
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
DXF2STEP = ROOT / "data" / "workspace" / "apps" / "dxf2step"
if str(DXF2STEP) not in sys.path:
    sys.path.insert(0, str(DXF2STEP))

import part_geometry_contract as pgc  # noqa: E402
import step_pmi_extract as spe  # noqa: E402


def _load_manifest(manifest_path: Path, *, enrich_pmi_from_step: bool = False) -> dict:
    manifest = pgc.load_part_manifest(manifest_path)
    pgc.validate_manifest(manifest)
    if enrich_pmi_from_step:
        manifest = spe.try_enrich_manifest_from_step(manifest, manifest_path=manifest_path)
    return manifest


def manifest_to_hub_body(
    manifest_path: Path,
    *,
    target: float = 0.05,
    mc_n: int = 10000,
    include_gdt: bool = True,
    enrich_pmi_from_step: bool = False,
    manifest: dict | None = None,
) -> dict:
    if manifest is None:
        manifest = _load_manifest(manifest_path, enrich_pmi_from_step=enrich_pmi_from_step)
    dims = pgc.merged_tolerance_dims(manifest, difficulty=1, default_tol=0.05, include_gdt=include_gdt)
    rows = []
    for d in dims:
        rows.append(
            {
                "name": str(d.get("name") or "dim"),
                "nominal": float(d.get("mean") or d.get("nominal_mm") or 0.0),
                "upper": float(d.get("tolerance") or d.get("upper") or 0.05),
                "lower": float(d.get("tolerance") or d.get("lower") or 0.05),
            }
        )
    part_id = manifest.get("source_dxf") or manifest_path.parent.name
    sources = {str(d.get("source") or "") for d in dims}
    geo = "measured" if "measured" in sources or "step_bbox" in sources else "synthetic"
    gdt_count = sum(1 for d in dims if str(d.get("source", "")).startswith("gdt"))
    return {
        "loop_name": f"manifest_{part_id}",
        "rows": rows,
        "target": target,
        "mc_n": mc_n,
        "geometry_source": geo,
        "manifest_path": str(manifest_path.resolve()),
        "include_gdt": include_gdt,
        "gdt_dim_count": gdt_count,
        "maturity_level": pgc.detect_maturity_level(manifest, include_gdt=include_gdt),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--target", type=float, default=0.05)
    parser.add_argument("--mc-n", type=int, default=10000)
    parser.add_argument("--no-gdt", action="store_true", help="L1 nominal-only stack (skip GD&T dims)")
    parser.add_argument(
        "--enrich-pmi-from-step",
        action="store_true",
        help="L4: read PMI/GD&T from STEP before building stack body",
    )
    parser.add_argument(
        "--post-hub",
        default="",
        help="POST to Hub. Use alone for PROGRESSIVE_DIE_HUB_URL or http://127.0.0.1:8004",
    )
    args = parser.parse_args()
    manifest = _load_manifest(args.manifest, enrich_pmi_from_step=args.enrich_pmi_from_step)
    body = manifest_to_hub_body(
        args.manifest,
        target=args.target,
        mc_n=args.mc_n,
        include_gdt=not args.no_gdt,
        enrich_pmi_from_step=args.enrich_pmi_from_step,
        manifest=manifest,
    )
    print(json.dumps(body, ensure_ascii=False, indent=2))
    if args.post_hub:
        hub_base = args.post_hub.strip()
        if hub_base.lower() in ("1", "true", "default", "yes"):
            hub_base = os.environ.get("PROGRESSIVE_DIE_HUB_URL", "http://127.0.0.1:8004")
        import urllib.request

        url = hub_base.rstrip("/") + "/api/tolerance-stack/from-manifest"
        req = urllib.request.Request(
            url,
            data=json.dumps(
                {
                    "manifest": manifest,
                    "loop_name": body.get("loop_name"),
                    "target": body.get("target"),
                    "mc_n": body.get("mc_n"),
                    "run_stack": True,
                    "include_gdt": body.get("include_gdt", True),
                }
            ).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            print(resp.read().decode("utf-8", errors="replace"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
