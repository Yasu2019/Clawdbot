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


DEFAULT_TASK_MOTION_THRESHOLDS = {
    "motion_naturalness_mean": 0.78,
    "task_success_rate": 0.70,
    "task_score_min": 78.0,
    "walk_arm_leg_phase_error_deg": 22.0,
    "walk_foot_sliding_m": 0.025,
    "door_hand_target_error_m": 0.055,
    "door_torso_twist_deg": 22.0,
    "sit_knee_hip_sync_error": 0.18,
    "sit_com_support_margin_m": -0.010,
    "stair_foot_clearance_m": 0.045,
    "factory_pick_hand_target_error_m": 0.045,
    "factory_pick_clearance_m": 0.040,
    "jerk_norm": 0.35,
    "collision_rate": 0.08,
}

IE_REFERENCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "assets"
    / "user_provided"
    / "ie_motion_knowledge"
    / "therblig_most_reference.json"
)

DEFAULT_THERBLIG_MOST_THRESHOLDS = {
    "therblig_label_coverage_pct": 85.0,
    "effective_therblig_ratio": 0.62,
    "non_effective_therblig_share": 0.38,
    "nva_time_ratio": 0.28,
    "ecrs_improvement_pct": 8.0,
    "most_sequence_valid": 1.0,
    "most_index_error_pct": 12.0,
    "most_cycle_efficiency_pct": 82.0,
    "workstudy_export_ready": 1.0,
    "parallel_therblig_rollout_count": 16,
    "therblig_score_floor": 72.0,
    "household_therblig_task_floor": 75.0,
    "factory_most_task_floor": 78.0,
}


