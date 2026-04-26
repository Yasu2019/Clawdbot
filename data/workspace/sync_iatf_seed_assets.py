from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
HOST_ATTACHEDFILE = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCUMENTS = ROOT / "iatf_system" / "db" / "documents"
DEV_DOCUMENTS = ROOT / "data" / "state" / "IATF_documents"
BACKUP_DIR = ROOT / "backups" / "iatf_seed_sync"
STATUS_PATH = ROOT / "data" / "workspace" / "iatf_seed_sync_status.json"
SOURCE_CONTAINER = "iatf_system-web-1"
SOURCE_ATTACHEDFILE = "/myapp/db/record/attachedfile.csv"


def export_live_attachedfile() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if HOST_ATTACHEDFILE.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(HOST_ATTACHEDFILE, BACKUP_DIR / f"attachedfile_{stamp}.csv")

    completed = subprocess.run(
        ["docker", "exec", SOURCE_CONTAINER, "cat", SOURCE_ATTACHEDFILE],
        capture_output=True,
        check=True,
    )
    HOST_ATTACHEDFILE.parent.mkdir(parents=True, exist_ok=True)
    HOST_ATTACHEDFILE.write_bytes(completed.stdout)


def listed_filenames() -> list[str]:
    filenames: list[str] = []
    with HOST_ATTACHEDFILE.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            filename = (row.get("filename") or "").strip()
            if filename:
                filenames.append(filename)
    return filenames


def sync_documents(filenames: list[str]) -> dict[str, object]:
    HOST_DOCUMENTS.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    missing: list[str] = []

    for filename in filenames:
        host_target = HOST_DOCUMENTS / filename
        if host_target.exists():
            continue

        dev_source = DEV_DOCUMENTS / filename
        if dev_source.exists():
            shutil.copy2(dev_source, host_target)
            copied.append(filename)
            continue

        missing.append(filename)

    return {
      "copied_from_dev_state": copied,
      "missing_after_sync": missing,
    }


def main() -> None:
    export_live_attachedfile()
    filenames = listed_filenames()
    sync_result = sync_documents(filenames)
    status = {
        "completed_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source_container": SOURCE_CONTAINER,
        "host_attachedfile": str(HOST_ATTACHEDFILE),
        "host_documents": str(HOST_DOCUMENTS),
        "record_count": len(filenames),
        "copied_from_dev_state_count": len(sync_result["copied_from_dev_state"]),
        "missing_after_sync_count": len(sync_result["missing_after_sync"]),
        "copied_from_dev_state": sync_result["copied_from_dev_state"][:50],
        "missing_after_sync_sample": sync_result["missing_after_sync"][:50],
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "seed_sync",
            "title": "IATF seed assets synchronized from production",
            "source": str(SOURCE_CONTAINER),
            "record_count": len(filenames),
            "details": {
                "host_attachedfile": str(HOST_ATTACHEDFILE),
                "host_documents": str(HOST_DOCUMENTS),
                "copied_from_dev_state_count": len(sync_result["copied_from_dev_state"]),
                "missing_after_sync_count": len(sync_result["missing_after_sync"]),
            },
        }
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
