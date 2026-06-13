# -*- coding: utf-8 -*-
"""OpenRadioss blank-sheet deck scaling from part_manifest (Fable5 phase2).

Minimal .rad stub: rescale template blank length/width + shell thickness from
manifest bbox_mm / sheet_thickness_mm. Full STEP mesh import is a later sprint.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

SCHEMA = "clawstack.openradioss_manifest_deck.v1"
_TEMPLATE_BLANK_LENGTH_MM = 20.0
_TEMPLATE_BLANK_WIDTH_MM = 5.0
_TEMPLATE_THICKNESS_MM = 1.2
_MIN_LENGTH_MM = 4.0
_MIN_WIDTH_MM = 2.0
_MAX_LENGTH_MM = 120.0
_MAX_WIDTH_MM = 60.0


def _clamp(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def manifest_blank_dims(manifest: dict[str, Any]) -> dict[str, float]:
    bbox = manifest.get("bbox_mm") or {}
    lx = float(bbox.get("Lx") or _TEMPLATE_BLANK_LENGTH_MM)
    ly = float(bbox.get("Ly") or _TEMPLATE_BLANK_WIDTH_MM)
    length = _clamp(max(lx, ly), _MIN_LENGTH_MM, _MAX_LENGTH_MM)
    width = _clamp(min(lx, ly), _MIN_WIDTH_MM, _MAX_WIDTH_MM)
    thickness = float(
        manifest.get("sheet_thickness_mm")
        or (manifest.get("physics_handoff") or {}).get("openradioss", {}).get("thickness_mm")
        or _TEMPLATE_THICKNESS_MM
    )
    thickness = _clamp(thickness, 0.2, 25.0)
    return {
        "blank_length_mm": round(length, 4),
        "blank_width_mm": round(width, 4),
        "sheet_thickness_mm": round(thickness, 4),
    }


def _format_node(node_id: int, x: float, y: float, z: float) -> str:
    return f"{node_id:7d}{x:12.2f}{y:12.2f}{z:12.2f}"


def _build_node_block(length_mm: float, width_mm: float, *, n_seg: int = 5) -> str:
    lines = ["/NODE"]
    node_id = 1
    for z in (0.0, width_mm):
        for col in range(n_seg + 1):
            x = col * length_mm / n_seg
            lines.append(_format_node(node_id, x, 0.0, z))
            node_id += 1
    return "\n".join(lines) + "\n"


def apply_manifest_to_press_blanking_rad(rad_content: str, manifest: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Scale press_blanking minimal blank mesh from manifest bbox + thickness."""
    dims = manifest_blank_dims(manifest)
    length = dims["blank_length_mm"]
    width = dims["blank_width_mm"]
    thickness = dims["sheet_thickness_mm"]

    content = rad_content
    node_block = _build_node_block(length, width)
    content = re.sub(r"(?m)^/NODE\n.*?(?=^/SHELL)", node_block, content, count=1, flags=re.DOTALL)

    # /PROP/SHELL: integration row then hm/hf/hr line then N + Thick row
    content = re.sub(
        r"(^\s*5\s+)([0-9.]+)(\s+[0-9.]+\s+[0-9]+\s+[0-9]+)",
        rf"\g<1>{thickness:.4f}\3",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    t_half = thickness / 2.0
    content = re.sub(
        r"(^#\s+hm\s+hf\s+hr.*\n\s*)([0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)",
        rf"\g<1>{t_half:.4f}\g<3>{t_half:.4f}\g<5>{t_half:.4f}\g<6>",
        content,
        count=1,
        flags=re.MULTILINE,
    )

    meta = {
        "schema": SCHEMA,
        "template_blank_length_mm": _TEMPLATE_BLANK_LENGTH_MM,
        "template_blank_width_mm": _TEMPLATE_BLANK_WIDTH_MM,
        "template_thickness_mm": _TEMPLATE_THICKNESS_MM,
        "scaled": dims,
        "part_id": manifest.get("source_dxf") or manifest.get("source_dxf_path"),
        "note": "BBox-scaled blank stub; not user STEP mesh",
    }
    return content, meta


def apply_manifest_to_press_bending_rad(rad_content: str, manifest: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Scale press_bending V-bend strip from manifest bbox + thickness."""
    dims = manifest_blank_dims(manifest)
    length = dims["blank_length_mm"]
    width = dims["blank_width_mm"]
    thickness = dims["sheet_thickness_mm"]

    lines = ["/NODE"]
    node_id = 1
    n_seg = 2
    for z in (0.0, width):
        for col in range(n_seg + 1):
            x = col * length / n_seg
            lines.append(_format_node(node_id, x, 0.0, z))
            node_id += 1
    node_block = "\n".join(lines) + "\n"

    content = rad_content
    content = re.sub(r"(?m)^/NODE\n.*?(?=^/SHELL)", node_block, content, count=1, flags=re.DOTALL)
    content = re.sub(
        r"(^\s*3\s+)([0-9.]+)(\s+[0-9.]+\s+[0-9]+\s+[0-9]+)",
        rf"\g<1>{thickness:.4f}\3",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    t_half = thickness / 2.0
    content = re.sub(
        r"(^#\s+hm\s+hf\s+hr.*\n\s*)([0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)(\s+[0-9.]+)",
        rf"\g<1>{t_half:.4f}\g<3>{t_half:.4f}\g<5>{t_half:.4f}\g<6>",
        content,
        count=1,
        flags=re.MULTILINE,
    )
    meta = {
        "schema": SCHEMA,
        "category": "press_bending",
        "scaled": dims,
        "part_id": manifest.get("source_dxf") or manifest.get("source_dxf_path"),
        "note": "BBox-scaled V-bend strip stub; not user STEP mesh",
    }
    return content, meta


def apply_manifest_deck(rad_content: str, manifest: dict[str, Any], category: str) -> tuple[str, dict[str, Any] | None]:
    if category in ("press_blanking", "press_blanking_stripper"):
        return apply_manifest_to_press_blanking_rad(rad_content, manifest)
    if category == "press_bending":
        return apply_manifest_to_press_bending_rad(rad_content, manifest)
    return rad_content, None


def apply_manifest_deck_with_step(
    rad_content: str,
    manifest: dict[str, Any],
    category: str,
    manifest_path: Path | None = None,
    *,
    prefer_step_shell: bool = True,
    run_dir: Path | None = None,
    starter_input_file: str = "press_blanking_0000.rad",
    docker_exe: str | None = None,
    docker_image: str | None = None,
) -> tuple[str, dict[str, Any] | None, str]:
    """Returns (content, meta, geometry_source) where source is step_shell|bbox_scale|template."""
    prefer = os.environ.get("OPENRADIOSS_PREFER_STEP_SHELL", "1").strip() not in {"0", "false", "False"}
    if prefer_step_shell and prefer and category.startswith("press_"):
        try:
            from step_to_openradioss_shell import (
                apply_step_shell_deck,
                starter_preflight_rad,
                starter_prune_invalid_shells,
                validate_shell_rad_references,
            )

            content, meta = apply_step_shell_deck(
                rad_content, manifest, manifest_path, category
            )
            if meta:
                part_id = 2 if category.startswith("press_blank") else 1
                ok_refs, issues = validate_shell_rad_references(content, part_id=part_id)
                if not ok_refs:
                    print(f"[openradioss] WARN step shell ref check failed: {issues[:5]}", flush=True)
                elif run_dir and docker_exe and docker_image:
                    pre_ok, _pre_log = starter_preflight_rad(
                        content,
                        run_dir=run_dir / "step_shell_preflight",
                        input_file=starter_input_file,
                        docker_exe=docker_exe,
                        docker_image=docker_image,
                    )
                    if not pre_ok:
                        content, pre_ok, dropped = starter_prune_invalid_shells(
                            content,
                            part_id=part_id,
                            run_dir=run_dir / "step_shell_prune",
                            input_file=starter_input_file,
                            docker_exe=docker_exe,
                            docker_image=docker_image,
                        )
                        if dropped:
                            meta["starter_pruned_shells"] = dropped
                            meta["shell_count"] = int(meta.get("shell_count") or 0) - len(dropped)
                    meta["starter_preflight_ok"] = pre_ok
                    if pre_ok:
                        meta["geometry_source"] = "step_shell"
                        return content, meta, "step_shell"
                    print(
                        "[openradioss] WARN step shell starter preflight failed; bbox fallback",
                        flush=True,
                    )
                elif ok_refs:
                    meta["geometry_source"] = "step_shell"
                    meta["starter_preflight_ok"] = None
                    return content, meta, "step_shell"
        except Exception as exc:
            print(f"[openradioss] WARN step shell deck failed: {exc}", flush=True)
    content, meta = apply_manifest_deck(rad_content, manifest, category)
    if meta:
        meta["geometry_source"] = "bbox_scale"
        meta["step_shell_fallback"] = True
        return content, meta, "bbox_scale"
    return rad_content, None, "template"


def write_deck_meta(run_dir: Path, meta: dict[str, Any]) -> Path:
    run_dir.mkdir(parents=True, exist_ok=True)
    out = run_dir / "manifest_deck_meta.json"
    out.write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out
