import json, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import cae_telegram_video_notify as notify

root = Path("artifacts/box_roundhole_v5/youtube_annotated_20260910")
results = []
for path in sorted(root.glob("*.mp4")):
    results.append({
        "file": path.name,
        "result": notify.notify_cae_video(
            path,
            "YouTube annotated contour interpretation | virtual screening only | measured calibration pending",
            gdrive_rel="C:/Users/yasu/Downloads/box_roundhole_v5_youtube_annotated_20260910/" + path.name,
        ),
    })
print(json.dumps(results, ensure_ascii=False))
