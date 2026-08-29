# -*- coding: utf-8 -*-
"""Document -> part_manifest (no Docker, no K10 paths).

Works with a real FreeCAD document or a plain dict fixture for tests.
"""
from __future__ import annotations

import math
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def _safe_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def cluster_holes(holes: list[dict[str, Any]], merge_mm: float = 0.6) -> list[dict[str, Any]]:
    """Merge cylindrical faces that share a center (two halves of one hole)."""
    out: list[dict[str, Any]] = []
    for h in holes:
        xyz = h.get("xyz_mm") or [0.0, 0.0, 0.0]
        x, y, z = _safe_float(xyz[0]), _safe_float(xyz[1]), _safe_float(xyz[2] if len(xyz) > 2 else 0.0)
        merged = False
        for e in out:
            ex, ey, ez = e["xyz_mm"]
            if math.hypot(x - ex, y - ey) <= merge_mm and abs(z - ez) <= merge_mm * 2:
                merged = True
                break
        if not merged:
            rec = dict(h)
            rec["xyz_mm"] = [round(x, 4), round(y, 4), round(z, 4)]
            out.append(rec)
    return out[:8]


def bbox_from_extents(
    xmin: float, xmax: float, ymin: float, ymax: float, zmin: float, zmax: float
) -> dict[str, float]:
    return {
        "Lx": round(max(xmax - xmin, 0.0), 4),
        "Ly": round(max(ymax - ymin, 0.0), 4),
        "Lz": round(max(zmax - zmin, 0.0), 4),
    }


def extract_joints_from_objects(objects: list[Any]) -> list[dict[str, Any]]:
    """Read FreeCAD Assembly JointType / Assembly4-style Label pairs (duck typing)."""
    joints: list[dict[str, Any]] = []
    seq = 1
    for obj in objects:
        jt = getattr(obj, "JointType", None)
        if jt is None:
            continue
        name = str(getattr(obj, "Label", None) or getattr(obj, "Name", "") or "joint")
        r1 = getattr(obj, "Reference1", None)
        r2 = getattr(obj, "Reference2", None)

        def _ref_label(ref: Any) -> str:
            if ref is None:
                return ""
            if isinstance(ref, (list, tuple)) and ref:
                a = ref[0]
                return str(getattr(a, "Label", None) or getattr(a, "Name", "") or a)
            return str(getattr(ref, "Label", None) or getattr(ref, "Name", "") or ref)

        kind = str(jt).lower()
        mapped = "planar_contact"
        if "cylin" in kind or "slider" in kind:
            mapped = "pin_hole_float"
        elif "revolute" in kind or "hinge" in kind:
            mapped = "revolute"
        elif "fixed" in kind or "ground" in kind:
            mapped = "fixed"
        elif "planar" in kind or "flush" in kind:
            mapped = "planar_contact"
        if mapped == "pin_hole_float":
            dofs = ["Tx", "Ty"]
        elif mapped == "fixed":
            dofs = ["Tx", "Ty", "Tz", "Rx", "Ry", "Rz"]
        elif mapped == "revolute":
            dofs = ["Tx", "Ty", "Tz", "Rx", "Ry"]
        else:
            dofs = ["Tz", "Rx", "Ry"]
        joints.append({
            "id": str(getattr(obj, "Name", name)),
            "label": name,
            "kind": mapped,
            "cad_joint_type": str(jt),
            "from": _ref_label(r1),
            "to": _ref_label(r2),
            "sequence": seq,
            "float": mapped == "pin_hole_float",
            "constrained_dof": dofs,
            "source": "freecad_assembly",
        })
        seq += 1
    return joints


def apply_pin_mmc_to_holes(
    holes: list[dict[str, Any]],
    pin_diameter_mm: float,
    pin_tol_mm: float = 0.02,
) -> list[dict[str, Any]]:
    """Attach MMC + pin size so the solver can apply a bonus (needs both)."""
    if pin_diameter_mm <= 0 or not holes:
        return holes
    for h in holes:
        if not isinstance(h, dict):
            continue
        h["mmc"] = h.get("mmc") or "MMC"
        if not h.get("diameter_tol_mm") and not h.get("size_tol_mm"):
            h["diameter_tol_mm"] = 0.05
        h["pin_diameter_mm"] = pin_diameter_mm
        h["pin_tol_mm"] = pin_tol_mm
        h["pin_mmc"] = h.get("pin_mmc") or "MMC"
    return holes


