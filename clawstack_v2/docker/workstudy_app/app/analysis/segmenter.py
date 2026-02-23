"""
Auto Segmenter — Velocity-based motion segmentation
Splits pose sequence into segments based on hand/body velocity changes.
"""
import numpy as np


class AutoSegmenter:
    def __init__(self, velocity_threshold: float = 0.02, min_segment_frames: int = 5):
        self.velocity_threshold = velocity_threshold
        self.min_segment_frames = min_segment_frames

    def segment(self, pose_data: list[dict]) -> list[dict]:
        """Segment pose data by detecting velocity change-points in hand motion."""
        if not pose_data or len(pose_data) < 3:
            return [{"start_frame": 0, "end_frame": len(pose_data) - 1,
                      "start_sec": 0, "end_sec": 0}]

        fps = pose_data[0].get("fps", 30.0)
        # Track right wrist (landmark 16) velocity
        wrist_positions = []
        for frame in pose_data:
            lms = frame.get("landmarks", [])
            if len(lms) > 16:
                wrist_positions.append((lms[16]["x"], lms[16]["y"]))
            else:
                wrist_positions.append((0.0, 0.0))

        velocities = [0.0]
        for i in range(1, len(wrist_positions)):
            dx = wrist_positions[i][0] - wrist_positions[i - 1][0]
            dy = wrist_positions[i][1] - wrist_positions[i - 1][1]
            velocities.append(np.sqrt(dx ** 2 + dy ** 2))

        # Smooth velocities
        kernel_size = 5
        smoothed = np.convolve(velocities, np.ones(kernel_size) / kernel_size, mode="same")

        # Detect change-points (high→low or low→high transitions)
        boundaries = [0]
        prev_state = "moving" if smoothed[0] > self.velocity_threshold else "still"
        for i in range(1, len(smoothed)):
            curr_state = "moving" if smoothed[i] > self.velocity_threshold else "still"
            if curr_state != prev_state:
                if (i - boundaries[-1]) >= self.min_segment_frames:
                    boundaries.append(i)
            prev_state = curr_state

        if boundaries[-1] != len(pose_data) - 1:
            boundaries.append(len(pose_data) - 1)

        segments = []
        for i in range(len(boundaries) - 1):
            segments.append({
                "start_frame": boundaries[i],
                "end_frame": boundaries[i + 1],
                "start_sec": round(boundaries[i] / fps, 2),
                "end_sec": round(boundaries[i + 1] / fps, 2),
            })

        return segments