def load_therblig_most_reference() -> dict[str, Any]:
    if not IE_REFERENCE_PATH.exists():
        return {}
    try:
        return json.loads(IE_REFERENCE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


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


def _therblig_level_verdict(score: int, high_count: int, metrics: dict[str, Any], limits: dict[str, float]) -> str:
    """Map IE motion mastery score to L31-L40 gate labels."""
    efficiency = _finite_number(metrics.get("most_cycle_efficiency_pct"))
    ecrs = _finite_number(metrics.get("ecrs_improvement_pct"))
    l40 = (
        score >= 90
        and high_count == 0
        and efficiency is not None
        and efficiency >= limits["most_cycle_efficiency_pct"] + 10.0
        and ecrs is not None
        and ecrs >= limits["ecrs_improvement_pct"] + 7.0
    )
    if l40:
        return "L40_IE_MASTER"
    if score >= 88 and high_count == 0:
        return "L39_FACTORY_MOST"
    if score >= 84 and high_count <= 1:
        return "L38_HOUSEHOLD_THERBLIG"
    if score >= 80 and high_count <= 1:
        return "L37_MULTI_ROBOT_IE"
    if score >= 76:
        return "L36_WORKSTUDY_BRIDGE"
    if score >= 72:
        return "L35_STANDARD_TIME"
    if score >= 68:
        return "L34_MOST_SEQUENCE"
    if score >= 64:
        return "L33_ECRS"
    if score >= 58:
        return "L32_EFFECTIVE_RATIO"
    if score >= 50:
        return "L31_RECOGNITION"
    return "HOLD"


def evaluate_therblig_most_metrics(metrics: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Score L31-L40 IE motion mastery: Therblig decomposition + MOST standard time.

    Uses therblig_most_reference.json (Funai therblig column + Sandin MOST textbook metadata).
    """
    limits = dict(DEFAULT_THERBLIG_MOST_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    reference = load_therblig_most_reference()
    violations: list[dict[str, Any]] = []
    corrections: list[str] = []

    def below(metric: str, rule_id: str, severity: str, message: str) -> None:
        value = _finite_number(metrics.get(metric))
        if value is not None and value < limits[metric]:
            violations.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "metric": metric,
                    "value": value,
                    "limit": limits[metric],
                }
            )
            corrections.append(message)

    def above(metric: str, rule_id: str, severity: str, message: str) -> None:
        value = _finite_number(metrics.get(metric))
        if value is not None and value > limits[metric]:
            violations.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "metric": metric,
                    "value": value,
                    "limit": limits[metric],
                }
            )
            corrections.append(message)

    below(
        "therblig_label_coverage_pct",
        "therblig_recognition_gate",
        "high",
        "Decompose each task into 18 therblig elements before scoring; label reach/grasp/move/use phases explicitly.",
    )
    below(
        "effective_therblig_ratio",
        "effective_therblig_ratio_gate",
        "high",
        "Reduce Search, Select, Hold, and Avoidable Delay; raise value-adding Reach/Grasp/Move/Use share.",
    )
    above(
        "non_effective_therblig_share",
        "effective_therblig_ratio_gate",
        "medium",
        "Apply ECRS Eliminate to Search/Select and fixture pre-positioning to cut non-effective therbligs.",
    )
    above(
        "nva_time_ratio",
        "ecrs_waste_reduction_gate",
        "medium",
        "Cut non-value-added time with bin organization, tool pre-position, and motion path rearrangement.",
    )
    below(
        "ecrs_improvement_pct",
        "ecrs_waste_reduction_gate",
        "medium",
        "Record before/after therblig counts and apply ECRS Eliminate/Combine/Rearrange/Simplify.",
    )

    most_valid = _finite_number(metrics.get("most_sequence_valid"))
    if most_valid is not None and most_valid < limits["most_sequence_valid"]:
        violations.append(
            {
                "rule_id": "most_sequence_encoding_gate",
                "severity": "high",
                "metric": "most_sequence_valid",
                "value": most_valid,
                "limit": limits["most_sequence_valid"],
            }
        )
        corrections.append("Encode factory pick/place as MOST General Move: reach-grasp-move-position-release.")

    above(
        "most_index_error_pct",
        "most_sequence_encoding_gate",
        "medium",
        "Tune MOST indices against Sandin sequence method; reduce index error before standard-time gate.",
    )
    below(
        "most_cycle_efficiency_pct",
        "most_standard_time_gate",
        "high",
        "Compare rollout cycle time to MOST standard time; improve until efficiency meets L35+ gate.",
    )

    export_ready = _finite_number(metrics.get("workstudy_export_ready"))
    if export_ready is not None and export_ready < limits["workstudy_export_ready"]:
        violations.append(
            {
                "rule_id": "workstudy_ai_bridge_gate",
                "severity": "medium",
                "metric": "workstudy_export_ready",
                "value": export_ready,
                "limit": limits["workstudy_export_ready"],
            }
        )
        corrections.append("Export therblig timeline + MOST TMU summary for WorkStudy AI (port 7870) review.")

    parallel = _finite_number(metrics.get("parallel_therblig_rollout_count"))
    if parallel is not None and parallel < limits["parallel_therblig_rollout_count"]:
        below(
            "parallel_therblig_rollout_count",
            "therblig_recognition_gate",
            "low",
            "Run therblig scoring on at least 16 parallel robot rollouts before L37 promotion.",
        )

    therblig_scores = metrics.get("therblig_task_scores") or {}
    if isinstance(therblig_scores, dict):
        household_scores = [
            float(v) for k, v in therblig_scores.items() if k in {"door", "sit_stand", "stairs"} and _finite_number(v) is not None
        ]
        if household_scores and min(household_scores) < limits["household_therblig_task_floor"]:
            violations.append(
                {
                    "rule_id": "household_task_curriculum",
                    "severity": "medium",
                    "metric": "household_therblig_task_floor",
                    "value": min(household_scores),
                    "limit": limits["household_therblig_task_floor"],
                }
            )
            corrections.append("Improve household therblig decomposition on door/chair/stair tasks.")

        factory_score = _finite_number(therblig_scores.get("factory_pick"))
        if factory_score is not None and factory_score < limits["factory_most_task_floor"]:
            violations.append(
                {
                    "rule_id": "factory_task_curriculum",
                    "severity": "high",
                    "metric": "factory_most_task_floor",
                    "value": factory_score,
                    "limit": limits["factory_most_task_floor"],
                }
            )
            corrections.append("Factory pick must pass MOST + therblig floor before L39 promotion.")

    score = 100
    for item in violations:
        if item["severity"] == "high":
            score -= 16
        elif item["severity"] == "medium":
            score -= 9
        else:
            score -= 4
    score = max(0, score)
    high_count = sum(1 for v in violations if v["severity"] == "high")
    verdict = _therblig_level_verdict(score, high_count, metrics, limits)

    return {
        "score": score,
        "verdict": verdict,
        "violations": violations,
        "corrections": list(dict.fromkeys(corrections)),
        "rules_loaded": load_algorithm_rules(),
        "thresholds": limits,
        "reference_loaded": bool(reference),
        "level_gates": reference.get("level_gates", {}),
    }


def evaluate_task_motion_metrics(metrics: dict[str, Any], thresholds: dict[str, float] | None = None) -> dict[str, Any]:
    """Score L11-L20 natural task motion readiness.

    L10 focuses on natural locomotion. L20 requires natural task movements:
    reaching a door handle, sit/stand transitions, stair clearance, and
    factory pick/place motions. This evaluator keeps the loop measurable before
    expensive Blender/physics rendering.
    """
    limits = dict(DEFAULT_TASK_MOTION_THRESHOLDS)
    if thresholds:
        limits.update(thresholds)

    violations: list[dict[str, Any]] = []
    corrections: list[str] = []

    def above(metric: str, rule_id: str, severity: str, message: str) -> None:
        value = _finite_number(metrics.get(metric))
        if value is not None and value > limits[metric]:
            violations.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "metric": metric,
                    "value": value,
                    "limit": limits[metric],
                }
            )
            corrections.append(message)

    def below(metric: str, rule_id: str, severity: str, message: str) -> None:
        value = _finite_number(metrics.get(metric))
        if value is not None and value < limits[metric]:
            violations.append(
                {
                    "rule_id": rule_id,
                    "severity": severity,
                    "metric": metric,
                    "value": value,
                    "limit": limits[metric],
                }
            )
            corrections.append(message)

    below(
        "motion_naturalness_mean",
        "l20_motion_naturalness_gate",
        "high",
        "Raise overall naturalness by smoothing pelvis/root timing and adding task-specific anticipation/follow-through.",
    )
    below(
        "task_success_rate",
        "l20_task_success_gate",
        "high",
        "Split long tasks into approach, align, contact, act, release, and recover phases before full task scoring.",
    )
    above(
        "walk_arm_leg_phase_error_deg",
        "contralateral_limb_phase",
        "high",
        "Keep right-leg-forward with left-arm-forward and left-leg-forward with right-arm-forward within one gait beat.",
    )
    above(
        "walk_foot_sliding_m",
        "foot_contact_lock",
        "high",
        "Lock stance foot in world space; solve pelvis and ankle over stance frames rather than sliding the foot.",
    )
    above(
        "door_hand_target_error_m",
        "door_reach_contact_gate",
        "medium",
        "Add approach-align-reach-contact-open phases and slow wrist motion near the handle.",
    )
    above(
        "door_torso_twist_deg",
        "door_reach_contact_gate",
        "medium",
        "Rotate torso and shoulder together; avoid opening a door with an isolated arm swing.",
    )
    above(
        "sit_knee_hip_sync_error",
        "sit_stand_support_gate",
        "medium",
        "Synchronize hip descent, knee flexion, and ankle counter-rotation during sit/stand.",
    )
    below(
        "sit_com_support_margin_m",
        "sit_stand_support_gate",
        "high",
        "Keep projected CoM inside foot support while sitting or standing; slow the transition when margin is low.",
    )
    below(
        "stair_foot_clearance_m",
        "stair_clearance_gate",
        "high",
        "Lift swing foot higher on stairs and place the foot flat before shifting pelvis weight.",
    )
    above(
        "factory_pick_hand_target_error_m",
        "factory_pick_place_gate",
        "medium",
        "Separate reach, grasp, lift, carry, place, and release phases; slow near fixture targets.",
    )
    below(
        "factory_pick_clearance_m",
        "factory_pick_place_gate",
        "medium",
        "Increase clearance around fixtures and bins before optimizing cycle time.",
    )
    above(
        "jerk_norm",
        "whole_body_smoothness_gate",
        "medium",
        "Limit frame-to-frame acceleration changes; blend task IK corrections over several frames.",
    )
    above(
        "collision_rate",
        "l20_task_safety_gate",
        "high",
        "Block L20 promotion until collisions are rare in all task families, not just walking.",
    )

    task_scores = metrics.get("task_scores") or {}
    if isinstance(task_scores, dict):
        for task_name, raw_score in task_scores.items():
            value = _finite_number(raw_score)
            if value is not None and value < limits["task_score_min"]:
                violations.append(
                    {
                        "rule_id": "l20_all_task_floor_gate",
                        "severity": "high" if value < 65 else "medium",
                        "metric": f"task_scores.{task_name}",
                        "value": value,
                        "limit": limits["task_score_min"],
                    }
                )
                corrections.append(
                    "Do not promote to L20 until every task family clears the minimum naturalness floor."
                )

    score = 100
    for item in violations:
        if item["severity"] == "high":
            score -= 18
        elif item["severity"] == "medium":
            score -= 9
        else:
            score -= 4
    score = max(0, score)

    high_count = sum(1 for v in violations if v["severity"] == "high")
    if score >= 86 and high_count == 0:
        verdict = "L20_CANDIDATE"
    elif score >= 72 and high_count <= 1:
        verdict = "L15_REVIEW"
    elif score >= 58:
        verdict = "L12_TRAIN"
    else:
        verdict = "HOLD"

    result: dict[str, Any] = {
        "score": score,
        "verdict": verdict,
        "violations": violations,
        "corrections": list(dict.fromkeys(corrections)),
        "rules_loaded": load_algorithm_rules(),
        "thresholds": limits,
    }

    therblig_keys = (
        "therblig_label_coverage_pct",
        "effective_therblig_ratio",
        "non_effective_therblig_share",
        "nva_time_ratio",
        "ecrs_improvement_pct",
        "most_sequence_valid",
        "most_index_error_pct",
        "most_cycle_efficiency_pct",
        "workstudy_export_ready",
        "parallel_therblig_rollout_count",
        "therblig_task_scores",
    )
    if any(key in metrics for key in therblig_keys):
        ie = evaluate_therblig_most_metrics(metrics)
        result["therblig_most"] = ie
        result["ie_verdict"] = ie["verdict"]
        if ie["verdict"].startswith("L3") or ie["verdict"].startswith("L4"):
            result["combined_verdict"] = ie["verdict"]
        else:
            result["combined_verdict"] = verdict

    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Robotics-informed gait QA for generated 3D motion.")
    parser.add_argument("--metrics-json", help="Path to measured gait metrics JSON.")
    parser.add_argument("--robot-learning-json", help="Path to embodied robot-learning readiness metrics JSON.")
    parser.add_argument("--task-motion-json", help="Path to L20 natural task motion metrics JSON.")
    parser.add_argument("--therblig-most-json", help="Path to L31-L40 therblig/MOST metrics JSON.")
    parser.add_argument("--print-rules", action="store_true", help="Print DB-backed algorithm rules.")
    args = parser.parse_args()

    if args.print_rules:
        print(json.dumps(load_algorithm_rules(), ensure_ascii=False, indent=2))
        return 0
    if args.robot_learning_json:
        metrics = json.loads(Path(args.robot_learning_json).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_robot_learning_metrics(metrics), ensure_ascii=False, indent=2))
        return 0
    if args.task_motion_json:
        metrics = json.loads(Path(args.task_motion_json).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_task_motion_metrics(metrics), ensure_ascii=False, indent=2))
        return 0
    if args.therblig_most_json:
        metrics = json.loads(Path(args.therblig_most_json).read_text(encoding="utf-8"))
        print(json.dumps(evaluate_therblig_most_metrics(metrics), ensure_ascii=False, indent=2))
        return 0
    if not args.metrics_json:
        parser.error("--metrics-json, --robot-learning-json, --task-motion-json, or --therblig-most-json is required unless --print-rules is used")
    metrics = json.loads(Path(args.metrics_json).read_text(encoding="utf-8"))
    print(json.dumps(evaluate_gait_metrics(metrics), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
