from __future__ import annotations

import csv
import json
from pathlib import Path


def main() -> None:
    base = Path(__file__).parent
    report_path = base.joinpath("iatf_testmondai_quality_report_20260321.json")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    bad_files = {file["path"]: {issue["row_number"] for issue in file["issues"] if issue["type"] in ("mojibake_suspected", "missing_rev", "invalid_seikai")} for file in report["files"]}

    out_reports = []
    for rel_path, drop_rows in bad_files.items():
        if not drop_rows:
            continue
        source = Path(r"D:\Clawdbot_Docker_20260125\iatf_system").joinpath(rel_path)
        if not source.exists():
            continue
        out_path = source.with_name(f"{source.stem}_mojibake_cleaned{source.suffix}")
        dropped = []

        with source.open("r", encoding="utf-8", errors="replace", newline="") as fp:
            reader = list(csv.reader(fp))
        header = reader[0]
        rows = []
        for index, row in enumerate(reader[1:], start=2):
            if index in drop_rows:
                dropped.append(index)
                continue
            rows.append(row)

        with out_path.open("w", encoding="utf-8", newline="") as fp:
            writer = csv.writer(fp)
            writer.writerow(header)
            writer.writerows(rows)

        out_report = {
            "source": str(source),
            "output": str(out_path),
            "dropped_rows": len(dropped),
            "dropped_row_numbers": dropped,
        }
        report_path = source.with_name(f"{source.stem}_mojibake_clean_report.json")
        report_path.write_text(json.dumps(out_report, ensure_ascii=False, indent=2), encoding="utf-8")
        out_report["report"] = str(report_path)
        out_reports.append(out_report)
        print(f"Cleaned {source.name}: dropped {len(dropped)} rows")

    summary = base.joinpath("iatf_testmondai_mojibake_clean_summary.json")
    summary.write_text(json.dumps(out_reports, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Summary written to {summary}")


if __name__ == "__main__":
    main()
