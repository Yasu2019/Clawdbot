from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path

import openpyxl
import xlrd


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
SOURCE_DIR = ROOT / "Supplier_20260329"
OUTPUT_DIR = ROOT / "iatf_system" / "db" / "record"
STATUS_PATH = ROOT / "data" / "workspace" / "supplier_workbooks_export_status.json"


@dataclass
class WorkbookTarget:
    source_name: str
    output_name: str
    title: str
    kind: str  # xlsx | xls


TARGETS = [
    WorkbookTarget(
        source_name="2025●供給者管理計画／実績表(KGM017).xlsx",
        output_name="supplier_management_plan_2025.json",
        title="2025供給者管理計画／実績表",
        kind="xlsx",
    ),
    WorkbookTarget(
        source_name="●供給者評価表・供給者再評価記録台帳2025.xls",
        output_name="supplier_evaluation_2025.json",
        title="2025供給者評価表・供給者再評価記録台帳",
        kind="xls",
    ),
]


def is_filled(value: object) -> bool:
    return value not in ("", None)


def normalize_value(value: object, datemode: int | None = None) -> object:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, bool):
        return value
    if isinstance(value, (int,)):
        return value
    if isinstance(value, float):
        if datemode is not None and value > 20000:
            try:
                dt_tuple = xlrd.xldate_as_tuple(value, datemode)
                if dt_tuple[:3] != (0, 0, 0):
                    return datetime(*dt_tuple[:3]).strftime("%Y-%m-%d")
            except Exception:
                pass
        if value.is_integer():
            return int(value)
        return value
    text = str(value).replace("\u3000", " ").strip()
    return text


def trim_table(rows: list[list[object]]) -> list[list[object]]:
    while rows and not any(cell not in ("", None) for cell in rows[-1]):
        rows.pop()
    max_len = 0
    for row in rows:
        for idx, cell in enumerate(row, start=1):
            if cell not in ("", None):
                max_len = max(max_len, idx)
    if max_len == 0:
        return []
    return [row[:max_len] for row in rows]


def load_xlsx(path: Path) -> dict[str, object]:
    wb = openpyxl.load_workbook(path, data_only=True)
    sheets = []
    for ws in wb.worksheets:
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append([normalize_value(cell) for cell in row])
        rows = trim_table(rows)
        sheets.append(
            {
                "name": ws.title.strip(),
                "row_count": len(rows),
                "column_count": max((len(r) for r in rows), default=0),
                "rows": rows,
            }
        )
    return {"sheet_count": len(sheets), "sheets": sheets}


def load_xls(path: Path) -> dict[str, object]:
    book = xlrd.open_workbook(path)
    sheets = []
    for name in book.sheet_names():
        sh = book.sheet_by_name(name)
        rows = []
        for r in range(sh.nrows):
            values = [normalize_value(sh.cell_value(r, c), datemode=book.datemode) for c in range(sh.ncols)]
            rows.append(values)
        rows = trim_table(rows)
        sheets.append(
            {
                "name": name.strip(),
                "row_count": len(rows),
                "column_count": max((len(r) for r in rows), default=0),
                "rows": rows,
            }
        )
    return {"sheet_count": len(sheets), "sheets": sheets}


