from pathlib import Path
import json
import pandas as pd

audit_dir = Path("/data/audit")
rows = []
for p in audit_dir.glob("*.json"):
    data = json.loads(p.read_text(encoding="utf-8"))
    rows.append({
        "timestamp": data.get("timestamp"),
        "inspection_id": data.get("inspection_id"),
        "part_no": data.get("part_no"),
        "lot_no": data.get("lot_no"),
        "machine_id": data.get("machine_id"),
        "judgement": data.get("judgement"),
        "defect_candidates": ",".join(data.get("defect_candidates", [])),
        "confidence": data.get("confidence"),
        "human_review_required": data.get("human_review_required"),
        "shot_count": data.get("shot_count"),
        "spm": data.get("spm"),
        "chokotei_count": data.get("chokotei_count"),
    })

df = pd.DataFrame(rows)
out = Path("/data/results/audit_export.csv")
out.parent.mkdir(parents=True, exist_ok=True)
df.to_csv(out, index=False, encoding="utf-8-sig")
print(out)
