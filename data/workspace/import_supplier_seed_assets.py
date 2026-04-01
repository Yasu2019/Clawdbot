from __future__ import annotations

import csv
import json
import shutil
from datetime import datetime
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SUPPLIER_DIR = ROOT / "Supplier_20260329"
HOST_CSV = ROOT / "iatf_system" / "db" / "record" / "attachedfile.csv"
HOST_DOCS = ROOT / "iatf_system" / "db" / "documents"
STATE_DOCS = ROOT / "data" / "state" / "IATF_documents"
STATUS_PATH = ROOT / "data" / "workspace" / "supplier_seed_import_status.json"
BACKUP_DIR = ROOT / "backups" / "supplier_seed"


FILES = [
    {
        "path": SUPPLIER_DIR / "供給者リスト.xlsx",
        "documentcategory": "供給者リスト",
        "documentnumber": "SUPPLIER-20260329-001",
    },
    {
        "path": SUPPLIER_DIR / "2025●供給者管理計画／実績表(KGM017).xlsx",
        "documentcategory": "供給者管理計画実績",
        "documentnumber": "SUPPLIER-20260329-002",
    },
    {
        "path": SUPPLIER_DIR / "●供給者評価表・供給者再評価記録台帳2025.xls",
        "documentcategory": "供給者評価再評価台帳",
        "documentnumber": "SUPPLIER-20260329-003",
    },
]


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


def build_rows() -> list[dict[str, str]]:
    rows = []
    for item in FILES:
        path = item["path"]
        if not path.exists():
            raise FileNotFoundError(f"Supplier source not found: {path}")
        dt = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        rows.append(
            {
                "filename": path.name,
                "category": "2",
                "partnumber": "",
                "materialcode": "",
                "phase": "",
                "stage": "",
                "description": "供給者データ seed asset",
                "status": "完了",
                "documenttype": path.suffix.lstrip(".").lower(),
                "documentname": path.stem,
                "documentrev": "",
                "documentcategory": item["documentcategory"],
                "documentnumber": item["documentnumber"],
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
    for row in rows:
        source = Path(row["_source_path"])
        for target_dir in (HOST_DOCS, STATE_DOCS):
            target = target_dir / source.name
            if not target.exists():
                shutil.copy2(source, target)
        copied.append(source.name)
    return copied


def main() -> None:
    rows = build_rows()
    appended = append_rows(rows)
    copied = copy_documents(rows)
    status = {
        "source_dir": str(SUPPLIER_DIR),
        "row_count": len(rows),
        "appended_count": len(appended),
        "copied_count": len(copied),
        "rows": [{k: v for k, v in row.items() if not k.startswith("_")} for row in rows],
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "supplier_seed_import",
            "title": "Supplier Excel assets synced to seed",
            "source": str(SUPPLIER_DIR),
            "record_count": len(rows),
            "details": {
                "category": 2,
                "appended_count": len(appended),
                "copied_count": len(copied),
                "filenames": [row["filename"] for row in rows],
            },
        }
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
