from __future__ import annotations

import uuid
from typing import Any

from inspection_ai.db import Database
from inspection_ai.schemas import ReviewLabelRequest
from inspection_ai.utils import utc_now_iso


class ReviewService:
    def __init__(self, db: Database):
        self.db = db

    def enqueue(self, inspection_id: str, ai_decision: str, reason: str) -> str:
        review_id = str(uuid.uuid4())
        self.db.execute(
            "INSERT OR IGNORE INTO reviews(id, inspection_id, status, ai_decision, ai_reason, created_at) VALUES(?,?,?,?,?,?)",
            (review_id, inspection_id, "PENDING", ai_decision, reason, utc_now_iso()),
        )
        self.db.audit("ENQUEUE_REVIEW", "inspection", inspection_id, {"ai_decision": ai_decision, "reason": reason})
        row = self.db.query_one("SELECT id FROM reviews WHERE inspection_id=?", (inspection_id,))
        return str(row["id"])

    def list(self, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        sql = """
        SELECT r.*, i.product_id, i.anomaly_score, i.original_path, i.annotated_path,
               i.measurements_json, i.regions_json, i.model_version, i.created_at AS inspected_at
        FROM reviews r JOIN inspections i ON i.id=r.inspection_id
        """
        params: tuple[Any, ...]
        if status:
            sql += " WHERE r.status=? ORDER BY r.created_at DESC LIMIT ?"
            params = (status, limit)
        else:
            sql += " ORDER BY r.created_at DESC LIMIT ?"
            params = (limit,)
        return self.db.query_all(sql, params)

    def label(self, review_id: str, request: ReviewLabelRequest) -> None:
        row = self.db.query_one("SELECT * FROM reviews WHERE id=?", (review_id,))
        if not row:
            raise KeyError("REVIEW項目がありません")
        self.db.execute(
            """UPDATE reviews SET status='REVIEWED', user_decision=?, defect_mode=?, comment=?, reviewer=?,
               use_for_training=?, reviewed_at=? WHERE id=?""",
            (
                request.decision, request.defect_mode, request.comment, request.reviewer,
                1 if request.use_for_training else 0, utc_now_iso(), review_id,
            ),
        )
        self.db.audit("LABEL_REVIEW", "review", review_id, request.model_dump(), request.reviewer)

    def training_candidates(self, product_id: str, decision: str | None = None) -> list[dict[str, Any]]:
        sql = """
        SELECT r.*, i.product_id, i.original_path, i.created_at AS inspected_at
        FROM reviews r JOIN inspections i ON i.id=r.inspection_id
        WHERE r.status='REVIEWED' AND r.use_for_training=1 AND i.product_id=?
        """
        params: list[Any] = [product_id]
        if decision:
            sql += " AND r.user_decision=?"
            params.append(decision)
        sql += " ORDER BY r.reviewed_at"
        return self.db.query_all(sql, tuple(params))
