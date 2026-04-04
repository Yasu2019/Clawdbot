#!/usr/bin/env python3
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
INPUT_PATH = WORKSPACE / "paperless_pdf_benchmark.json"
STATUS_PATH = WORKSPACE / "paperless_pdf_benchmark_status.json"


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def main() -> None:
    try:
        payload = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    except Exception:
        payload = {"items": []}

    items = payload.get("items") or []
    reviewed = [item for item in items if item.get("text_acceptable") is not None]
    pass_text = sum(1 for item in reviewed if item.get("text_acceptable") is True)
    pass_figure = sum(1 for item in reviewed if item.get("figure_summary_useful") is True)
    asset_present = sum(1 for item in reviewed if item.get("figure_asset_present") is True)
    pass_caption = sum(1 for item in reviewed if item.get("caption_acceptable") is True)
    pass_table = sum(1 for item in reviewed if item.get("table_detection_acceptable") is True)

    status = {
        "generatedAt": now_jst_text(),
        "service": "paperless_pdf_benchmark",
        "sampleCount": len(items),
        "reviewedCount": len(reviewed),
        "textAcceptableRate": round((pass_text / len(reviewed)) * 100.0, 1) if reviewed else None,
        "figureSummaryUsefulRate": round((pass_figure / len(reviewed)) * 100.0, 1) if reviewed else None,
        "figureAssetPresentRate": round((asset_present / len(reviewed)) * 100.0, 1) if reviewed else None,
        "captionAcceptableRate": round((pass_caption / len(reviewed)) * 100.0, 1) if reviewed else None,
        "tableDetectionAcceptableRate": round((pass_table / len(reviewed)) * 100.0, 1) if reviewed else None,
        "ready": bool(reviewed),
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(status, ensure_ascii=False))


if __name__ == "__main__":
    main()
