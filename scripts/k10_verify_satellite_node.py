# -*- coding: utf-8 -*-
"""Verify satellite node (K3/LAVIE) from K10."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx

ROOT = Path(__file__).resolve().parents[1]
K10_IP = "192.168.3.87"


def load_k10_bridge(satellite_ip: str = "") -> str:
    router_path = ROOT / "data" / "workspace" / "cae_workload_router.yaml"
    registry_path = ROOT / "data" / "workspace" / "lavie_node_registry.json"
    if registry_path.exists():
        try:
            reg = json.loads(registry_path.read_text(encoding="utf-8-sig"))
            bridge = (reg.get("k10_bridge") or "").strip()
            if bridge and not satellite_ip.startswith("100."):
                return bridge
        except Exception:
            pass
    if router_path.exists():
        try:
            import yaml

            cfg = yaml.safe_load(router_path.read_text(encoding="utf-8")) or {}
            k10 = cfg.get("k10") or {}
            ts_ip = (k10.get("tailscale_ip") or "").strip()
            if ts_ip and satellite_ip.startswith("100."):
                return f"http://{ts_ip}:5679/webhook/k10_exec_bridge"
            lan_ip = (k10.get("ip") or K10_IP).strip()
            return f"http://{lan_ip}:5679/webhook/k10_exec_bridge"
        except Exception:
            pass
    return f"http://{K10_IP}:5679/webhook/k10_exec_bridge"


def probe_bridge(base: str, label: str) -> bool:
    ok = True
    health = httpx.get(f"{base}/healthz", timeout=10)
    print(f"[{label} healthz] {health.status_code}")
    ok &= health.status_code == 200

    bridge_url = f"{base}/webhook/exec_bridge"
    echo = httpx.post(bridge_url, json={"cmd": f"echo {label}_BRIDGE_OK"}, timeout=30)
    print(f"[{label} exec_bridge echo] {echo.status_code}")
    ok &= echo.status_code == 200 and f"{label}_BRIDGE_OK" in echo.text

    docker = httpx.post(
        bridge_url,
        json={"cmd": "docker ps --format \"{{.Names}}|{{.Status}}\""},
        timeout=60,
    )
    print(f"[{label} exec_bridge docker] {docker.status_code}")
    if docker.status_code == 200:
        body = docker.json()
        print((body.get("stdout") or "")[:800])
        ok &= body.get("exitCode") == 0
    else:
        ok = False
    return ok


def probe_k10_from_satellite_worker(node_id: str, label: str, k10_bridge: str) -> bool:
    """Use job worker (:5680); LAVIE exec_bridge rejects powershell/curl in n8n workflow."""
    if str(ROOT / "scripts") not in sys.path:
        sys.path.insert(0, str(ROOT / "scripts"))
    import k10_satellite_dispatch as sjp
    import k10_sync_cae_experiments_to_lavie as sync

    payload = json.dumps({"cmd": f"echo K10_FROM_{label}"})
    payload_escaped = payload.replace('"', '\\"')
    cmd = (
        f'curl.exe -s -X POST -H "Content-Type: application/json" '
        f'-d "{payload_escaped}" "{k10_bridge}"'
    )
    try:
        token = sjp.load_token()
        result = sync.dispatch_shell(node_id, cmd, 90, token)
    except Exception as exc:
        print(f"[{label} -> K10 bridge] dispatch error: {exc}")
        return False
    exit_code = result.get("exit_code")
    if exit_code is None:
        exit_code = 1
    else:
        exit_code = int(exit_code)
    stdout = result.get("stdout_tail") or ""
    stderr = result.get("stderr_tail") or ""
    ok_dispatch = result.get("status") == "ok" and exit_code == 0
    print(f"[{label} -> K10 bridge via worker] status={result.get('status')} exit={exit_code}")
    print(stdout[:400])
    if stderr:
        print(f"stderr: {stderr[:200]}")
    if not ok_dispatch:
        return False
    if "K10_FROM_" in stdout:
        return True
    try:
        inner = json.loads(stdout)
        inner_stdout = inner.get("stdout") or ""
        return "K10_FROM_" in inner_stdout and inner.get("exitCode") == 0
    except json.JSONDecodeError:
        return "K10_FROM_" in stdout


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify satellite node from K10")
    parser.add_argument("--node-id", default="lavie", help="Node label for logs")
    parser.add_argument("--ip", required=True, help="Satellite LAN IP")
    parser.add_argument("--port", type=int, default=5679)
    parser.add_argument("--skip-k10-return", action="store_true")
    args = parser.parse_args()

    base = f"http://{args.ip}:{args.port}"
    satellite_bridge = f"{base}/webhook/exec_bridge"
    k10_bridge = load_k10_bridge(args.ip)

    ok = probe_bridge(base, args.node_id.upper())
    if not args.skip_k10_return:
        ok &= probe_k10_from_satellite_worker(args.node_id, args.node_id.upper(), k10_bridge)

    status = {
        "node_id": args.node_id,
        "ip": args.ip,
        "port": args.port,
        "base_url": base,
        "exec_bridge": satellite_bridge,
        "k10_bridge": k10_bridge,
        "ok": ok,
    }
    out = ROOT / "data" / "workspace" / f"{args.node_id}_node_verify_status.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
    print(f"status: {out}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
