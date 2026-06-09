# -*- coding: utf-8 -*-
"""Dispatch guarded allow-listed SSH jobs from K10 to the Ubuntu ThinkPad."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import subprocess
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
REGISTRY = WORKSPACE / "thinkpad_node_registry.json"
LOG_PATH = WORKSPACE / "thinkpad_ssh_job_log.jsonl"
JST = timezone(timedelta(hours=9))

JOB_COMMANDS = {
    "health_snapshot": "hostname; uptime; lscpu | grep -E 'Model name|CPU\\(s\\)|Core\\(s\\)|Thread'; free -h; df -h /",
    "document_parse_probe": "python3 --version; mkdir -p ~/clawstack_jobs/document_parse; echo ready > ~/clawstack_jobs/document_parse/status.txt; cat ~/clawstack_jobs/document_parse/status.txt",
    "rag_index_probe": "python3 --version; mkdir -p ~/clawstack_jobs/rag_index; echo ready > ~/clawstack_jobs/rag_index/status.txt; cat ~/clawstack_jobs/rag_index/status.txt",
    "qms_iatf_probe": "python3 --version; mkdir -p ~/clawstack_jobs/qms_iatf; echo ready > ~/clawstack_jobs/qms_iatf/status.txt; cat ~/clawstack_jobs/qms_iatf/status.txt",
    "dataset_download_probe": "mkdir -p ~/clawstack_jobs/dataset_download; df -h ~; echo ready",
    "cae_pregate_probe": "python3 --version; mkdir -p ~/clawstack_jobs/cae_pregate; echo dry_run_ready",
}


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def run_job(job_type: str, timeout: int) -> dict[str, Any]:
    if job_type not in JOB_COMMANDS:
        raise ValueError(f"unsupported job_type: {job_type}")
    reg = read_json(REGISTRY)
    ssh_host = reg.get("ssh_host") or reg.get("tailscale_ip")
    ssh_user = reg.get("ssh_user") or "yasu"
    key_path = reg.get("ssh_key_path") or str(Path.home() / ".ssh" / "id_ed25519")
    target = f"{ssh_user}@{ssh_host}"
    job_id = f"thinkpad-{job_type}-{uuid.uuid4().hex[:8]}"
    started = datetime.now(JST).isoformat()
    proc = subprocess.run(
        [
            "ssh",
            "-i",
            str(key_path),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "StrictHostKeyChecking=accept-new",
            target,
            "bash",
            "-lc",
            JOB_COMMANDS[job_type],
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )
    entry = {
        "job_id": job_id,
        "job_type": job_type,
        "node": "thinkpad",
        "target": target,
        "started_at": started,
        "finished_at": datetime.now(JST).isoformat(),
        "status": "ok" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "stdout_tail": proc.stdout[-2000:],
        "stderr_tail": proc.stderr[-2000:],
    }
    append_log(entry)
    return entry


def main() -> int:
    parser = argparse.ArgumentParser(description="Dispatch guarded SSH job to ThinkPad")
    parser.add_argument("--job-type", required=True, choices=sorted(JOB_COMMANDS))
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    entry = run_job(args.job_type, args.timeout)
    if args.json:
        print(json.dumps(entry, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] node=thinkpad job={entry['job_type']} status={entry['status']} id={entry['job_id']}")
    return 0 if entry["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
