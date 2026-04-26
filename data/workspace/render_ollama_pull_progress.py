from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path


def iso_now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat()


def discover_workspace() -> Path:
    for path in [Path("E:/ClawstackData/workspace"), Path("D:/Clawdbot_Docker_20260125/data/workspace")]:
        if path.exists():
            return path
    raise FileNotFoundError("Workspace not found.")


WORKSPACE = discover_workspace()
STATUS_PATH = WORKSPACE / "ollama_pull_status.json"
SUMMARY_JSON = WORKSPACE / "ollama_pull_progress_summary.json"
SUMMARY_MD = WORKSPACE / "ollama_pull_progress_summary.md"

PERCENT_RE = re.compile(r"(\d{1,3})%")
SIZE_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*GB/([0-9]+(?:\.[0-9]+)?)\s*GB")
SPEED_RE = re.compile(r"([0-9]+(?:\.[0-9]+)?)\s*MB/s")
ETA_RE = re.compile(r"(\d+m\d+s)")


def main() -> int:
    raw = json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    last = str(raw.get("lastOutput", ""))

    percent = None
    downloaded_gb = None
    total_gb = None
    speed_mbps = None
    eta = None

    if match := PERCENT_RE.search(last):
        percent = int(match.group(1))
    if match := SIZE_RE.search(last):
        downloaded_gb = float(match.group(1))
        total_gb = float(match.group(2))
    if match := SPEED_RE.search(last):
        speed_mbps = float(match.group(1))
    if match := ETA_RE.search(last):
        eta = match.group(1)

    summary = {
        "updatedAt": iso_now(),
        "model": raw.get("model"),
        "state": raw.get("state"),
        "percent": percent,
        "downloadedGB": downloaded_gb,
        "totalGB": total_gb,
        "speedMBps": speed_mbps,
        "eta": eta,
        "startedAt": raw.get("startedAt"),
        "lastOutput": last,
        "sourceStatusPath": str(STATUS_PATH),
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Ollama Pull Progress",
        "",
        f"- Updated: `{summary['updatedAt']}`",
        f"- Model: `{summary['model']}`",
        f"- State: `{summary['state']}`",
        f"- Progress: `{percent if percent is not None else '--'}%`",
        f"- Downloaded: `{downloaded_gb if downloaded_gb is not None else '--'} / {total_gb if total_gb is not None else '--'} GB`",
        f"- Speed: `{speed_mbps if speed_mbps is not None else '--'} MB/s`",
        f"- ETA: `{eta or '--'}`",
        "",
        "## Raw Output",
        "",
        "```text",
        last,
        "```",
        "",
    ]
    SUMMARY_MD.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
