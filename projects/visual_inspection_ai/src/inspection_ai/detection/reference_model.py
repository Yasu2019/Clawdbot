from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import cv2
import numpy as np

from inspection_ai.detection.alignment import align_translation
from inspection_ai.schemas import DetectionResult, Region
from inspection_ai.utils import compact_timestamp


@dataclass
class ReferenceModelData:
    mean: np.ndarray
    std: np.ndarray
    image_height: int
    image_width: int
    version: str


class ReferenceModelTrainer:
    """良品群の画素平均・標準偏差を保存する軽量基準モデル。"""

    def train(
        self,
        image_paths: Iterable[str | Path],
        output: str | Path,
        size_hw: tuple[int, int],
        roi: list[int] | None = None,
    ) -> Path:
        arrays: list[np.ndarray] = []
        h, w = size_hw
        for p in image_paths:
            img = cv2.imread(str(p), cv2.IMREAD_GRAYSCALE)
            if img is None:
                continue
            if roi:
                x1, y1, x2, y2 = map(int, roi)
                img = img[y1:y2, x1:x2]
                if img.size == 0:
                    continue
            img = cv2.resize(img, (w, h), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
            arrays.append(img)
        if len(arrays) < 3:
            raise ValueError("基準モデル学習には3枚以上の良品画像が必要です")
        stack = np.stack(arrays, axis=0)
        mean = np.median(stack, axis=0).astype(np.float32)
        # 外れ値に比較的強いMADを標準偏差相当に変換
        mad = np.median(np.abs(stack - mean[None, ...]), axis=0)
        std = np.maximum(mad * 1.4826, 0.018).astype(np.float32)
        out = Path(output)
        out.parent.mkdir(parents=True, exist_ok=True)
        version = f"ref-{compact_timestamp()}"
        np.savez_compressed(out, mean=mean, std=std, image_height=h, image_width=w, version=version)
        return out


class ReferenceDifferenceDetector:
    def __init__(self, model_path: str | Path, recipe: dict):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(f"モデルがありません: {self.model_path}")
        data = np.load(self.model_path, allow_pickle=False)
        self.mean = data["mean"].astype(np.float32)
        self.std = data["std"].astype(np.float32)
        self.height = int(data["image_height"])
        self.width = int(data["image_width"])
        self.version = str(data["version"])
        self.cfg = recipe.get("model", {})

    def predict(self, image_bgr: np.ndarray, offset: tuple[int, int] = (0, 0)) -> tuple[DetectionResult, np.ndarray]:
        gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
        resized = cv2.resize(gray, (self.width, self.height), interpolation=cv2.INTER_AREA).astype(np.float32) / 255.0
        # 位置ズレ耐性: recipe model.alignment="ecc" で基準meanへ並進アライメント
        align_dx = align_dy = 0.0
        align_ok = None
        if str(self.cfg.get("alignment", "none")).lower() == "ecc":
            resized, align_dx, align_dy, align_ok = align_translation(
                resized, self.mean,
                max_shift_px=float(self.cfg.get("alignment_max_shift_px", 24.0)))
        z = np.abs(resized - self.mean) / self.std
        z = cv2.GaussianBlur(z, (3, 3), 0)
        threshold = float(self.cfg.get("pixel_z_threshold", 4.0))
        mask = (z >= threshold).astype(np.uint8) * 255
        k = max(1, int(self.cfg.get("morphology_kernel", 3)))
        kernel = np.ones((k, k), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

        min_area = int(self.cfg.get("min_region_area_px", 18))
        max_regions = int(self.cfg.get("max_regions", 20))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        regions: list[Region] = []
        sx = image_bgr.shape[1] / self.width
        sy = image_bgr.shape[0] / self.height
        ox, oy = offset
        for c in sorted(contours, key=cv2.contourArea, reverse=True):
            area = int(cv2.contourArea(c))
            if area < min_area:
                continue
            x, y, w, h = cv2.boundingRect(c)
            region_z = z[y:y+h, x:x+w]
            regions.append(Region(
                x=int(x * sx) + ox,
                y=int(y * sy) + oy,
                width=max(1, int(w * sx)),
                height=max(1, int(h * sy)),
                area=max(1, int(area * sx * sy)),
                score=float(np.clip(region_z.mean() / max(threshold, 1e-6), 0, 9)),
                label="surface_anomaly",
            ))
            if len(regions) >= max_regions:
                break

        abnormal_fraction = float((mask > 0).mean())
        peak_component = float(np.percentile(z, 99.5) / max(threshold, 1e-6))
        # 面積を中心に、局所ピークを弱く加味。0～1に抑制。
        score = float(np.clip(abnormal_fraction * 6.0 + min(peak_component, 2.0) * 0.01, 0.0, 1.0))
        heat = np.clip(z / max(threshold * 2, 1e-6), 0, 1)
        heat_u8 = (heat * 255).astype(np.uint8)
        heat_color = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
        heat_color = cv2.resize(heat_color, (image_bgr.shape[1], image_bgr.shape[0]))
        return DetectionResult(
            anomaly_score=score,
            regions=regions,
            model_version=self.version,
            diagnostics={
                "abnormal_fraction": abnormal_fraction,
                "peak_component": peak_component,
                "pixel_threshold": threshold,
                "align_dx": align_dx,
                "align_dy": align_dy,
                "align_ok": align_ok,
            },
        ), heat_color
