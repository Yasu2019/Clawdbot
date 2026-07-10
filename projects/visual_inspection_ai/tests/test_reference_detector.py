import cv2

from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.detection.reference_model import ReferenceDifferenceDetector
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.preprocessing.image_ops import apply_roi


def score(path):
    config = AppConfig()
    db = Database(config.paths.database)
    registry = ModelRegistry(db, config.paths.model_registry, config.paths.root)
    champion = registry.get_champion("demo_press_part")
    detector = ReferenceDifferenceDetector(config.paths.root / champion["path"], config.recipe("demo_press_part"))
    image = cv2.imread(str(path))
    roi, offset = apply_roi(image, config.recipe("demo_press_part")["image"]["roi"])
    return detector.predict(roi, offset)[0].anomaly_score


def test_defect_scores_higher_than_good():
    config = AppConfig()
    good = config.paths.root / "data/demo/upload_samples/normal_0000.png"
    defect = next((config.paths.root / "data/demo/upload_samples").glob("short_shot_*.png"))
    assert score(defect) > score(good) * 20
