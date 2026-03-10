"""
Pose Estimator — MediaPipe PoseLandmarker (Tasks API, MediaPipe ≥ 0.10.14)

The legacy mp.solutions.pose was removed in MediaPipe 0.10.14+.
This module uses the new Tasks API (mp.tasks.vision.PoseLandmarker).

Model: pose_landmarker_lite.task  (~7 MB, downloaded at Docker build time)
Output: per-frame list of 33 landmark dicts {x, y, z, visibility}
        — same schema as the old API, so all downstream code is unchanged.
"""
import cv2
import numpy as np
import mediapipe as mp
from mediapipe.tasks import python as mp_python
from mediapipe.tasks.python import vision as mp_vision

# Path where Dockerfile downloads the model
_MODEL_PATH = "/app/pose_landmarker_lite.task"


class PoseEstimator:
    def __init__(self):
        base_options = mp_python.BaseOptions(model_asset_path=_MODEL_PATH)
        options = mp_vision.PoseLandmarkerOptions(
            base_options=base_options,
            running_mode=mp_vision.RunningMode.VIDEO,
            num_poses=1,
            min_pose_detection_confidence=0.5,
            min_pose_presence_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self._landmarker = mp_vision.PoseLandmarker.create_from_options(options)

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

            rgb      = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
            ts_ms    = int(frame_idx * 1000 / fps)  # monotonically increasing timestamp

            result    = self._landmarker.detect_for_video(mp_image, ts_ms)
            landmarks = []

            if result.pose_landmarks:
                for lm in result.pose_landmarks[0]:
                    landmarks.append({
                        "x":          round(lm.x, 4),
                        "y":          round(lm.y, 4),
                        "z":          round(lm.z, 4),
                        "visibility": round(lm.visibility if lm.visibility is not None else 0.0, 3),
                    })

            frames.append({
                "frame":    frame_idx,
                "time_sec": round(frame_idx / fps, 3),
                "fps":      fps,
                "landmarks": landmarks,
            })
            frame_idx += 1

        cap.release()
        self._landmarker.close()
        return frames

    @staticmethod
    def compute_angle(a: dict, b: dict, c: dict) -> float:
        """Compute angle at point b given 3 landmark dicts."""
        ba = np.array([a["x"] - b["x"], a["y"] - b["y"]])
        bc = np.array([c["x"] - b["x"], c["y"] - b["y"]])
        cos_angle = np.dot(ba, bc) / (np.linalg.norm(ba) * np.linalg.norm(bc) + 1e-8)
        return float(np.degrees(np.arccos(np.clip(cos_angle, -1.0, 1.0))))
