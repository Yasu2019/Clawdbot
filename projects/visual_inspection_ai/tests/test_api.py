from fastapi.testclient import TestClient

from inspection_ai.api.main import create_app
from inspection_ai.config import AppConfig


def test_health_and_inspect():
    app = create_app()
    client = TestClient(app)
    health = client.get("/api/health")
    assert health.status_code == 200
    config = AppConfig()
    image_path = config.paths.root / "data/demo/upload_samples/normal_0000.png"
    with image_path.open("rb") as f:
        response = client.post(
            "/api/inspect",
            files={"file": (image_path.name, f, "image/png")},
            data={"product_id": "demo_press_part"},
        )
    assert response.status_code == 200, response.text
    assert response.json()["decision"] in {"OK", "REVIEW", "NG"}
