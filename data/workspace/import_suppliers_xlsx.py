from __future__ import annotations

import csv
import json
import shutil
import subprocess
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import openpyxl


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
XLSX_PATH = ROOT / "供給者リスト.xlsx"
CSV_PATH = ROOT / "iatf_system" / "db" / "record" / "suppliers.csv"
RUBY_IMPORTER = "/myapp/script/import_suppliers_csv.rb"
STATUS_PATH = ROOT / "data" / "workspace" / "supplier_import_status.json"
BACKUP_DIR = ROOT / "backups" / "suppliers"

CSV_HEADERS = [
    "no",
    "supplier_name",
    "manufacturer_name",
    "iso_existence",
    "target",
    "qms",
    "second_party_audit",
    "supplier_development",
    "automotive_related",
    "departments",
    "transaction_details",
    "address1",
    "address2",
    "postal_code",
    "tel",
    "fax",
    "filename",
    "document_name",
    "issue_date",
    "feedback_date",
]


@dataclass
class SupplierRow:
    no: str
    supplier_name: str
    manufacturer_name: str
    iso_existence: str
    target: str
    qms: str
    second_party_audit: str
    supplier_development: str
    automotive_related: str
    departments: str
    transaction_details: str
    address1: str
    address2: str
    postal_code: str
    tel: str
    fax: str
    filename: str = ""
    document_name: str = ""
    issue_date: str = ""
    feedback_date: str = ""

    def to_csv_row(self) -> dict[str, str]:
        return {field: getattr(self, field) for field in CSV_HEADERS}


def stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, date):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def load_rows() -> list[SupplierRow]:
    wb = openpyxl.load_workbook(XLSX_PATH, data_only=True)
    ws = wb["Sheet1"]
    rows: list[SupplierRow] = []
    for raw in ws.iter_rows(min_row=7, values_only=True):
        no = stringify(raw[1])
        supplier_name = stringify(raw[2])
        manufacturer_name = stringify(raw[3])
        if not any([no, supplier_name, manufacturer_name]):
            continue
        rows.append(
            SupplierRow(
                no=no,
                supplier_name=supplier_name,
                manufacturer_name=manufacturer_name,
                iso_existence=stringify(raw[8]),
                target=stringify(raw[11]),
                qms=stringify(raw[12]),
                second_party_audit=stringify(raw[13]),
                supplier_development=stringify(raw[14]),
                automotive_related=stringify(raw[17]),
                departments=stringify(raw[18]),
                transaction_details=stringify(raw[19]),
                address1=stringify(raw[23]),
                address2=stringify(raw[24]),
                postal_code=stringify(raw[25]),
                tel=stringify(raw[26]),
                fax=stringify(raw[27]),
            )
        )
    return rows


def backup_existing_csv() -> Path:
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = BACKUP_DIR / f"suppliers_before_2025_09_import_{timestamp}.csv"
    shutil.copy2(CSV_PATH, backup_path)
    return backup_path


def write_csv(rows: list[SupplierRow]) -> None:
    with CSV_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_csv_row())


def run_rails_import() -> dict[str, object]:
    subprocess.run(
        ["docker", "cp", str(CSV_PATH), "iatf_system-web-1:/myapp/db/record/suppliers.csv"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    subprocess.run(
        ["docker", "cp", str(ROOT / "iatf_system" / "script" / "import_suppliers_csv.rb"), "iatf_system-web-1:/myapp/script/import_suppliers_csv.rb"],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    command = [
        "docker",
        "exec",
        "iatf_system-web-1",
        "bash",
        "-lc",
        f"cd /myapp && bundle exec rails runner {RUBY_IMPORTER} db/record/suppliers.csv",
    ]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    payload: dict[str, object] = {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }
    if result.returncode != 0:
        raise RuntimeError(json.dumps(payload, ensure_ascii=False))
    try:
        payload["parsed"] = json.loads(result.stdout.strip().splitlines()[-1])
    except Exception:
        payload["parsed"] = None
    return payload


def main() -> None:
    rows = load_rows()
    backup_path = backup_existing_csv()
    write_csv(rows)
    import_result = run_rails_import()
    status = {
        "step": "completed",
        "xlsx_path": str(XLSX_PATH),
        "csv_path": str(CSV_PATH),
        "backup_csv_path": str(backup_path),
        "row_count": len(rows),
        "import": import_result,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
