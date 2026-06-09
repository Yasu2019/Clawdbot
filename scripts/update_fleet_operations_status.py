# -*- coding: utf-8 -*-
"""Aggregate 24/7 fleet operations status for Portal (K10 / G3 / LAVIE / ThinkPad)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "workspace" / "fleet_operations_status.json"
JST = timezone(timedelta(hours=9))

from fleet_node_registry import g3_endpoints, dynabook_endpoints, thinkpad_endpoints, load_registry
import thinkpad_ssh_metrics

G3 = g3_endpoints()
G3_BRIDGE = G3["bridge"]
G3_IATF = G3["iatf"]
G3_N8N = G3["n8n_healthz"]

try:
    _lavie = load_registry("lavie")
    LAVIE_WORKER = f"{_lavie.get('job_worker_url', 'http://100.87.244.46:5680')}/healthz"
    LAVIE_N8N = f"http://{_lavie.get('lan_ip', '100.87.244.46')}:{_lavie.get('n8n_port', 5679)}/healthz"
except FileNotFoundError:
    LAVIE_WORKER = "http://100.87.244.46:5680/healthz"
    LAVIE_N8N = "http://100.87.244.46:5679/healthz"

try:
    _dynabook = dynabook_endpoints()
    DYNABOOK_WORKER = _dynabook.get("job_worker_healthz") or ""
except FileNotFoundError:
    DYNABOOK_WORKER = ""

try:
    _thinkpad = thinkpad_endpoints()
except FileNotFoundError:
    _thinkpad = {}


def probe_url(url: str, timeout: float = 6.0) -> dict[str, Any]:
    try:
        r = httpx.get(url, timeout=timeout)
        return {"online": r.status_code == 200, "status": r.status_code, "url": url}
    except Exception as exc:
        return {"online": False, "url": url, "error": str(exc)[:160]}


def probe_g3_bridge() -> dict[str, Any]:
    try:
        r = httpx.post(G3_BRIDGE, json={"cmd": "echo G3_FLEET_OK"}, timeout=20)
        ok = r.status_code == 200 and "G3_FLEET_OK" in r.text
        return {"online": ok, "bridge": G3_BRIDGE, "http": r.status_code}
    except Exception as exc:
        return {"online": False, "bridge": G3_BRIDGE, "error": str(exc)[:160]}


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}


def build_status() -> dict[str, Any]:
    k10: dict[str, Any] = {
        "n8n": probe_url("http://127.0.0.1:5679/healthz"),
        "portal": probe_url("http://127.0.0.1:8088/portal.html"),
        "growth_dashboard": probe_url(
            "http://127.0.0.1:8088/apps/growth_dashboard/index.html"
        ),
        "ollama": probe_url("http://127.0.0.1:11434/api/tags"),
        "email_search": probe_url("http://127.0.0.1:8792/api/stats"),
        "email_blacklist": probe_url("http://127.0.0.1:8791/api/email-blacklist/candidates"),
        "dxf2step": probe_url("http://127.0.0.1:8002/api/dxf2step/health"),
        "learning_engine": probe_url("http://127.0.0.1:8110/health"),
    }
    k10["balanced_stack"] = read_json(ROOT / "data" / "state" / "minipc_balanced_stack" / "startup_status.json")
    k10["email_watchdog"] = read_json(ROOT / "data" / "workspace" / "email_continuous_watchdog_status.json")
    k10["satellite_cae"] = read_json(ROOT / "data" / "workspace" / "satellite_cae_live_status.json")

    g3 = {
        "node_id": "g3",
        "alias": "K3",
        "n8n": probe_url(G3_N8N),
        "exec_bridge": probe_g3_bridge(),
        "iatf": probe_url(G3_IATF, timeout=12.0),
    }

    lavie = {
        "job_worker": probe_url(LAVIE_WORKER),
        "n8n": probe_url(LAVIE_N8N),
        "verify": read_json(ROOT / "data" / "workspace" / "lavie_node_verify_status.json"),
    }

    dynabook: dict[str, Any] = {
        "node_id": "dynabook",
        "profile": "light",
        "verify": read_json(ROOT / "data" / "workspace" / "dynabook_node_verify_status.json"),
        "registry": read_json(ROOT / "data" / "workspace" / "dynabook_node_registry.json"),
        "light_loop": read_json(ROOT / "data" / "workspace" / "dynabook_light_loop_status.json"),
    }
    if DYNABOOK_WORKER:
        dynabook["job_worker"] = probe_url(DYNABOOK_WORKER)
    else:
        dynabook["job_worker"] = {"online": False, "url": "", "error": "ip not registered"}

    thinkpad_metrics = thinkpad_ssh_metrics.collect_metrics() if _thinkpad else {
        "ok": False,
        "error": "registry missing",
    }
    if _thinkpad:
        thinkpad_ssh_metrics.write_outputs(thinkpad_metrics)
    thinkpad = {
        "node_id": "thinkpad",
        "profile": _thinkpad.get("profile") or "medium_ssh",
        "registry": read_json(ROOT / "data" / "workspace" / "thinkpad_node_registry.json"),
        "metrics": thinkpad_metrics,
        "ssh": {
            "online": bool(thinkpad_metrics.get("ok")),
            "host": _thinkpad.get("ssh_host") or _thinkpad.get("ip"),
            "user": _thinkpad.get("ssh_user"),
            "transport": "ssh",
            "error": thinkpad_metrics.get("error", ""),
        },
        "assigned_work": [
            "web_research",
            "dataset_download",
            "document_parse",
            "rag_indexing",
            "qms_iatf_analysis",
            "cae_pregate_dry_run",
        ] if thinkpad_metrics.get("ok") else [],
    }

    fleet_start = read_json(ROOT / "data" / "workspace" / "fleet_24x7_startup_log.json")

    issues: list[str] = []
    if not k10["email_search"].get("online"):
        issues.append("K10 email_search_api offline")
    if not k10["dxf2step"].get("online"):
        issues.append("K10 dxf2step API offline")
    if not lavie["job_worker"].get("online"):
        issues.append("LAVIE job worker offline")
    if not lavie["n8n"].get("online"):
        issues.append("LAVIE n8n offline")
    if not g3["n8n"].get("online") and not g3["exec_bridge"].get("online"):
        issues.append("G3 unreachable (check Tailscale / WiFi)")
    elif not g3["iatf"].get("online"):
        issues.append("G3 IATF offline (:3004)")
    if DYNABOOK_WORKER and not dynabook["job_worker"].get("online"):
        issues.append("Dynabook job worker offline (:5683)")
    elif not DYNABOOK_WORKER and dynabook.get("registry", {}).get("status") == "pending_setup":
        issues.append("Dynabook pending setup (run dynabook_node_setup.ps1 + k10_dynabook_register.py)")
    if _thinkpad and not thinkpad["ssh"].get("online"):
        issues.append("ThinkPad SSH metrics unavailable")

    overall = "ok"
    if any("offline" in i or "unreachable" in i for i in issues):
        overall = "warning" if lavie["job_worker"].get("online") and k10["n8n"].get("online") else "critical"

    return {
        "updated_at": datetime.now(JST).isoformat(),
        "overall": overall,
        "issues": issues,
        "mode": "24x7",
        "k10": k10,
        "g3": g3,
        "k3": g3,
        "lavie": lavie,
        "dynabook": dynabook,
        "thinkpad": thinkpad,
        "last_startup": fleet_start,
        "runbook": "docs/FLEET_24X7_OPERATIONS.md",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Update fleet 24/7 status JSON")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    status = build_status()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    tmp = OUT.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(OUT)

    if args.json:
        print(json.dumps(status, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] wrote {OUT} overall={status['overall']} issues={len(status['issues'])}")
    return 0 if status["overall"] != "critical" else 1


if __name__ == "__main__":
    raise SystemExit(main())
