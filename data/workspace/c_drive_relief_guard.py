from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path


WORKSPACE = Path(r"D:\Clawdbot_Docker_20260125\data\workspace")
STATUS_PATH = WORKSPACE / "c_drive_relief_guard_status.json"
TARGET_ROOT = Path(r"E:\ClawstackData\CDriveRelief")
CURRENT_TEMP = Path(os.environ.get("TEMP", r"E:\ClawstackData\LocalTemp"))
LEGACY_TEMP = Path(r"C:\Users\yasu\AppData\Local\Temp")
LOCALAPPDATA = Path(os.environ.get("LOCALAPPDATA", r"C:\Users\yasu\AppData\Local"))


@dataclass
class MoveRecord:
    source: str
    target: str
    bytes_moved: int


def now_iso() -> str:
    return datetime.now().astimezone().isoformat()


def drive_free_gb(path: str) -> float:
    usage = shutil.disk_usage(path)
    return round(usage.free / (1024 ** 3), 2)


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


def move_entry(src: Path, dst_root: Path) -> MoveRecord | None:
    if not src.exists():
        return None
    rel_name = src.name
    dst = dst_root / rel_name
    if dst.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = dst_root / f"{rel_name}_{stamp}"
    dst_root.mkdir(parents=True, exist_ok=True)
    size = safe_size(src)
    shutil.move(str(src), str(dst))
    return MoveRecord(source=str(src), target=str(dst), bytes_moved=size)


def collect_candidates(days_old: int) -> list[Path]:
    cutoff = datetime.now() - timedelta(days=days_old)
    candidates: list[Path] = []

    explicit_dirs = [
        LOCALAPPDATA / "Temp" / "clawdbot_email_db_repair",
        LOCALAPPDATA / "Temp" / "clawdbot_temp",
        LOCALAPPDATA / "Temp" / "pip-unpack",
        LOCALAPPDATA / "Docker" / "log",
        LOCALAPPDATA / "Docker" / "panic.log",
    ]
    for p in explicit_dirs:
        if p.exists():
            candidates.append(p)

    for root in [LEGACY_TEMP, CURRENT_TEMP]:
        if not root.exists():
            continue
        try:
            for child in root.iterdir():
                name = child.name.lower()
                if name.startswith(("clawdbot_", "tmp", "pip-", "n8n-", "playwright", "brv", "ollama")) or name.endswith((".log", ".tmp")):
                    try:
                        mtime = datetime.fromtimestamp(child.stat().st_mtime)
                    except OSError:
                        continue
                    if mtime <= cutoff:
                        candidates.append(child)
        except OSError:
            continue

    uniq: list[Path] = []
    seen = set()
    for p in candidates:
        key = str(p).lower()
        if key not in seen:
            seen.add(key)
            uniq.append(p)
    return uniq


def run_once(warn_gb: float, critical_gb: float, days_old: int) -> dict:
    TARGET_ROOT.mkdir(parents=True, exist_ok=True)
    free_c = drive_free_gb("C:\\")
    level = "healthy"
    if free_c <= critical_gb:
        level = "critical"
    elif free_c <= warn_gb:
        level = "warning"

    result = {
        "updatedAt": now_iso(),
        "service": "c_drive_relief_guard",
        "freeC_GB": free_c,
        "warnThresholdGB": warn_gb,
        "criticalThresholdGB": critical_gb,
        "level": level,
        "moves": [],
        "notes": [],
    }

    if level in {"warning", "critical"}:
        candidates = collect_candidates(days_old=days_old)
        relief_dir = TARGET_ROOT / datetime.now().strftime("%Y%m%d")
        for candidate in candidates:
            try:
                record = move_entry(candidate, relief_dir)
                if record:
                    result["moves"].append(asdict(record))
            except Exception as exc:  # noqa: BLE001
                result["notes"].append(f"move failed: {candidate} :: {exc}")
        result["freeCAfter_GB"] = drive_free_gb("C:\\")
        result["notes"].append("Only temp/cache/log style paths are moved. No user document folders are touched.")
    else:
        result["notes"].append("C drive has enough free space; no action taken.")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--warn-gb", type=float, default=60.0)
    parser.add_argument("--critical-gb", type=float, default=30.0)
    parser.add_argument("--days-old", type=int, default=2)
    parser.add_argument("--poll-seconds", type=int, default=0)
    args = parser.parse_args()

    while True:
        result = run_once(args.warn_gb, args.critical_gb, args.days_old)
        STATUS_PATH.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        if args.poll_seconds <= 0:
            return 0
        time.sleep(args.poll_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
