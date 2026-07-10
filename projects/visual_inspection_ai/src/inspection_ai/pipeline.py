from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import cv2
import numpy as np

from inspection_ai.annotation import annotate
from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.decision.ensemble import decide
from inspection_ai.detection.fallback import FallbackEdgeDetector
from inspection_ai.detection.reference_model import ReferenceDifferenceDetector
from inspection_ai.measurement.geometry import measure_part
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.preprocessing.image_ops import apply_roi, ensure_bgr
from inspection_ai.preprocessing.quality import evaluate_quality
from inspection_ai.review.service import ReviewService
from inspection_ai.schemas import InspectionResult
from inspection_ai.utils import safe_filename, utc_now_iso


class InspectionPipeline:
    def __init__(self, config: AppConfig, db: Database, registry: ModelRegistry):
        self.config = config
        self.db = db
        self.registry = registry
        self.review = ReviewService(db)
        self._detectors: dict[tuple[str, str], object] = {}

    def _detector(self, product_id: str, recipe: dict):
        champion = self.registry.get_champion(product_id)
        if champion:
            key = (product_id, champion["version"])
            if key not in self._detectors:
                path = self.config.paths.root / champion["path"]
                if champion["kind"] == "reference_difference":
                    self._detectors[key] = ReferenceDifferenceDetector(path, recipe)
                else:
                    raise NotImplementedError(f"未実装モデル種別: {champion['kind']}")
            return self._detectors[key]
        return FallbackEdgeDetector(recipe)

    def inspect_bytes(self, content: bytes, filename: str, product_id: str, lot: str = "", equipment: str = "") -> InspectionResult:
        t0 = time.perf_counter()
        array = np.frombuffer(content, np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_UNCHANGED)
        image = ensure_bgr(image)
        decode_ms = (time.perf_counter() - t0) * 1000
        return self.inspect_image(image, filename, product_id, lot, equipment, decode_ms)

    def inspect_image(
        self,
        image: np.ndarray,
        filename: str,
        product_id: str,
        lot: str = "",
        equipment: str = "",
        decode_ms: float = 0.0,
    ) -> InspectionResult:
        total_start = time.perf_counter()
        recipe = self.config.recipe(product_id)
        inspection_id = str(uuid.uuid4())
        created_at = utc_now_iso()
        date_part = created_at[:10]
        run_dir = self.config.paths.runtime / date_part / inspection_id
        run_dir.mkdir(parents=True, exist_ok=True)
        original_path = run_dir / f"original_{safe_filename(filename)}"
        if not cv2.imwrite(str(original_path), image):
            raise RuntimeError("元画像を保存できません")

        t = time.perf_counter()
        quality = evaluate_quality(image, recipe)
        quality_ms = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        roi, offset = apply_roi(image, recipe.get("image", {}).get("roi"))
        preprocess_ms = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        detector = self._detector(product_id, recipe)
        detection, heatmap = detector.predict(roi, offset=offset)
        inference_ms = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        measurements, overlays = measure_part(roi, recipe, offset=offset)
        measurement_ms = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        decision, reasons = decide(detection, quality, measurements, recipe)
        decision_ms = (time.perf_counter() - t) * 1000

        t = time.perf_counter()
        annotated = annotate(image, decision, detection.anomaly_score, detection.regions, overlays, measurements)
        annotated_path = run_dir / "annotated.png"
        heatmap_path = run_dir / "heatmap.png"
        cv2.imwrite(str(annotated_path), annotated)
        cv2.imwrite(str(heatmap_path), heatmap)
        save_ms = (time.perf_counter() - t) * 1000

        elapsed = {
            "decode": round(decode_ms, 3),
            "quality": round(quality_ms, 3),
            "preprocess": round(preprocess_ms, 3),
            "inference": round(inference_ms, 3),
            "measurement": round(measurement_ms, 3),
            "decision": round(decision_ms, 3),
            "save": round(save_ms, 3),
            "total": round((time.perf_counter() - total_start) * 1000, 3),
        }
        rel_original = original_path.relative_to(self.config.paths.root).as_posix()
        rel_annotated = annotated_path.relative_to(self.config.paths.root).as_posix()
        self.db.execute(
            """INSERT INTO inspections(id, product_id, decision, anomaly_score, reasons_json, quality_json,
               measurements_json, regions_json, original_path, annotated_path, model_version, elapsed_json,
               lot, equipment, created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                inspection_id, product_id, decision, detection.anomaly_score,
                json.dumps(reasons, ensure_ascii=False), quality.model_dump_json(),
                json.dumps([m.model_dump() for m in measurements], ensure_ascii=False),
                json.dumps([r.model_dump() for r in detection.regions], ensure_ascii=False),
                rel_original, rel_annotated, detection.model_version,
                json.dumps(elapsed, ensure_ascii=False), lot, equipment, created_at,
            ),
        )
        self.db.audit("INSPECT", "inspection", inspection_id, {"decision": decision, "score": detection.anomaly_score})
        if decision in ("REVIEW", "NG"):
            self.review.enqueue(inspection_id, decision, " / ".join(reasons))

        return InspectionResult(
            inspection_id=inspection_id,
            product_id=product_id,
            decision=decision,
            reasons=reasons,
            anomaly_score=detection.anomaly_score,
            quality=quality,
            measurements=measurements,
            regions=detection.regions,
            original_image_url="/" + rel_original,
            annotated_image_url="/" + rel_annotated,
            model_version=detection.model_version,
            elapsed_ms=elapsed,
            created_at=created_at,
        )
