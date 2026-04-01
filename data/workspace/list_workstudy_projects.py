#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
ROOT = Path(__file__).resolve().parents[2]
PROJECTS_DIR = ROOT / "clawstack_v2" / "data" / "workstudy" / "projects"
STATUS_PATH = ROOT / "data" / "workspace" / "workstudy_project_inventory.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_project(project_dir: Path) -> dict[str, Any]:
    labels_path = project_dir / "labels.json"
    metrics_path = project_dir / "metrics.json"
    segments_path = project_dir / "segments.json"
    summary: dict[str, Any] = {
        "project_id": project_dir.name,
        "path": str(project_dir),
        "updatedAt": datetime.fromtimestamp(project_dir.stat().st_mtime, JST).strftime("%Y-%m-%d %H:%M:%S JST"),
        "has_labels": labels_path.exists(),
        "has_metrics": metrics_path.exists(),
        "has_segments": segments_path.exists(),
    }
    if labels_path.exists():
        labels = load_json(labels_path)
        summary["label_count"] = len(labels)
        summary["label_distribution"] = {}
        summary["has_confidence"] = any("confidence" in item for item in labels)
        review_count = sum(1 for item in labels if item.get("review_required"))
        summary["review_required_count"] = review_count
        for item in labels:
            label = str(item.get("label", "UNKNOWN"))
            summary["label_distribution"][label] = summary["label_distribution"].get(label, 0) + 1
    if metrics_path.exists():
        metrics = load_json(metrics_path)
        kpi = metrics.get("kpi", {})
        summary["avg_confidence"] = kpi.get("avg_confidence")
        summary["low_confidence_ratio"] = kpi.get("low_confidence_ratio")
        summary["most_efficiency"] = kpi.get("most_efficiency")
    return summary


def main() -> int:
    payload = {
        "generatedAt": now_jst_text(),
        "projectsDir": str(PROJECTS_DIR),
        "projects": [],
    }
    if PROJECTS_DIR.exists():
        payload["projects"] = [summarize_project(project_dir) for project_dir in sorted(PROJECTS_DIR.iterdir()) if project_dir.is_dir()]
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
