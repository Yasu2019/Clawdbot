from __future__ import annotations

import json
from pathlib import Path

from update_history_utils import HISTORY_PATH, append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
STATUS_FILES = [
    ROOT / "data" / "workspace" / "iatf_seed_sync_status.json",
    ROOT / "data" / "workspace" / "backfill_jqa_audit_reports_status.json",
    ROOT / "data" / "workspace" / "manufacturing_design_zip_import_status.json",
]


def reset_history() -> None:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_PATH.write_text("[]", encoding="utf-8")


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    reset_history()

    seed_sync = load_json(STATUS_FILES[0])
    append_history_entry(
        {
            "type": "seed_sync",
            "title": "IATF seed assets synchronized from production",
            "source": seed_sync.get("source_container"),
            "record_count": seed_sync.get("record_count"),
            "details": {
                "host_attachedfile": seed_sync.get("host_attachedfile"),
                "host_documents": seed_sync.get("host_documents"),
                "missing_after_sync_count": seed_sync.get("missing_after_sync_count"),
            },
        }
    )

    jqa = load_json(STATUS_FILES[1])
    append_history_entry(
        {
            "type": "jqa_backfill",
            "title": "JQA audit reports backfilled",
            "source": "審査報告書",
            "record_count": jqa.get("report_count"),
            "details": {
                "report_filenames": [item.get("filename") for item in jqa.get("reports", [])],
                "result_count": len(jqa.get("results", [])),
            },
        }
    )

    design = load_json(STATUS_FILES[2])
    append_history_entry(
        {
            "type": "manufacturing_design_import",
            "title": "Manufacturing design ZIP imported",
            "source": design.get("zip_path"),
            "record_count": design.get("row_count"),
            "details": {
                "appended_count": design.get("appended_count"),
                "copied_count": design.get("copied_count"),
                "partnumbers": sorted({item.get("partnumber") for item in design.get("rows", []) if item.get("partnumber")}),
            },
        }
    )

    print(HISTORY_PATH.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
