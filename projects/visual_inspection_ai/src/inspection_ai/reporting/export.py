from __future__ import annotations

import csv
import json
from pathlib import Path

from inspection_ai.db import Database
from inspection_ai.utils import compact_timestamp


def export_reviews_csv(db: Database, output_dir: str | Path, status: str | None = None) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"reviews_{compact_timestamp()}.csv"
    sql = """
    SELECT r.id AS review_id, r.status, r.ai_decision, r.ai_reason, r.user_decision,
           r.defect_mode, r.comment, r.reviewer, r.use_for_training, r.created_at,
           r.reviewed_at, i.id AS inspection_id, i.product_id, i.anomaly_score,
           i.original_path, i.annotated_path, i.model_version, i.measurements_json
    FROM reviews r JOIN inspections i ON i.id=r.inspection_id
    """
    params = ()
    if status:
        sql += " WHERE r.status=?"
        params = (status,)
    sql += " ORDER BY r.created_at DESC"
    rows = db.query_all(sql, params)
    fields = list(rows[0].keys()) if rows else ["review_id", "status"]
    with path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    return path


def export_inspection_summary(db: Database, output_dir: str | Path) -> Path:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    path = output / f"inspection_summary_{compact_timestamp()}.json"
    rows = db.query_all(
        "SELECT product_id, decision, COUNT(*) AS count, AVG(anomaly_score) AS avg_score FROM inspections GROUP BY product_id, decision"
    )
    path.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
