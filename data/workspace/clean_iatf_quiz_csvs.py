from __future__ import annotations

import csv
import json
from pathlib import Path


REQUIRED = ["kajyou", "mondai_no", "rev", "mondai", "mondai_a", "mondai_b", "mondai_c", "seikai", "kaisetsu"]


def normalize_header(value: str) -> str:
    return value.strip().lower().replace("\ufeff", "")


def should_keep(row: dict[str, str]) -> tuple[bool, list[str]]:
    issues: list[str] = []
    if not row.get("mondai", "").strip():
        issues.append("blank_question")
    if not row.get("kaisetsu", "").strip():
        issues.append("blank_explanation")
    if row.get("seikai", "").strip().lower() not in {"a", "b", "c"}:
        issues.append("invalid_seikai")
    return not issues, issues


def clean_csv(path: Path) -> dict:
    with path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames is None:
            raise ValueError("CSV has no header row")
        headers = [normalize_header(h or "") for h in reader.fieldnames]
        missing = [h for h in REQUIRED if h not in headers]
        if missing:
            raise ValueError(f"Missing headers: {', '.join(missing)}")

        rows = []
        dropped = []
        for idx, raw in enumerate(reader, start=2):
            row = {normalize_header(k or ""): (v or "").strip() for k, v in raw.items()}
            keep, issues = should_keep(row)
            if keep:
                rows.append({key: row.get(key, "") for key in REQUIRED})
            else:
                dropped.append({"row_number": idx, "issues": issues})

    out_path = path.with_name(f"{path.stem}_cleaned{path.suffix}")
    with out_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED)
        writer.writeheader()
        writer.writerows(rows)

    report = {
        "source": str(path),
        "output": str(out_path),
        "kept_rows": len(rows),
        "dropped_rows": len(dropped),
        "dropped": dropped[:50],
    }
    report_path = path.with_name(f"{path.stem}_clean_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    report["report"] = str(report_path)
    return report


def main() -> None:
    base = Path(r"D:\Clawdbot_Docker_20260125\iatf_system\db\record")
    targets = [
        base / "additional_testmondai.csv",
        base / "6.1.2.1_additional_testmondai.csv",
    ]
    reports = [clean_csv(path) for path in targets]
    out = Path(r"D:\Clawdbot_Docker_20260125\data\workspace\iatf_testmondai_cleaning_report_20260321.json")
    out.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)


if __name__ == "__main__":
    main()
