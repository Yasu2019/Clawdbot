"""
Therbligs Labeler — Assigns Therbligs-compatible motion labels to segments.
Uses template expected_flow and heuristic rules to classify motions.
"""
import numpy as np


# Standard Therbligs symbol set
THERBLIGS = {
    "GET": "つかむ (Grasp)",
    "POSITION": "位置決め (Position)",
    "INSPECT": "検査 (Inspect)",
    "PUT": "置く (Release Load)",
    "RECORD": "記録 (Use)",
    "MOVE": "運ぶ (Transport Loaded)",
    "USE_TOOL": "道具使用 (Use)",
    "WAIT": "待ち (Unavoidable Delay)",
    "SEARCH": "探す (Search)",
    "HOLD": "保持 (Hold)",
    "REST": "休憩 (Rest)",
}


class TherbligLabeler:
    def __init__(self, template: dict):
        self.template = template
        self.expected_flow = template.get("expected_flow", [])

    def label(self, segments: list[dict], pose_data: list[dict]) -> list[dict]:
        """Assign Therbligs labels to each segment based on motion heuristics."""
        labeled = []
        flow_len = len(self.expected_flow)

        for idx, seg in enumerate(segments):
            start_f = seg["start_frame"]
            end_f = seg["end_frame"]
            duration = seg["end_sec"] - seg["start_sec"]

            # Heuristic: use expected flow cycle position
            if flow_len > 0:
                flow_idx = idx % flow_len
                base_label = self.expected_flow[flow_idx]
            else:
                base_label = self._classify_by_motion(pose_data, start_f, end_f)

            # Override with motion-specific heuristics
            avg_velocity = self._avg_hand_velocity(pose_data, start_f, end_f)
            if avg_velocity < 0.005 and duration > 1.0:
                base_label = "WAIT"
            elif avg_velocity > 0.08:
                base_label = "MOVE"

            label_desc = THERBLIGS.get(base_label, base_label)

            labeled.append({
                "segment_id": idx,
                "start_frame": start_f,
                "end_frame": end_f,
                "start_sec": seg["start_sec"],
                "end_sec": seg["end_sec"],
                "label": base_label,
                "label_jp": label_desc,
                "duration_sec": round(duration, 2),
                "avg_velocity": round(avg_velocity, 4),
                "is_nva": base_label in ("WAIT", "SEARCH", "HOLD"),
            })

        return labeled

    def _avg_hand_velocity(self, pose_data, start_f, end_f) -> float:
        """Compute average hand velocity over a segment."""
        positions = []
        for i in range(start_f, min(end_f + 1, len(pose_data))):
            lms = pose_data[i].get("landmarks", [])
            if len(lms) > 16:
                positions.append((lms[16]["x"], lms[16]["y"]))

        if len(positions) < 2:
            return 0.0

        velocities = []
        for i in range(1, len(positions)):
            dx = positions[i][0] - positions[i - 1][0]
            dy = positions[i][1] - positions[i - 1][1]
            velocities.append(np.sqrt(dx ** 2 + dy ** 2))

        return float(np.mean(velocities)) if velocities else 0.0

    @staticmethod
    def _classify_by_motion(pose_data, start_f, end_f) -> str:
        """Fallback classifier using body displacement."""
        if end_f - start_f < 3:
            return "WAIT"
        return "USE_TOOL"
