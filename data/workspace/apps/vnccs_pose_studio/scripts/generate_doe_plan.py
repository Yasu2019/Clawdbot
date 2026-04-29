from itertools import product
import csv
from pathlib import Path

out = Path(__file__).resolve().parents[1] / "doe" / "vnccs_doe_plan.csv"
out.parent.mkdir(parents=True, exist_ok=True)

factors = {
    "pose_arm_angle_deg": [30, 60, 90],
    "camera_distance": ["near", "middle", "far"],
    "key_light_position": ["left_front", "front", "right_front"],
    "key_light_strength": [0.6, 1.0, 1.4],
    "ambient_strength": [0.2, 0.5]
}

keys = list(factors.keys())
rows = []
for idx, values in enumerate(product(*[factors[k] for k in keys]), start=1):
    row = {"condition_id": f"VNCCS_DOE_{idx:04d}"}
    row.update(dict(zip(keys, values)))
    row["prompt_note"] = "Describe character, material, background, defect or target scene here."
    row["status"] = "planned"
    rows.append(row)

with out.open("w", newline="", encoding="utf-8-sig") as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(f"DOE plan written: {out}")
print(f"conditions: {len(rows)}")
