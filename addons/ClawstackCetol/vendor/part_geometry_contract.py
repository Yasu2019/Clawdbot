# -*- coding: utf-8 -*-
"""Minimal part_geometry_contract for the portable FreeCAD vendor tree."""
from __future__ import annotations

from typing import Any


def merged_tolerance_dims(manifest: dict[str, Any], include_gdt: bool = True) -> list[dict[str, Any]]:
    feats = (manifest or {}).get("features") or {}
    rows: list[dict[str, Any]] = []
    for h in feats.get("holes") or []:
        if not isinstance(h, dict):
            continue
        rows.append({
            "name": str(h.get("name") or "hole"),
            "tolerance": float(h.get("position_tol_mm") or h.get("tolerance_mm") or 0.05),
            "coef": 1.0,
            "source": str(h.get("source") or "gdt_measured"),
            "distribution": "normal",
        })
    return rows


def detect_maturity_level(manifest: dict[str, Any], include_gdt: bool = True) -> str:
    holes = ((manifest or {}).get("features") or {}).get("holes") or []
    joints = (manifest or {}).get("freecad_assembly_joints") or []
    if joints and holes:
        return "L3_freecad_assembly_holes"
    if holes:
        return "L2_freecad_holes"
    return "L1_freecad_bbox"
