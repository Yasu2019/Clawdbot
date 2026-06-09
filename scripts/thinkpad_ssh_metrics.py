# -*- coding: utf-8 -*-
"""Collect Ubuntu ThinkPad metrics from K10 over SSH."""
from __future__ import annotations

import sys
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
REGISTRY = WORKSPACE / "thinkpad_node_registry.json"
STATUS_OUT = WORKSPACE / "thinkpad_node_metrics.json"
DASHBOARD_OUT = WORKSPACE / "apps" / "growth_dashboard" / "thinkpad_metrics.json"
JST = timezone(timedelta(hours=9))


REMOTE_SCRIPT = r"""
set -u
echo "HOSTNAME=$(hostname)"
echo "UNAME=$(uname -srmo)"
echo "CPU_NAME=$(lscpu | awk -F: '/Model name/ {gsub(/^[ \t]+/,"",$2); print $2; exit}')"
echo "CPU_THREADS=$(nproc)"
echo "CPU_CORES=$(lscpu | awk -F: '/Core\(s\) per socket/ {gsub(/^[ \t]+/,"",$2); print $2; exit}')"
echo "CPU_MAX_MHZ=$(lscpu | awk -F: '/CPU max MHz/ {gsub(/^[ \t]+/,"",$2); print int($2); exit}')"
echo "CPU_MIN_MHZ=$(lscpu | awk -F: '/CPU min MHz/ {gsub(/^[ \t]+/,"",$2); print int($2); exit}')"
awk '/cpu / {idle=$5; total=0; for(i=2;i<=NF;i++) total+=$i; printf("CPU_TICKS_1=%s %s\n", idle, total)}' /proc/stat
sleep 0.35
awk '/cpu / {idle=$5; total=0; for(i=2;i<=NF;i++) total+=$i; printf("CPU_TICKS_2=%s %s\n", idle, total)}' /proc/stat
free -m | awk '/Mem:/ {printf("RAM_MB=%s %s %s\n", $3, $2, $7)}'
awk '{printf("LOAD_AVG=%s %s %s\n", $1, $2, $3)}' /proc/loadavg
for f in /sys/class/thermal/thermal_zone*/temp /sys/class/hwmon/hwmon*/temp*_input; do
  if [ -r "$f" ]; then
    v=$(cat "$f" 2>/dev/null || true)
    case "$v" in
      ''|*[!0-9-]*) ;;
      *) echo "TEMP_MILLIC=$v" ;;
    esac
  fi
done
"""


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def run_ssh(registry: dict[str, Any], timeout: int = 12) -> subprocess.CompletedProcess[str]:
    ssh_host = registry.get("ssh_host") or registry.get("tailscale_ip")
    ssh_user = registry.get("ssh_user") or "yasu"
    key_path = registry.get("ssh_key_path") or str(Path.home() / ".ssh" / "id_ed25519")
    target = f"{ssh_user}@{ssh_host}"
    return subprocess.run(
        [
            "ssh",
            "-i",
            str(key_path),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=8",
            "-o",
            "StrictHostKeyChecking=accept-new",
            target,
            "bash",
            "-lc",
            REMOTE_SCRIPT,
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
    )


def parse_key_values(text: str) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        values.setdefault(key.strip(), []).append(value.strip())
    return values


def _float(value: str | None, default: float = 0.0) -> float:
    if not value:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _int(value: str | None, default: int = 0) -> int:
    if not value:
        return default
    match = re.search(r"-?\d+", value)
    return int(match.group(0)) if match else default


def collect_metrics() -> dict[str, Any]:
    registry = read_json(REGISTRY)
    now = datetime.now(JST).isoformat()
    try:
        proc = run_ssh(registry)
    except Exception as exc:
        return {
            "ok": False,
            "hostname": registry.get("hostname") or registry.get("node_name") or "thinkpad",
            "node_id": "thinkpad",
            "updated_at": now,
            "error": str(exc)[:240],
            "transport": "ssh",
        }

    if proc.returncode != 0:
        return {
            "ok": False,
            "hostname": registry.get("hostname") or "thinkpad",
            "node_id": "thinkpad",
            "updated_at": now,
            "error": (proc.stderr or proc.stdout)[-240:],
            "transport": "ssh",
        }

    kv = parse_key_values(proc.stdout)
    tick1 = [int(x) for x in (kv.get("CPU_TICKS_1") or ["0 0"])[0].split()[:2]]
    tick2 = [int(x) for x in (kv.get("CPU_TICKS_2") or ["0 0"])[0].split()[:2]]
    idle_delta = max(0, tick2[0] - tick1[0])
    total_delta = max(1, tick2[1] - tick1[1])
    cpu_percent = round(max(0.0, min(100.0, (1.0 - idle_delta / total_delta) * 100.0)), 1)

    ram_parts = (kv.get("RAM_MB") or ["0 0 0"])[0].split()
    ram_used_mb = _float(ram_parts[0] if len(ram_parts) > 0 else None)
    ram_total_mb = _float(ram_parts[1] if len(ram_parts) > 1 else None)
    ram_available_mb = _float(ram_parts[2] if len(ram_parts) > 2 else None)
    ram_percent = round((ram_used_mb / ram_total_mb * 100.0), 1) if ram_total_mb else 0.0

    temps = []
    for raw in kv.get("TEMP_MILLIC") or []:
        value = _float(raw)
        if value > 1000:
            celsius = value / 1000.0
            if 0 < celsius < 110:
                temps.append(celsius)
    cpu_temp = round(max(temps), 1) if temps else None
    cores = _int((kv.get("CPU_CORES") or ["0"])[0])
    threads = _int((kv.get("CPU_THREADS") or ["0"])[0])

    metrics: dict[str, Any] = {
        "ok": True,
        "node_id": "thinkpad",
        "hostname": (kv.get("HOSTNAME") or [registry.get("hostname") or "thinkpad"])[0],
        "os": "ubuntu",
        "uname": (kv.get("UNAME") or [""])[0],
        "transport": "ssh",
        "updated_at": now,
        "cpu_name": (kv.get("CPU_NAME") or ["CPU spec pending"])[0],
        "cpu_usage_percent": cpu_percent,
        "cpu_physical_cores": cores or None,
        "cpu_logical_threads": threads or None,
        "cpu_max_clock_mhz": _int((kv.get("CPU_MAX_MHZ") or ["0"])[0]) or None,
        "cpu_min_clock_mhz": _int((kv.get("CPU_MIN_MHZ") or ["0"])[0]) or None,
        "cpu_current_clock_mhz": None,
        "ram_used_gb": round(ram_used_mb / 1024.0, 2),
        "ram_total_gb": round(ram_total_mb / 1024.0, 2),
        "ram_available_gb": round(ram_available_mb / 1024.0, 2),
        "ram_usage_percent": ram_percent,
        "cpu_temp_celsius": cpu_temp,
        "thermal_control_temp_c": cpu_temp,
        "cpu_limit_percent": 100,
        "lhm_ok": False,
        "load_avg": (kv.get("LOAD_AVG") or [""])[0],
        "recommended_work": "Medium SSH jobs: web research, dataset download, document parsing, RAG indexing, IATF/QMS analysis, and CAE pregate dry-runs. Heavy solver/render jobs remain blocked until a job worker and thermal history are proven.",
    }
    return metrics


def write_outputs(metrics: dict[str, Any]) -> None:
    for path in (STATUS_OUT, DASHBOARD_OUT):
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description="Collect ThinkPad metrics over SSH")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    metrics = collect_metrics()
    if not args.no_write:
        write_outputs(metrics)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(f"[OK] thinkpad metrics ok={metrics.get('ok')} host={metrics.get('hostname')}")
    return 0 if metrics.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
