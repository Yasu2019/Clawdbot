from __future__ import annotations

import csv
import json
from pathlib import Path


def load_report(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def row_tuple(issue: dict) -> tuple:
    return (
        issue["path"],
        issue.get("kajyou", ""),
        issue.get("mondai_no", ""),
        issue["row_number"],
        issue["type"],
        issue["message"],
    )


def main() -> None:
    report_path = Path(__file__).parent.joinpath("iatf_testmondai_quality_report_20260321.json")
    out_path = Path(__file__).parent.joinpath("iatf_testmondai_quality_issues_20260321.csv")

    report = load_report(report_path)
    rows = [row_tuple(issue) for file in report["files"] for issue in file["issues"]]

    with out_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["path", "kajyou", "mondai_no", "row", "type", "message"])
        writer.writerows(rows)

    print(f"Written issue list: {out_path}")


if __name__ == "__main__":
    main()
