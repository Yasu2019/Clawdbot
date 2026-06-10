# -*- coding: utf-8 -*-
"""Refresh Windows monitor_agent.py on a satellite job worker node."""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_satellite_dispatch as sjp


def build_refresh_command(k10_base: str) -> str:
    """Return a short command so older Windows nodes do not hit cmdline limits."""
    base = k10_base.rstrip("/")
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        "\"$ErrorActionPreference='Stop'; "
        "$p=Join-Path $env:TEMP 'refresh_monitor_agent_node.ps1'; "
        f"(New-Object System.Net.WebClient).DownloadFile('{base}/refresh_monitor_agent_node.ps1',$p); "
        f"powershell -NoProfile -ExecutionPolicy Bypass -File $p -K10Base '{base}'\""
    )


def refresh_node(node: str, k10_base: str, timeout: int) -> dict[str, Any]:
    token = sjp.load_token()
    info = sjp.load_node(node)
    base_url = sjp.worker_base_url(info)
    command = build_refresh_command(k10_base)
    job = {
        "job_id": f"refresh-monitor-{node}-{uuid.uuid4().hex[:8]}",
        "type": "shell",
        "timeout_sec": timeout,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    result = sjp.dispatch_job(base_url, token, job, timeout)
    sjp.append_log({"node": node, "base_url": base_url, "request": job, "result": result})
    return {"node": node, "base_url": base_url, "result": result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Refresh monitor_agent via satellite worker")
    parser.add_argument("--nodes", nargs="+", default=["red_lavie", "dynabook"])
    parser.add_argument("--k10-base", default="http://100.119.18.40:8123")
    parser.add_argument("--timeout", type=int, default=180)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    outputs = []
    ok = True
    for node in args.nodes:
        try:
            item = refresh_node(node, args.k10_base, args.timeout)
        except Exception as exc:
            item = {"node": node, "error": str(exc)}
            ok = False
        else:
            result = item.get("result") or {}
            stdout = result.get("stdout_tail") or ""
            if result.get("status") != "ok" or (
                "DIAGNOSTICS_READY" not in stdout and "DIAGNOSTICS_READY_ALT" not in stdout
            ):
                ok = False
        outputs.append(item)

    if args.json:
        print(json.dumps(outputs, ensure_ascii=False, indent=2))
    else:
        for item in outputs:
            result = item.get("result") or {}
            print(
                f"{item.get('node')}: status={result.get('status')} "
                f"exit={result.get('exit_code')} error={item.get('error') or result.get('error') or ''}"
            )
            tail = result.get("stdout_tail") or ""
            if tail:
                print(tail[-1200:])
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
