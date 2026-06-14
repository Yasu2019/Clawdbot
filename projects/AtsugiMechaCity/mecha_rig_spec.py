# -*- coding: utf-8 -*-
"""Mecha rig spec contract (clawstack.mecha_rig_spec.v1) -- pure Python, no bpy.

The bridge between auto-classification, the human-in-the-loop GUI, and the
Blender rig builder:

  classifier  -> build_rig_spec() -> rig_spec.json  -> [GUI edits] -> Blender

The auto-classifier proposes a bone per segment (proposed_bone + confidence +
flagged). The spec keeps the user-editable decision separate (`bone`, `locked`)
so the GUI can correct the hard cases (which armor/pad belongs to which bone)
without losing the proposal. Joints carry the mechanical motion constraints
(hinge/ball/fixed + axis + limits) the user sets, which the Blender builder
turns into LIMIT_ROTATION constraints.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import mecha_rig_classifier as mrc

SCHEMA = "clawstack.mecha_rig_spec.v1"

# Skeleton hierarchy: child_bone -> parent_bone. Drives joint inference.
BONE_PARENT: dict[str, str] = {
    "Hips": "Root",
    "Chest": "Hips",
    "Neck": "Chest",
    "Head": "Neck",
    "MonoEye": "Head",
    "UpperArm_L": "Chest", "UpperArm_R": "Chest",
    "LowerArm_L": "UpperArm_L", "LowerArm_R": "UpperArm_R",
    "Hand_L": "LowerArm_L", "Hand_R": "LowerArm_R",
    "UpperLeg_L": "Hips", "UpperLeg_R": "Hips",
    "LowerLeg_L": "UpperLeg_L", "LowerLeg_R": "UpperLeg_R",
    "Foot_L": "LowerLeg_L", "Foot_R": "LowerLeg_R",
}

# Default motion constraint per child bone (the joint to its parent).
# type: hinge (1-axis) | revolute (limited swivel) | ball (free-ish) | fixed.
# axis is the local hinge axis; limits_deg the rotation range.
_JOINT_DEFAULTS: dict[str, dict[str, Any]] = {
    "Chest": {"name": "spine", "type": "revolute", "axis": [0, 0, 1], "limits_deg": {"min": -20, "max": 20}},
    "Neck": {"name": "neck", "type": "revolute", "axis": [0, 0, 1], "limits_deg": {"min": -45, "max": 45}},
    "Head": {"name": "head", "type": "revolute", "axis": [1, 0, 0], "limits_deg": {"min": -30, "max": 30}},
    "MonoEye": {"name": "mono_eye", "type": "revolute", "axis": [0, 0, 1], "limits_deg": {"min": -60, "max": 60}},
    "UpperArm_L": {"name": "shoulder_L", "type": "ball", "axis": [1, 0, 0], "limits_deg": {"min": -90, "max": 90}},
    "UpperArm_R": {"name": "shoulder_R", "type": "ball", "axis": [1, 0, 0], "limits_deg": {"min": -90, "max": 90}},
    "LowerArm_L": {"name": "elbow_L", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": -150, "max": 0}},
    "LowerArm_R": {"name": "elbow_R", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": -150, "max": 0}},
    "Hand_L": {"name": "wrist_L", "type": "hinge", "axis": [0, 0, 1], "limits_deg": {"min": -30, "max": 30}},
    "Hand_R": {"name": "wrist_R", "type": "hinge", "axis": [0, 0, 1], "limits_deg": {"min": -30, "max": 30}},
    "UpperLeg_L": {"name": "hip_L", "type": "ball", "axis": [1, 0, 0], "limits_deg": {"min": -90, "max": 60}},
    "UpperLeg_R": {"name": "hip_R", "type": "ball", "axis": [1, 0, 0], "limits_deg": {"min": -90, "max": 60}},
    "LowerLeg_L": {"name": "knee_L", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": 0, "max": 150}},
    "LowerLeg_R": {"name": "knee_R", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": 0, "max": 150}},
    "Foot_L": {"name": "ankle_L", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": -30, "max": 30}},
    "Foot_R": {"name": "ankle_R", "type": "hinge", "axis": [1, 0, 0], "limits_deg": {"min": -30, "max": 30}},
}

VALID_JOINT_TYPES = {"hinge", "revolute", "ball", "fixed"}

# Part characteristic, auto-set then user-confirmed:
#   structural     -> primary limb/torso mass, moves rigidly with its bone
#   armor_fixed    -> broad shell pinned to a bone (shoulder shield, backpack)
#   armor_follower -> partially follows an adjacent bone (skirt armor that opens
#                     when a leg lifts) -- needs a driver_bone + influence; NOT
#                     auto-detected (the hard case), left for the user to set.
VALID_PART_TYPES = {"structural", "armor_fixed", "armor_follower"}


def _infer_part_type(bone: str, size_norm: list[float] | tuple, source: str) -> str:
    """Auto-set the basic part characteristic (user confirms in the GUI)."""
    wide = max(float(s) for s in size_norm)
    # A broad segment pinned to the torso is shell armor, not structural mass.
    if bone in ("Chest", "Hips") and wide >= 0.40:
        return "armor_fixed"
    return "structural"


def _mean_centroid(segments: list[dict[str, Any]]) -> list[float] | None:
    pts = [s.get("centroid_norm") for s in segments if s.get("centroid_norm")]
    if not pts:
        return None
    n = len(pts)
    return [round(sum(p[i] for p in pts) / n, 4) for i in range(3)]


def build_rig_spec(
    audit_segments: list[dict[str, Any]],
    overrides: dict[str, Any] | None = None,
    *,
    model: str = "unknown",
    bounds_min: list[float] | None = None,
    bounds_max: list[float] | None = None,
    source_audit: str | None = None,
) -> dict[str, Any]:
    """Produce a rig spec proposal from classifier output (GUI-editable)."""
    overrides = overrides or {"exact": {}, "prefix": {}}
    seg_rows: list[dict[str, Any]] = []
    bone_segments: dict[str, list[dict[str, Any]]] = {}

    for seg in audit_segments:
        name = str(seg.get("mesh") or seg.get("name") or "?")
        centroid = seg.get("centroid_norm") or [0, 0, 0]
        size = seg.get("size_norm") or [0, 0, 0]
        a = mrc.classify_with_overrides(name, centroid, size, overrides)
        flagged = a.source == "heuristic" and (
            a.confidence < mrc.DEFAULT_CONFIDENCE_FLOOR or mrc._size_implausible(a.bone, size)
        )
        row = {
            "name": name,
            "centroid_norm": centroid,
            "size_norm": size,
            "proposed_bone": a.bone,
            "confidence": a.confidence,
            "proposal_source": a.source,  # override | heuristic
            "flagged": bool(flagged),
            # user-editable decision (defaults to the proposal):
            "bone": a.bone,
            "locked": a.source == "override",  # overrides are pre-confirmed
            # basic part characteristic, auto-set then user-confirmed:
            "part_type": _infer_part_type(a.bone, size, a.source),
            "driver_bone": None,   # for armor_follower (e.g. skirt -> UpperLeg_*)
            "follow_influence": 0.0,
        }
        seg_rows.append(row)
        bone_segments.setdefault(a.bone, []).append({"centroid_norm": centroid})

    # Infer one joint per structural bone present, positioned at the boundary
    # between the parent's and child's segment clusters (an editable estimate).
    joints: list[dict[str, Any]] = []
    present = set(bone_segments)
    for child, parent in BONE_PARENT.items():
        if child not in present:
            continue
        defaults = _JOINT_DEFAULTS.get(child, {})
        c_mean = _mean_centroid(bone_segments.get(child, []))
        p_mean = _mean_centroid(bone_segments.get(parent, []))
        if c_mean and p_mean:
            pos = [round((c_mean[i] + p_mean[i]) / 2.0, 4) for i in range(3)]
        else:
            pos = c_mean or p_mean
        joints.append(
            {
                "name": defaults.get("name", f"{parent}_{child}"),
                "parent_bone": parent,
                "child_bone": child,
                "position_norm": pos,
                "position_source": "estimated_boundary",
                "type": defaults.get("type", "hinge"),
                "axis": defaults.get("axis", [1, 0, 0]),
                "limits_deg": defaults.get("limits_deg", {"min": -45, "max": 45}),
                "locked": False,
            }
        )

    flagged_names = [s["name"] for s in seg_rows if s["flagged"]]
    return {
        "schema": SCHEMA,
        "model": model,
        "source_audit": source_audit,
        "bounds_min": bounds_min,
        "bounds_max": bounds_max,
        "segments": seg_rows,
        "joints": joints,
        "review": {
            "segment_count": len(seg_rows),
            "flagged_for_review": flagged_names,
            "flagged_count": len(flagged_names),
            "needs_user_confirmation": bool(flagged_names),
        },
    }


def validate_rig_spec(spec: dict[str, Any]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if spec.get("schema") != SCHEMA:
        issues.append(f"bad_schema:{spec.get('schema')}")
    segs = spec.get("segments") or []
    if not segs:
        issues.append("no_segments")
    for s in segs:
        if not s.get("bone"):
            issues.append(f"segment_no_bone:{s.get('name')}")
        pt = s.get("part_type")
        if pt and pt not in VALID_PART_TYPES:
            issues.append(f"bad_part_type:{s.get('name')}={pt}")
        if pt == "armor_follower" and not s.get("driver_bone"):
            issues.append(f"follower_without_driver:{s.get('name')}")
    for j in spec.get("joints") or []:
        if j.get("type") not in VALID_JOINT_TYPES:
            issues.append(f"bad_joint_type:{j.get('name')}={j.get('type')}")
        lim = j.get("limits_deg") or {}
        if j.get("type") != "fixed" and "min" in lim and "max" in lim and lim["min"] > lim["max"]:
            issues.append(f"joint_limits_inverted:{j.get('name')}")
    # A spec is only build-ready once every flagged segment has been confirmed.
    unconfirmed = [s["name"] for s in segs if s.get("flagged") and not s.get("locked")]
    if unconfirmed:
        issues.append(f"unconfirmed_flagged_segments:{unconfirmed}")
    return len(issues) == 0, issues


def build_rig_spec_from_audit(
    audit_json_path: str | Path,
    overrides_path: str | Path | None = None,
    *,
    model: str = "unknown",
) -> dict[str, Any]:
    data = json.loads(Path(audit_json_path).read_text(encoding="utf-8-sig"))
    overrides = mrc.load_overrides(overrides_path)
    return build_rig_spec(
        data.get("segment_assignments") or [],
        overrides,
        model=model,
        bounds_min=data.get("bounds_min"),
        bounds_max=data.get("bounds_max"),
        source_audit=str(audit_json_path),
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Mecha rig spec contract (build / validate)")
    parser.add_argument("--from-audit", help="Build a rig spec from a *_audit.json")
    parser.add_argument("--overrides", help="Per-model bone overrides JSON")
    parser.add_argument("--model", default="unknown")
    parser.add_argument("--validate", help="Validate an existing rig_spec.json")
    parser.add_argument("-o", "--out", help="Write rig spec to this path")
    args = parser.parse_args()

    if args.validate:
        spec = json.loads(Path(args.validate).read_text(encoding="utf-8-sig"))
        ok, issues = validate_rig_spec(spec)
        print(json.dumps({"ok": ok, "issues": issues}, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    if args.from_audit:
        spec = build_rig_spec_from_audit(args.from_audit, args.overrides, model=args.model)
        if args.out:
            Path(args.out).write_text(json.dumps(spec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        ok, issues = validate_rig_spec(spec)
        summary = {
            "model": spec["model"],
            "segments": spec["review"]["segment_count"],
            "joints": len(spec["joints"]),
            "flagged_for_review": spec["review"]["flagged_for_review"],
            "build_ready": ok,
            "blocking_issues": issues,
            "out": args.out,
        }
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0

    parser.error("Specify --from-audit or --validate")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
