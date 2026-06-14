# -*- coding: utf-8 -*-
"""Generalized mecha segment -> bone classifier (pure Python, no bpy).

Extracted from zaku_segmentation_rigid_rig.choose_bone_for_object so any mecha
(Zaku, RickDias, ...) can be auto-rigged from arbitrary segmentation. Adds:

- a confidence score per assignment (distance to the decision boundary that
  would flip the bone), so low-confidence segments are flagged automatically
  instead of being hand-corrected in code;
- data-driven overrides loaded from a per-model JSON (replacing the hard-coded
  MANUAL_BONE_OVERRIDES dict);
- an audit gate that fails closed when too many segments are low-confidence.

Inputs are normalized to the model bounding box, matching the convention of
zaku_segmentation_rigid_rig.normalized_point:
  centroid_norm = [nx, ny, nz]  with nx,ny in [-1,1] and nz in [0,1]
  size_norm     = [sx, sy, sz]  each = segment_extent_axis / model_extent_axis

This module has no Blender dependency and is fully unit/replay testable.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any

# Confidence threshold below which a segment is flagged for review.
DEFAULT_CONFIDENCE_FLOOR = 0.18
# Audit fails closed when the low-confidence ratio exceeds this.
DEFAULT_MAX_LOW_CONF_RATIO = 0.30

# Wide-shell thresholds: a segment spanning this much of the model is a broad
# armor/backpack shell and is pinned to the torso to avoid flying armor.
_WIDE_UPPER = 0.46
_WIDE_LOWER = 0.40

# Ground-truth-free anomaly check: these bones should own only small segments.
# A large segment assigned here is "confidently wrong" (e.g. a torso pipe landing
# on Neck, a shoulder shell on Head) -- confidence alone misses these, so size
# plausibility is a second, independent flag.
_SMALL_BONES = {"Head", "Neck", "Hand_L", "Hand_R", "Foot_L", "Foot_R", "MonoEye"}
_SMALL_BONE_MAX_SIZE = 0.25


def _size_implausible(bone: str, size_norm: list[float] | tuple) -> bool:
    return bone in _SMALL_BONES and max(float(s) for s in size_norm) > _SMALL_BONE_MAX_SIZE


@dataclass
class Assignment:
    bone: str
    confidence: float
    reason: str | None  # override reason, "wide_*", or None for clean heuristic
    source: str  # "override" | "heuristic"

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _clamp01(v: float) -> float:
    return 0.0 if v < 0 else (1.0 if v > 1 else v)


def classify_segment(
    centroid_norm: list[float] | tuple[float, float, float],
    size_norm: list[float] | tuple[float, float, float],
) -> Assignment:
    """Classify one normalized segment into a bone with a confidence score.

    The bone decision is a faithful port of the proven Zaku heuristic. The
    confidence is the normalized margin to the nearest boundary that, if
    crossed, would change the bone -- small margin => ambiguous => low score.
    """
    nx, ny, nz = float(centroid_norm[0]), float(centroid_norm[1]), float(centroid_norm[2])
    sx, sz = float(size_norm[0]), float(size_norm[2])
    abs_x = abs(nx)
    side = "L" if nx < 0 else "R"
    wide = max(sx, sz)

    # --- bone decision (port of choose_bone_for_object body) ---
    if wide >= _WIDE_UPPER and nz > 0.42:
        # Broad upper shell -> torso. Inherently a catch-all: cap confidence.
        margin = min(wide - _WIDE_UPPER, nz - 0.42)
        return Assignment("Chest", min(0.5, 0.2 + margin * 2.0), "wide_upper_segment_to_chest", "heuristic")
    if wide >= _WIDE_LOWER and nz <= 0.48:
        margin = min(wide - _WIDE_LOWER, 0.48 - nz)
        return Assignment("Hips", min(0.5, 0.2 + margin * 2.0), "wide_lower_segment_to_hips", "heuristic")

    if abs_x > 0.40 and 0.44 <= nz <= 0.86:
        # Arm chain by horizontal distance.
        if abs_x > 0.78:
            bone = f"Hand_{side}"
            margin = min(abs_x - 0.78, nz - 0.44, 0.86 - nz)
        elif abs_x > 0.58:
            bone = f"LowerArm_{side}"
            margin = min(abs_x - 0.58, 0.78 - abs_x, nz - 0.44, 0.86 - nz)
        else:
            bone = f"UpperArm_{side}"
            margin = min(abs_x - 0.40, 0.58 - abs_x, nz - 0.44, 0.86 - nz)
        return Assignment(bone, _conf(margin), None, "heuristic")

    if nz > 0.76:
        return Assignment("Head", _conf(nz - 0.76), None, "heuristic")
    if nz > 0.66:
        return Assignment("Neck", _conf(min(nz - 0.66, 0.76 - nz)), None, "heuristic")
    if nz > 0.43:
        return Assignment("Chest", _conf(min(nz - 0.43, 0.66 - nz)), None, "heuristic")
    if nz > 0.32:
        return Assignment("Hips", _conf(min(nz - 0.32, 0.43 - nz)), None, "heuristic")
    if abs_x > 0.12:
        if nz < 0.10:
            bone = f"Foot_{side}"
            margin = min(0.10 - nz, abs_x - 0.12)
        elif nz < 0.23:
            bone = f"LowerLeg_{side}"
            margin = min(nz - 0.10, 0.23 - nz, abs_x - 0.12)
        else:
            bone = f"UpperLeg_{side}"
            margin = min(nz - 0.23, 0.32 - nz, abs_x - 0.12)
        return Assignment(bone, _conf(margin), None, "heuristic")
    return Assignment("Root", _conf(0.12 - abs_x), None, "heuristic")


def _conf(margin: float, scale: float = 0.12) -> float:
    """Map a boundary margin (normalized units) to a confidence in [0,1].

    scale=0.12 means a segment ~0.12 normalized units clear of every flip
    boundary is fully confident; right on a boundary -> 0.
    """
    return round(_clamp01(margin / scale), 4)


def load_overrides(path: str | Path | None) -> dict[str, Any]:
    """Load per-model overrides JSON: {exact: {name: [bone, reason]},
    prefix: {prefix: [bone, reason]}}. Missing file -> empty overrides."""
    if not path:
        return {"exact": {}, "prefix": {}}
    p = Path(path)
    if not p.exists():
        return {"exact": {}, "prefix": {}}
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return {"exact": data.get("exact") or {}, "prefix": data.get("prefix") or {}}


def classify_with_overrides(
    name: str,
    centroid_norm: list[float] | tuple,
    size_norm: list[float] | tuple,
    overrides: dict[str, Any],
) -> Assignment:
    """Apply data-driven overrides first, else fall back to the heuristic."""
    exact = overrides.get("exact") or {}
    if name in exact:
        bone, reason = exact[name]
        return Assignment(bone, 1.0, reason, "override")
    for prefix, (bone, reason) in (overrides.get("prefix") or {}).items():
        if name.startswith(prefix):
            return Assignment(bone, 1.0, reason, "override")
    return classify_segment(centroid_norm, size_norm)


def audit_rig(
    segments: list[dict[str, Any]],
    overrides: dict[str, Any] | None = None,
    *,
    confidence_floor: float = DEFAULT_CONFIDENCE_FLOOR,
    max_low_conf_ratio: float = DEFAULT_MAX_LOW_CONF_RATIO,
) -> dict[str, Any]:
    """Classify all segments and fail closed if too many are low-confidence.

    Each segment dict needs: name/mesh, centroid_norm, size_norm.
    Returns assignments + flagged lists + pass verdict.
    """
    overrides = overrides or {"exact": {}, "prefix": {}}
    assignments: list[dict[str, Any]] = []
    low_confidence: list[str] = []
    size_anomaly: list[str] = []
    flagged: list[str] = []

    for seg in segments:
        name = str(seg.get("name") or seg.get("mesh") or "?")
        size_norm = seg.get("size_norm") or [0, 0, 0]
        a = classify_with_overrides(
            name, seg.get("centroid_norm") or [0, 0, 0], size_norm, overrides
        )
        row = {"name": name, **a.as_dict()}
        # Only heuristic assignments get audited; explicit overrides are trusted.
        if a.source == "heuristic":
            is_low = a.confidence < confidence_floor
            is_big = _size_implausible(a.bone, size_norm)
            if is_low:
                low_confidence.append(name)
            if is_big:
                size_anomaly.append(name)
                row["anomaly"] = f"size_implausible_for_{a.bone}"
            if is_low or is_big:
                flagged.append(name)
        assignments.append(row)

    n = len(assignments)
    flag_ratio = (len(flagged) / n) if n else 0.0
    ok = flag_ratio <= max_low_conf_ratio
    return {
        "schema": "clawstack.mecha_rig_audit.v1",
        "segment_count": n,
        "assignments": assignments,
        "flagged_for_review": flagged,
        "flagged_count": len(flagged),
        "low_confidence": low_confidence,
        "size_anomaly": size_anomaly,
        "flagged_ratio": round(flag_ratio, 4),
        "confidence_floor": confidence_floor,
        "max_flagged_ratio": max_low_conf_ratio,
        "verdict": "PASS" if ok else "FAIL",
        "verdict_reason": (
            "ok"
            if ok
            else f"flagged_ratio {round(flag_ratio,4)} > {max_low_conf_ratio}; review {flagged}"
        ),
    }


def replay_audit(audit_json_path: str | Path, overrides_path: str | Path | None = None) -> dict[str, Any]:
    """Re-run the classifier against an existing Blender-produced audit JSON.

    Verifies (no Blender): does the extracted classifier reproduce the recorded
    heuristic bones, and does it flag exactly the segments that needed manual
    overrides? Returns a comparison report.
    """
    data = json.loads(Path(audit_json_path).read_text(encoding="utf-8-sig"))
    recorded = data.get("segment_assignments") or []
    overrides = load_overrides(overrides_path)
    prefixes = tuple((overrides.get("prefix") or {}).keys())

    rows: list[dict[str, Any]] = []
    heuristic_match = 0
    heuristic_total = 0
    override_recorded = 0
    override_flagged_low = 0
    # Honest gate metric: separate GROSS individual misclassifications (a torso
    # pipe landing on Neck, a shell on Head -- visibly broken rigs) from bulk
    # near-boundary sub-segments resolved by a blanket prefix rule (e.g. a knee
    # split). The safety property is catching the gross ones.
    gross_disagreements = 0
    gross_flagged = 0
    bulk_disagreements = 0
    for seg in recorded:
        name = str(seg.get("mesh") or seg.get("name") or "?")
        rec_bone = seg.get("bone")
        rec_reason = seg.get("reason")
        size_norm = seg.get("size_norm") or [0, 0, 0]
        a = classify_segment(seg.get("centroid_norm") or [0, 0, 0], size_norm)
        was_override = bool(rec_reason and str(rec_reason).startswith("manual"))
        # Production-equivalent flag: no ground truth available, only confidence
        # and size plausibility (NOT bone mismatch, which needs the answer).
        flagged = a.confidence < DEFAULT_CONFIDENCE_FLOOR or _size_implausible(a.bone, size_norm)
        row = {
            "name": name,
            "recorded_bone": rec_bone,
            "recorded_reason": rec_reason,
            "classifier_bone": a.bone,
            "confidence": a.confidence,
            "flagged_for_review": flagged,
            "was_manual_override": was_override,
        }
        if a.bone != rec_bone:
            if prefixes and name.startswith(prefixes):
                bulk_disagreements += 1
            else:
                gross_disagreements += 1
                if flagged:
                    gross_flagged += 1
        if was_override:
            override_recorded += 1
            if flagged:
                override_flagged_low += 1
                row["flagged"] = True
        else:
            heuristic_total += 1
            if a.bone == rec_bone:
                heuristic_match += 1
            else:
                row["heuristic_mismatch"] = True
        rows.append(row)

    return {
        "schema": "clawstack.mecha_rig_replay.v1",
        "audit_json": str(audit_json_path),
        "segment_count": len(recorded),
        "heuristic_faithful_match": f"{heuristic_match}/{heuristic_total}",
        "heuristic_match_pct": round(100.0 * heuristic_match / heuristic_total, 1) if heuristic_total else 0.0,
        "gross_misclassifications": gross_disagreements,
        "gross_flagged_by_audit": gross_flagged,
        "gross_audit_recall_pct": round(100.0 * gross_flagged / gross_disagreements, 1) if gross_disagreements else 100.0,
        "bulk_split_disagreements": bulk_disagreements,
        "manual_override_segments": override_recorded,
        "rows": rows,
    }


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Mecha segment->bone classifier / audit")
    parser.add_argument("--replay-audit", help="Existing *_audit.json to replay the classifier against")
    parser.add_argument("--overrides", help="Per-model bone overrides JSON")
    parser.add_argument("--json", action="store_true", help="Full per-segment rows")
    args = parser.parse_args()

    if args.replay_audit:
        report = replay_audit(args.replay_audit, args.overrides)
        if not args.json:
            report.pop("rows", None)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    parser.error("Specify --replay-audit <audit.json>")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
