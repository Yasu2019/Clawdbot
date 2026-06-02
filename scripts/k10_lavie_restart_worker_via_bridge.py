# -*- coding: utf-8 -*-
"""Restart LAVIE job worker via n8n exec_bridge (no docker compose down)."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ip", default="")
    parser.add_argument("--port", type=int, default=5679)
    args = parser.parse_args()

    cfg = router.load_config()
    ip = args.ip or (cfg.get("lavie") or {}).get("ip") or "100.87.244.46"
    url = f"http://{ip}:{args.port}/webhook/exec_bridge"

    ps_cmd = (
        "powershell -NoProfile -ExecutionPolicy Bypass -File "
        "C:\\lavie_usb_pack\\scripts\\lavie_start_job_worker.ps1 "
        "-RepoRoot C:\\lavie_usb_pack -InstallRoot C:\\clawstack_satellite"
    )
    pre = (
        "powershell -NoProfile -Command "
        "\"Get-NetTCPConnection -LocalPort 5680 -State Listen -EA SilentlyContinue | "
        "ForEach-Object { $p=Get-Process -Id $_.OwningProcess -EA SilentlyContinue; "
        "if ($p -and $p.ProcessName -match 'python') { Stop-Process -Id $p.Id -Force } }\""
    )

    with httpx.Client(timeout=120) as client:
        print("[bridge] stop old worker listener...")
        r0 = client.post(url, json={"cmd": pre})
        print(r0.status_code, (r0.text or "")[:400])

        print("[bridge] start lavie_start_job_worker.ps1...")
        r1 = client.post(url, json={"cmd": ps_cmd})
        print(r1.status_code, (r1.text or "")[:800])

    import time

    time.sleep(8)
    import k10_satellite_dispatch as sjp

    ok, detail = sjp.probe_worker(
        sjp.worker_base_url(sjp.load_node("lavie")), sjp.load_token()
    )
    print(f"probe ok={ok} {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
