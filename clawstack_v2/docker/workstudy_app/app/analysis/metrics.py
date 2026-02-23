"""
Metrics Engine — Compute KPIs, waste patterns, and ergonomic risk.
"""
import numpy as np
from pose.estimator import PoseEstimator


class MetricsEngine:
    def __init__(self, template: dict):
        self.template = template
        self.ergo_thresholds = template.get("ergo_thresholds", {})
        self.waste_patterns = template.get("waste_patterns", [])
        self.focus_kpi = template.get("focus_kpi", [])

    def compute(self, pose_data: list[dict], segments: list[dict], labels: list[dict]) -> dict:
        """Compute all metrics for the analysis."""
        total_frames = len(pose_data)
        fps = pose_data[0].get("fps", 30.0) if pose_data else 30.0
        total_time = total_frames / fps

        kpi = {}

        # Cycle time
        kpi["cycle_time"] = round(total_time, 2)

        # Label-based ratios
        label_times = {}
        nva_time = 0.0
        for lbl in labels:
            dur = lbl["duration_sec"]
            label_times[lbl["label"]] = label_times.get(lbl["label"], 0) + dur
            if lbl["is_nva"]:
                nva_time += dur

        kpi["inspect_ratio"] = round(label_times.get("INSPECT", 0) / max(total_time, 0.01), 3)
        kpi["walking_ratio"] = round(label_times.get("MOVE", 0) / max(total_time, 0.01), 3)
        kpi["waiting_ratio"] = round(label_times.get("WAIT", 0) / max(total_time, 0.01), 3)
        kpi["nva_ratio"] = round(nva_time / max(total_time, 0.01), 3)

        # Hand travel (total displacement of right wrist)
        hand_travel = self._compute_hand_travel(pose_data)
        kpi["hand_travel"] = round(hand_travel, 3)

        # Count-based metrics
        kpi["orientation_changes"] = self._count_direction_changes(pose_data)
        kpi["recheck_loops"] = self._count_recheck_loops(labels)
        kpi["tilt_actions"] = self._count_tilt_actions(pose_data)
        kpi["tool_switch_count"] = self._count_label_switches(labels)
        kpi["regrasp_count"] = self._count_regrasp(labels)
        kpi["carry_count"] = sum(1 for l in labels if l["label"] == "MOVE")
        kpi["roundtrip_count"] = 0  # Needs zone data (v0.2)
        kpi["search_ratio"] = round(label_times.get("SEARCH", 0) / max(total_time, 0.01), 3)
        kpi["static_posture_ratio"] = round(label_times.get("HOLD", 0) / max(total_time, 0.01), 3)
        kpi["hold_ratio"] = kpi["static_posture_ratio"]
        kpi["overlap_ratio"] = 0.0  # Needs multi-worker (v0.2)

        # Ergonomic assessment
        ergo = self._compute_ergo(pose_data)
        kpi["trunk_risk_ratio"] = ergo.get("trunk_risk_ratio", 0)
        kpi["shoulder_risk_ratio"] = ergo.get("shoulder_risk_ratio", 0)

        # Evaluate waste patterns
        waste_fired = []
        for pattern in self.waste_patterns:
            trigger = pattern.get("trigger", {})
            metric_name = trigger.get("metric", "")
            op = trigger.get("op", ">")
            threshold = trigger.get("value", 0)
            actual = kpi.get(metric_name, 0)

            fired = False
            if op == ">" and actual > threshold:
                fired = True
            elif op == ">=" and actual >= threshold:
                fired = True

            if fired:
                waste_fired.append({
                    "id": pattern["id"],
                    "description": pattern["description"],
                    "suggestion": pattern["suggestion"],
                    "metric": metric_name,
                    "actual_value": actual,
                    "threshold": threshold,
                })

        return {
            "kpi": kpi,
            "ergo": ergo,
            "waste_fired": waste_fired,
            "label_distribution": label_times,
            "total_time_sec": total_time,
            "total_frames": total_frames,
        }

    def _compute_hand_travel(self, pose_data: list[dict]) -> float:
        total = 0.0
        prev = None
        for frame in pose_data:
            lms = frame.get("landmarks", [])
            if len(lms) > 16:
                curr = (lms[16]["x"], lms[16]["y"])
                if prev:
                    total += np.sqrt((curr[0]-prev[0])**2 + (curr[1]-prev[1])**2)
                prev = curr
        return total

    def _count_direction_changes(self, pose_data: list[dict]) -> int:
        changes = 0
        prev_dx = 0
        for i in range(1, len(pose_data)):
            lms_prev = pose_data[i-1].get("landmarks", [])
            lms_curr = pose_data[i].get("landmarks", [])
            if len(lms_prev) > 16 and len(lms_curr) > 16:
                dx = lms_curr[16]["x"] - lms_prev[16]["x"]
                if prev_dx * dx < 0:
                    changes += 1
                prev_dx = dx
        return changes

    def _count_recheck_loops(self, labels: list[dict]) -> int:
        loops = 0
        for i in range(2, len(labels)):
            if (labels[i]["label"] == "INSPECT" and
                labels[i-1]["label"] != "INSPECT" and
                labels[i-2]["label"] == "INSPECT"):
                loops += 1
        return loops

    def _count_tilt_actions(self, pose_data: list[dict]) -> int:
        tilts = 0
        for i in range(1, len(pose_data)):
            lms = pose_data[i].get("landmarks", [])
            if len(lms) > 16:
                wrist_y = lms[16]["y"]
                prev_lms = pose_data[i-1].get("landmarks", [])
                if len(prev_lms) > 16:
                    if abs(wrist_y - prev_lms[16]["y"]) > 0.03:
                        tilts += 1
        return tilts // 10  # Normalize

    def _count_label_switches(self, labels: list[dict]) -> int:
        switches = 0
        for i in range(1, len(labels)):
            if labels[i]["label"] != labels[i-1]["label"]:
                switches += 1
        return switches

    def _count_regrasp(self, labels: list[dict]) -> int:
        count = 0
        for i in range(2, len(labels)):
            if (labels[i]["label"] == "GET" and
                labels[i-1]["label"] == "PUT" and
                labels[i-2]["label"] == "GET"):
                count += 1
        return count

    def _compute_ergo(self, pose_data: list[dict]) -> dict:
        trunk_threshold = self.ergo_thresholds.get("trunk_deg_gt", 40)
        shoulder_threshold = self.ergo_thresholds.get("shoulder_deg_gt", 60)

        trunk_risk_frames = 0
        shoulder_risk_frames = 0
        valid_frames = 0

        for frame in pose_data:
            lms = frame.get("landmarks", [])
            if len(lms) < 25:
                continue
            valid_frames += 1

            # Trunk: angle at hip (11-23-25 approximation)
            trunk_angle = PoseEstimator.compute_angle(lms[11], lms[23], lms[25])
            if abs(180 - trunk_angle) > trunk_threshold:
                trunk_risk_frames += 1

            # Shoulder: angle at shoulder (13-11-23)
            shoulder_angle = PoseEstimator.compute_angle(lms[13], lms[11], lms[23])
            if shoulder_angle > shoulder_threshold:
                shoulder_risk_frames += 1

        total = max(valid_frames, 1)
        return {
            "trunk_risk_ratio": round(trunk_risk_frames / total, 3),
            "shoulder_risk_ratio": round(shoulder_risk_frames / total, 3),
            "trunk_threshold_deg": trunk_threshold,
            "shoulder_threshold_deg": shoulder_threshold,
        }
