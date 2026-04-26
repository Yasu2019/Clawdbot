from __future__ import annotations

import base64
import csv
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE_DIR = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "IATF成果報告書"
HOST_CSV = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCS = ROOT / "iatf_system" / "db" / "documents"
STATE_DOCS = ROOT / "data" / "state" / "IATF_documents"
STATUS_PATH = ROOT / "data" / "workspace" / "process_monitoring_measurement_seed_import_status.json"
BACKUP_DIR = ROOT / "backups" / "process_monitoring_measurement_seed"

TARGETS = [
    {"container": "iatf_system_dev-web-1", "environment": "development"},
    {"container": "iatf_system-web-1", "environment": "production"},
]

YEARS = ["2024", "2025", "2026"]
HEADERS = [
    "filename",
    "category",
    "partnumber",
    "materialcode",
    "phase",
    "stage",
    "description",
    "status",
    "documenttype",
    "documentname",
    "documentrev",
    "documentcategory",
    "documentnumber",
    "start_time",
    "deadline_at",
    "end_at",
    "goal_attainment_level",
    "tasseido",
    "object",
]


def backup_csv() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if HOST_CSV.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(HOST_CSV, BACKUP_DIR / f"attachedfile_{stamp}.csv")


def collect_pdfs() -> list[Path]:
    files: list[Path] = []
    for year in YEARS:
        year_dir = SOURCE_DIR / year
        if not year_dir.exists():
            continue
        files.extend(sorted(year_dir.glob("*.pdf")))
    return files


def build_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for path in collect_pdfs():
        dt = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "filename": path.name,
                "category": "2",
                "partnumber": "",
                "materialcode": "",
                "phase": "16",
                "stage": "343",
                "description": "プロセスの監視・測定記録 seed asset",
                "status": "完了",
                "documenttype": path.suffix.lstrip(".").lower(),
                "documentname": path.stem,
                "documentrev": "",
                "documentcategory": "プロセスの監視・測定記録",
                "documentnumber": "9.1.3.1",
                "start_time": dt,
                "deadline_at": dt,
                "end_at": dt,
                "goal_attainment_level": "100",
                "tasseido": "100",
                "object": "object1",
                "_source_path": str(path),
            }
        )
    return rows


def append_rows(rows: list[dict[str, str]]) -> list[str]:
    backup_csv()
    existing = set()
    with HOST_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            existing.add(
                (
                    row.get("filename", ""),
                    row.get("category", ""),
                    row.get("phase", ""),
                    row.get("stage", ""),
                )
            )

    appended: list[str] = []
    with HOST_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        for row in rows:
            key = (row["filename"], row["category"], row["phase"], row["stage"])
            if key in existing:
                continue
            writer.writerow({header: row.get(header, "") for header in HEADERS})
            appended.append(row["filename"])
            existing.add(key)
    return appended


def copy_documents(rows: list[dict[str, str]]) -> list[str]:
    HOST_DOCS.mkdir(parents=True, exist_ok=True)
    STATE_DOCS.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for row in rows:
        source = Path(row["_source_path"])
        for target_dir in (HOST_DOCS, STATE_DOCS):
            target = target_dir / source.name
            if not target.exists():
                shutil.copy2(source, target)
        copied.append(source.name)
    return copied


def run_import(rows: list[dict[str, str]], target: dict[str, str]) -> dict[str, object]:
    payload = [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows]
    payload_b64 = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    runner = f"""
# encoding: UTF-8
require "json"
require "base64"
rows = JSON.parse(Base64.decode64("{payload_b64}"))
puts JSON.generate(AttachedfileSeedImportService.call(rows: rows))
"""
    completed = subprocess.run(
        [
            "docker", "exec", "-i", target["container"],
            "bundle", "exec", "rails", "runner", "-e", target["environment"], "-"
        ],
        input=runner.encode("utf-8"),
        capture_output=True,
        check=False,
    )
    return {
        "container": target["container"],
        "environment": target["environment"],
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", errors="replace").strip(),
        "stderr": completed.stderr.decode("utf-8", errors="replace").strip(),
    }


def main() -> None:
    rows = build_rows()
    appended = append_rows(rows)
    copied = copy_documents(rows)
    results = [run_import(rows, target) for target in TARGETS]

    status = {
        "source_dir": str(SOURCE_DIR),
        "row_count": len(rows),
        "appended_count": len(appended),
        "copied_count": len(copied),
        "years": YEARS,
        "rows": [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows],
        "results": results,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "process_monitoring_measurement_seed_import",
            "title": "Process monitoring measurement PDFs synced to seed",
            "source": str(SOURCE_DIR),
            "record_count": len(rows),
            "details": {
                "category": 2,
                "phase": 16,
                "stage": 343,
                "appended_count": len(appended),
                "copied_count": len(copied),
                "filenames": [row["filename"] for row in rows],
                "target_results": [
                    {
                        "container": item["container"],
                        "environment": item["environment"],
                        "returncode": item["returncode"],
                    }
                    for item in results
                ],
            },
        }
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
