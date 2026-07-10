import cv2

from inspection_ai.config import AppConfig
from inspection_ai.measurement.geometry import measure_part


def test_demo_measurement_is_in_spec():
    config = AppConfig()
    image = cv2.imread(str(config.paths.root / "data/demo/upload_samples/normal_0000.png"))
    recipe = config.recipe("demo_press_part")
    roi = recipe["image"]["roi"]
    x1, y1, x2, y2 = roi
    items, overlays = measure_part(image[y1:y2, x1:x2], recipe, offset=(x1, y1))
    values = {item.name: item for item in items}
    assert values["width_mm"].passed is True
    assert values["height_mm"].passed is True
    assert values["hole_diameter_mm"].value_mm is not None
    assert overlays
