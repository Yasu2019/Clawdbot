from __future__ import annotations

import csv
import json
import shutil
import zipfile
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
ZIP_PATH = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "文書照合_20250329.zip"
HOST_CSV = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCS = ROOT / "iatf_system" / "db" / "documents"
STATE_DOCS = ROOT / "data" / "state" / "IATF_documents"
STATUS_PATH = ROOT / "data" / "workspace" / "document_reconciliation_seed_import_status.json"
BACKUP_DIR = ROOT / "backups" / "document_reconciliation_seed"


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


def collect_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with zipfile.ZipFile(ZIP_PATH) as zf:
        excel_members = [
            member
            for member in zf.namelist()
            if not member.endswith("/") and Path(member).suffix.lower() in {".xls", ".xlsx"}
        ]
        for index, member in enumerate(sorted(excel_members), start=1):
            info = zf.getinfo(member)
            filename = Path(member).name
            dt = datetime(*info.date_time).strftime("%Y-%m-%d %H:%M:%S")
            rows.append(
                {
                    "filename": filename,
                    "category": "2",
                    "partnumber": "",
                    "materialcode": "",
                    "phase": "",
                    "stage": "",
                    "description": "文書照合用台帳一式",
                    "status": "完了",
                    "documenttype": Path(filename).suffix.lstrip(".").lower(),
                    "documentname": Path(filename).stem,
                    "documentrev": "",
                    "documentcategory": "文書照合資料",
                    "documentnumber": f"DOCREC-20250329-{index:03d}",
                    "start_time": dt,
                    "deadline_at": dt,
                    "end_at": dt,
                    "goal_attainment_level": "100",
                    "tasseido": "100",
                    "object": "object1",
                    "_zip_member": member,
                }
            )
    return rows


def append_rows(rows: list[dict[str, str]]) -> list[str]:
    backup_csv()
    existing = set()
    with HOST_CSV.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            existing.add((row.get("filename", ""), row.get("category", "")))

    appended: list[str] = []
    with HOST_CSV.open("a", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        for row in rows:
            key = (row["filename"], row["category"])
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
    with zipfile.ZipFile(ZIP_PATH) as zf:
        for row in rows:
            filename = row["filename"]
            data = zf.read(row["_zip_member"])
            for target_dir in (HOST_DOCS, STATE_DOCS):
                target = target_dir / filename
                if not target.exists():
                    target.write_bytes(data)
            copied.append(filename)
    return copied


def main() -> None:
    rows = collect_rows()
    appended = append_rows(rows)
    copied = copy_documents(rows)

    status = {
        "zip_path": str(ZIP_PATH),
        "row_count": len(rows),
        "appended_count": len(appended),
        "copied_count": len(copied),
        "rows": [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows],
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "document_reconciliation_seed_import",
            "title": "Document reconciliation Excel assets synced to seed",
            "source": str(ZIP_PATH),
            "record_count": len(rows),
            "details": {
                "category": 2,
                "documentcategory": "文書照合資料",
                "appended_count": len(appended),
                "copied_count": len(copied),
                "filenames": [row["filename"] for row in rows],
            },
        }
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
