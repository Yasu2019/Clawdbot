from __future__ import annotations

import argparse
import json
import os
import shutil
from datetime import datetime, timedelta
from pathlib import Path


WORKSPACE = Path(r"D:\Clawdbot_Docker_20260125\data\workspace")
OUTPUT_PATH = WORKSPACE / "storage_cleanup_candidates.json"
SUMMARY_PATH = WORKSPACE / "storage_cleanup_candidates.md"

ROOTS = [
    Path(r"E:\ClawstackData\CDriveRelief"),
    Path(r"E:\ClawstackData\LocalTemp"),
    Path(r"E:\ClawstackData\logs"),
    Path(r"C:\Users\yasu\AppData\Local\Temp"),
    Path(r"C:\Users\yasu\AppData\Local\Docker\log"),
]

DELETE_READY_DAYS = 45
ARCHIVE_READY_DAYS = 14


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def safe_size(path: Path) -> int:
    try:
        if path.is_file():
            return path.stat().st_size
        total = 0
        for child in path.rglob("*"):
            if child.is_file():
                try:
                    total += child.stat().st_size
                except OSError:
                    pass
        return total
    except OSError:
        return 0


def classify_root(path: Path) -> str:
    p = str(path).lower()
    if "localtemp" in p or p.endswith("\\temp"):
        return "temp"
    if "log" in p:
        return "logs"
    if "cdriverelief" in p:
        return "relief_archive"
    return "cache"


def scan(limit: int = 300) -> dict:
    now = datetime.now()
    candidates: list[dict] = []
    total_bytes = 0

    for root in ROOTS:
        if not root.exists():
            continue
        try:
            entries = list(root.iterdir())
        except OSError:
            continue

        for entry in entries:
            if len(candidates) >= limit:
                break
            try:
                stat = entry.stat()
            except OSError:
                continue
            modified = datetime.fromtimestamp(stat.st_mtime)
            age_days = (now - modified).days
            if age_days < ARCHIVE_READY_DAYS:
                continue

            size_bytes = safe_size(entry)
            if size_bytes <= 0:
                continue

            category = classify_root(root)
            recommended = "archive_delete" if age_days >= DELETE_READY_DAYS else "archive"
            row = {
                "path": str(entry),
                "name": entry.name,
                "type": "dir" if entry.is_dir() else "file",
                "category": category,
                "size_bytes": size_bytes,
                "size_gb": round(size_bytes / (1024 ** 3), 3),
                "modified_at": modified.isoformat(),
                "age_days": age_days,
                "recommended_action": recommended,
            }
            total_bytes += size_bytes
            candidates.append(row)

    candidates.sort(key=lambda x: (x["age_days"], x["size_bytes"]), reverse=True)
    result = {
        "updatedAt": now_iso(),
        "service": "storage_cleanup_candidates",
        "roots": [str(r) for r in ROOTS],
        "candidateCount": len(candidates),
        "totalCandidateGB": round(total_bytes / (1024 ** 3), 2),
        "deleteReadyDays": DELETE_READY_DAYS,
        "archiveReadyDays": ARCHIVE_READY_DAYS,
        "candidates": candidates,
    }
    OUTPUT_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# Storage Cleanup Candidates",
        "",
        f"- Updated: {result['updatedAt']}",
        f"- Candidates: {result['candidateCount']}",
        f"- Total size: {result['totalCandidateGB']} GB",
        "",
    ]
    for row in candidates[:50]:
        lines.append(f"- `{row['name']}` | {row['category']} | {row['size_gb']} GB | {row['age_days']} days | {row['recommended_action']}")
    SUMMARY_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=300)
    args = parser.parse_args()
    result = scan(limit=args.limit)
    print(json.dumps({"output": str(OUTPUT_PATH), "count": result["candidateCount"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