def summarize_management_plan(payload: dict[str, object]) -> dict[str, object]:
    sheets = payload["sheets"]
    action_totals = {
        "評価": {"planned": 0, "actual": 0, "complete": 0, "pending": 0},
        "QMS開発": {"planned": 0, "actual": 0, "complete": 0, "pending": 0},
        "監査": {"planned": 0, "actual": 0, "complete": 0, "pending": 0},
        "供給者開発": {"planned": 0, "actual": 0, "complete": 0, "pending": 0},
    }
    suppliers = []

    for sheet in sheets:
        rows = sheet["rows"]
        if len(rows) < 18:
            continue
        timeline = rows[9][10:] if len(rows) > 9 else []
        row_index = 10
        while row_index + 7 < len(rows):
            lead = rows[row_index]
            if not is_filled(lead[0]) and not is_filled(lead[1]):
                row_index += 1
                continue
            supplier_name = str(lead[1]).strip()
            if not supplier_name:
                row_index += 8
                continue
            supplier_summary = {
                "sheet": sheet["name"],
                "no": lead[0],
                "supplier_name": supplier_name,
                "status_mark": lead[4],
                "actions": [],
            }
            action_pairs = [
                ("評価", rows[row_index], rows[row_index + 1]),
                ("QMS開発", rows[row_index + 2], rows[row_index + 3]),
                ("監査", rows[row_index + 4], rows[row_index + 5]),
                ("供給者開発", rows[row_index + 6], rows[row_index + 7]),
            ]
            for action_name, plan_row, actual_row in action_pairs:
                plan_cells = plan_row[10:]
                actual_cells = actual_row[10:]
                planned_labels = [str(timeline[i]).strip() for i, cell in enumerate(plan_cells) if i < len(timeline) and is_filled(cell)]
                actual_labels = [str(timeline[i]).strip() for i, cell in enumerate(actual_cells) if i < len(timeline) and is_filled(cell)]
                planned_count = len(planned_labels)
                actual_count = len(actual_labels)
                action_totals[action_name]["planned"] += planned_count
                action_totals[action_name]["actual"] += actual_count
                if planned_count > 0 and actual_count >= planned_count:
                    action_totals[action_name]["complete"] += 1
                elif planned_count > 0:
                    action_totals[action_name]["pending"] += 1
                supplier_summary["actions"].append(
                    {
                        "name": action_name,
                        "planned_count": planned_count,
                        "actual_count": actual_count,
                        "planned_labels": planned_labels,
                        "actual_labels": actual_labels,
                        "complete": planned_count > 0 and actual_count >= planned_count,
                    }
                )
            suppliers.append(supplier_summary)
            row_index += 8

    return {
        "total_suppliers": len(suppliers),
        "action_totals": action_totals,
        "suppliers": suppliers,
    }


def summarize_evaluation(payload: dict[str, object]) -> dict[str, object]:
    sheet = next((s for s in payload["sheets"] if s["name"] == "評価票Ⅱ供給者"), payload["sheets"][0])
    rows = sheet["rows"]
    entries = []
    rank_counts: dict[str, int] = {}
    planned = executed = pending = 0

    for row in rows[8:]:
        supplier_name = str(row[0]).strip() if len(row) > 0 else ""
        method = str(row[3]).strip() if len(row) > 3 else ""
        if not supplier_name or not method:
            continue
        plan_month = row[1] if len(row) > 1 else ""
        actual_date = row[2] if len(row) > 2 else ""
        score = row[5] if len(row) > 5 else ""
        complaint_count = row[4] if len(row) > 4 else ""
        evaluation_result = str(score).strip()
        if is_filled(plan_month):
          planned += 1
        if is_filled(actual_date):
          executed += 1
        if is_filled(plan_month) and not is_filled(actual_date):
          pending += 1
        if evaluation_result:
            rank_counts[evaluation_result] = rank_counts.get(evaluation_result, 0) + 1
        entries.append(
            {
                "supplier_name": supplier_name,
                "plan_month": plan_month,
                "actual_date": actual_date,
                "method": method,
                "complaint_count": complaint_count,
                "evaluation_result": evaluation_result,
                "iso_status": row[10] if len(row) > 10 else "",
                "continue_trade": row[11] if len(row) > 11 else "",
                "stop_trade": row[12] if len(row) > 12 else "",
            }
        )

    return {
        "sheet_name": sheet["name"],
        "total_rows": len(entries),
        "planned_count": planned,
        "executed_count": executed,
        "pending_count": pending,
        "rank_counts": rank_counts,
        "entries": entries,
    }


def export_target(target: WorkbookTarget) -> dict[str, object]:
    source_path = SOURCE_DIR / target.source_name
    output_path = OUTPUT_DIR / target.output_name
    if target.kind == "xlsx":
        payload = load_xlsx(source_path)
    else:
        payload = load_xls(source_path)

    payload.update(
        {
            "title": target.title,
            "source_name": target.source_name,
            "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        }
    )
    payload["summary"] = summarize_evaluation(payload) if target.output_name == "supplier_evaluation_2025.json" else summarize_management_plan(payload)
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "source": str(source_path),
        "output": str(output_path),
        "sheet_count": payload["sheet_count"],
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    exports = [export_target(target) for target in TARGETS]
    status = {
        "step": "completed",
        "exports": exports,
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
