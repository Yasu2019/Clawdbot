import cv2

from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.pipeline import InspectionPipeline


def test_pipeline_normal_and_defect():
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    pipeline = InspectionPipeline(config, db, registry)
    normal_path = config.paths.root / "data/demo/upload_samples/normal_0000.png"
    bad_path = next((config.paths.root / "data/demo/upload_samples").glob("short_shot_*.png"))
    normal = pipeline.inspect_image(cv2.imread(str(normal_path)), normal_path.name, "demo_press_part")
    bad = pipeline.inspect_image(cv2.imread(str(bad_path)), bad_path.name, "demo_press_part")
    assert normal.decision == "OK"
    assert bad.decision in {"NG", "REVIEW"}
    assert bad.anomaly_score > normal.anomaly_score
