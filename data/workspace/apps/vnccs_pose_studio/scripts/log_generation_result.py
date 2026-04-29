import csv
import json
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = ROOT / "logs" / "vnccs_generation_log.csv"
LOG.parent.mkdir(parents=True, exist_ok=True)

FIELDS = [
    "timestamp", "condition_id", "image_path", "condition_json_path",
    "pose_match_score", "lighting_match_score", "identity_consistency",
    "defect_visibility", "usability_flag", "notes"
]

def append_log(condition_id, image_path, condition_json_path, notes=""):
    exists = LOG.exists()
    row = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "condition_id": condition_id,
        "image_path": str(image_path),
        "condition_json_path": str(condition_json_path),
        "pose_match_score": "",
        "lighting_match_score": "",
        "identity_consistency": "",
        "defect_visibility": "",
        "usability_flag": "pending",
        "notes": notes,
    }
    with LOG.open("a", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        if not exists:
            writer.writeheader()
        writer.writerow(row)
    return LOG

if __name__ == "__main__":
    p = append_log("VNCCS_DOE_0001", "samples/example.png", "samples/example.json", "manual test")
    print(f"log appended: {p}")
