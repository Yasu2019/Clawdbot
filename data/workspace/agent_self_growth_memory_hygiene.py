#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import requests


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
ROOT = WORKSPACE.parent.parent
STATUS_PATH = WORKSPACE / "agent_self_growth_memory_hygiene_status.json"
STATE_PATH = WORKSPACE / "agent_self_growth_memory_hygiene_state.json"
HARNESS_PATH = ROOT / "data" / "state" / "agent_self_growth_memory_hygiene" / "harness_status.json"
ARCHIVE_DIR = ROOT / "backups" / "qdrant_self_growth_archive"
QDRANT_URL = os.environ.get("QDRANT_URL", "http://127.0.0.1:6333").rstrip("/")
COLLECTION = os.environ.get("SELF_GROWTH_COLLECTION", "agent_self_growth_memory")


def now_jst() -> datetime:
    return datetime.now(JST)


def now_jst_text() -> str:
    return now_jst().strftime("%Y-%m-%d %H:%M:%S JST")


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def load_json(path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def qdrant_get(path: str) -> dict[str, Any]:
    response = requests.get(f"{QDRANT_URL}{path}", timeout=60)
    response.raise_for_status()
    return response.json()


def qdrant_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{QDRANT_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def qdrant_delete(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = requests.post(f"{QDRANT_URL}{path}", json=payload, timeout=120)
    response.raise_for_status()
    return response.json()


def collection_info() -> dict[str, Any]:
    return qdrant_get(f"/collections/{COLLECTION}")


def scroll_points(limit: int = 256) -> list[dict[str, Any]]:
    points: list[dict[str, Any]] = []
    offset: Any = None
    while True:
        payload: dict[str, Any] = {"limit": limit, "with_payload": True, "with_vector": False}
        if offset is not None:
            payload["offset"] = offset
        result = qdrant_post(f"/collections/{COLLECTION}/points/scroll", payload)
        batch = result.get("result", {}).get("points", [])
        points.extend(batch)
        offset = result.get("result", {}).get("next_page_offset")
        if not batch or offset is None:
            break
    return points


def payload_bytes(points: list[dict[str, Any]]) -> int:
    total = 0
    for point in points:
        payload = point.get("payload") or {}
        total += len(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    return total


def vector_size(info: dict[str, Any]) -> int:
    vectors = (((info.get("result") or {}).get("config") or {}).get("params") or {}).get("vectors") or {}
    if isinstance(vectors, dict):
        return int(vectors.get("size") or 0)
    return 0


def score_point(point: dict[str, Any]) -> tuple[int, str]:
    payload = point.get("payload") or {}
    score = int(payload.get("total_score") or 0)
    recency = (
        payload.get("approved_date")
        or payload.get("synced_at")
        or payload.get("updated_at")
        or payload.get("created_at")
        or ""
    )
    return score, str(recency)


def dedupe_key(point: dict[str, Any]) -> str:
    payload = point.get("payload") or {}
    return str(payload.get("skill_name") or payload.get("external_id") or point.get("id"))


def choose_archive(points: list[dict[str, Any]], max_points: int, max_bytes: int, estimated_total_bytes: int) -> list[dict[str, Any]]:
    if len(points) <= max_points and estimated_total_bytes <= max_bytes:
        return []
    kept_keys: set[str] = set()
    ordered = sorted(points, key=lambda item: (score_point(item)[0], score_point(item)[1]), reverse=True)
    kept: list[dict[str, Any]] = []
    archived: list[dict[str, Any]] = []
    current_bytes = estimated_total_bytes
    payload_only = payload_bytes(points)
    vector_overhead_per_point = max(0, (estimated_total_bytes - payload_only) // max(len(points), 1))
    for point in ordered:
        key = dedupe_key(point)
        point_bytes = len(json.dumps(point.get("payload") or {}, ensure_ascii=False).encode("utf-8")) + vector_overhead_per_point
        if key not in kept_keys and len(kept) < max_points and current_bytes - point_bytes <= max_bytes:
            kept.append(point)
            kept_keys.add(key)
            current_bytes -= point_bytes
            continue
        archived.append(point)
    return archived


def archive_points(points: list[dict[str, Any]]) -> Path:
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    archive_path = ARCHIVE_DIR / f"agent_self_growth_memory_{now_jst().strftime('%Y%m%d_%H%M%S')}.jsonl"
    with archive_path.open("w", encoding="utf-8") as handle:
        for point in points:
            handle.write(json.dumps(point, ensure_ascii=False) + "\n")
    return archive_path


def delete_points(points: list[dict[str, Any]]) -> dict[str, Any]:
    ids = [point.get("id") for point in points if point.get("id") is not None]
    if not ids:
        return {"status": "skipped", "deleted": 0}
    return qdrant_delete(
        f"/collections/{COLLECTION}/points/delete",
        {"points": ids, "wait": True},
    )


def write_harness(status: dict[str, Any]) -> None:
    save_json(
        HARNESS_PATH,
        {
            "service": "agent_self_growth_memory_hygiene",
            "updatedAt": now_jst().isoformat(),
            "state": status.get("stage"),
            "reason": status.get("reason"),
            "lastAction": status.get("lastAction"),
        },
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Hygiene and archive guard for agent_self_growth_memory")
    parser.add_argument("--max-points", type=int, default=1000)
    parser.add_argument("--max-mb", type=int, default=100)
    parser.add_argument("--poll-seconds", type=int, default=21600)
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    started_at = load_json(STATE_PATH, {}).get("startedAt") or now_jst_text()
    cycle = int(load_json(STATE_PATH, {}).get("cycle") or 0)

    while True:
        cycle += 1
        status: dict[str, Any] = {
            "startedAt": started_at,
            "updatedAt": now_jst_text(),
            "stage": "running",
            "lastAction": "inspect",
            "collection": COLLECTION,
            "cycle": cycle,
        }
        save_json(STATUS_PATH, status)
        write_harness(status)

        info = collection_info()
        points = scroll_points()
        payload_total = payload_bytes(points)
        vec_size = vector_size(info)
        estimated_total = payload_total + (len(points) * vec_size * 4)
        status["metrics"] = {
            "pointsCount": len(points),
            "vectorSize": vec_size,
            "payloadBytes": payload_total,
            "estimatedTotalBytes": estimated_total,
            "estimatedTotalMb": round(estimated_total / (1024 * 1024), 3),
        }

        archive_candidates = choose_archive(
            points=points,
            max_points=args.max_points,
            max_bytes=args.max_mb * 1024 * 1024,
            estimated_total_bytes=estimated_total,
        )
        if args.force and not archive_candidates and points:
            archive_candidates = sorted(points, key=lambda item: (score_point(item)[0], score_point(item)[1]))[:-1]

        if not archive_candidates:
            status["stage"] = "healthy"
            status["reason"] = "collection is within thresholds"
            status["lastAction"] = "none"
            status["updatedAt"] = now_jst_text()
            save_json(STATUS_PATH, status)
            save_json(STATE_PATH, {"startedAt": started_at, "cycle": cycle})
            write_harness(status)
            if args.once:
                return 0
            time.sleep(max(args.poll_seconds, 300))
            continue

        archive_path = archive_points(archive_candidates)
        delete_result = delete_points(archive_candidates)
        status["stage"] = "archived"
        status["reason"] = "archived low-priority points to keep collection within thresholds"
        status["lastAction"] = "archive_and_delete"
        status["archivedCount"] = len(archive_candidates)
        status["archivePath"] = str(archive_path)
        status["deleteResult"] = delete_result
        status["updatedAt"] = now_jst_text()
        save_json(STATUS_PATH, status)
        save_json(
            STATE_PATH,
            {
                "startedAt": started_at,
                "cycle": cycle,
                "lastArchiveAt": now_jst_text(),
                "archivePath": str(archive_path),
                "archivedCount": len(archive_candidates),
            },
        )
        write_harness(status)
        if args.once:
            return 0
        time.sleep(max(args.poll_seconds, 300))


if __name__ == "__main__":
    raise SystemExit(main())
