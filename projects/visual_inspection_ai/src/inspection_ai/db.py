from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

from .utils import utc_now_iso

_SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS inspections (
    id TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    anomaly_score REAL NOT NULL,
    reasons_json TEXT NOT NULL,
    quality_json TEXT NOT NULL,
    measurements_json TEXT NOT NULL,
    regions_json TEXT NOT NULL,
    original_path TEXT NOT NULL,
    annotated_path TEXT NOT NULL,
    model_version TEXT NOT NULL,
    elapsed_json TEXT NOT NULL,
    lot TEXT NOT NULL DEFAULT '',
    equipment TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    inspection_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL DEFAULT 'PENDING',
    ai_decision TEXT NOT NULL,
    ai_reason TEXT NOT NULL,
    user_decision TEXT,
    defect_mode TEXT NOT NULL DEFAULT '',
    comment TEXT NOT NULL DEFAULT '',
    reviewer TEXT NOT NULL DEFAULT '',
    use_for_training INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    reviewed_at TEXT,
    FOREIGN KEY(inspection_id) REFERENCES inspections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS models (
    version TEXT PRIMARY KEY,
    product_id TEXT NOT NULL,
    kind TEXT NOT NULL,
    path TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    stage TEXT NOT NULL,
    metrics_json TEXT NOT NULL DEFAULT '{}',
    parent_version TEXT,
    created_at TEXT NOT NULL,
    promoted_at TEXT,
    promoted_by TEXT,
    note TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS audit_log (
    id TEXT PRIMARY KEY,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    details_json TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_inspections_product_date ON inspections(product_id, created_at);
CREATE INDEX IF NOT EXISTS idx_reviews_status ON reviews(status, created_at);
CREATE INDEX IF NOT EXISTS idx_models_product_stage ON models(product_id, stage);
"""


class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._write_lock = threading.RLock()
        self.initialize()

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(_SCHEMA)

    def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        with self._write_lock, self.connect() as conn:
            conn.execute(sql, params)

    def query_all(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        with self.connect() as conn:
            return [dict(r) for r in conn.execute(sql, params).fetchall()]

    def query_one(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        rows = self.query_all(sql, params)
        return rows[0] if rows else None

    def audit(self, action: str, entity_type: str, entity_id: str, details: dict[str, Any], actor: str = "system") -> None:
        self.execute(
            "INSERT INTO audit_log VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(uuid.uuid4()), action, entity_type, entity_id, json.dumps(details, ensure_ascii=False), actor, utc_now_iso()),
        )
