import json
from pathlib import Path

def test_manifest_exists_and_has_required_fields():
    root = Path(__file__).resolve().parents[1]
    manifest = json.loads((root / "MANIFEST.json").read_text(encoding="utf-8"))
    assert manifest["package_name"]
    assert manifest["version"]
    assert manifest["safety"]["requires_human_approval_before_publish"] is True
    assert "auto_publish_without_approval" in manifest["safety"]["prohibited_actions"]
