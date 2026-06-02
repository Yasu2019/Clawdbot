# -*- coding: utf-8 -*-
"""Start LAVIE SJP worker in python:3.11-slim via exec_bridge (no compose down / no FEM stop)."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import json
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]


def load_token() -> str:
    for line in (ROOT / ".env").read_text(encoding="utf-8", errors="replace").splitlines():
        if line.strip().startswith("SATELLITE_JOB_TOKEN="):
            return line.split("=", 1)[1].strip().strip('"').strip("'")
    raise RuntimeError("SATELLITE_JOB_TOKEN missing in .env")


def main() -> int:
    import cae_workload_router as router

    cfg = router.load_config()
    ip = (cfg.get("lavie") or {}).get("ip") or "100.87.244.46"
    url = f"http://{ip}:5679/webhook/exec_bridge"
    token = load_token()

    rm = "docker rm -f lavie-sjp-worker-rescue 2>nul || true"
    run = (
        "docker run -d --name lavie-sjp-worker-rescue --restart unless-stopped "
        "-p 5680:5680 "
        "-v /var/run/docker.sock:/var/run/docker.sock "
        "-v /c/lavie_usb_pack:/repo "
        "-v /e/clawstack_satellite/data/work/jobs:/jobs "
        "-e SATELLITE_JOB_TOKEN=" + token + " "
        "-e SATELLITE_NODE_ID=lavie "
        "-e SATELLITE_JOBS_ROOT=/jobs "
        "-e SATELLITE_REPO_ROOT=/repo "
        "-e CAE_TE_WORKSPACE=/e/clawstack_satellite/data/work/cae_te_workspace "
        "-w /repo/scripts python:3.11-slim "
        "bash -lc \"pip install -q httpx pyyaml numpy && "
        "python lavie_job_worker.py --bind 0.0.0.0 --port 5680 --host lavie --jobs-root /jobs\""
    )

    with httpx.Client(timeout=180) as client:
        print("[rescue] remove old container...")
        r0 = client.post(url, json={"cmd": rm})
        print(r0.status_code, (r0.text or "")[:300])
        print("[rescue] start worker container...")
        r1 = client.post(url, json={"cmd": run})
        print(r1.status_code, (r1.text or "")[:800])
        if r1.status_code != 200:
            return 1
        body = r1.json()
        if body.get("exitCode", 1) != 0:
            print("[NG] docker run failed", file=sys.stderr)
            return 1

    import time

    time.sleep(12)
    import k10_satellite_dispatch as sjp

    ok, detail = sjp.probe_worker(
        sjp.worker_base_url(sjp.load_node("lavie")), sjp.load_token()
    )
    print(f"probe ok={ok} {detail}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
