from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from inspection_ai.utils import utc_now_iso


@dataclass
class ScaleCalibration:
    calibration_id: str
    mm_per_pixel: float
    known_length_mm: float
    measured_length_px: float
    image_width: int
    image_height: int
    created_at: str
    note: str = ""

    def save(self, path: str | Path) -> Path:
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(asdict(self), ensure_ascii=False, indent=2), encoding="utf-8")
        return output

    @classmethod
    def load(cls, path: str | Path) -> "ScaleCalibration":
        return cls(**json.loads(Path(path).read_text(encoding="utf-8")))


def estimate_scale(
    image: np.ndarray,
    point_a: tuple[float, float],
    point_b: tuple[float, float],
    known_length_mm: float,
    calibration_id: str,
    note: str = "",
) -> ScaleCalibration:
    if known_length_mm <= 0:
        raise ValueError("known_length_mmは正である必要があります")
    distance_px = float(np.linalg.norm(np.asarray(point_b, dtype=float) - np.asarray(point_a, dtype=float)))
    if distance_px <= 0:
        raise ValueError("2点の画素距離が0です")
    h, w = image.shape[:2]
    return ScaleCalibration(
        calibration_id=calibration_id,
        mm_per_pixel=known_length_mm / distance_px,
        known_length_mm=known_length_mm,
        measured_length_px=distance_px,
        image_width=w,
        image_height=h,
        created_at=utc_now_iso(),
        note=note,
    )


def calibrate_chessboard(
    image_paths: Iterable[str | Path],
    pattern_size: tuple[int, int],
    square_size_mm: float,
) -> dict:
    """OpenCVチェスボードによる内部パラメータ・歪み校正。

    pattern_sizeは内側コーナー数 (columns, rows) です。
    """
    if square_size_mm <= 0:
        raise ValueError("square_size_mmは正である必要があります")
    cols, rows = pattern_size
    object_points_template = np.zeros((rows * cols, 3), np.float32)
    object_points_template[:, :2] = np.mgrid[0:cols, 0:rows].T.reshape(-1, 2) * square_size_mm
    object_points = []
    image_points = []
    image_size = None
    used = []
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 40, 0.001)
    for path in image_paths:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
        if image is None:
            continue
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        found, corners = cv2.findChessboardCorners(gray, pattern_size)
        if not found:
            continue
        refined = cv2.cornerSubPix(gray, corners, (11, 11), (-1, -1), criteria)
        object_points.append(object_points_template.copy())
        image_points.append(refined)
        image_size = gray.shape[::-1]
        used.append(str(path))
    if len(used) < 5 or image_size is None:
        raise ValueError(f"校正に使用できる画像が不足しています: {len(used)}枚。5枚以上を推奨します")
    rms, camera_matrix, distortion, rotation_vectors, translation_vectors = cv2.calibrateCamera(
        object_points, image_points, image_size, None, None
    )
    return {
        "rms_reprojection_error": float(rms),
        "camera_matrix": camera_matrix.tolist(),
        "distortion_coefficients": distortion.tolist(),
        "image_size": list(image_size),
        "pattern_size": list(pattern_size),
        "square_size_mm": square_size_mm,
        "used_images": used,
        "created_at": utc_now_iso(),
    }


def undistort(image: np.ndarray, calibration: dict) -> np.ndarray:
    matrix = np.asarray(calibration["camera_matrix"], dtype=np.float64)
    distortion = np.asarray(calibration["distortion_coefficients"], dtype=np.float64)
    return cv2.undistort(image, matrix, distortion)
