from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import cv2

from inspection_ai.config import AppConfig
from inspection_ai.db import Database
from inspection_ai.detection.reference_model import ReferenceDifferenceDetector
from inspection_ai.learning.evaluation import evaluate_labeled_paths
from inspection_ai.model_registry import ModelRegistry
from inspection_ai.preprocessing.image_ops import apply_roi
from inspection_ai.review.service import ReviewService
from inspection_ai.utils import compact_timestamp, utc_now_iso


def build_evaluation_set(config: AppConfig, db: Database, product_id: str) -> list[tuple[Path, str]]:
    base = config.paths.root / "data/internal" / product_id / "fixed_test"
    labeled: list[tuple[Path, str]] = []
    labeled.extend((path, "OK") for path in (base / "good").glob("**/*") if path.is_file())
    labeled.extend((path, "NG") for path in (base / "bad").glob("**/*") if path.is_file())
    for row in ReviewService(db).training_candidates(product_id):
        path = config.paths.root / row["original_path"]
        if path.exists() and row.get("user_decision") in {"OK", "NG"}:
            labeled.append((path, row["user_decision"]))
    # 同一パスの重複を除く。固定テストを優先する。
    unique: dict[str, tuple[Path, str]] = {}
    for path, label in labeled:
        unique.setdefault(str(path.resolve()), (path, label))
    return list(unique.values())


def compare_candidate(
    config: AppConfig,
    db: Database,
    registry: ModelRegistry,
    product_id: str,
    candidate_version: str,
    minimum_accuracy: float = 0.90,
) -> dict[str, Any]:
    candidate = db.query_one("SELECT * FROM models WHERE version=? AND product_id=?", (candidate_version, product_id))
    if not candidate:
        raise KeyError("Challengerがありません")
    champion = registry.get_champion(product_id)
    if not champion:
        raise ValueError("比較対象Championがありません")
    labeled = build_evaluation_set(config, db, product_id)
    if len(labeled) < 10:
        raise ValueError(f"評価データが不足しています: {len(labeled)}")
    recipe = config.recipe(product_id)
    champion_metrics = evaluate_labeled_paths(config.paths.root / champion["path"], recipe, labeled).to_dict()
    candidate_metrics = evaluate_labeled_paths(config.paths.root / candidate["path"], recipe, labeled).to_dict()
    reasons: list[str] = []
    if candidate_metrics["accuracy"] < minimum_accuracy:
        reasons.append(f"accuracy不足: {candidate_metrics['accuracy']:.4f} < {minimum_accuracy:.4f}")
    if candidate_metrics["recall"] + 1e-9 < champion_metrics["recall"]:
        reasons.append("見逃し率がChampionより悪化")
    if candidate_metrics["fp"] > champion_metrics["fp"]:
        reasons.append("誤検出数がChampionより増加")
    if candidate_metrics["fn"] > champion_metrics["fn"]:
        reasons.append("見逃し数がChampionより増加")
    report = {
        "product_id": product_id,
        "candidate_version": candidate_version,
        "champion_version": champion["version"],
        "evaluation_count": len(labeled),
        "champion": champion_metrics,
        "candidate": candidate_metrics,
        "gate_passed": not reasons,
        "gate_reasons": reasons or ["固定評価ゲート合格。シャドー運用と人承認は別途必要"],
        "auto_promoted": False,
        "created_at": utc_now_iso(),
    }
    db.execute("UPDATE models SET metrics_json=? WHERE version=?", (json.dumps(report, ensure_ascii=False), candidate_version))
    db.audit("COMPARE_CHALLENGER", "model", candidate_version, report)
    registry.snapshot()
    output = config.paths.reports / f"model_gate_{candidate_version}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report_path"] = str(output)
    return report


def shadow_compare_folder(
    config: AppConfig,
    db: Database,
    registry: ModelRegistry,
    product_id: str,
    candidate_version: str,
    folder: str | Path,
) -> Path:
    candidate = db.query_one("SELECT * FROM models WHERE version=?", (candidate_version,))
    champion = registry.get_champion(product_id)
    if not candidate or not champion:
        raise ValueError("ChampionまたはChallengerがありません")
    recipe = config.recipe(product_id)
    champion_detector = ReferenceDifferenceDetector(config.paths.root / champion["path"], recipe)
    candidate_detector = ReferenceDifferenceDetector(config.paths.root / candidate["path"], recipe)
    review_threshold = float(recipe.get("model", {}).get("review_threshold", 0.01))
    rows = []
    for path in Path(folder).glob("**/*"):
        if path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff"}:
            continue
        image = cv2.imread(str(path))
        if image is None:
            continue
        roi, offset = apply_roi(image, recipe.get("image", {}).get("roi"))
        ch, _ = champion_detector.predict(roi, offset)
        ca, _ = candidate_detector.predict(roi, offset)
        ch_dec = "ALERT" if ch.anomaly_score >= review_threshold else "OK"
        ca_dec = "ALERT" if ca.anomaly_score >= review_threshold else "OK"
        rows.append({
            "path": str(path),
            "champion_score": ch.anomaly_score,
            "candidate_score": ca.anomaly_score,
            "champion_decision": ch_dec,
            "candidate_decision": ca_dec,
            "different": ch_dec != ca_dec,
        })
    output = config.paths.reports / f"shadow_{candidate_version}_{compact_timestamp()}.csv"
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()) if rows else ["path"])
        writer.writeheader()
        writer.writerows(rows)
    db.audit("SHADOW_COMPARE", "model", candidate_version, {"folder": str(folder), "rows": len(rows), "output": str(output)})
    return output
