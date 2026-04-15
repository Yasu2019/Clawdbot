#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any


JST = timezone(timedelta(hours=9))
WORKSPACE = Path(__file__).resolve().parent
STATUS_PATH = WORKSPACE / "minipc_optimizer_status.json"

LITE_STOP_SERVICES = [
    "infinity",
    "docling",
    "clickhouse",
    "langfuse",
    "langfuse-worker",
    "metabase",
    "dify-web",
    "dify-worker",
    "dify-api",
    "dify-plugin-daemon",
    "dify-db",
    "dify-redis",
    "open_notebook",
    "open_notebook_db",
    "crawl4ai",
    "paperless",
    "stirling_pdf",
    "immich_server",
    "immich_machine_learning",
    "immich_postgres",
    "immich_redis",
    "redis-stack",
    "nodered",
    "drawio",
    "diagram_cli",
    "meilisearch",
    "stable_diffusion",
    "portainer",
    "dozzle",
    "uptime-kuma",
    "watchtower",
    "lemonade",
]


def resolve_root() -> Path:
    candidates: list[Path] = []
    seen: set[str] = set()
    for base in [WORKSPACE.parents[1], Path.cwd(), *Path.cwd().parents]:
        key = str(base)
        if key in seen:
            continue
        seen.add(key)
        candidates.append(base)
    for candidate in candidates:
        compose = candidate / "clawstack_v2" / "docker-compose.yml"
        workspace = candidate / "data" / "workspace"
        if compose.exists() and workspace.exists():
            return candidate
    return WORKSPACE.parents[1]


ROOT = resolve_root()
COMPOSE_FILE = ROOT / "clawstack_v2" / "docker-compose.yml"


def now_jst() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def run(args: list[str], timeout: int = 120) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        cwd=str(ROOT),
    )


def parse_mem_to_mib(mem_usage: str) -> float:
    used = mem_usage.split("/", 1)[0].strip().replace("i", "")
    value = float("".join(ch for ch in used if ch.isdigit() or ch == ".") or "0")
    if "GiB" in used:
        return value * 1024.0
    if "MiB" in used:
        return value
    if "KiB" in used:
        return value / 1024.0
    return value


def container_name_to_service(name: str) -> str:
    if not name.startswith("clawstack-unified-"):
        return name
    tail = name.removeprefix("clawstack-unified-")
    if tail.endswith("-1"):
        tail = tail[:-2]
    return tail


def get_cpu_load() -> float:
    try:
        # Get global CPU load percentage via PowerShell CIM
        proc = run(["powershell", "-Command", "Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average | Select-Object -ExpandProperty Average"], timeout=15)
        val = proc.stdout.strip()
        return float(val) if val else 0.0
    except Exception:
        return 0.0


def collect_stats() -> dict[str, Any]:
    proc = run(["docker", "stats", "--no-stream", "--format", "{{json .}}"], timeout=60)
    rows: list[dict[str, Any]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        item["serviceGuess"] = container_name_to_service(item.get("Name", ""))
        item["memMiB"] = round(parse_mem_to_mib(item.get("MemUsage", "0MiB / 0MiB")), 2)
        rows.append(item)
    rows.sort(key=lambda item: item.get("memMiB", 0), reverse=True)
    return {
        "capturedAt": now_jst(),
        "cpuLoad": get_cpu_load(),
        "services": rows,
        "topHeavy": rows[:12],
    }


def compose_cmd(*extra: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *extra]


def currently_running_containers() -> list[dict[str, str]]:
    proc = run(["docker", "ps", "--format", "{{.Names}}"], timeout=30)
    containers: list[dict[str, str]] = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        containers.append({"name": line, "service": container_name_to_service(line)})
    return containers


def apply_lite_mode() -> dict[str, Any]:
    running = currently_running_containers()
    targets = [item for item in running if item["service"] in LITE_STOP_SERVICES]
    if not targets:
        return {"changed": False, "targets": [], "containers": [], "stdout": "", "stderr": ""}
    container_names = [item["name"] for item in targets]
    proc = run(["docker", "stop", *container_names], timeout=600)
    return {
        "changed": proc.returncode == 0,
        "targets": [item["service"] for item in targets],
        "containers": container_names,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def cleanup_temp() -> dict[str, Any]:
    temp_dirs = [
        ROOT / "data" / "workspace" / "tmp",
        ROOT / "data" / "workspace" / "temp_eml",
        ROOT / "data" / "workspace" / "logs",
        ROOT / "data" / "work" / "logs",
    ]
    cleaned: list[str] = []
    errors: list[str] = []
    total_deleted = 0
    
    for d in temp_dirs:
        if not d.exists():
            continue
        try:
            # Remove files older than 7 days
            cutoff = datetime.now().timestamp() - (7 * 24 * 3600)
            for f in d.rglob("*"):
                if f.is_file() and f.stat().st_mtime < cutoff:
                    try:
                        f.unlink()
                        total_deleted += 1
                    except Exception as e:
                        errors.append(f"unlink {f}: {e}")
            cleaned.append(str(d))
        except Exception as e:
            errors.append(f"walk {d}: {e}")
            
    return {
        "cleaned": cleaned,
        "totalDeleted": total_deleted,
        "errors": errors
    }
 
 
def build_report(mode: str, apply_result: dict[str, Any] | None = None) -> dict[str, Any]:
    stats = collect_stats()
    heavy_running = [
        item["serviceGuess"]
        for item in stats["topHeavy"]
        if item.get("serviceGuess") in LITE_STOP_SERVICES
    ]
    report = {
        "capturedAt": now_jst(),
        "mode": mode,
        "composeFile": str(COMPOSE_FILE),
        "liteStopServices": LITE_STOP_SERVICES,
        "heavyRunningCandidates": heavy_running,
        "stats": stats,
    }
    if apply_result is not None:
        report["applyResult"] = apply_result
    STATUS_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report


def cmd_status(_: argparse.Namespace) -> int:
    report = build_report("status")
    print(json.dumps({
        "capturedAt": report["capturedAt"],
        "cpuLoad": report["stats"].get("cpuLoad", 0.0),
        "heavyRunningCandidates": report["heavyRunningCandidates"]
    }, ensure_ascii=False, indent=2))
    return 0


def cmd_apply_lite(_: argparse.Namespace) -> int:
    apply_result = apply_lite_mode()
    report = build_report("apply-lite", apply_result)
    print(json.dumps({"capturedAt": report["capturedAt"], "applyResult": apply_result}, ensure_ascii=False, indent=2))
    return 0 if apply_result.get("returncode", 0) == 0 else 1


def cmd_cleanup_temp(_: argparse.Namespace) -> int:
    result = cleanup_temp()
    print(json.dumps({"capturedAt": now_jst(), "cleanupResult": result}, ensure_ascii=False, indent=2))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini PC optimization harness for Clawstack")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="capture current resource-heavy services")
    status.set_defaults(func=cmd_status)

    apply_lite = sub.add_parser("apply-lite", help="stop optional heavyweight services")
    apply_lite.set_defaults(func=cmd_apply_lite)

    cleanup = sub.add_parser("cleanup-temp", help="remove old logs and temporary files")
    cleanup.set_defaults(func=cmd_cleanup_temp)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
