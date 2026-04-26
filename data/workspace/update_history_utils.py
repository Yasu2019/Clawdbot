from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
HISTORY_PATH = ROOT / "iatf_system" / "db" / "update_history.json"


def _load_history() -> list[dict[str, Any]]:
    if not HISTORY_PATH.exists():
        return []
    try:
        return json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_history_entry(entry: dict[str, Any]) -> dict[str, Any]:
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = _load_history()
    normalized = {
        "recorded_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        **entry,
    }
    payload.append(normalized)
    HISTORY_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return normalized
