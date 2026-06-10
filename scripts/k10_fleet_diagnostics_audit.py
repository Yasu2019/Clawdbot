# -*- coding: utf-8 -*-
"""Audit fleet monitor_agent diagnostics reachability from K10."""
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
OUT_PATH = WORKSPACE / "fleet_diagnostics_status.json"
JST = timezone(timedelta(hours=9))


NODES = [
    {"node_id": "k10", "name": "K10", "metrics": "http://127.0.0.1:8111/metrics", "diagnostics": "http://127.0.0.1:8111/diagnostics", "diagnostics_alt": ["http://127.0.0.1:8112/diagnostics"]},
    {"node_id": "red_lavie", "name": "Red LAVIE", "metrics": "http://100.99.145.3:8111/metrics", "diagnostics": "http://100.99.145.3:8111/diagnostics", "diagnostics_alt": ["http://100.99.145.3:8112/diagnostics"]},
    {"node_id": "lavie", "name": "LAVIE", "metrics": "http://100.87.244.46:8111/metrics", "diagnostics": "http://100.87.244.46:8111/diagnostics", "diagnostics_alt": ["http://100.87.244.46:8112/diagnostics"]},
    {"node_id": "vivobook", "name": "Vivobook mhn15", "metrics": "http://100.65.182.27:8111/metrics", "diagnostics": "http://100.65.182.27:8111/diagnostics", "diagnostics_alt": ["http://100.65.182.27:8112/diagnostics"]},
    {"node_id": "dynabook", "name": "Dynabook", "metrics": "http://100.98.133.40:8111/metrics", "diagnostics": "http://100.98.133.40:8111/diagnostics", "diagnostics_alt": ["http://100.98.133.40:8112/diagnostics"]},
]


def fetch_json(url: str, timeout: int = 6) -> dict[str, Any]:
    try:
        req = Request(url, headers={"User-Agent": "k10_fleet_diagnostics_audit/1"})
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read(512 * 1024).decode("utf-8", errors="replace")
            data = json.loads(body)
            return {"online": True, "status": resp.status, "data": data}
    except HTTPError as exc:
        return {"online": False, "status": exc.code, "error": str(exc)}
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return {"online": False, "error": str(exc)}


def compact_metrics(data: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "hostname",
        "cpu_usage_percent",
        "ram_usage_percent",
        "ram_used_gb",
        "ram_total_gb",
        "cpu_temp_celsius",
        "thermal_control_temp_c",
        "lhm_ok",
        "temp_source",
        "node_diagnostic",
        "fleet_evidence",
    )
    return {key: data.get(key) for key in keys if key in data}


def audit_node(node: dict[str, str]) -> dict[str, Any]:
    metrics_result = fetch_json(node["metrics"])
    diag_result = fetch_json(node["diagnostics"])
    active_diag_url = node["diagnostics"]
    if not diag_result.get("online"):
        for alt_url in node.get("diagnostics_alt", []):
            alt_result = fetch_json(alt_url)
            if alt_result.get("online"):
                diag_result = alt_result
                active_diag_url = alt_url
                break
    item: dict[str, Any] = {
        "node_id": node["node_id"],
        "name": node["name"],
        "metrics_url": node["metrics"],
        "diagnostics_url": node["diagnostics"],
        "active_diagnostics_url": active_diag_url,
        "metrics_online": metrics_result.get("online", False),
        "diagnostics_online": diag_result.get("online", False),
        "metrics_status": metrics_result.get("status"),
        "diagnostics_status": diag_result.get("status"),
        "metrics_error": metrics_result.get("error"),
        "diagnostics_error": diag_result.get("error"),
    }
    if isinstance(metrics_result.get("data"), dict):
        item["metrics"] = compact_metrics(metrics_result["data"])
    if isinstance(diag_result.get("data"), dict):
        status = diag_result["data"].get("status") or {}
        recent = diag_result["data"].get("recent") or []
        item["diagnostic_status"] = status
        item["recent_count"] = len(recent) if isinstance(recent, list) else 0
        item["last_recent_event"] = recent[-1] if isinstance(recent, list) and recent else None
    if not item["diagnostics_online"]:
        if item["metrics_online"]:
            item["action"] = "refresh_monitor_agent"
        else:
            item["action"] = "manual_power_network_or_startup_check"
    else:
        item["action"] = "ok"
    return item


def main() -> int:
    rows = [audit_node(node) for node in NODES]
    summary = {
        "updated_at": datetime.now(JST).isoformat(timespec="seconds"),
        "schema": "clawstack.fleet_diagnostics_status.v1",
        "nodes": rows,
        "ok_count": sum(1 for row in rows if row.get("diagnostics_online")),
        "needs_refresh": [row["node_id"] for row in rows if row.get("action") == "refresh_monitor_agent"],
        "needs_manual": [row["node_id"] for row in rows if row.get("action") == "manual_power_network_or_startup_check"],
    }
    OUT_PATH.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if not summary["needs_manual"] and not summary["needs_refresh"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
