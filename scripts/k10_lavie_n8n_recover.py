# -*- coding: utf-8 -*-
"""Recover LAVIE n8n (:5679) + exec_bridge from K10 via job worker shell."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync_base


def probe_n8n_healthz(ip: str, port: int = 5679) -> tuple[bool, str]:
    url = f"http://{ip}:{port}/healthz"
    try:
        r = httpx.get(url, timeout=8)
        return r.status_code == 200, f"{url} status={r.status_code}"
    except Exception as exc:
        return False, f"{url} {exc}"


def probe_exec_bridge(ip: str, port: int = 5679) -> tuple[bool, str]:
    url = f"http://{ip}:{port}/webhook/exec_bridge"
    try:
        r = httpx.post(url, json={"cmd": "echo N8N_RECOVER_OK"}, timeout=30)
        ok = r.status_code == 200 and "N8N_RECOVER_OK" in r.text
        return ok, f"{url} status={r.status_code}"
    except Exception as exc:
        return False, f"{url} {exc}"


def lavie_ip(cfg: dict[str, Any]) -> str:
    lavie = cfg.get("lavie") or {}
    return (lavie.get("ip") or "").strip()


def restart_n8n_stack(node: str, token: str, install_root: str, timeout: int) -> dict[str, Any]:
    cmd = (
        f"powershell -NoProfile -ExecutionPolicy Bypass "
        f"-File C:\\lavie_usb_pack\\scripts\\lavie_n8n_restart.ps1 "
        f"-InstallRoot {install_root}"
    )
    print("[n8n-recover] queue docker compose restart on LAVIE...")
    return sync_base.dispatch_shell(node, cmd, timeout, token)


def deploy_exec_bridge(base_url: str) -> int:
    script = ROOT / "scripts" / "satellite_deploy_exec_bridge.py"
    proc = subprocess.run(
        [sys.executable, str(script), "--base-url", base_url],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    tail = (proc.stdout or "")[-1500:] + (proc.stderr or "")[-800:]
    print(tail)
    return proc.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description="Recover LAVIE n8n + exec_bridge from K10")
    parser.add_argument("--node", default="lavie")
    parser.add_argument("--install-root", default="C:\\clawstack_satellite")
    parser.add_argument("--wait-sec", type=int, default=60)
    parser.add_argument("--skip-restart", action="store_true")
    parser.add_argument("--skip-bridge-deploy", action="store_true")
    parser.add_argument("--skip-verify", action="store_true")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    cfg = router.load_config()
    ip = lavie_ip(cfg)
    if not ip:
        print("[NG] lavie.ip missing in cae_workload_router.yaml", file=sys.stderr)
        return 1
    port = int((cfg.get("lavie") or {}).get("port") or 5679)
    base_url = f"http://{ip}:{port}"

    worker_ok, worker_detail = router.probe_satellite_job_worker(cfg, args.node)
    if not worker_ok:
        print(f"[NG] LAVIE job worker offline: {worker_detail}", file=sys.stderr)
        return 1
    print(f"[OK] job worker online: {worker_detail}")

    token = sjp.load_token()
    if not args.skip_restart:
        result = restart_n8n_stack(args.node, token, args.install_root, args.timeout)
        stdout = result.get("stdout_tail") or ""
        exit_code = result.get("exit_code")
        if exit_code is None:
            exit_code = 1
        else:
            exit_code = int(exit_code)
        if result.get("status") != "ok" or exit_code != 0:
            print(f"[NG] n8n restart job failed: {result}", file=sys.stderr)
            return 1
        if "N8N_RESTART_OK" not in stdout:
            print(f"[WARN] restart stdout missing N8N_RESTART_OK: {stdout[:400]}")
        else:
            print(stdout.strip())

    print(f"[n8n-recover] waiting up to {args.wait_sec}s for n8n healthz...")
    deadline = time.time() + args.wait_sec
    n8n_ok = False
    while time.time() < deadline:
        n8n_ok, detail = probe_n8n_healthz(ip, port)
        if n8n_ok:
            print(f"[OK] n8n healthz: {detail}")
            break
        time.sleep(5)
        print(f"[..] {detail}")
    if not n8n_ok:
        print("[NG] n8n did not become healthy in time", file=sys.stderr)
        return 1

    if not args.skip_bridge_deploy:
        bridge_ok, bridge_detail = probe_exec_bridge(ip, port)
        if not bridge_ok:
            print(f"[n8n-recover] exec_bridge probe failed ({bridge_detail}); deploying workflow...")
            rc = deploy_exec_bridge(base_url)
            if rc != 0:
                print("[NG] satellite_deploy_exec_bridge failed", file=sys.stderr)
                return 1
            time.sleep(3)
            bridge_ok, bridge_detail = probe_exec_bridge(ip, port)
        if bridge_ok:
            print(f"[OK] exec_bridge: {bridge_detail}")
        else:
            print(f"[NG] exec_bridge still failing: {bridge_detail}", file=sys.stderr)
            return 1

    if not args.skip_verify:
        verify = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / "k10_verify_satellite_node.py"),
                "--node-id",
                args.node,
                "--ip",
                ip,
                "--port",
                str(port),
            ],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
        print((verify.stdout or "")[-2000:])
        if verify.returncode != 0:
            print((verify.stderr or "")[-1000:], file=sys.stderr)
            print("[NG] LAVIE n8n/exec_bridge verify FAIL", file=sys.stderr)
            return 1

    status_path = ROOT / "data" / "workspace" / f"{args.node}_node_verify_status.json"
    print(f"\nRESULT: PASS")
    print(f"status: {status_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
