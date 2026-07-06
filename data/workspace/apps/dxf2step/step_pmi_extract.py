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


_GDT_SUBTYPES = (
    "POSITION_TOLERANCE", "FLATNESS_TOLERANCE", "PERPENDICULARITY_TOLERANCE",
    "PARALLELISM_TOLERANCE", "ANGULARITY_TOLERANCE", "CYLINDRICITY_TOLERANCE",
    "CIRCULARITY_TOLERANCE", "STRAIGHTNESS_TOLERANCE", "SYMMETRY_TOLERANCE",
    "CONCENTRICITY_TOLERANCE", "COAXIALITY_TOLERANCE", "TOTAL_RUNOUT_TOLERANCE",
    "CIRCULAR_RUNOUT_TOLERANCE", "SURFACE_PROFILE_TOLERANCE", "LINE_PROFILE_TOLERANCE",
    "GEOMETRIC_TOLERANCE",
)


def _step_entity_map(content: str) -> dict[str, str]:
    """#id -> entity body (single or complex instance), semicolon-terminated."""
    ents: dict[str, str] = {}
    for m in re.finditer(r"#(\d+)\s*=\s*(.*?);", content, re.S):
        ents[m.group(1)] = m.group(2).strip()
    return ents


def _length_measure(body: str) -> float | None:
    m = re.search(r"LENGTH_MEASURE\s*\(\s*([\d.eE+\-]+)\s*\)", body or "")
    if not m:
        m = re.search(r"MEASURE_WITH_UNIT\s*\(\s*[A-Z_]*\(?\s*([\d.eE+\-]+)", body or "")
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _refs(body: str) -> list[str]:
    return re.findall(r"#(\d+)", body or "")


