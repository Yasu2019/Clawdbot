from __future__ import annotations

import base64
import csv
import json
import re
import shutil
import subprocess
import zipfile
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
ZIP_PATH = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "製造工程設計" / "52期2025年.zip"
HOST_CSV = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCS = ROOT / "iatf_system" / "db" / "documents"
DEV_DOCS = ROOT / "data" / "state" / "IATF_documents"
STATUS_PATH = ROOT / "data" / "workspace" / "manufacturing_design_zip_import_status.json"
BACKUP_DIR = ROOT / "backups" / "manufacturing_design_zip"

TARGETS = [
    {"container": "iatf_system_dev-web-1", "environment": "development"},
    {"container": "iatf_system-web-1", "environment": "production"},
]

STAGE_BY_KIND = {
    "設計計画書": "105",
    "設計検証チェックリスト": "106",
    "Ｄ.R会議議事録": "112",
    "D.R会議議事録": "112",
}


def normalize_doc_kind(name: str) -> str | None:
    for kind in STAGE_BY_KIND:
        if kind in name:
            return kind
    return None


def parse_partnumber(name: str) -> str:
    match = re.search(r"(NT\d+-P\d+(?:-\d+)?)", name)
    return match.group(1) if match else ""


def parse_materialcode(name: str) -> str:
    match = re.search(r"_(PM[0-9A-Z]+)(?:_|【|\.|$)", name)
    return match.group(1) if match else ""


def collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen: set[str] = set()

    with zipfile.ZipFile(ZIP_PATH) as zf:
        for info in zf.infolist():
            if info.is_dir():
                continue
            filename = Path(info.filename).name
            if filename in seen:
                continue
            kind = normalize_doc_kind(filename)
            if not kind:
                continue
            seen.add(filename)
            stem = Path(filename).stem.lstrip("_")
            rows.append(
                {
                    "filename": filename,
                    "category": "1",
                    "partnumber": parse_partnumber(filename),
                    "materialcode": parse_materialcode(filename),
                    "phase": "10",
                    "stage": STAGE_BY_KIND[kind],
                    "description": "",
                    "status": "完了",
                    "documenttype": "",
                    "documentname": stem,
                    "documentrev": "",
                    "documentcategory": "",
                    "documentnumber": "",
                    "start_time": "2025-03-29 00:00:00",
                    "deadline_at": "2025-03-29 00:00:00",
                    "end_at": "2025-03-29 00:00:00",
                    "goal_attainment_level": "100",
                    "tasseido": "100",
                    "object": "object1",
                    "_zip_member": info.filename,
                }
            )
    return sorted(rows, key=lambda row: (row["partnumber"], row["stage"], row["filename"]))


def backup_csv() -> None:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    if HOST_CSV.exists():
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        shutil.copy2(HOST_CSV, BACKUP_DIR / f"attachedfile_{stamp}.csv")


def append_rows(rows: list[dict[str, str]]) -> list[str]:
    backup_csv()
    existing = set()
    with HOST_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            existing.add((row.get("filename", ""), row.get("category", ""), row.get("stage", "")))

    appended: list[str] = []
    headers = [
        "filename","category","partnumber","materialcode","phase","stage","description","status","documenttype",
        "documentname","documentrev","documentcategory","documentnumber","start_time","deadline_at","end_at",
        "goal_attainment_level","tasseido","object"
    ]

    with HOST_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        for row in rows:
            key = (row["filename"], row["category"], row["stage"])
            if key in existing:
                continue
            writer.writerow({header: row.get(header, "") for header in headers})
            appended.append(row["filename"])
            existing.add(key)
    return appended


def extract_documents(rows: list[dict[str, str]]) -> list[str]:
    HOST_DOCS.mkdir(parents=True, exist_ok=True)
    DEV_DOCS.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for row in rows:
            filename = row["filename"]
            member = row["_zip_member"]
            data = zf.read(member)
            for target_dir in (HOST_DOCS, DEV_DOCS):
                target = target_dir / filename
                if not target.exists():
                    target.write_bytes(data)
            copied.append(filename)
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
    rows = collect_rows()
    appended = append_rows(rows)
    copied = extract_documents(rows)
    results = [run_import(rows, target) for target in TARGETS]

    status = {
        "zip_path": str(ZIP_PATH),
        "row_count": len(rows),
        "appended_count": len(appended),
        "copied_count": len(copied),
        "rows": [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows],
        "results": results,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "manufacturing_design_import",
            "title": "Manufacturing design ZIP imported",
            "source": str(ZIP_PATH),
            "record_count": len(rows),
            "details": {
                "appended_count": len(appended),
                "copied_count": len(copied),
                "partnumbers": sorted({row["partnumber"] for row in rows if row["partnumber"]}),
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
