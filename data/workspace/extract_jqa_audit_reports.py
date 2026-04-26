from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import fitz


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
REPORT_ROOT = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "審査報告書"
OUTPUT_PATH = ROOT / "iatf_system" / "db" / "jqa_audit_reports.json"
STATUS_PATH = ROOT / "data" / "workspace" / "jqa_audit_reports_status.json"

DATE_RE = re.compile(r"^\d{2}\.[A-Za-z]{3}\.\d{4}$")
NC_ID_RE = re.compile(r"^[A-Z]{1,4}-\d+$")
CLAUSE_RE = re.compile(r"^\d+(?:\.\d+)+$|^\.\d+$")


@dataclass
class ReportFile:
    source_kind: str
    source_path: str
    display_name: str
    pdf_name: str
    pdf_bytes: bytes


def iter_report_files() -> list[ReportFile]:
    reports: list[ReportFile] = []
    for path in REPORT_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() == ".pdf" and "NcManagement" in path.name:
            reports.append(
                ReportFile(
                    source_kind="pdf",
                    source_path=str(path),
                    display_name=path.name,
                    pdf_name=path.name,
                    pdf_bytes=path.read_bytes(),
                )
            )
        elif path.is_file() and path.suffix.lower() == ".zip":
            with zipfile.ZipFile(path) as zf:
                for member in zf.infolist():
                    if member.is_dir():
                        continue
                    name = Path(member.filename).name
                    if "NcManagement" not in name or not name.lower().endswith(".pdf"):
                        continue
                    reports.append(
                        ReportFile(
                            source_kind="zip",
                            source_path=str(path),
                            display_name=path.name,
                            pdf_name=name,
                            pdf_bytes=zf.read(member),
                        )
                    )
    return reports


def extract_text(pdf_bytes: bytes, max_pages: int = 6) -> str:
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    return "\n".join(page.get_text() for page in doc[:max_pages])


def compact_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def normalize_clause(parts: list[str]) -> str:
    clause = ""
    for part in parts:
        if part.startswith(".") and clause:
            clause += part
        elif CLAUSE_RE.match(part):
            clause = part
    return clause


def parse_entries(text: str) -> list[dict[str, object]]:
    lines = compact_lines(text)
    entries: list[dict[str, object]] = []
    i = 0
    while i < len(lines) - 2:
        if not lines[i].isdigit() or not NC_ID_RE.match(lines[i + 1]):
            i += 1
            continue

        nc_no = lines[i]
        nc_id = lines[i + 1]
        j = i + 2
        clause_candidates: list[str] = []
        classification = ""
        due_date = ""
        process = ""

        while j < len(lines):
            line = lines[j]
            if DATE_RE.match(line):
                due_date = line
                process = lines[j + 1] if j + 1 < len(lines) else ""
                break
            lowered = line.lower()
            if lowered in {"minor", "major"} or "マイナー" in line or "メジャー" in line:
                classification = line
            if CLAUSE_RE.match(line):
                clause_candidates.append(line)
            j += 1

        if due_date:
            entries.append(
                {
                    "nc_no": nc_no,
                    "nc_id": nc_id,
                    "clause": normalize_clause(clause_candidates),
                    "classification": classification,
                    "due_date": due_date,
                    "process": process,
                }
            )
            i = j + 1
        else:
            i += 1
    return entries


def parse_year(date_text: str, fallback_name: str) -> int | None:
    try:
        return datetime.strptime(date_text, "%d.%b.%Y").year
    except Exception:
        m = re.search(r"(20\d{2})", fallback_name)
        return int(m.group(1)) if m else None


def summarize_reports(report_files: list[ReportFile]) -> dict[str, object]:
    reports: list[dict[str, object]] = []
    year_map: dict[int, dict[str, object]] = {}

    for report in report_files:
        text = extract_text(report.pdf_bytes)
        entries = parse_entries(text)
        if not entries:
            continue

        year = parse_year(entries[0]["due_date"], report.pdf_name)
        process_counts: dict[str, int] = {}
        for entry in entries:
            process = str(entry.get("process", "")).strip()
            process_counts[process] = process_counts.get(process, 0) + 1

        report_payload = {
            "source_kind": report.source_kind,
            "source_path": report.source_path,
            "display_name": report.display_name,
            "pdf_name": report.pdf_name,
            "year": year,
            "entry_count": len(entries),
            "entries": entries,
            "process_counts": process_counts,
        }
        reports.append(report_payload)

        if year is None:
            continue
        bucket = year_map.setdefault(year, {"year": year, "finding_count": 0, "process_counts": {}})
        bucket["finding_count"] += len(entries)
        for process, count in process_counts.items():
            bucket["process_counts"][process] = bucket["process_counts"].get(process, 0) + count

    return {
        "generated_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "report_count": len(reports),
        "reports": reports,
        "years": sorted(year_map.values(), key=lambda item: item["year"]),
    }


def main() -> None:
    report_files = iter_report_files()
    payload = summarize_reports(report_files)
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    status = {
        "step": "completed",
        "report_count": payload["report_count"],
        "years": [item["year"] for item in payload["years"]],
        "output_path": str(OUTPUT_PATH),
        "finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
