from __future__ import annotations

import json
import re
from pathlib import Path

import fitz
from openpyxl import load_workbook
from openpyxl.utils import get_column_letter


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
CONSUME_DIR = ROOT / "clawstack_v2" / "data" / "paperless" / "consume"
SOURCE_DIR = next(p for p in CONSUME_DIR.iterdir() if p.name.startswith("IATF") and 25104 in [ord(ch) for ch in p.name])
TEMPLATE_2024 = SOURCE_DIR / "プロセスの監視・測定記録_提出.xlsx"
PDF_YEAR_DIRS = {
    int(p.name): p
    for p in SOURCE_DIR.iterdir()
    if p.is_dir() and p.name.isdigit() and int(p.name) >= 2025
}
OUTPUT_JSON = ROOT / "iatf_system" / "db" / "process_monitoring_measurement.json"
MAX_TEMPLATE_COL = 24  # X列


TARGET_PATTERN = re.compile(r"(以上|以下|達成|件/年|件以上|以内|%/年|％/年|100%|１００％|0件/年|0件|1件/年|2件以下/年|4件/年)")
ACTUAL_PATTERN = re.compile(r"^(当月|内部監査|累計|校正計画|当月　|当月 )")
MONTH_PATTERN = re.compile(r"(20\d{2})年(\d{1,2})月度")
DATE_PATTERN = re.compile(r"作成日\s*[:：]\s*(\d{4}年\d{1,2}月\d{1,2}日)")


def normalize_cell(value):
    if value is None:
        return ""
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.4f}".rstrip("0").rstrip(".")
    return str(value).replace("\r\n", "\n").replace("\r", "\n")


def extract_2024():
    if not TEMPLATE_2024.exists():
        raise FileNotFoundError(f"Template not found: {TEMPLATE_2024}")

    wb = load_workbook(TEMPLATE_2024, data_only=True)
    ws = wb[wb.sheetnames[0]]
    max_col = min(ws.max_column, MAX_TEMPLATE_COL)

    covered = set()
    merged_ranges = []
    for merged in ws.merged_cells.ranges:
        min_col, min_row, merged_max_col, max_row = merged.bounds
        if min_col > MAX_TEMPLATE_COL:
            continue
        merged_max_col = min(merged_max_col, MAX_TEMPLATE_COL)
        merged_ranges.append(
            {
                "start_row": min_row,
                "start_col": min_col,
                "end_row": max_row,
                "end_col": merged_max_col,
                "rowspan": max_row - min_row + 1,
                "colspan": merged_max_col - min_col + 1,
            }
        )
        for row in range(min_row, max_row + 1):
            for col in range(min_col, merged_max_col + 1):
                if row == min_row and col == min_col:
                    continue
                covered.add((row, col))

    merged_lookup = {(m["start_row"], m["start_col"]): m for m in merged_ranges}
    rows = []
    for row_idx in range(1, ws.max_row + 1):
        row_cells = []
        for col_idx in range(1, max_col + 1):
            if (row_idx, col_idx) in covered:
                continue
            cell = ws.cell(row_idx, col_idx)
            merge = merged_lookup.get((row_idx, col_idx))
            row_cells.append(
                {
                    "col": col_idx,
                    "value": normalize_cell(cell.value),
                    "rowspan": merge["rowspan"] if merge else 1,
                    "colspan": merge["colspan"] if merge else 1,
                }
            )
        rows.append({"row": row_idx, "cells": row_cells})

    column_widths = []
    for col_idx in range(1, max_col + 1):
        letter = get_column_letter(col_idx)
        width = ws.column_dimensions[letter].width
        column_widths.append(width if width else 13)

    return {
        "source_file": TEMPLATE_2024.name,
        "sheet_name": ws.title,
        "max_row": ws.max_row,
        "max_col": max_col,
        "column_widths": column_widths,
        "rows": rows,
    }


def is_process_heading(line: str) -> bool:
    return "プロセス" in line and not line.startswith("品質又は")


def is_target_line(line: str) -> bool:
    return bool(TARGET_PATTERN.search(line))


def is_actual_line(line: str) -> bool:
    return bool(ACTUAL_PATTERN.search(line))


def extract_section_text(full_text: str, start_marker: str, end_marker: str | None) -> str:
    start = full_text.find(start_marker)
    if start == -1:
        return ""
    end = full_text.find(end_marker, start + len(start_marker)) if end_marker else -1
    return full_text[start:end if end != -1 else None].strip()


def parse_entries(lines: list[str]) -> list[dict]:
    entries = []
    current_process = ""
    i = 0
    while i < len(lines):
        line = lines[i]
        if line in {"Ⅰ", "Ⅱ", "Ⅲ", "Ⅳ", "Ⅴ"}:
            i += 1
            continue
        if is_process_heading(line):
            current_process = line
            i += 1
            continue

        matched = False
        for metric_span in (1, 2, 3):
            if i + metric_span + 1 >= len(lines):
                continue
            metric = "".join(lines[i : i + metric_span]).strip()
            target = lines[i + metric_span].strip()
            actual = lines[i + metric_span + 1].strip()
            if metric and is_target_line(target) and is_actual_line(actual):
                entries.append(
                    {
                        "process": current_process,
                        "metric": metric,
                        "target": target,
                        "actual": actual,
                    }
                )
                i += metric_span + 2
                matched = True
                break
        if not matched:
            i += 1
    return entries


def extract_year_pdf(pdf_path: Path, default_year: int):
    doc = fitz.open(pdf_path)
    full_text = "".join(page.get_text("text") for page in doc)
    lines = [line.strip() for line in full_text.splitlines() if line.strip()]

    month_match = MONTH_PATTERN.search(pdf_path.name) or MONTH_PATTERN.search(full_text)
    created_match = DATE_PATTERN.search(full_text)

    return {
        "source_file": pdf_path.name,
        "year": int(month_match.group(1)) if month_match else default_year,
        "month": int(month_match.group(2)) if month_match else None,
        "created_date": created_match.group(1) if created_match else "",
        "entries": parse_entries(lines),
        "observations": extract_section_text(full_text, "Ⅲ", "Ⅳ"),
        "next_actions": extract_section_text(full_text, "Ⅳ", "Ⅴ"),
        "adjustments": extract_section_text(full_text, "Ⅴ", None),
        "raw_preview": full_text[:2000],
    }


def extract_year(year: int):
    year_dir = PDF_YEAR_DIRS.get(year)
    if not year_dir:
        return []

    files = sorted(
        year_dir.glob("*.pdf"),
        key=lambda p: int(MONTH_PATTERN.search(p.name).group(2)) if MONTH_PATTERN.search(p.name) else 99,
    )
    return [extract_year_pdf(pdf, year) for pdf in files]


def main():
    payload = {
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "source_dir": str(SOURCE_DIR),
        "year_2024": extract_2024(),
    }
    for year in sorted(PDF_YEAR_DIRS):
        payload[f"year_{year}"] = extract_year(year)
    OUTPUT_JSON.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(OUTPUT_JSON)


if __name__ == "__main__":
    main()
