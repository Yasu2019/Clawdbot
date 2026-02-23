"""
Pose Estimator — MediaPipe Pose skeleton extraction
Processes video frame-by-frame and outputs per-frame landmark data.
"""
import cv2
import mediapipe as mp
import numpy as np


class PoseEstimator:
    def __init__(self):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )

    def process(self, video_path: str) -> list[dict]:
        """Process video and return per-frame pose landmarks."""
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        frames = []
        frame_idx = 0

        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = self.pose.process(rgb)

            landmarks = []
            if result.pose_landmarks:
                for lm in result.pose_landmarks.landmark:
                    landmarks.append({
                        "x": round(lm.x, 4),
                        "y": round(lm.y, 4),
                        "z": round(lm.z, 4),
                        "visibility": round(lm.visibility, 3),
                    })

            frames.append({
                "frame": frame_idx,
                "time_sec": round(frame_idx / fps, 3),
                "fps": fps,
                "landmarks": landmarks,
            })
            frame_idx += 1

        cap.release()
        return frames

    @staticmethod
    def compute_angle(a, b, c) -> float:
        """Compute angle at point b given 3 landmark dicts."""
        ba = np.array([a["x"] - b["x"], a["y"] - b["y"]])
        bc = np.array([c["x"] - b["x"], c["y"] - b["y"]])
        cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
        return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))
