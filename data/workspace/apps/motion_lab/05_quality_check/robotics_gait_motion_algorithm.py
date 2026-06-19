import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import math
import sqlite3
from pathlib import Path
from typing import Any


DEFAULT_DB = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "web_sourced"
    / "robotics_gait_knowledge"
    / "robotics_gait_knowledge.db"
)


DEFAULT_THRESHOLDS = {
    "stance_foot_velocity_mps": 0.035,
    "foot_penetration_m": 0.015,
    "support_margin_m": -0.025,
    "root_speed_cv": 0.35,
    "swing_foot_clearance_min_m": 0.025,
    "swing_foot_clearance_max_m": 0.30,
    "joint_delta_deg_per_frame": 18.0,
    "com_lateral_sway_ratio": 0.30,
}


def load_algorithm_rules(db_path: Path = DEFAULT_DB) -> list[dict[str, Any]]:
    if not db_path.exists():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT id, priority, metric, rule, motion_use, source_ids FROM algorithm_rules ORDER BY priority, id"
    ).fetchall()
    conn.close()
    rules = []
    for row in rows:
        item = dict(row)
        try:
            item["source_ids"] = json.loads(item.get("source_ids") or "[]")
        except json.JSONDecodeError:
            item["source_ids"] = []
        rules.append(item)
    return rules


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(number):
        return None
    return number


def evaluate_gait_metrics(metrics: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Score a generated walk using robotics-informed visual stability rules.

    This function is intentionally read-only: it does not edit animation data.
    Feed it measured QA values from Blender or a render analyzer, then use the
    returned corrections as the next-pass animation plan.
    """
    limits = dict(DEFAULT_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    violations: list[dict[str, Any]] = []
    corrections: list[str] = []

    stance_speed = _finite_number(metrics.get("stance_foot_velocity_mps"))
    if stance_speed is not None and stance_speed > limits["stance_foot_velocity_mps"]:
        violations.append(
            {
                "rule_id": "foot_contact_lock",
                "severity": "high",
                "metric": "stance_foot_velocity_mps",
                "value": stance_speed,
                "limit": limits["stance_foot_velocity_mps"],
            }
        )
        corrections.append("Lock planted foot in world space during stance and solve pelvis/knee with IK.")

    penetration = _finite_number(metrics.get("foot_penetration_m"))
    if penetration is not None and penetration > limits["foot_penetration_m"]:
        violations.append(
            {
                "rule_id": "foot_contact_lock",
                "severity": "high",
                "metric": "foot_penetration_m",
                "value": penetration,
                "limit": limits["foot_penetration_m"],
            }
        )
        corrections.append("Raise stance foot to terrain height and blend ankle/pelvis correction over nearby frames.")

    support_margin = _finite_number(metrics.get("support_margin_m"))
    if support_margin is not None and support_margin < limits["support_margin_m"]:
        violations.append(
            {
                "rule_id": "support_polygon_gate",
                "severity": "high",
                "metric": "support_margin_m",
                "value": support_margin,
                "limit": limits["support_margin_m"],
            }
        )
        corrections.append("Shift pelvis/root toward the stance foot or widen stance until projected CoM reads stable.")

    root_cv = _finite_number(metrics.get("root_speed_cv"))
    if root_cv is not None and root_cv > limits["root_speed_cv"]:
        violations.append(
            {
                "rule_id": "root_com_smoothing",
                "severity": "medium",
                "metric": "root_speed_cv",
                "value": root_cv,
                "limit": limits["root_speed_cv"],
            }
        )
        corrections.append("Smooth root translation and make stride distance consistent with footfall timing.")

    clearance = _finite_number(metrics.get("swing_foot_clearance_m"))
    if clearance is not None:
        if clearance < limits["swing_foot_clearance_min_m"]:
            violations.append(
                {
                    "rule_id": "swing_foot_clearance",
                    "severity": "medium",
                    "metric": "swing_foot_clearance_m",
                    "value": clearance,
                    "limit": limits["swing_foot_clearance_min_m"],
                }
            )
            corrections.append("Increase swing-foot arc during mid-swing to avoid scraping.")
        elif clearance > limits["swing_foot_clearance_max_m"]:
            violations.append(
                {
                    "rule_id": "swing_foot_clearance",
                    "severity": "low",
                    "metric": "swing_foot_clearance_m",
                    "value": clearance,
                    "limit": limits["swing_foot_clearance_max_m"],
                }
            )
            corrections.append("Lower swing-foot arc to avoid a floating or marching look.")

    joint_delta = _finite_number(metrics.get("max_joint_delta_deg_per_frame"))
    if joint_delta is not None and joint_delta > limits["joint_delta_deg_per_frame"]:
        violations.append(
            {
                "rule_id": "ik_continuity_gate",
                "severity": "medium",
                "metric": "max_joint_delta_deg_per_frame",
                "value": joint_delta,
                "limit": limits["joint_delta_deg_per_frame"],
            }
        )
        corrections.append("Limit IK correction weight per frame and smooth hip/knee/ankle deltas.")

    sway_ratio = _finite_number(metrics.get("com_lateral_sway_ratio"))
    if sway_ratio is not None and sway_ratio > limits["com_lateral_sway_ratio"]:
        violations.append(
            {
                "rule_id": "support_polygon_gate",
                "severity": "medium",
                "metric": "com_lateral_sway_ratio",
                "value": sway_ratio,
                "limit": limits["com_lateral_sway_ratio"],
            }
        )
        corrections.append("Reduce side-to-side pelvis sway or increase step width for visual balance.")

    score = 100
    for item in violations:
        if item["severity"] == "high":
            score -= 22
        elif item["severity"] == "medium":
            score -= 12
        else:
            score -= 6
    score = max(0, score)
    verdict = "PASS" if score >= 82 and not any(v["severity"] == "high" for v in violations) else "REVIEW"
    if score < 60 or sum(1 for v in violations if v["severity"] == "high") >= 2:
        verdict = "FAIL"

    return {
        "score": score,
        "verdict": verdict,
        "violations": violations,
        "corrections": list(dict.fromkeys(corrections)),
        "rules_loaded": load_algorithm_rules(),
        "thresholds": limits,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Robotics-informed gait QA for generated 3D motion.")
    parser.add_argument("--metrics-json", help="Path to measured gait metrics JSON.")
    parser.add_argument("--print-rules", action="store_true", help="Print DB-backed algorithm rules.")
    args = parser.parse_args()

    if args.print_rules:
        print(json.dumps(load_algorithm_rules(), ensure_ascii=False, indent=2))
        return 0
    if not args.metrics_json:
        parser.error("--metrics-json is required unless --print-rules is used")
    metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
    print(json.dumps(evaluate_gait_metrics(metrics), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
