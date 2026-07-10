from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def project_root() -> Path:
    env = os.getenv("INSPECTION_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return Path(__file__).resolve().parents[2]


def load_yaml(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.is_absolute():
        p = project_root() / p
    if not p.exists():
        raise FileNotFoundError(f"設定ファイルがありません: {p}")
    with p.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAMLのルートは辞書である必要があります: {p}")
    return data


@dataclass(frozen=True)
class Paths:
    root: Path
    database: Path
    runtime: Path
    reports: Path
    product_recipes: Path
    model_registry: Path


class AppConfig:
    def __init__(self, path: str | Path | None = None):
        path = path or os.getenv("INSPECTION_APP_CONFIG", "configs/app.yaml")
        self.raw = load_yaml(path)
        root = project_root()
        paths = self.raw.get("paths", {})
        self.paths = Paths(
            root=root,
            database=root / os.getenv("INSPECTION_DB", paths.get("database", "data/inspection.db")),
            runtime=root / paths.get("runtime", "data/runtime"),
            reports=root / paths.get("reports", "data/reports"),
            product_recipes=root / paths.get("product_recipes", "configs/products"),
            model_registry=root / paths.get("model_registry", "models/registry.json"),
        )
        self.app = self.raw.get("app", {})
        self.learning = self.raw.get("learning", {})
        self.security = self.raw.get("security", {})
        self.disable_external_api = (
            os.getenv("INSPECTION_DISABLE_EXTERNAL_API", "1") != "0"
            or bool(self.app.get("disable_external_api", True))
        )
        for p in (self.paths.runtime, self.paths.reports, self.paths.model_registry.parent):
            p.mkdir(parents=True, exist_ok=True)

    def recipe(self, product_id: str) -> dict[str, Any]:
        safe = "".join(c for c in product_id if c.isalnum() or c in ("-", "_"))
        if safe != product_id or not safe:
            raise ValueError("product_idに使用できない文字があります")
        return load_yaml(self.paths.product_recipes / f"{safe}.yaml")
