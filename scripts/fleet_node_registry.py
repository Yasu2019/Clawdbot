# -*- coding: utf-8 -*-
"""Load fleet node endpoints from data/workspace/*_node_registry.json."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"


def load_registry(node_id: str) -> dict[str, Any]:
    path = WORKSPACE / f"{node_id}_node_registry.json"
    if not path.exists():
        raise FileNotFoundError(f"missing registry: {path}")
    return json.loads(path.read_text(encoding="utf-8-sig"))


def g3_n8n_base() -> str:
    reg = load_registry("g3")
    return f"http://{reg['tailscale_ip']}:{reg.get('n8n_port', 5679)}"


def g3_endpoints() -> dict[str, str]:
    reg = load_registry("g3")
    base = g3_n8n_base()
    return {
        "bridge": reg.get("exec_bridge") or f"{base}/webhook/exec_bridge",
        "n8n_base": base,
        "n8n_healthz": reg.get("n8n_healthz") or f"{base}/healthz",
        "iatf": reg.get("iatf_url") or f"http://{reg['tailscale_ip']}:{reg.get('iatf_port', 3004)}",
        "iatf_dir": reg.get("iatf_dir") or r"C:\hermes_openclaw_fullpack\n8n_test\data\work\iatf_system",
        "sat_dir": reg.get("install_root") or r"C:\clawstack_satellite",
        "node_name": reg.get("node_name") or "G3",
    }


def dynabook_endpoints() -> dict[str, Any]:
    reg = load_registry("dynabook")
    ip = (reg.get("tailscale_ip") or reg.get("lan_ip") or "").strip()
    port = int(reg.get("job_worker_port") or 5683)
    base_url = (reg.get("job_worker_url") or "").strip().rstrip("/")
    if not base_url and ip:
        base_url = f"http://{ip}:{port}"
    return {
        "node_id": "dynabook",
        "node_name": reg.get("node_name") or "Dynabook",
        "ip": ip,
        "port": port,
        "job_worker_url": base_url,
        "job_worker_healthz": f"{base_url}/healthz" if base_url else "",
        "install_root": reg.get("install_root") or r"C:\dynabook_satellite",
        "cae_repo_root": reg.get("cae_repo_root") or r"C:\dynabook_usb_pack",
        "profile": reg.get("profile") or "light",
        "worker_flags": reg.get("worker_flags") or {},
        "status": reg.get("status") or "unknown",
    }


def thinkpad_endpoints() -> dict[str, Any]:
    reg = load_registry("thinkpad")
    ip = (reg.get("tailscale_ip") or reg.get("lan_ip") or "").strip()
    return {
        "node_id": "thinkpad",
        "node_name": reg.get("node_name") or "ThinkPad L590",
        "hostname": reg.get("hostname") or "",
        "ip": ip,
        "ssh_user": reg.get("ssh_user") or "yasu",
        "ssh_host": reg.get("ssh_host") or ip,
        "ssh_key_path": reg.get("ssh_key_path") or "",
        "profile": reg.get("profile") or "medium_ssh",
        "job_transport": reg.get("job_transport") or "ssh",
        "allowed_workloads": reg.get("allowed_workloads") or [],
        "blocked_workloads": reg.get("blocked_workloads") or [],
        "status": reg.get("status") or "unknown",
    }