def pin_diameter_from_objects(objects: list[Any]) -> tuple[float, float]:
    """Return (pin_diameter_mm, pin_tol_mm) from an object named Pin, else (0, 0)."""
    for obj in objects:
        lab = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "").lower()
        if lab != "pin":
            continue
        shape = getattr(obj, "Shape", None)
        faces = getattr(shape, "Faces", None) or []
        for face in faces:
            surf = getattr(face, "Surface", None)
            if surf is None or not hasattr(surf, "Radius"):
                continue
            try:
                rad = float(surf.Radius)
            except Exception:
                continue
            if rad > 0.05:
                return round(2.0 * rad, 4), 0.02
    return 0.0, 0.0


def manifest_from_shape_records(
    *,
    job_id: str,
    bbox: dict[str, float],
    holes: list[dict[str, Any]],
    joints: list[dict[str, Any]] | None = None,
    datums: list[dict[str, Any]] | None = None,
    object_names: list[str] | None = None,
) -> dict[str, Any]:
    lx = _safe_float(bbox.get("Lx"))
    ly = _safe_float(bbox.get("Ly"))
    lz = _safe_float(bbox.get("Lz"))
    sheet = min(v for v in (lx, ly, lz) if v > 0) if any(v > 0 for v in (lx, ly, lz)) else 2.0
    clustered = cluster_holes(holes)
    return {
        "schema": "clawstack.part_manifest.v1",
        "job_id": job_id,
        "source_dxf": job_id + ".FCStd",
        "bbox_mm": {"Lx": lx or 40.0, "Ly": ly or 20.0, "Lz": lz or sheet},
        "sheet_thickness_mm": sheet,
        "features": {
            "holes": clustered,
            "datums": datums or [],
            "nominal_dims_mm": [],
        },
        "freecad_assembly_joints": joints or [],
        "freecad_objects": object_names or [],
        "units": "mm",
        "extract_source": "freecad_workbench",
    }


def extract_from_freecad_document(doc: Any) -> dict[str, Any]:
    """Active FreeCAD document -> manifest. Requires a document with Shape objects."""
    job = str(getattr(doc, "Name", None) or "FreeCADDoc")
    xmin = ymin = zmin = 1.0e9
    xmax = ymax = zmax = -1.0e9
    holes: list[dict[str, Any]] = []
    names: list[str] = []
    objects = list(getattr(doc, "Objects", []) or [])
    for obj in objects:
        names.append(str(getattr(obj, "Name", "") or ""))
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        is_null = getattr(shape, "isNull", None)
        if callable(is_null) and is_null():
            continue
        bb = getattr(shape, "BoundBox", None)
        if bb is not None:
            xmin = min(xmin, float(bb.XMin))
            xmax = max(xmax, float(bb.XMax))
            ymin = min(ymin, float(bb.YMin))
            ymax = max(ymax, float(bb.YMax))
            zmin = min(zmin, float(bb.ZMin))
            zmax = max(zmax, float(bb.ZMax))
        faces = getattr(shape, "Faces", None) or []
        for i, face in enumerate(faces):
            surf = getattr(face, "Surface", None)
            if surf is None or not hasattr(surf, "Radius"):
                continue
            try:
                rad = float(surf.Radius)
                ctr = surf.Center
                hx, hy, hz = float(ctr.x), float(ctr.y), float(ctr.z)
            except Exception:
                continue
            if rad <= 0.05 or rad > 80.0:
                continue
            holes.append({
                "name": f"{getattr(obj, 'Name', 'part')}_hole_{i + 1}",
                "diameter_mm": round(2.0 * rad, 4),
                "xyz_mm": [round(hx, 4), round(hy, 4), round(hz, 4)],
                "position_tol_mm": 0.05,
                "source": "freecad_cylindrical_face",
            })
    pin_d, pin_tol = pin_diameter_from_objects(objects)
    holes = apply_pin_mmc_to_holes(holes, pin_d, pin_tol)
    if xmax < xmin:
        xmin = ymin = zmin = 0.0
        xmax, ymax, zmax = 40.0, 20.0, 2.0
    bbox = bbox_from_extents(xmin, xmax, ymin, ymax, zmin, zmax)
    joints = extract_joints_from_objects(objects)
    for j in joints:
        if j.get("kind") != "pin_hole_float" or j.get("clearance_mm"):
            continue
        hd = 0.0
        for h in holes:
            try:
                hd = max(hd, float(h.get("diameter_mm") or 0.0))
            except (TypeError, ValueError):
                continue
        if pin_d > 0 and hd > pin_d:
            j["clearance_mm"] = round(max((hd - pin_d) * 0.5, 0.01), 4)
        elif hd > 0:
            j["clearance_mm"] = round(max(hd * 0.02, 0.02), 4)
    datums: list[dict[str, Any]] = []
    if joints:
        datums.append({"name": "datum_A", "letter": "A", "flatness_tol_mm": 0.02})
    return manifest_from_shape_records(
        job_id=job,
        bbox=bbox,
        holes=holes,
        joints=joints,
        datums=datums,
        object_names=[n for n in names if n],
    )
