# -*- coding: utf-8 -*-
"""STEP text PMI/GD&T read + part_manifest enrich (L4, shared by CLI and worker)."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

SCHEMA = "clawstack.part_manifest.v1"

# A STEP CYLINDRICAL_SURFACE below this diameter is an edge fillet/blend, not a
# drilled/pierced hole. For press/sheet-metal parts the smallest real pierced
# hole is >= material thickness; 0.5mm is a conservative floor that drops blend
# artifacts (e.g. dia 0.02mm) while keeping genuine holes. Env-overridable.
MIN_HOLE_DIAMETER_MM = float(os.getenv("DXF2STEP_PMI_MIN_HOLE_DIAMETER_MM", "0.5"))


def parse_step_pmi(step_path: Path) -> dict[str, Any]:
    """Best-effort STEP text PMI/GD&T read (no FreeCAD required)."""
    content = step_path.read_text(encoding="utf-8", errors="replace")

    holes: list[dict[str, Any]] = []
    seen_r: set[float] = set()
    filtered_sub_min_diameter = 0
    cyl_radii = re.findall(
        r"CYLINDRICAL_SURFACE\s*\([^,]+,[^,]+,\s*([\d.eE+\-]+)\)", content
    )
    for r_str in cyl_radii:
        try:
            r = round(float(r_str), 4)
        except ValueError:
            continue
        if r <= 0 or r in seen_r:
            continue
        seen_r.add(r)
        diameter = round(r * 2, 4)
        # Skip fillet/blend cylinders: a sub-threshold "hole" is not a real hole.
        if diameter < MIN_HOLE_DIAMETER_MM:
            filtered_sub_min_diameter += 1
            continue
        holes.append(
            {
                "name": f"hole_{len(holes) + 1}",
                "diameter_mm": diameter,
                "position_tol_mm": 0.05,
                "source": "gdt_pmi_step_cylinder",
            }
        )

    datums: list[dict[str, Any]] = []
    for idx, m in enumerate(re.finditer(r"DATUM(?:_FEATURE)?\s*\(\s*'([^']+)'", content)):
        datums.append(
            {
                "name": str(m.group(1)),
                "flatness_tol_mm": 0.02,
                "source": "gdt_pmi_step_datum",
            }
        )
    if not datums:
        for idx, m in enumerate(re.finditer(r"DATUM\s*\(\s*#(\d+)", content)):
            datums.append(
                {
                    "name": f"datum_{idx + 1}_ref_{m.group(1)}",
                    "flatness_tol_mm": 0.02,
                    "source": "gdt_pmi_step_datum_ref",
                }
            )

    gdt_annotations: list[dict[str, Any]] = []
    tol_vals = re.findall(r"TOLERANCE_VALUE\s*\([^,]+,\s*([\d.eE+\-]+)", content)
    for idx, tv in enumerate(tol_vals):
        try:
            val = float(tv)
        except ValueError:
            continue
        gdt_annotations.append(
            {
                "name": f"gdt_tol_{idx + 1}",
                "tolerance_mm": val,
                "gdt_type": "unspecified",
                "source": "gdt_pmi_step_tolerance_value",
            }
        )
    for idx, m in enumerate(re.finditer(r"GEOMETRIC_TOLERANCE[^;]{0,200}", content)):
        snippet = m.group(0)[:180]
        gdt_annotations.append(
            {
                "name": f"gdt_entity_{idx + 1}",
                "raw": snippet,
                "source": "gdt_pmi_step_geometric_tolerance",
            }
        )

    maturity = "L4_pmi_step_read" if (holes or datums or gdt_annotations) else "L2_gdt_proxy"
    return {
        "parse_method": "step_text_v1",
        "step_path": str(step_path),
        "holes": holes,
        "datums": datums,
        "gdt_annotations": gdt_annotations,
        "hole_count": len(holes),
        "datum_count": len(datums),
        "gdt_annotation_count": len(gdt_annotations),
        "filtered_sub_min_diameter": filtered_sub_min_diameter,
        "min_hole_diameter_mm": MIN_HOLE_DIAMETER_MM,
        "maturity_level": maturity,
    }


def enrich_manifest_with_pmi(manifest: dict[str, Any], pmi: dict[str, Any]) -> dict[str, Any]:
    """Merge PMI read into manifest features; bump maturity when PMI found."""
    out = json.loads(json.dumps(manifest))
    features = out.setdefault("features", {})
    if pmi.get("holes"):
        features["holes"] = pmi["holes"]
    if pmi.get("datums"):
        features["datums"] = pmi["datums"]
    if pmi.get("gdt_annotations"):
        features["gdt_annotations"] = pmi["gdt_annotations"]
    out["pmi_enrichment"] = {
        "parse_method": pmi.get("parse_method"),
        "maturity_level": pmi.get("maturity_level"),
        "hole_count": pmi.get("hole_count", 0),
        "datum_count": pmi.get("datum_count", 0),
        "gdt_annotation_count": pmi.get("gdt_annotation_count", 0),
    }
    tol = (out.get("physics_handoff") or {}).get("tolerance") or {}
    tol["pmi_ready"] = bool(pmi.get("holes") or pmi.get("datums") or pmi.get("gdt_annotations"))
    tol["maturity_level"] = pmi.get("maturity_level", "L2_gdt_proxy")
    out.setdefault("physics_handoff", {})["tolerance"] = tol
    return out


def resolve_step_path(manifest: dict[str, Any], manifest_path: Path) -> Path | None:
    step_ref = manifest.get("step_path") or (
        (manifest.get("physics_handoff") or {}).get("moldflow") or {}
    ).get("step_path")
    if step_ref:
        p = Path(str(step_ref))
        if p.is_absolute() and p.exists():
            return p
        cand = manifest_path.parent / p.name
        if cand.exists():
            return cand
        cand2 = manifest_path.parent / str(step_ref).lstrip("/\\")
        if cand2.exists():
            return cand2
    for pattern in ("*.step", "*.STEP", "*.stp", "*.STP"):
        for hit in sorted(manifest_path.parent.glob(pattern)):
            if hit.is_file():
                return hit
    return None


def parse_step_pmi_best_in_dir(manifest_path: Path) -> dict[str, Any]:
    """Pick richest PMI read among STEP files co-located with manifest."""
    best: dict[str, Any] | None = None
    best_score = -1
    for step in sorted(manifest_path.parent.glob("*.step")):
        if not step.is_file():
            continue
        pmi = parse_step_pmi(step)
        score = int(pmi.get("hole_count") or 0) + int(pmi.get("datum_count") or 0) * 2
        score += int(pmi.get("gdt_annotation_count") or 0)
        if score > best_score:
            best_score = score
            best = pmi
    if best is not None:
        return best
    return {
        "parse_method": "step_text_v1",
        "step_path": "",
        "holes": [],
        "datums": [],
        "gdt_annotations": [],
        "hole_count": 0,
        "datum_count": 0,
        "gdt_annotation_count": 0,
        "maturity_level": "L2_gdt_proxy",
    }


def try_enrich_manifest_from_step(
    manifest: dict[str, Any],
    *,
    step_path: Path | None = None,
    manifest_path: Path | None = None,
    best_in_dir: bool = True,
) -> dict[str, Any]:
    """Enrich manifest when a local STEP file is available; no-op on failure."""
    if step_path is None and manifest_path is not None:
        step_path = resolve_step_path(manifest, manifest_path)
    if manifest_path is not None and best_in_dir:
        pmi = parse_step_pmi_best_in_dir(manifest_path)
        if int(pmi.get("hole_count") or 0) + int(pmi.get("datum_count") or 0) > 0:
            return enrich_manifest_with_pmi(manifest, pmi)
    if not step_path or not step_path.exists():
        return manifest
    try:
        pmi = parse_step_pmi(step_path)
        if int(pmi.get("hole_count") or 0) + int(pmi.get("datum_count") or 0) == 0 and manifest_path:
            pmi = parse_step_pmi_best_in_dir(manifest_path)
        return enrich_manifest_with_pmi(manifest, pmi)
    except OSError:
        return manifest
