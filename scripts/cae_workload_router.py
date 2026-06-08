# -*- coding: utf-8 -*-
"""Pick K10 vs LAVIE for a CAE trial (rule-based). Trial day: probe + dry-run only."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "data" / "workspace" / "cae_workload_router.yaml"
REGISTRY_PATH = ROOT / "data" / "workspace" / "lavie_node_registry.json"
STATUS_PATH = ROOT / "data" / "state" / "cae_te_engine" / "status.json"


def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        return {}
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8")) or {}


def host_stats() -> dict[str, float]:
    try:
        import psutil

        return {
            "cpu_percent": float(psutil.cpu_percent(interval=0.5)),
            "ram_percent": float(psutil.virtual_memory().percent),
        }
    except ImportError:
        return {"cpu_percent": 0.0, "ram_percent": 0.0}


def probe_satellite_bridge(cfg: dict[str, Any], node_id: str) -> tuple[bool, str]:
    sat = cfg.get(node_id) or {}
    if not sat.get("enabled"):
        return False, f"{node_id} disabled in config"
    ip = (sat.get("ip") or "").strip()
    if not ip:
        return False, f"{node_id} ip empty"
    port = int(sat.get("port") or 5679)
    path = sat.get("bridge_path") or "/webhook/exec_bridge"
    url = f"http://{ip}:{port}{path}"
    try:
        health = httpx.get(f"http://{ip}:{port}/healthz", timeout=5)
        if health.status_code != 200:
            return False, f"healthz {health.status_code}"
        r = httpx.post(url, json={"cmd": f"echo {node_id.upper()}_ROUTER_PROBE"}, timeout=20)
        if r.status_code != 200 or f"{node_id.upper()}_ROUTER_PROBE" not in r.text:
            return False, f"exec_bridge failed {r.status_code}"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def probe_satellite_job_worker(cfg: dict[str, Any], node_id: str) -> tuple[bool, str]:
    sat = cfg.get(node_id) or {}
    if not sat.get("enabled"):
        return False, f"{node_id} disabled in config"
    ip = (sat.get("ip") or "").strip()
    if not ip:
        return False, f"{node_id} ip empty"
    port = int(sat.get("job_worker_port") or 5680)
    path = sat.get("job_worker_path") or "/healthz"
    url = f"http://{ip}:{port}{path}"
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code == 200:
            return True, url
        return False, f"{url} -> {r.status_code}"
    except Exception as exc:
        return False, f"{url} -> {exc}"


def probe_satellite_metrics(cfg: dict[str, Any], node_id: str) -> tuple[bool, dict[str, Any], str]:
    sat = cfg.get(node_id) or {}
    if not sat.get("enabled"):
        return False, {}, f"{node_id} disabled in config"
    ip = (sat.get("ip") or "").strip()
    if not ip:
        return False, {}, f"{node_id} ip empty"
    port = int(sat.get("monitor_agent_port") or 8111)
    url = f"http://{ip}:{port}/metrics"
    try:
        r = httpx.get(url, timeout=8)
        if r.status_code != 200:
            return False, {}, f"{url} -> {r.status_code}"
        data = r.json()
        if not isinstance(data, dict):
            return False, {}, f"{url} -> non-object json"
        return True, data, url
    except Exception as exc:
        return False, {}, f"{url} -> {exc}"


def satellite_load_guard(cfg: dict[str, Any], node_id: str) -> tuple[bool, str, dict[str, Any]]:
    sat = cfg.get(node_id) or {}
    ok, metrics, detail = probe_satellite_metrics(cfg, node_id)
    if not ok:
        return False, f"metrics unavailable: {detail}", {}

    def as_float(key: str, default: float = 0.0) -> float:
        try:
            return float(metrics.get(key) or default)
        except (TypeError, ValueError):
            return default

    cpu = as_float("cpu_usage_percent")
    ram = as_float("ram_usage_percent")
    temp = as_float("thermal_control_temp_c", as_float("cpu_temp_celsius"))
    max_cpu = float(sat.get("max_cpu_percent") or 85)
    max_ram = float(sat.get("max_ram_percent") or 80)
    max_temp = float(sat.get("max_temp_c") or 78)
    if cpu >= max_cpu:
        return False, f"cpu {cpu:.1f}% >= {max_cpu:.1f}%", metrics
    if ram >= max_ram:
        return False, f"ram {ram:.1f}% >= {max_ram:.1f}%", metrics
    if temp >= max_temp:
        return False, f"temp {temp:.1f}C >= {max_temp:.1f}C", metrics
    return True, f"load ok cpu={cpu:.1f}% ram={ram:.1f}% temp={temp:.1f}C", metrics


def k10_cae_busy(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    cfg = cfg or load_config()
    if STATUS_PATH.exists():
        try:
            status = json.loads(STATUS_PATH.read_text(encoding="utf-8-sig"))
            if status.get("phase") == "RUNNING":
                return True, f"cae_te_engine RUNNING trial={status.get('current_trial')}"
        except Exception:
            pass
    images = (
        "clawstack-unified-openradioss:latest",
        "opencfd/openfoam-dev:latest",
    )
    for image in images:
        try:
            proc = subprocess.run(
                ["docker", "ps", "--filter", f"ancestor={image}", "--format", "{{.ID}}"],
                capture_output=True,
                text=True,
                timeout=8,
                encoding="utf-8",
                errors="replace",
            )
            if proc.returncode == 0 and proc.stdout.strip():
                return True, f"docker running image={image}"
        except Exception:
            continue
    parallel = cfg.get("parallel_mode") or {}
    if parallel.get("assume_k10_busy"):
        return True, "parallel_mode.assume_k10_busy"
    return False, "idle"


def pick_host(category: str, cfg: dict[str, Any] | None = None) -> dict[str, Any]:
    cfg = cfg or load_config()
    heavy = set(cfg.get("heavy_categories") or [])
    light = set(cfg.get("light_categories") or [])
    lavie_openfoam = set(cfg.get("lavie_openfoam_categories") or [])
    k10_cfg = cfg.get("k10") or {}
    parallel = cfg.get("parallel_mode") or {}
    stats = host_stats()
    busy, busy_reason = k10_cae_busy(cfg)
    
    available_satellites = []
    # Prioritize red_lavie (newer/more ram) over lavie
    for node_id in ["red_lavie", "lavie"]:
        ok, reason = probe_satellite_job_worker(cfg, node_id)
        if not ok:
            bridge_ok, bridge_reason = probe_satellite_bridge(cfg, node_id)
            if bridge_ok:
                ok = True
                reason = f"job_worker unavailable; bridge={bridge_reason}"
        if ok:
            load_ok, load_reason, _metrics = satellite_load_guard(cfg, node_id)
            if load_ok:
                available_satellites.append((node_id, f"{reason}; {load_reason}"))
            else:
                available_satellites.append((f"{node_id}:guarded", f"{reason}; {load_reason}"))

    decision = {
        "host": "k10",
        "reason": "default k10",
        "category": category,
        "k10_stats": stats,
        "k10_cae_busy": busy,
        "k10_busy_reason": busy_reason,
        "satellites_online": any(not node_id.endswith(":guarded") for node_id, _ in available_satellites),
        "satellites_probe": available_satellites,
    }

    dispatchable_satellites = [
        (node_id, reason) for node_id, reason in available_satellites if not node_id.endswith(":guarded")
    ]

    if dispatchable_satellites and category in lavie_openfoam:
        if busy or parallel.get("openfoam_to_lavie", True):
            chosen_sat, _ = dispatchable_satellites[0]
            decision["host"] = chosen_sat
            decision["reason"] = f"OpenFOAM offload -> {chosen_sat} ({busy_reason})"
            return decision

    ram = stats.get("ram_percent", 0.0)
    cpu = stats.get("cpu_percent", 0.0)
    force_k10 = float(k10_cfg.get("force_when_ram_above_percent") or 88)
    prefer_k10 = float(k10_cfg.get("prefer_when_ram_below_percent") or 70)
    red_lavie_ready = any(node_id == "red_lavie" for node_id, _ in dispatchable_satellites)

    if category in heavy:
        if red_lavie_ready and (busy or ram >= prefer_k10 or cpu >= 75):
            decision["host"] = "red_lavie"
            decision["reason"] = (
                f"heavy category -> red_lavie because k10 load is high "
                f"(cpu {cpu:.1f}%, ram {ram:.1f}%, busy={busy})"
            )
            return decision
        decision["host"] = "k10"
        decision["reason"] = "heavy category -> k10"
        return decision

    if ram >= force_k10:
        if dispatchable_satellites and category in light:
            chosen_sat, _ = dispatchable_satellites[0]
            decision["host"] = chosen_sat
            decision["reason"] = f"k10 ram {ram:.1f}% >= {force_k10}, offload light trial to {chosen_sat}"
        else:
            decision["host"] = "k10"
            decision["reason"] = f"k10 ram high but satellites unavailable"
        return decision

    if category in light and dispatchable_satellites and ram > prefer_k10:
        chosen_sat, _ = dispatchable_satellites[0]
        decision["host"] = chosen_sat
        decision["reason"] = f"light category, k10 ram {ram:.1f}% > {prefer_k10}, dispatch to {chosen_sat}"
        return decision

    decision["host"] = "k10"
    decision["reason"] = f"k10 preferred (ram {ram:.1f}%)"
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description="CAE workload router (K10 vs Cluster)")
    parser.add_argument("--category", default="press_blanking", help="Trial category")
    parser.add_argument("--probe-lavie", action="store_true", help="Only probe bridge")
    parser.add_argument("--probe-lavie-jobs", action="store_true", help="Only probe job worker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    cfg = load_config()
    if args.probe_lavie_jobs:
        out = {}
        for node in ["red_lavie", "lavie"]:
            ok, reason = probe_satellite_job_worker(cfg, node)
            out[node] = {"online": ok, "probe": reason, "config": cfg.get(node)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0
    if args.probe_lavie:
        out = {}
        for node in ["red_lavie", "lavie"]:
            ok, reason = probe_satellite_bridge(cfg, node)
            out[node] = {"online": ok, "probe": reason, "config": cfg.get(node)}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0

    decision = pick_host(args.category, cfg)
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(f"host={decision['host']} reason={decision['reason']}")
        print(f"satellites_online={decision['satellites_online']} ({decision['satellites_probe']})")
        print(f"k10 ram={decision['k10_stats'].get('ram_percent', 0):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
