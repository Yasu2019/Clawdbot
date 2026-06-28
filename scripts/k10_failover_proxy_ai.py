# -*- coding: utf-8 -*-
"""K10 failover proxy AI harness.

Read-only first stage:
- deploys a small planner script to selected satellites through the existing
  job_worker channel;
- asks satellites to produce local failover planning reports only;
- never starts Docker, pulls models, or executes CAE jobs.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import socket
import sys
import textwrap
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
STATUS_PATH = WORKSPACE / "k10_failover_proxy_ai_status.json"
LOG_PATH = WORKSPACE / "k10_failover_proxy_ai_log.jsonl"
JST = timezone(timedelta(hours=9))

DEFAULT_NODES = ("g3", "red_lavie", "lavie", "thinkpad")
PLANNER_VERSION = "2026-06-28-readonly-v1"


NODE_PLANNER_SOURCE = r'''
# -*- coding: utf-8 -*-
"""Satellite-side K10 failover planning node.

This script is intentionally read-only. It writes a report and exits.
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import sys
import textwrap
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

JST = timezone(timedelta(hours=9))
PLANNER_VERSION = "__PLANNER_VERSION__"


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_text_limited(path: Path, limit: int = 18000) -> str:
    try:
        text = path.read_text(encoding="utf-8-sig", errors="replace")
    except Exception:
        return ""
    if len(text) <= limit:
        return text
    return text[: limit // 2] + "\n\n[TRUNCATED]\n\n" + text[-limit // 2 :]


def get_json_url(url: str, timeout: float = 5.0) -> dict[str, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "clawstack-failover-proxy-ai/1"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read(512 * 1024).decode("utf-8", errors="replace")
        data = json.loads(body)
        return data if isinstance(data, dict) else {"_non_object": True}
    except Exception as exc:
        return {"_error": str(exc)[:300], "_url": url}


def post_json_url(url: str, payload: dict[str, Any], timeout: float = 45.0) -> dict[str, Any]:
    try:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", "User-Agent": "clawstack-failover-proxy-ai/1"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read(1024 * 1024).decode("utf-8", errors="replace")
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            data = {"response": text}
        return data if isinstance(data, dict) else {"response": str(data)}
    except Exception as exc:
        return {"_error": str(exc)[:300]}


def candidate_roots() -> list[Path]:
    raw = [
        os.environ.get("SATELLITE_REPO_ROOT", ""),
        os.environ.get("CLAWSTACK_REPO_ROOT", ""),
        r"C:\lavie_usb_pack",
        r"C:\clawstack_satellite\repo",
        r"D:\Clawdbot_Docker_20260125",
        "/home/yasu/clawstack_satellite/cae_repo",
        "/home/yasu/Clawdbot_Docker_20260125",
    ]
    roots: list[Path] = []
    for item in raw:
        if not item:
            continue
        path = Path(item)
        if path.exists() and path not in roots:
            roots.append(path)
    return roots


def first_existing(relative: str) -> Path | None:
    for root in candidate_roots():
        path = root / relative
        if path.exists():
            return path
    return None


def output_root() -> Path:
    for raw in (
        os.environ.get("FAILOVER_PROXY_AI_ROOT", ""),
        os.environ.get("SATELLITE_INSTALL_ROOT", ""),
        r"C:\clawstack_satellite",
        "/home/yasu/clawstack_satellite",
    ):
        if not raw:
            continue
        base = Path(raw)
        try:
            base.mkdir(parents=True, exist_ok=True)
            out = base / "data" / "failover_proxy_ai"
            out.mkdir(parents=True, exist_ok=True)
            return out
        except Exception:
            continue
    out = Path.cwd() / "failover_proxy_ai"
    out.mkdir(parents=True, exist_ok=True)
    return out


def compact_metrics(metrics: dict[str, Any]) -> dict[str, Any]:
    keys = (
        "hostname",
        "cpu_name",
        "cpu_logical_threads",
        "cpu_usage_percent",
        "ram_total_gb",
        "ram_used_gb",
        "ram_usage_percent",
        "thermal_control_temp_c",
        "cpu_temp_celsius",
        "core_max_c",
        "thermal_throttle_label",
        "is_throttling",
        "cpu_limit_percent",
        "lhm_ok",
        "wlan",
        "disk_warnings",
    )
    return {key: metrics.get(key) for key in keys if key in metrics}


def build_context(node_id: str, role: str) -> dict[str, Any]:
    metrics = get_json_url("http://127.0.0.1:8111/metrics", timeout=5.0)
    docs: dict[str, str] = {}
    for name, rel in (
        ("PROMISES", "data/workspace/PROMISES.md"),
        ("trouble_history", "data/workspace/memory/trouble_history.md"),
        ("cae_north_star", "docs/cae_north_star_and_meaning_gate_protocol.md"),
        ("fleet_allocation", "docs/fleet_job_allocation_20260613.md"),
        ("incident_log_tail", "docs/INCIDENT_LOG.md"),
    ):
        path = first_existing(rel)
        if path:
            docs[name] = read_text_limited(path, 12000 if name == "incident_log_tail" else 8000)
    return {
        "schema": "clawstack.failover_proxy_ai.context.v1",
        "version": PLANNER_VERSION,
        "generated_at": now_iso(),
        "node_id": node_id,
        "role": role,
        "hostname": socket.gethostname(),
        "metrics": compact_metrics(metrics),
        "metrics_error": metrics.get("_error"),
        "available_docs": sorted(docs.keys()),
        "docs": docs,
    }


def deterministic_plan(context: dict[str, Any]) -> str:
    node_id = context.get("node_id", "")
    role = context.get("role", "")
    metrics = context.get("metrics") or {}
    temp = metrics.get("thermal_control_temp_c") or metrics.get("cpu_temp_celsius") or 0
    ram = metrics.get("ram_usage_percent") or 100
    cpu = metrics.get("cpu_usage_percent") or 100
    throttle = bool(metrics.get("is_throttling"))

    guards = [
        "No automatic destructive action.",
        "No Docker start/stop unless a human explicitly approves it.",
        "No CAE production dispatch from failover mode; prepare plan only.",
        "Keep raw facts separate from inference.",
    ]
    if throttle or (isinstance(temp, (int, float)) and temp >= 75):
        guards.append("Thermal guard: node is warm/throttling; plan only, no heavy job.")
    if isinstance(ram, (int, float)) and ram >= 75:
        guards.append("RAM guard: high memory use; avoid indexing and LLM loops.")

    if node_id == "g3":
        next_actions = [
            "Confirm K10 outage by repeated heartbeat failures.",
            "Notify Telegram/operator with outage timestamp and live fleet status.",
            "Ask red_lavie, lavie, and thinkpad to produce read-only plans.",
            "Do not run heavy compute on G3.",
        ]
    elif node_id == "red_lavie":
        next_actions = [
            "Continue or prepare OpenRadioss/QMS planning only if thermals are normal.",
            "Prefer press_blanking, press_bending, qms_iatf_analysis planning.",
            "Do not take over K10 GPU/video/RAG core duties.",
        ]
    elif node_id == "lavie":
        next_actions = [
            "Prepare OpenFOAM/resin_fill plan only; do not start new solver while warm.",
            "Check current CAE workspace status and existing outputs before proposing rerun.",
            "Keep regular LAVIE away from heavy fallback unless Red LAVIE is unavailable and human approves.",
        ]
    elif node_id == "thinkpad":
        next_actions = [
            "Prepare DXF2STEP/FEM impact plan from local manifests and history.",
            "Do not run OpenFOAM/OpenRadioss real solvers.",
            "Prioritize geometry validity, manifest consistency, and cached artifact QC.",
        ]
    else:
        next_actions = ["Produce monitoring-only status and wait for K10 recovery."]

    lines = [
        f"# K10 Failover Proxy Plan - {node_id}",
        "",
        f"- generated_at: {context.get('generated_at')}",
        f"- hostname: {context.get('hostname')}",
        f"- role: {role}",
        f"- cpu_percent: {cpu}",
        f"- ram_percent: {ram}",
        f"- temp_c: {temp}",
        f"- throttling: {throttle}",
        f"- docs_available: {', '.join(context.get('available_docs') or [])}",
        "",
        "## Guardrails",
    ]
    lines.extend(f"- {item}" for item in guards)
    lines.extend(["", "## Next Calculation Plan"])
    lines.extend(f"- {item}" for item in next_actions)
    lines.extend(
        [
            "",
            "## Handoff To K10",
            "- Save this report and status JSON.",
            "- When K10 returns, K10 should review this plan before resuming queues.",
            "- Any production execution requires normal router/thermal gates.",
        ]
    )
    return "\n".join(lines) + "\n"


def ollama_plan(context: dict[str, Any], model: str) -> tuple[str, str]:
    prompt = textwrap.dedent(
        f"""
        You are a read-only failover planner for Clawstack.
        K10 is unavailable. Do not execute jobs. Do not propose destructive changes.
        Create a concise Japanese calculation plan for this node only.
        Separate facts, risks, next checks, and prohibited actions.

        Context JSON:
        {json.dumps({k: v for k, v in context.items() if k != 'docs'}, ensure_ascii=False)[:12000]}

        Documentation excerpts:
        {json.dumps(context.get('docs', {}), ensure_ascii=False)[:18000]}
        """
    ).strip()
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 900},
    }
    result = post_json_url("http://127.0.0.1:11434/api/generate", payload, timeout=90.0)
    text = str(result.get("response") or "").strip()
    if text:
        return text + "\n", "ollama"
    return deterministic_plan(context), "deterministic_fallback"


