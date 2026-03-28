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
ROOT = WORKSPACE.parents[1]
COMPOSE_FILE = ROOT / "clawstack_v2" / "docker-compose.yml"
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
]


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
        "services": rows,
        "topHeavy": rows[:12],
    }


def compose_cmd(*extra: str) -> list[str]:
    return ["docker", "compose", "-f", str(COMPOSE_FILE), *extra]


def currently_running_services() -> list[str]:
    proc = run(["docker", "ps", "--format", "{{.Names}}"], timeout=30)
    services = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        services.append(container_name_to_service(line))
    return services


def apply_lite_mode() -> dict[str, Any]:
    running = set(currently_running_services())
    targets = [service for service in LITE_STOP_SERVICES if service in running]
    if not targets:
        return {"changed": False, "targets": [], "stdout": "", "stderr": ""}
    proc = run(compose_cmd("stop", *targets), timeout=600)
    return {
        "changed": proc.returncode == 0,
        "targets": targets,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
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
    print(json.dumps({"capturedAt": report["capturedAt"], "heavyRunningCandidates": report["heavyRunningCandidates"]}, ensure_ascii=False, indent=2))
    return 0


def cmd_apply_lite(_: argparse.Namespace) -> int:
    apply_result = apply_lite_mode()
    report = build_report("apply-lite", apply_result)
    print(json.dumps({"capturedAt": report["capturedAt"], "applyResult": apply_result}, ensure_ascii=False, indent=2))
    return 0 if apply_result.get("returncode", 0) == 0 else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="Mini PC optimization harness for Clawstack")
    sub = parser.add_subparsers(dest="command", required=True)

    status = sub.add_parser("status", help="capture current resource-heavy services")
    status.set_defaults(func=cmd_status)

    apply_lite = sub.add_parser("apply-lite", help="stop optional heavyweight services")
    apply_lite.set_defaults(func=cmd_apply_lite)

    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
