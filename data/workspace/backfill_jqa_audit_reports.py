from __future__ import annotations

import base64
import json
import subprocess
import zipfile
from pathlib import Path

from update_history_utils import append_history_entry


ROOT = Path(r"D:\Clawdbot_Docker_20260125")
REPORT_ROOT = ROOT / "clawstack_v2" / "data" / "paperless" / "consume" / "審査報告書"
STATUS_PATH = ROOT / "data" / "workspace" / "backfill_jqa_audit_reports_status.json"

TARGETS = [
    {"container": "iatf_system_dev-web-1", "environment": "development"},
    {"container": "iatf_system-web-1", "environment": "production"},
]


def collect_reports() -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    for path in sorted(REPORT_ROOT.rglob("*")):
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix == ".pdf":
            items.append(
                {
                    "filename": path.name,
                    "base64": base64.b64encode(path.read_bytes()).decode("ascii"),
                    "source_path": str(path),
                }
            )
        elif suffix == ".zip":
            with zipfile.ZipFile(path) as zf:
                for info in zf.infolist():
                    if info.is_dir():
                        continue
                    member_name = Path(info.filename).name
                    if Path(member_name).suffix.lower() != ".pdf":
                        continue
                    items.append(
                        {
                            "filename": member_name,
                            "base64": base64.b64encode(zf.read(info)).decode("ascii"),
                            "source_path": f"{path}::{info.filename}",
                        }
                    )
    return items


def build_runner_script(payload: list[dict[str, str]]) -> str:
    payload_json = json.dumps(payload, ensure_ascii=False)
    payload_b64 = base64.b64encode(payload_json.encode("utf-8")).decode("ascii")
    return f"""
# encoding: UTF-8
require "json"
require "base64"
require "stringio"

class UploadedStub
  attr_reader :original_filename

  def initialize(original_filename, bytes)
    @original_filename = original_filename
    @bytes = bytes
  end

  def read
    @bytes
  end

  def rewind; end
end

payload = JSON.parse(Base64.decode64("{payload_b64}"))
files = payload.map do |item|
  UploadedStub.new(item.fetch("filename"), Base64.decode64(item.fetch("base64")))
end
result = JqaAuditReportIngestService.call(files: files, description: "JQA report backfill")
puts JSON.generate(result)
"""


def run_target(target: dict[str, str], payload: list[dict[str, str]]) -> dict[str, object]:
    command = [
        "docker",
        "exec",
        "-i",
        target["container"],
        "bundle",
        "exec",
        "rails",
        "runner",
        "-e",
        target["environment"],
        "-",
    ]
    completed = subprocess.run(
        command,
        input=build_runner_script(payload).encode("utf-8"),
        capture_output=True,
        check=False,
    )
    result: dict[str, object] = {
        "container": target["container"],
        "environment": target["environment"],
        "returncode": completed.returncode,
        "stdout": completed.stdout.decode("utf-8", errors="replace").strip(),
        "stderr": completed.stderr.decode("utf-8", errors="replace").strip(),
    }
    if completed.returncode == 0:
        try:
            result["parsed"] = json.loads(completed.stdout)
        except json.JSONDecodeError:
            pass
    return result


def main() -> None:
    payload = collect_reports()
    results = [run_target(target, payload) for target in TARGETS]
    status = {
        "report_count": len(payload),
        "reports": [{"filename": item["filename"], "source_path": item["source_path"]} for item in payload],
        "results": results,
    }
    STATUS_PATH.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    append_history_entry(
        {
            "type": "jqa_backfill",
            "title": "JQA audit reports backfilled",
            "source": str(REPORT_ROOT),
            "record_count": len(payload),
            "details": {
                "report_filenames": [item["filename"] for item in payload],
                "target_results": [
                    {
                        "container": item["container"],
                        "environment": item["environment"],
                        "returncode": item["returncode"],
                    }
                    for item in results
                ],
            },
        }
    )
    print(json.dumps(status, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
