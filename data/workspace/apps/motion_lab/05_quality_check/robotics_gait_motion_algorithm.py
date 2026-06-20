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


DEFAULT_ROBOT_LEARNING_THRESHOLDS = {
    "parallel_rollout_count": 16,
    "household_task_success_rate": 0.55,
    "factory_task_success_rate": 0.55,
    "collision_rate": 0.12,
    "unsafe_event_count": 0,
    "edge_latency_ms": 80.0,
    "real_robot_gate_passed": 1.0,
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


def evaluate_robot_learning_metrics(metrics: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Score embodied robot-learning readiness using DB-backed web knowledge.

    This complements single-walk QA. It checks whether the system is ready for
    many parallel robots, household tasks, factory tasks, and safe edge deployment.
    """
    limits = dict(DEFAULT_ROBOT_LEARNING_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    violations: list[dict[str, Any]] = []
    corrections: list[str] = []

    parallel = _finite_number(metrics.get("parallel_rollout_count"))
    if parallel is not None and parallel < limits["parallel_rollout_count"]:
        violations.append(
            {
                "rule_id": "vectorized_experience_collection",
                "severity": "medium",
                "metric": "parallel_rollout_count",
                "value": parallel,
                "limit": limits["parallel_rollout_count"],
            }
        )
        corrections.append("Increase headless rollout count before judging curriculum progress; render only sampled episodes.")

    household = _finite_number(metrics.get("household_task_success_rate"))
    if household is not None and household < limits["household_task_success_rate"]:
        violations.append(
            {
                "rule_id": "household_task_curriculum",
                "severity": "medium",
                "metric": "household_task_success_rate",
                "value": household,
                "limit": limits["household_task_success_rate"],
            }
        )
        corrections.append("Train household curriculum in small stages: approach, reach, open/close, sit/stand, then long-horizon tasks.")

    factory = _finite_number(metrics.get("factory_task_success_rate"))
    if factory is not None and factory < limits["factory_task_success_rate"]:
        violations.append(
            {
                "rule_id": "factory_task_curriculum",
                "severity": "medium",
                "metric": "factory_task_success_rate",
                "value": factory,
                "limit": limits["factory_task_success_rate"],
            }
        )
        corrections.append("Separate factory reward terms for fixture alignment, cycle time, failed-grasp recovery, and safety zones.")

    collision = _finite_number(metrics.get("collision_rate"))
    if collision is not None and collision > limits["collision_rate"]:
        violations.append(
            {
                "rule_id": "factory_task_curriculum",
                "severity": "high",
                "metric": "collision_rate",
                "value": collision,
                "limit": limits["collision_rate"],
            }
        )
        corrections.append("Add collision penalties, slower approach speed, larger clearance margins, and replay failing contacts.")

    unsafe = _finite_number(metrics.get("unsafe_event_count"))
    if unsafe is not None and unsafe > limits["unsafe_event_count"]:
        violations.append(
            {
                "rule_id": "sim_to_edge_deployment_gate",
                "severity": "high",
                "metric": "unsafe_event_count",
                "value": unsafe,
                "limit": limits["unsafe_event_count"],
            }
        )
        corrections.append("Block real-robot promotion until unsafe events are eliminated in offline replay.")

    latency = _finite_number(metrics.get("edge_latency_ms"))
    if latency is not None and latency > limits["edge_latency_ms"]:
        violations.append(
            {
                "rule_id": "sim_to_edge_deployment_gate",
                "severity": "medium",
                "metric": "edge_latency_ms",
                "value": latency,
                "limit": limits["edge_latency_ms"],
            }
        )
        corrections.append("Keep Raspberry Pi deployment to lightweight policy inference and push heavy training to K10/GPU.")

    real_gate = _finite_number(metrics.get("real_robot_gate_passed"))
    if real_gate is not None and real_gate < limits["real_robot_gate_passed"]:
        violations.append(
            {
                "rule_id": "sim_to_edge_deployment_gate",
                "severity": "high",
                "metric": "real_robot_gate_passed",
                "value": real_gate,
                "limit": limits["real_robot_gate_passed"],
            }
        )
        corrections.append("Require emergency stop, speed/force limits, and hardware-in-loop dry run before real-world task trials.")

    score = 100
    for item in violations:
        if item["severity"] == "high":
            score -= 24
        elif item["severity"] == "medium":
            score -= 11
        else:
            score -= 5
    score = max(0, score)
    verdict = "PASS" if score >= 82 and not any(v["severity"] == "high" for v in violations) else "REVIEW"
    if score < 60 or any(v["severity"] == "high" for v in violations):
        verdict = "HOLD"

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
    parser.add_argument("--robot-learning-json", help="Path to embodied robot-learning readiness metrics JSON.")
    parser.add_argument("--print-rules", action="store_true", help="Print DB-backed algorithm rules.")
    args = parser.parse_args()

    if args.print_rules:
        print(json.dumps(load_algorithm_rules(), ensure_ascii=False, indent=2))
        return 0
    if args.robot_learning_json:
        metrics = json.loads(Path(args.robot_learning_json).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_robot_learning_metrics(metrics), ensure_ascii=False, indent=2))
        return 0
    if not args.metrics_json:
        parser.error("--metrics-json or --robot-learning-json is required unless --print-rules is used")
    metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
    print(json.dumps(evaluate_gait_metrics(metrics), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