def parse_step_ap242_pmi(content: str) -> dict[str, Any]:
    """AP242 semantic PMI: +/- tolerances on dimensions, GD&T magnitudes, datums.

    T-iy63/L4 (2026-07-07): reads the real drawing tolerances instead of the
    synthetic defaults, so the tolerance stack becomes drawing-driven.
    """
    ents = _step_entity_map(content)

    # dimensional characteristics: id -> display name
    dim_char_name: dict[str, str] = {}
    for eid, body in ents.items():
        if body.startswith("DIMENSIONAL_LOCATION"):
            m = re.match(r"DIMENSIONAL_LOCATION\s*\(\s*'([^']*)'", body)
            dim_char_name[eid] = (m.group(1) if m else "") or f"dim_loc_{eid}"
        elif body.startswith("DIMENSIONAL_SIZE"):
            m = re.match(r"DIMENSIONAL_SIZE\s*\(\s*#\d+\s*,\s*'([^']*)'", body)
            dim_char_name[eid] = (m.group(1) if m else "") or f"dim_size_{eid}"

    # characteristic -> nominal via DIMENSIONAL_CHARACTERISTIC_REPRESENTATION
    dim_nominal: dict[str, float] = {}
    for body in ents.values():
        if not body.startswith("DIMENSIONAL_CHARACTERISTIC_REPRESENTATION"):
            continue
        ref = _refs(body)
        if len(ref) < 2:
            continue
        char_id, repr_id = ref[0], ref[1]
        repr_body = ents.get(repr_id, "")
        nominal = _length_measure(repr_body)
        if nominal is None:
            for item_id in _refs(repr_body):
                nominal = _length_measure(ents.get(item_id, ""))
                if nominal is not None:
                    break
        if nominal is not None and char_id in dim_char_name:
            dim_nominal[char_id] = nominal

    # +/- tolerances: PLUS_MINUS_TOLERANCE(#TOLERANCE_VALUE, #dim_char)
    pmi_dims: list[dict[str, Any]] = []
    for body in ents.values():
        if not body.startswith("PLUS_MINUS_TOLERANCE"):
            continue
        ref = _refs(body)
        if len(ref) < 2:
            continue
        tv_id, char_id = ref[0], ref[1]
        tv_refs = _refs(ents.get(tv_id, ""))
        if len(tv_refs) < 2:
            continue
        lower = _length_measure(ents.get(tv_refs[0], ""))
        upper = _length_measure(ents.get(tv_refs[1], ""))
        if lower is None or upper is None:
            continue
        minus_mm, plus_mm = (min(lower, upper), max(lower, upper))
        pmi_dims.append(
            {
                "name": dim_char_name.get(char_id, f"dim_{char_id}"),
                "nominal_mm": dim_nominal.get(char_id),
                "plus_mm": round(plus_mm, 6),
                "minus_mm": round(minus_mm, 6),
                "tol_mm": round((plus_mm - minus_mm) / 2.0, 6),
                "source": "gdt_pmi_step_ap242",
            }
        )

    # geometric tolerances with resolved magnitude
    gdt_semantic: list[dict[str, Any]] = []
    for eid, body in ents.items():
        subtype = next(
            (s for s in _GDT_SUBTYPES if re.search(r"\b" + s + r"\s*\(", body)), None
        )
        if not subtype:
            continue
        magnitude = None
        for rid in _refs(body):
            magnitude = _length_measure(ents.get(rid, ""))
            if magnitude is not None:
                break
        if magnitude is None:
            continue
        m = re.search(subtype + r"\s*\(\s*'([^']*)'", body)
        gdt_semantic.append(
            {
                "name": (m.group(1) if m and m.group(1) else f"gdt_{eid}"),
                "gdt_type": subtype.replace("_TOLERANCE", "").lower(),
                "tolerance_mm": round(magnitude, 6),
                "source": "gdt_pmi_step_ap242",
            }
        )

    # datum labels: AP242 puts the identification letter as the LAST string arg
    datum_labels: list[str] = []
    for body in ents.values():
        if re.match(r"DATUM\s*\(", body):
            strings = re.findall(r"'([^']*)'", body)
            label = next((s for s in reversed(strings) if s.strip()), "")
            if label and label not in datum_labels:
                datum_labels.append(label)

    return {
        "pmi_dims": pmi_dims,
        "gdt_semantic": gdt_semantic,
        "datum_labels": datum_labels,
    }


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

    # T-iy63/L4: semantic AP242 PMI (real drawing tolerances)
    ap242 = parse_step_ap242_pmi(content)
    pmi_dims = ap242.get("pmi_dims") or []
    if ap242.get("gdt_semantic"):
        gdt_annotations.extend(ap242["gdt_semantic"])
    for label in ap242.get("datum_labels") or []:
        if not any(d.get("name") == label for d in datums):
            datums.append(
                {"name": label, "flatness_tol_mm": 0.02, "source": "gdt_pmi_step_ap242"}
            )

    maturity = (
        "L4_pmi_step_read"
        if (holes or datums or gdt_annotations or pmi_dims)
        else "L2_gdt_proxy"
    )
    return {
        "parse_method": "step_text_v2_ap242",
        "step_path": str(step_path),
        "holes": holes,
        "datums": datums,
        "gdt_annotations": gdt_annotations,
        "pmi_dims": pmi_dims,
        "hole_count": len(holes),
        "datum_count": len(datums),
        "gdt_annotation_count": len(gdt_annotations),
        "pmi_dim_count": len(pmi_dims),
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
    # T-iy63/L4: merge real +/- tolerances into nominal dims (drawing-driven stack)
    if pmi.get("pmi_dims"):
        nominal = list(features.get("nominal_dims_mm") or [])
        by_name = {str(d.get("name")): d for d in nominal if isinstance(d, dict)}
        for pd in pmi["pmi_dims"]:
            row = by_name.get(str(pd.get("name")))
            payload = {
                "plus_mm": pd.get("plus_mm"),
                "minus_mm": pd.get("minus_mm"),
                "tol_mm": pd.get("tol_mm"),
                "source": pd.get("source", "gdt_pmi_step_ap242"),
            }
            if row is not None:
                if pd.get("nominal_mm") is not None:
                    row["nominal_mm"] = pd["nominal_mm"]
                row.update(payload)
            else:
                nominal.append(
                    {"name": pd.get("name"), "nominal_mm": pd.get("nominal_mm"), **payload}
                )
        features["nominal_dims_mm"] = nominal
    out["pmi_enrichment"] = {
        "parse_method": pmi.get("parse_method"),
        "maturity_level": pmi.get("maturity_level"),
        "hole_count": pmi.get("hole_count", 0),
        "datum_count": pmi.get("datum_count", 0),
        "gdt_annotation_count": pmi.get("gdt_annotation_count", 0),
        "pmi_dim_count": pmi.get("pmi_dim_count", 0),
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
        score += int(pmi.get("pmi_dim_count") or 0) * 3  # real drawing tolerances win
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
