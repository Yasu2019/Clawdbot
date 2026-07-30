# -*- coding: utf-8 -*-
"""Monitor WSL/Docker host storage and create a reversible CAE dispatch gate."""
from __future__ import annotations

import argparse
import ctypes
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
STATE_DIR = ROOT / "data" / "state" / "wsl_storage_guard"
STATUS_PATH = STATE_DIR / "status.json"
HISTORY_PATH = STATE_DIR / "history.jsonl"
BLOCK_PATH = STATE_DIR / "CAE_DISPATCH_BLOCKED.json"
VHD_PATHS = (
    Path(r"F:\WSL\Ubuntu-20260730\ext4.vhdx"),
    Path(r"F:\WSL\Ubuntu-20260730\ubuntu-inc177-backup.vhdx"),
    Path(r"F:\WSL\INC177_Rollback_20260730\ext4-original.vhdx"),
    Path(r"F:\WSL\Ubuntu-Active\INCOMPLETE-DO-NOT-USE.vhdx"),
    Path(r"E:\WSL\Ubuntu\ext4.vhdx"),
    Path(r"E:\DockerData\DockerDesktopWSL\disk\docker_data.vhdx"),
)


def drive_usage(letter: str) -> dict[str, float | str]:
    free = ctypes.c_ulonglong()
    total = ctypes.c_ulonglong()
    available = ctypes.c_ulonglong()
    root = f"{letter}:\\"
    if not ctypes.windll.kernel32.GetDiskFreeSpaceExW(
        root, ctypes.byref(available), ctypes.byref(total), ctypes.byref(free)
    ):
        raise OSError(ctypes.get_last_error(), f"Cannot inspect {root}")
    gib = 1024**3
    return {
        "drive": letter.upper(),
        "total_gb": round(total.value / gib, 2),
        "free_gb": round(free.value / gib, 2),
        "free_percent": round((free.value / total.value) * 100, 2),
    }


def drive_severity(drive: dict[str, float | str]) -> str:
    free_gb = float(drive["free_gb"])
    free_percent = float(drive["free_percent"])
    if free_gb < 60 or free_percent < 6:
        return "emergency"
    if free_gb < 100 or free_percent < 10:
        return "critical"
    if free_gb < 150 or free_percent < 15:
        return "warning"
    return "healthy"


def worst_severity(drives: dict[str, dict[str, float | str]]) -> str:
    order = {"healthy": 0, "warning": 1, "critical": 2, "emergency": 3}
    return max((drive_severity(value) for value in drives.values()), key=order.__getitem__)


def atomic_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--task-mode", action="store_true", help="Always return success after writing status")
    args = parser.parse_args()

    now = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    drives = {letter: drive_usage(letter) for letter in ("E", "F")}
    level = worst_severity(drives)
    vhds = []
    for path in VHD_PATHS:
        if path.exists():
            stat = path.stat()
            vhds.append(
                {
                    "path": str(path),
                    "size_gb": round(stat.st_size / 1024**3, 2),
                    "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                }
            )
    payload = {
        "checked_at": now,
        "severity": level,
        "drives": drives,
        "vhds": vhds,
        "policy": {
            "warning": "E or F free <150GB or <15%",
            "critical": "E or F free <100GB or <10%; block new CAE dispatch",
            "emergency": "E or F free <60GB or <6%; block dispatch and request safe recovery",
            "clear_hysteresis": "E free >=175GB and >=18%; F free >=175GB and >=16%",
        },
    }
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    atomic_json(STATUS_PATH, payload)
    with HISTORY_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")

    if level in {"critical", "emergency"}:
        atomic_json(
            BLOCK_PATH,
            {
                "blocked_at": now,
                "severity": level,
                "reason": (
                    f"E free={drives['E']['free_gb']}GB ({drives['E']['free_percent']}%); "
                    f"F free={drives['F']['free_gb']}GB ({drives['F']['free_percent']}%)"
                ),
                "status_path": str(STATUS_PATH),
            },
        )
    elif (
        BLOCK_PATH.exists()
        and float(drives["E"]["free_gb"]) >= 175
        and float(drives["E"]["free_percent"]) >= 18
        and float(drives["F"]["free_gb"]) >= 175
        and float(drives["F"]["free_percent"]) >= 16
    ):
        BLOCK_PATH.unlink()

    print(json.dumps(payload, ensure_ascii=False, indent=None if args.json else 2))
    if args.task_mode:
        return 0
    return 2 if level == "emergency" else 1 if level == "critical" else 0


if __name__ == "__main__":
    raise SystemExit(main())
