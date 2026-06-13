# -*- coding: utf-8 -*-
"""part_manifest.json -> tolerance-stack rows (Hub-local, mirrors part_geometry_contract)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SCHEMA = "clawstack.part_manifest.v1"


def validate_manifest(manifest: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if manifest.get("schema") != SCHEMA:
        issues.append(f"schema!={SCHEMA}")
    for key in ("units", "bbox_mm", "sheet_thickness_mm", "physics_handoff"):
        if key not in manifest:
            issues.append(f"missing:{key}")
    bbox = manifest.get("bbox_mm") or {}
    for axis in ("Lx", "Ly", "Lz"):
        if axis not in bbox:
            issues.append(f"bbox_mm.{axis} missing")
        elif float(bbox.get(axis) or 0) <= 0:
            issues.append(f"bbox_mm.{axis}<=0")
    if float(manifest.get("sheet_thickness_mm") or 0) <= 0:
        issues.append("sheet_thickness_mm<=0")
    handoff = manifest.get("physics_handoff") or {}
    for domain in ("moldflow", "tolerance", "openradioss"):
        if domain not in handoff:
            issues.append(f"physics_handoff.{domain} missing")
    return len(issues) == 0, issues


def to_tolerance_dims(
    manifest: dict[str, Any],
    *,
    difficulty: int = 1,
    default_tol: float | None = None,
) -> list[dict[str, Any]]:
    per_dim_tol = default_tol if default_tol is not None else (0.04 + 0.02 * (difficulty - 1))
    sheet_tol = max(0.01, float(manifest.get("sheet_thickness_mm") or 1.0) * 0.02)

    nominal_dims: list[dict[str, Any]] = list(
        (manifest.get("features") or {}).get("nominal_dims_mm") or []
    )
    tol_handoff = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    if not nominal_dims:
        nominal_dims = list(tol_handoff.get("nominal_dims_mm") or [])

    if not nominal_dims:
        bbox = manifest.get("bbox_mm") or {}
        if float(bbox.get("Lx") or 0) > 0:
            nominal_dims = [
                {"name": "bbox_Lx", "nominal_mm": bbox["Lx"], "source": "step_bbox"},
                {"name": "bbox_Ly", "nominal_mm": bbox["Ly"], "source": "step_bbox"},
                {
                    "name": "sheet_thickness",
                    "nominal_mm": manifest.get("sheet_thickness_mm"),
                    "source": "layer_thickness",
                },
            ]

    dims: list[dict[str, Any]] = []
    for idx, row in enumerate(nominal_dims):
        name = str(row.get("name") or f"dim_{idx}")
        mean = float(row.get("nominal_mm") or 0.0)
        if mean <= 0:
            continue
        tol = sheet_tol if "thickness" in name.lower() else per_dim_tol
        dims.append(
            {
                "name": name,
                "mean": mean,
                "tolerance": tol,
                "source": str(row.get("source") or "measured"),
            }
        )
    return dims


def detect_maturity_level(manifest: dict[str, Any], *, include_gdt: bool = True) -> str:
    """Return L1/L2/L4/L10 maturity from manifest enrichment and GD&T sources."""
    cetol = manifest.get("cetol_full_enrichment") or {}
    if cetol.get("maturity_level") == "L10_cetol_full":
        return "L10_cetol_full"
    tol_handoff = (manifest.get("physics_handoff") or {}).get("tolerance") or {}
    if str(tol_handoff.get("cetol_full_ready") or "").lower() in ("1", "true", "yes"):
        return "L10_cetol_full"
    enrich = manifest.get("pmi_enrichment") or {}
    if enrich.get("maturity_level"):
        return str(enrich["maturity_level"])
    if tol_handoff.get("maturity_level"):
        return str(tol_handoff["maturity_level"])
    features = manifest.get("features") or {}
    holes = features.get("holes") or []
    datums = features.get("datums") or []
    gdt_ann = features.get("gdt_annotations") or []
    if any(str(h.get("source", "")).startswith("gdt_pmi") for h in holes if isinstance(h, dict)):
        return "L4_pmi_step_read"
    if any(str(d.get("source", "")).startswith("gdt_pmi") for d in datums if isinstance(d, dict)):
        return "L4_pmi_step_read"
    if gdt_ann:
        return "L4_pmi_step_read"
    if str(tol_handoff.get("l10_ready") or "").lower() in ("1", "true", "yes"):
        return "L10_assembly_6sigma"
    if manifest.get("freecad_3d_loop", {}).get("ok"):
        return "L10_freecad_3d_loop"
    if include_gdt:
        return "L2_gdt_proxy"
    return "L1_nominal_only"


def to_gdt_tolerance_dims(
    manifest: dict[str, Any],
    *,
    default_position_tol: float = 0.05,
    default_flatness_tol: float = 0.02,
) -> list[dict[str, Any]]:
    """L2 GD&T contributors from manifest features (holes/datums) or bbox pitch proxy."""
    features = manifest.get("features") or {}
    dims: list[dict[str, Any]] = []

    for idx, hole in enumerate(features.get("holes") or []):
        if not isinstance(hole, dict):
            continue
        nominal = float(hole.get("diameter_mm") or hole.get("nominal_mm") or 0)
        pos_tol = float(hole.get("position_tol_mm") or hole.get("tolerance_mm") or default_position_tol)
        src = str(hole.get("source") or "gdt_measured")
        if nominal <= 0 and pos_tol <= 0:
            continue
        dims.append(
            {
                "name": str(hole.get("name") or f"hole_{idx + 1}_position"),
                "mean": nominal if nominal > 0 else 0.0,
                "tolerance": max(pos_tol, 0.001),
                "source": "gdt_pmi" if src.startswith("gdt_pmi") else "gdt_measured",
                "gdt_type": "position",
            }
        )

    for idx, datum in enumerate(features.get("datums") or []):
        if not isinstance(datum, dict):
            continue
        flat_tol = float(datum.get("flatness_tol_mm") or datum.get("tolerance_mm") or default_flatness_tol)
        src = str(datum.get("source") or "gdt_measured")
        dims.append(
            {
                "name": str(datum.get("name") or f"datum_{idx + 1}_flatness"),
                "mean": 0.0,
                "tolerance": max(flat_tol, 0.001),
                "source": "gdt_pmi" if src.startswith("gdt_pmi") else "gdt_measured",
                "gdt_type": "flatness",
            }
        )

    if not dims:
        bbox = manifest.get("bbox_mm") or {}
        lx = float(bbox.get("Lx") or 0)
        ly = float(bbox.get("Ly") or 0)
        if lx > 0:
            dims.append(
                {
                    "name": "gdt_pitch_proxy_Lx",
                    "mean": lx,
                    "tolerance": default_position_tol,
                    "source": "gdt_proxy",
                    "gdt_type": "position",
                }
            )
        if ly > 0:
            dims.append(
                {
                    "name": "gdt_pitch_proxy_Ly",
                    "mean": ly,
                    "tolerance": default_position_tol,
                    "source": "gdt_proxy",
                    "gdt_type": "position",
                }
            )
    return dims


def merged_tolerance_dims(
    manifest: dict[str, Any],
    *,
    difficulty: int = 1,
    default_tol: float | None = None,
    include_gdt: bool = True,
) -> list[dict[str, Any]]:
    """Nominal stack dims + optional GD&T contributors (L2 Cetol proxy)."""
    base = to_tolerance_dims(manifest, difficulty=difficulty, default_tol=default_tol)
    if not include_gdt:
        return base
    gdt = to_gdt_tolerance_dims(manifest)
    seen = {d["name"] for d in base}
    for row in gdt:
        if row["name"] not in seen:
            base.append(row)
            seen.add(row["name"])
    return base


def manifest_to_stack_rows(manifest: dict[str, Any], *, include_gdt: bool = True) -> list[dict[str, float]]:
    ok, issues = validate_manifest(manifest)
    if not ok:
        raise ValueError("invalid manifest: " + "; ".join(issues))
    spec_rows = merged_tolerance_dims(manifest, difficulty=1, default_tol=0.05, include_gdt=include_gdt)
    rows = []
    for d in spec_rows:
        tol = float(d.get("tolerance") or 0.05)
        rows.append(
            {
                "name": str(d.get("name") or "dim"),
                "nominal": float(d.get("mean") or 0.0),
                "upper": tol,
                "lower": tol,
            }
        )
    return rows


def load_manifest_from_workspace_path(path: str, workspace_root: Path = Path("/workspace")) -> dict[str, Any]:
    raw = Path(path)
    candidates = [raw]
    if not raw.is_absolute():
        candidates.append(workspace_root / raw)
    for cand in candidates:
        if cand.exists():
            return json.loads(cand.read_text(encoding="utf-8-sig"))
    raise FileNotFoundError(f"manifest not found: {path}")
