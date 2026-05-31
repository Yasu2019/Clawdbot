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


def probe_lavie_bridge(cfg: dict[str, Any]) -> tuple[bool, str]:
    lavie = cfg.get("lavie") or {}
    if not lavie.get("enabled"):
        return False, "lavie disabled in config"
    ip = (lavie.get("ip") or "").strip()
    if not ip:
        return False, "lavie ip empty"
    port = int(lavie.get("port") or 5679)
    path = lavie.get("bridge_path") or "/webhook/exec_bridge"
    url = f"http://{ip}:{port}{path}"
    try:
        health = httpx.get(f"http://{ip}:{port}/healthz", timeout=5)
        if health.status_code != 200:
            return False, f"healthz {health.status_code}"
        r = httpx.post(url, json={"cmd": "echo LAVIE_ROUTER_PROBE"}, timeout=20)
        if r.status_code != 200 or "LAVIE_ROUTER_PROBE" not in r.text:
            return False, f"exec_bridge failed {r.status_code}"
        return True, "ok"
    except Exception as exc:
        return False, str(exc)


def probe_lavie_job_worker(cfg: dict[str, Any]) -> tuple[bool, str]:
    lavie = cfg.get("lavie") or {}
    if not lavie.get("enabled"):
        return False, "lavie disabled in config"
    ip = (lavie.get("ip") or "").strip()
    if not ip:
        return False, "lavie ip empty"
    port = int(lavie.get("job_worker_port") or 5680)
    path = lavie.get("job_worker_path") or "/healthz"
    url = f"http://{ip}:{port}{path}"
    try:
        r = httpx.get(url, timeout=10)
        if r.status_code == 200:
            return True, url
        return False, f"{url} -> {r.status_code}"
    except Exception as exc:
        return False, f"{url} -> {exc}"


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
    lavie_cfg = cfg.get("lavie") or {}
    parallel = cfg.get("parallel_mode") or {}
    stats = host_stats()
    busy, busy_reason = k10_cae_busy(cfg)
    lavie_ok, lavie_reason = probe_lavie_job_worker(cfg)
    if not lavie_ok:
        bridge_ok, bridge_reason = probe_lavie_bridge(cfg)
        lavie_ok = bridge_ok
        lavie_reason = f"job_worker unavailable; bridge={bridge_reason}"

    decision = {
        "host": "k10",
        "reason": "default k10",
        "category": category,
        "k10_stats": stats,
        "k10_cae_busy": busy,
        "k10_busy_reason": busy_reason,
        "lavie_online": lavie_ok,
        "lavie_probe": lavie_reason,
    }

    if lavie_ok and category in lavie_openfoam:
        if busy or parallel.get("openfoam_to_lavie", True):
            decision["host"] = "lavie"
            decision["reason"] = f"OpenFOAM offload -> lavie ({busy_reason})"
            return decision

    if category in heavy:
        decision["host"] = "k10"
        decision["reason"] = "heavy category -> k10"
        return decision

    ram = stats.get("ram_percent", 0.0)
    force_k10 = float(k10_cfg.get("force_when_ram_above_percent") or 88)
    prefer_k10 = float(k10_cfg.get("prefer_when_ram_below_percent") or 70)

    if ram >= force_k10:
        if lavie_ok and category in light:
            decision["host"] = "lavie"
            decision["reason"] = f"k10 ram {ram:.1f}% >= {force_k10}, offload light trial"
        else:
            decision["host"] = "k10"
            decision["reason"] = f"k10 ram high but lavie unavailable ({lavie_reason})"
        return decision

    if category in light and lavie_ok and ram > prefer_k10:
        decision["host"] = "lavie"
        decision["reason"] = f"light category, k10 ram {ram:.1f}% > {prefer_k10}"
        return decision

    decision["host"] = "k10"
    decision["reason"] = f"k10 preferred (ram {ram:.1f}%)"
    return decision


def main() -> int:
    parser = argparse.ArgumentParser(description="CAE workload router (K10 vs LAVIE)")
    parser.add_argument("--category", default="press_blanking", help="Trial category")
    parser.add_argument("--probe-lavie", action="store_true", help="Only probe LAVIE bridge")
    parser.add_argument("--probe-lavie-jobs", action="store_true", help="Only probe LAVIE job worker")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    cfg = load_config()
    if args.probe_lavie_jobs:
        ok, reason = probe_lavie_job_worker(cfg)
        out = {"lavie_job_worker_online": ok, "probe": reason, "config": cfg.get("lavie")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1
    if args.probe_lavie:
        ok, reason = probe_lavie_bridge(cfg)
        out = {"lavie_online": ok, "probe": reason, "config": cfg.get("lavie")}
        print(json.dumps(out, ensure_ascii=False, indent=2))
        return 0 if ok else 1

    decision = pick_host(args.category, cfg)
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(f"host={decision['host']} reason={decision['reason']}")
        print(f"lavie_online={decision['lavie_online']} ({decision['lavie_probe']})")
        print(f"k10 ram={decision['k10_stats'].get('ram_percent', 0):.1f}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