def main() -> int:
    parser = argparse.ArgumentParser(description="Satellite read-only K10 failover planner")
    parser.add_argument("--node-id", required=True)
    parser.add_argument("--role", default="readonly_failover_planner")
    parser.add_argument("--model", default=os.environ.get("FAILOVER_PROXY_AI_MODEL", "qwen2.5:3b"))
    parser.add_argument("--no-ollama", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    context = build_context(args.node_id, args.role)
    if args.no_ollama:
        plan, planner = deterministic_plan(context), "deterministic"
    else:
        plan, planner = ollama_plan(context, args.model)

    out_dir = output_root()
    stamp = datetime.now(JST).strftime("%Y%m%d_%H%M%S")
    base = out_dir / f"{args.node_id}_failover_plan_{stamp}"
    md_path = base.with_suffix(".md")
    json_path = base.with_suffix(".json")
    payload = {
        "schema": "clawstack.failover_proxy_ai.report.v1",
        "version": PLANNER_VERSION,
        "node_id": args.node_id,
        "role": args.role,
        "planner": planner,
        "model": args.model if planner == "ollama" else "",
        "generated_at": context.get("generated_at"),
        "context": {k: v for k, v in context.items() if k != "docs"},
        "report_md": str(md_path),
    }
    md_path.write_text(plan, encoding="utf-8")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"ok": True, "planner": planner, "md": str(md_path), "json": str(json_path)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
'''


NODE_ROLES = {
    "g3": "heartbeat_monitor_and_failover_trigger",
    "red_lavie": "primary_readonly_proxy_ai_for_openradioss_qms",
    "lavie": "readonly_proxy_ai_for_openfoam_resin_fill",
    "thinkpad": "readonly_proxy_ai_for_dxf2step_fem_impact",
}


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = dict(entry)
    payload["logged_at"] = now_iso()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def load_env_value(key: str) -> str:
    for env_path in (ROOT / ".env", Path.cwd() / ".env"):
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8-sig", errors="replace").splitlines():
            line = line.strip()
            if line.startswith(f"{key}="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return os.environ.get(key, "").strip()


def load_node(node_id: str) -> dict[str, Any]:
    path = WORKSPACE / f"{node_id}_node_registry.json"
    if not path.exists():
        raise RuntimeError(f"registry not found: {path}")
    node = read_json(path)
    node["_registry_path"] = str(path)
    return node


def worker_base_url(node: dict[str, Any]) -> str:
    if node.get("job_worker_url"):
        return str(node["job_worker_url"]).rstrip("/")
    ip = (node.get("tailscale_ip") or node.get("lan_ip") or "").strip()
    port = int(node.get("job_worker_port") or 5680)
    if not ip:
        raise RuntimeError(f"{node.get('node_id')}: missing worker ip")
    return f"http://{ip}:{port}"


def node_transport(node_id: str, node: dict[str, Any]) -> str:
    if node_id == "g3" or (node.get("exec_bridge") and not node.get("job_worker_url")):
        return "exec_bridge"
    return "job_worker"


def is_windows_node(node_id: str, node: dict[str, Any]) -> bool:
    os_name = str(node.get("os") or "").lower()
    if os_name:
        return "win" in os_name
    return node_id != "thinkpad"


def install_script_path(node_id: str, node: dict[str, Any]) -> str:
    root = str(node.get("install_root") or "").strip()
    if not root:
        root = r"C:\clawstack_satellite" if is_windows_node(node_id, node) else "/home/yasu/clawstack_satellite"
    sep = "\\" if is_windows_node(node_id, node) else "/"
    return root.rstrip("\\/") + sep + "scripts" + sep + "failover_proxy_ai_node.py"


def http_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 10.0,
) -> tuple[int, dict[str, Any] | str]:
    data = None
    if payload is not None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers or {}, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read(1024 * 1024).decode("utf-8", errors="replace")
            status = int(resp.status)
    except urllib.error.HTTPError as exc:
        text = exc.read(512 * 1024).decode("utf-8", errors="replace")
        status = int(exc.code)
    try:
        return status, json.loads(text)
    except json.JSONDecodeError:
        return status, text[:1000]


def probe_worker(node_id: str, token: str) -> dict[str, Any]:
    node = load_node(node_id)
    if node_transport(node_id, node) == "exec_bridge":
        url = str(node.get("n8n_healthz") or "").strip()
        if not url:
            return {"node_id": node_id, "ok": False, "transport": "exec_bridge", "error": "n8n_healthz missing"}
        try:
            status, body = http_json("GET", url, timeout=8.0)
            return {
                "node_id": node_id,
                "ok": status == 200,
                "status": status,
                "transport": "exec_bridge",
                "base_url": str(node.get("exec_bridge") or ""),
                "body": body,
            }
        except Exception as exc:
            return {
                "node_id": node_id,
                "ok": False,
                "transport": "exec_bridge",
                "base_url": str(node.get("exec_bridge") or ""),
                "error": str(exc)[:300],
            }
    base = worker_base_url(node)
    try:
        status, body = http_json("GET", f"{base}/healthz", headers={"X-Satellite-Token": token}, timeout=8.0)
        ok = status == 200
        return {"node_id": node_id, "ok": ok, "status": status, "base_url": base, "body": body}
    except Exception as exc:
        return {"node_id": node_id, "ok": False, "base_url": base, "error": str(exc)[:300]}


def dispatch_shell(node_id: str, command: str, timeout_sec: int, token: str) -> dict[str, Any]:
    node = load_node(node_id)
    if node_transport(node_id, node) == "exec_bridge":
        bridge = str(node.get("exec_bridge") or "").strip()
        if not bridge:
            result = {"status": "error", "exit_code": 1, "error": "exec_bridge missing", "_http_status": 0}
            append_log({"node_id": node_id, "transport": "exec_bridge", "command": command, "result": result})
            return result
        try:
            status, body = http_json(
                "POST",
                bridge,
                {"cmd": command},
                headers={"Content-Type": "application/json"},
                timeout=timeout_sec + 45,
            )
            result = body if isinstance(body, dict) else {"status": "unknown", "body": body}
            result["_http_status"] = status
        except Exception as exc:
            result = {"status": "error", "exit_code": 1, "error": str(exc)[:500], "_http_status": 0}
        append_log({"node_id": node_id, "transport": "exec_bridge", "command": command, "result": result})
        return result

    base = worker_base_url(node)
    job = {
        "job_id": f"failover-{node_id}-{uuid.uuid4().hex[:8]}",
        "type": "shell",
        "timeout_sec": timeout_sec,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    headers = {"X-Satellite-Token": token, "Content-Type": "application/json"}
    try:
        status, body = http_json("POST", f"{base}/jobs", job, headers=headers, timeout=timeout_sec + 45)
        result = body if isinstance(body, dict) else {"status": "error", "body": body}
        result["_http_status"] = status
    except Exception as exc:
        result = {"status": "error", "exit_code": 1, "error": str(exc)[:500], "_http_status": 0}
    append_log({"node_id": node_id, "job": job, "result": result})
    return result


def make_node_source() -> str:
    return NODE_PLANNER_SOURCE.replace("__PLANNER_VERSION__", PLANNER_VERSION)


def deploy_command(node_id: str, node: dict[str, Any]) -> str:
    script_b64 = base64.b64encode(make_node_source().encode("utf-8")).decode("ascii")
    path = install_script_path(node_id, node)
    if is_windows_node(node_id, node):
        escaped = path.replace("'", "''")
        return (
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            f"\"$p='{escaped}'; New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; "
            f"[IO.File]::WriteAllBytes($p,[Convert]::FromBase64String('{script_b64}')); "
            "Write-Output ('DEPLOYED ' + $p)\""
        )
    escaped = path.replace("'", "'\"'\"'")
    return (
        "python3 -c \"import base64,pathlib; "
        f"p=pathlib.Path('{escaped}'); p.parent.mkdir(parents=True, exist_ok=True); "
        f"p.write_bytes(base64.b64decode('{script_b64}')); print('DEPLOYED '+str(p))\""
    )


def windows_init_b64_command(path: str) -> str:
    escaped = path.replace("'", "''")
    b64_path = (path + ".b64").replace("'", "''")
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        f"\"$p='{escaped}'; $b='{b64_path}'; "
        "New-Item -ItemType Directory -Force -Path (Split-Path $p) | Out-Null; "
        "if (Test-Path $b) { Remove-Item -Force $b }; "
        "[IO.File]::WriteAllText($b,'',[Text.Encoding]::ASCII); "
        "Write-Output ('INIT ' + $b)\""
    )


def windows_append_b64_command(path: str, chunk: str) -> str:
    b64_path = (path + ".b64").replace("'", "''")
    safe_chunk = chunk.replace("'", "''")
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        f"\"$b='{b64_path}'; [IO.File]::AppendAllText($b,'{safe_chunk}',[Text.Encoding]::ASCII); "
        "Write-Output 'APPEND_OK'\""
    )


def windows_finalize_b64_command(path: str) -> str:
    escaped = path.replace("'", "''")
    b64_path = (path + ".b64").replace("'", "''")
    return (
        "powershell -NoProfile -ExecutionPolicy Bypass -Command "
        f"\"$p='{escaped}'; $b='{b64_path}'; "
        "$s=[IO.File]::ReadAllText($b,[Text.Encoding]::ASCII); "
        "[IO.File]::WriteAllBytes($p,[Convert]::FromBase64String($s)); "
        "Remove-Item -Force $b; Write-Output ('DEPLOYED ' + $p)\""
    )


def run_plan_command(node_id: str, node: dict[str, Any], no_ollama: bool) -> str:
    path = install_script_path(node_id, node)
    role = NODE_ROLES.get(node_id, "readonly_failover_planner")
    flag = " --no-ollama" if no_ollama else ""
    if is_windows_node(node_id, node):
        escaped = path.replace("'", "''")
        return (
            "powershell -NoProfile -ExecutionPolicy Bypass -Command "
            f"\"$p='{escaped}'; if (-not (Test-Path $p)) {{ throw 'planner script missing: ' + $p }}; "
            f"python $p --node-id {node_id} --role {role}{flag}\""
        )
    escaped = path.replace("'", "'\"'\"'")
    return f"python3 '{escaped}' --node-id {node_id} --role {role}{flag}"


def tcp_probe(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def k10_heartbeat() -> dict[str, Any]:
    local_host = socket.gethostname().lower()
    local_is_k10 = "nucbox_k10" in local_host or "nucbox-k10" in local_host
    checks = [
        {"name": "local_hostname_is_k10", "host": socket.gethostname(), "port": 0, "ok": local_is_k10},
        {"name": "tailscale_ping_tcp_5679", "host": "100.119.18.40", "port": 5679},
        {"name": "k10_monitor_tcp_8111", "host": "100.119.18.40", "port": 8111},
        {"name": "k10_script_server_tcp_8123", "host": "100.119.18.40", "port": 8123},
    ]
    results = []
    for item in checks:
        if item["name"] == "local_hostname_is_k10":
            ok = bool(item["ok"])
        else:
            ok = tcp_probe(str(item["host"]), int(item["port"]))
        results.append({**item, "ok": ok})
    return {
        "schema": "clawstack.k10_failover_heartbeat.v1",
        "timestamp": now_iso(),
        "k10_considered_down": not any(item["ok"] for item in results),
        "checks": results,
    }


def deploy_one(node_id: str, token: str) -> dict[str, Any]:
    node = load_node(node_id)
    if not is_windows_node(node_id, node):
        return dispatch_shell(node_id, deploy_command(node_id, node), 120, token)

    path = install_script_path(node_id, node)
    script_b64 = base64.b64encode(make_node_source().encode("utf-8")).decode("ascii")
    steps: list[dict[str, Any]] = []
    init = dispatch_shell(node_id, windows_init_b64_command(path), 60, token)
    steps.append({"step": "init", "result": init})
    if str(init.get("status", "")).lower() not in {"ok", "success"} and int(init.get("exit_code") or 1) != 0:
        return {"status": "failed", "step": "init", "steps": steps}

    chunk_size = 2400
    for idx in range(0, len(script_b64), chunk_size):
        chunk = script_b64[idx : idx + chunk_size]
        res = dispatch_shell(node_id, windows_append_b64_command(path, chunk), 60, token)
        steps.append({"step": f"append_{idx // chunk_size:03d}", "result": res})
        if str(res.get("status", "")).lower() not in {"ok", "success"} and int(res.get("exit_code") or 1) != 0:
            return {"status": "failed", "step": f"append_{idx // chunk_size:03d}", "steps": steps}

    final = dispatch_shell(node_id, windows_finalize_b64_command(path), 60, token)
    steps.append({"step": "finalize", "result": final})
    ok = str(final.get("status", "")).lower() in {"ok", "success"} or int(final.get("exit_code") or 1) == 0
    return {"status": "ok" if ok else "failed", "steps": steps, "install_path": path}


def deploy(nodes: list[str], token: str) -> dict[str, Any]:
    results = []
    for node_id in nodes:
        result = deploy_one(node_id, token)
        results.append({"node_id": node_id, "result": result})
    return {"action": "deploy", "nodes": results}


def run_plans(nodes: list[str], token: str, no_ollama: bool) -> dict[str, Any]:
    results = []
    for node_id in nodes:
        node = load_node(node_id)
        result = dispatch_shell(node_id, run_plan_command(node_id, node, no_ollama), 180, token)
        results.append({"node_id": node_id, "result": result})
    return {"action": "run-plans", "nodes": results}


def write_status(payload: dict[str, Any]) -> None:
    status = {
        "schema": "clawstack.k10_failover_proxy_ai_status.v1",
        "updated_at": now_iso(),
        "planner_version": PLANNER_VERSION,
        **payload,
    }
    write_json_atomic(STATUS_PATH, status)


def main() -> int:
    parser = argparse.ArgumentParser(description="K10 failover proxy AI harness")
    parser.add_argument(
        "action",
        choices=["status", "heartbeat-once", "deploy", "run-plans", "deploy-and-run"],
    )
    parser.add_argument("--nodes", nargs="*", default=list(DEFAULT_NODES))
    parser.add_argument("--token", default="")
    parser.add_argument("--no-ollama", action="store_true", help="Force deterministic planning on satellites")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    token = args.token or load_env_value("SATELLITE_JOB_TOKEN")
    if args.action in {"status", "deploy", "run-plans", "deploy-and-run"} and not token:
        raise RuntimeError("SATELLITE_JOB_TOKEN missing; refusing to dispatch")

    started = time.time()
    if args.action == "heartbeat-once":
        result = k10_heartbeat()
    elif args.action == "status":
        result = {
            "action": "status",
            "heartbeat": k10_heartbeat(),
            "workers": [probe_worker(node_id, token) for node_id in args.nodes],
        }
    elif args.action == "deploy":
        result = deploy(args.nodes, token)
    elif args.action == "run-plans":
        result = run_plans(args.nodes, token, args.no_ollama)
    else:
        result = {
            "action": "deploy-and-run",
            "deploy": deploy(args.nodes, token),
            "run": run_plans(args.nodes, token, args.no_ollama),
        }

    result["duration_sec"] = round(time.time() - started, 3)
    write_status(result)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False))
        print(f"status: {STATUS_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
