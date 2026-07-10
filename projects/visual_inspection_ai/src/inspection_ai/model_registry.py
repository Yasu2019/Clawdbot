from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from .db import Database
from .utils import atomic_write_json, sha256_file, utc_now_iso


class ModelRegistry:
    def __init__(self, db: Database, registry_path: str | Path, root: str | Path):
        self.db = db
        self.registry_path = Path(registry_path)
        self.root = Path(root)
        for stage in ("champion", "challenger", "archived"):
            (self.root / "models" / stage).mkdir(parents=True, exist_ok=True)

    def register(
        self,
        product_id: str,
        kind: str,
        model_path: str | Path,
        stage: str = "CHALLENGER",
        metrics: dict[str, Any] | None = None,
        parent_version: str | None = None,
        note: str = "",
    ) -> str:
        src = Path(model_path)
        if not src.exists():
            raise FileNotFoundError(src)
        # NPZ内versionを優先。一般ファイルはstem。
        version = src.stem
        if src.suffix.lower() == ".npz":
            try:
                import numpy as np
                d = np.load(src, allow_pickle=False)
                version = str(d["version"])
            except Exception:
                pass
        stage_dir = self.root / "models" / stage.lower()
        stage_dir.mkdir(parents=True, exist_ok=True)
        dest = stage_dir / f"{product_id}__{version}{src.suffix}"
        if src.resolve() != dest.resolve():
            shutil.copy2(src, dest)
        rel = dest.relative_to(self.root).as_posix()
        self.db.execute(
            "INSERT OR REPLACE INTO models(version, product_id, kind, path, sha256, stage, metrics_json, parent_version, created_at, promoted_at, promoted_by, note) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                version, product_id, kind, rel, sha256_file(dest), stage.upper(),
                json.dumps(metrics or {}, ensure_ascii=False), parent_version, utc_now_iso(), None, None, note,
            ),
        )
        self.db.audit("REGISTER_MODEL", "model", version, {"product_id": product_id, "stage": stage, "path": rel})
        self.snapshot()
        return version

    def get_champion(self, product_id: str) -> dict[str, Any] | None:
        return self.db.query_one(
            "SELECT * FROM models WHERE product_id=? AND stage='CHAMPION' ORDER BY promoted_at DESC, created_at DESC LIMIT 1",
            (product_id,),
        )

    def list_models(self, product_id: str | None = None) -> list[dict[str, Any]]:
        if product_id:
            return self.db.query_all("SELECT * FROM models WHERE product_id=? ORDER BY created_at DESC", (product_id,))
        return self.db.query_all("SELECT * FROM models ORDER BY created_at DESC")

    def promote(self, version: str, approved_by: str, note: str = "") -> None:
        row = self.db.query_one("SELECT * FROM models WHERE version=?", (version,))
        if not row:
            raise KeyError(f"モデルがありません: {version}")
        product_id = row["product_id"]
        old = self.get_champion(product_id)
        if old and old["version"] != version:
            self.db.execute("UPDATE models SET stage='ARCHIVED' WHERE version=?", (old["version"],))
            self._move_file(old, "archived")
        self.db.execute(
            "UPDATE models SET stage='CHAMPION', promoted_at=?, promoted_by=?, note=? WHERE version=?",
            (utc_now_iso(), approved_by, note, version),
        )
        self._move_file(row, "champion")
        self.db.audit("PROMOTE_MODEL", "model", version, {"previous": old["version"] if old else None, "note": note}, approved_by)
        self.snapshot()

    def rollback(self, product_id: str, version: str, approved_by: str) -> None:
        row = self.db.query_one("SELECT * FROM models WHERE version=? AND product_id=?", (version, product_id))
        if not row:
            raise KeyError("指定モデルがありません")
        self.promote(version, approved_by, note="rollback")
        self.db.audit("ROLLBACK_MODEL", "model", version, {"product_id": product_id}, approved_by)

    def _move_file(self, row: dict[str, Any], target_stage: str) -> None:
        src = self.root / row["path"]
        if not src.exists():
            return
        dest = self.root / "models" / target_stage / src.name
        dest.parent.mkdir(parents=True, exist_ok=True)
        if src.resolve() != dest.resolve():
            shutil.move(str(src), str(dest))
        rel = dest.relative_to(self.root).as_posix()
        self.db.execute("UPDATE models SET path=?, sha256=? WHERE version=?", (rel, sha256_file(dest), row["version"]))

    def snapshot(self) -> None:
        atomic_write_json(self.registry_path, {"updated_at": utc_now_iso(), "models": self.list_models()})
