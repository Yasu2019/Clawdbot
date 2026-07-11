# -*- coding: utf-8 -*-
"""Read-only MCP readiness bridge for Moldflow Insight 2010 on Dynabook."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
import os
import platform
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from mcp.server.fastmcp import FastMCP


BRIDGE_VERSION = "0.1.0"
PROG_IDS = ("synergy.Synergy", "Synergy.Synergy", "synergy.Synergy.2010")
ROOT = Path(__file__).resolve().parent
PROBE_SCRIPT = ROOT / "check_synergy_com.vbs"
DEFAULT_WORK_ROOT = Path(os.environ.get("MOLDFLOW_WORK_ROOT", r"G:\moldflow_bridge\work"))

mcp = FastMCP("dynabook-moldflow-readiness")


def _run(command: list[str], timeout_sec: int = 30) -> dict[str, Any]:
    """Run a bounded local diagnostic command without invoking a shell."""
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(1, min(int(timeout_sec), 60)),
            check=False,
        )
        return {
            "ok": completed.returncode == 0,
            "exit_code": completed.returncode,
            "stdout": completed.stdout[-4000:],
            "stderr": completed.stderr[-2000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {"ok": False, "exit_code": 124, "error": f"timeout after {exc.timeout}s"}
    except OSError as exc:
        return {"ok": False, "exit_code": 1, "error": str(exc)}


def _cscript_path(bitness: int) -> Path:
    windows = Path(os.environ.get("WINDIR", r"C:\Windows"))
    folder = "SysWOW64" if bitness == 32 else "System32"
    return windows / folder / "cscript.exe"


def collect_status() -> dict[str, Any]:
    work_drive = Path(DEFAULT_WORK_ROOT.anchor) if DEFAULT_WORK_ROOT.anchor else DEFAULT_WORK_ROOT
    disk = shutil.disk_usage(work_drive) if work_drive.exists() else None
    return {
        "bridge_version": BRIDGE_VERSION,
        "mode": "read_only_preflight",
        "analysis_enabled": False,
        "hostname": platform.node(),
        "python_bitness": platform.architecture()[0],
        "work_root": str(DEFAULT_WORK_ROOT),
        "work_root_exists": DEFAULT_WORK_ROOT.exists(),
        "work_drive_free_gb": round(disk.free / (1024 ** 3), 2) if disk else None,
        "probe_script_exists": PROBE_SCRIPT.exists(),
        "cscript_64_exists": _cscript_path(64).exists(),
        "cscript_32_exists": _cscript_path(32).exists(),
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
    }


@mcp.tool()
def moldflow_bridge_status() -> str:
    """Return bridge and host readiness without starting or controlling Moldflow."""
    return json.dumps(collect_status(), ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_probe_com(bitness: int = 32, timeout_sec: int = 30) -> str:
    """Probe the registered Synergy COM object with bounded 32/64-bit cscript.

    This may instantiate the COM object, but it never creates or runs a study.
    Moldflow/Synergy may need to be started interactively before this returns OK.
    """
    if bitness not in (32, 64):
        return json.dumps({"ok": False, "error": "bitness must be 32 or 64"})
    if not PROBE_SCRIPT.exists():
        return json.dumps({"ok": False, "error": f"missing {PROBE_SCRIPT}"})
    cscript = _cscript_path(bitness)
    if not cscript.exists():
        return json.dumps({"ok": False, "error": f"missing {cscript}"})
    result = _run([str(cscript), "//nologo", str(PROBE_SCRIPT)], timeout_sec)
    result["bitness"] = bitness
    result["analysis_started"] = False
    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool()
def moldflow_readiness_gate() -> str:
    """Evaluate whether the bridge may advance to analysis-tool implementation."""
    status = collect_status()
    blockers = []
    if not status["probe_script_exists"]:
        blockers.append("COM probe script is missing")
    if not status["cscript_32_exists"]:
        blockers.append("32-bit cscript is missing")
    if not status["work_root_exists"]:
        blockers.append("G: work root is not initialized")
    return json.dumps(
        {
            "ready_for_mcp_preflight": not blockers,
            "ready_for_analysis": False,
            "blockers": blockers + ["Synergy COM probe has not passed in this process"],
            "next_action": "Start Moldflow Synergy, then call moldflow_probe_com with bitness=32",
        },
        ensure_ascii=False,
        indent=2,
    )


def main() -> int:
    host = os.environ.get("MOLDFLOW_MCP_HOST", "127.0.0.1")
    port = int(os.environ.get("MOLDFLOW_MCP_PORT", "8765"))
    DEFAULT_WORK_ROOT.mkdir(parents=True, exist_ok=True)
    mcp.settings.host = host
    mcp.settings.port = port
    print(f"[moldflow-mcp] host={host} port={port} mode=read_only_preflight", flush=True)
    mcp.run(transport="streamable-http")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
