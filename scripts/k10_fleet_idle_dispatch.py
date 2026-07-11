# -*- coding: utf-8 -*-
"""Central K10 fleet idle dispatch: poll node metrics and assign jobs when idle and cool."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx
import psutil
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
POLICY_PATH = WORKSPACE / "fleet_idle_dispatch_policy.yaml"
STATE_PATH = WORKSPACE / "fleet_idle_dispatch_state.json"
STATUS_PATH = WORKSPACE / "fleet_idle_dispatch_status.json"
DASHBOARD_STATUS_PATH = WORKSPACE / "apps" / "growth_dashboard" / "fleet_idle_dispatch_status.json"
LOG_PATH = WORKSPACE / "fleet_idle_dispatch_log.jsonl"
EMAIL_OFFLOAD_STATUS_PATH = WORKSPACE / "email_postprocess_offload_status.json"
DASHBOARD_EMAIL_OFFLOAD_STATUS_PATH = (
    WORKSPACE / "apps" / "growth_dashboard" / "email_postprocess_offload_status.json"
)
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_fleet_idle_job_commands as job_cmds
import k10_satellite_dispatch as sjp


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    entry = dict(entry)
    entry["logged_at"] = now_iso()
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        raise RuntimeError(f"missing policy: {POLICY_PATH}")
    return yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8")) or {}


def node_metrics_url(registry_id: str) -> str:
    reg = sjp.load_node(registry_id)
    ip = (reg.get("tailscale_ip") or reg.get("lan_ip") or "").strip()
    port = int(reg.get("monitor_agent_port") or 8111)
    if reg.get("monitor_agent_url"):
        return str(reg["monitor_agent_url"]).replace("/metrics", "") + "/metrics"
    if not ip:
        raise RuntimeError(f"{registry_id}: no tailscale_ip for metrics")
    return f"http://{ip}:{port}/metrics"


def fetch_metrics(registry_id: str) -> tuple[bool, dict[str, Any], str]:
    if registry_id == "thinkpad":
        try:
            import thinkpad_ssh_metrics

            data = thinkpad_ssh_metrics.collect_metrics()
            if data.get("ok"):
                return True, data, "ssh_metrics"
        except Exception:
            pass
    try:
        url = node_metrics_url(registry_id)
        resp = httpx.get(url, timeout=10.0)
        if resp.status_code != 200:
            return False, {}, f"{url} -> HTTP {resp.status_code}"
        data = resp.json()
        if not isinstance(data, dict):
            return False, {}, f"{url} -> non-object json"
        return True, data, url
    except Exception as exc:
        return False, {}, str(exc)[:300]


def is_daytime_blocked(policy: dict[str, Any], node_id: str) -> bool:
    cfg = policy.get("daytime_light_only") or {}
    if not cfg.get("enabled"):
        return False
    ids = {str(x).lower() for x in (cfg.get("node_ids") or [])}
    if node_id.lower() not in ids:
        return False
    hour = datetime.now(JST).hour
    start = int(cfg.get("start_hour") or 8)
    end = int(cfg.get("end_hour") or 19)
    return start <= hour < end


def is_cae_loop_active(node_cfg: dict[str, Any]) -> bool:
    rel = node_cfg.get("cae_status_path") or ""
    if not rel:
        return False
    status = read_json(WORKSPACE / rel)
    if not status:
        return False
    if status.get("running"):
        return True
    last = status.get("last_cycle") or {}
    stage = str(last.get("stage") or "")
    if stage in {"dispatch", "trial_running", "openfoam", "openradioss"}:
        return True
    return False


def evaluate_idle(
    metrics: dict[str, Any],
    thresholds: dict[str, Any],
) -> tuple[bool, str]:
    def as_float(key: str, default: float = 0.0) -> float:
        try:
            return float(metrics.get(key) or default)
        except (TypeError, ValueError):
            return default

    cpu = as_float("cpu_usage_percent", 100.0)
    ram = as_float("ram_usage_percent", 100.0)
    temp = as_float("thermal_control_temp_c", as_float("cpu_temp_celsius"))
    max_cpu = float(thresholds.get("max_cpu_percent") or 70)
    max_ram = float(thresholds.get("max_ram_percent") or 75)
    max_temp = float(thresholds.get("max_temp_c") or 75)

    if cpu >= max_cpu:
        return False, f"cpu {cpu:.1f}% >= {max_cpu:.1f}%"
    if ram >= max_ram:
        return False, f"ram {ram:.1f}% >= {max_ram:.1f}%"
    if temp > 0 and temp >= max_temp:
        return False, f"temp {temp:.1f}C >= {max_temp:.1f}C"
    if thresholds.get("block_when_throttling", True):
        limit = as_float("cpu_limit_percent", 100.0)
        block_at = float(thresholds.get("block_cpu_limit_at_or_below") or 10)
        if metrics.get("is_throttling") or limit <= block_at:
            return False, f"thermal throttle (cpu_limit={limit:.0f}%)"
    return True, f"idle ok cpu={cpu:.1f}% ram={ram:.1f}% temp={temp:.1f}C"


def local_k10_metrics() -> dict[str, float]:
    return {
        "cpu_usage_percent": round(float(psutil.cpu_percent(interval=0.2)), 1),
        "ram_usage_percent": round(float(psutil.virtual_memory().percent), 1),
    }


def build_email_offload_plan(
    cfg: dict[str, Any],
    k10_metrics: dict[str, Any],
    observations: list[dict[str, Any]],
) -> dict[str, Any]:
    max_k10_cpu = float(cfg.get("k10_max_cpu_percent") or 70)
    max_k10_ram = float(cfg.get("k10_max_ram_percent") or 80)
    k10_cpu = float(k10_metrics.get("cpu_usage_percent") or 0)
    k10_ram = float(k10_metrics.get("ram_usage_percent") or 0)
    pressure_reasons: list[str] = []
    if k10_cpu >= max_k10_cpu:
        pressure_reasons.append(f"cpu {k10_cpu:.1f}% >= {max_k10_cpu:.1f}%")
    if k10_ram >= max_k10_ram:
        pressure_reasons.append(f"ram {k10_ram:.1f}% >= {max_k10_ram:.1f}%")

    eligible = [row for row in observations if row.get("eligible")]
    eligible.sort(key=lambda row: float(row.get("load_score") or 999))
    selected = eligible[0].get("node_id") if pressure_reasons and eligible else None
    dispatch_enabled = bool(cfg.get("dispatch_enabled", False))
    if not pressure_reasons:
        decision = "not_needed"
    elif not selected:
        decision = "no_capacity"
    elif dispatch_enabled:
        decision = "dispatch_enabled_no_sender_implemented"
    else:
        decision = "recommend"

    return {
        "schema": "clawstack.email_postprocess_offload_plan.v1",
        "mode": "observe" if not dispatch_enabled else "guarded",
        "decision": decision,
        "k10_metrics": k10_metrics,
        "k10_pressure": bool(pressure_reasons),
        "pressure_reasons": pressure_reasons,
        "selected_node": selected,
        "candidates": observations,
        "allowed_work": list(cfg.get("allowed_work") or []),
        "forbidden_transfer": list(cfg.get("forbidden_transfer") or []),
        "dispatch_enabled": dispatch_enabled,
        "safety": {
            "gmail_credentials_remain_on_k10": True,
            "production_db_remote_write": False,
            "raw_mail_remote_transfer": False,
        },
    }


def evaluate_email_offload(policy: dict[str, Any], token: str) -> dict[str, Any]:
    cfg = policy.get("email_postprocess_offload") or {}
    if not cfg.get("enabled", False):
        return {"decision": "disabled", "mode": "observe"}

    thresholds = cfg.get("candidate_thresholds") or {}
    observations: list[dict[str, Any]] = []
    for node_id in cfg.get("candidate_node_ids") or []:
        row: dict[str, Any] = {"node_id": str(node_id), "eligible": False}
        ok, metrics, detail = fetch_metrics(str(node_id))
        row["metrics_detail"] = detail
        if not ok:
            row["reason"] = "metrics_unavailable"
            observations.append(row)
            continue
        idle_ok, idle_reason = evaluate_idle(metrics, thresholds)
        row["metrics"] = {
            "cpu_usage_percent": metrics.get("cpu_usage_percent"),
            "ram_usage_percent": metrics.get("ram_usage_percent"),
            "cpu_temp_celsius": metrics.get("cpu_temp_celsius"),
        }
        row["load_score"] = round(
            float(metrics.get("cpu_usage_percent") or 100)
            + float(metrics.get("ram_usage_percent") or 100),
            1,
        )
        if not idle_ok:
            row["reason"] = idle_reason
            observations.append(row)
            continue
        try:
            node = sjp.load_node(str(node_id))
            worker_ok, worker_detail = sjp.probe_worker(sjp.worker_base_url(node), token)
        except Exception as exc:
            worker_ok, worker_detail = False, str(exc)[:160]
        row["worker_online"] = worker_ok
        row["reason"] = idle_reason if worker_ok else f"worker_offline: {worker_detail}"
        row["eligible"] = worker_ok
        observations.append(row)

    return build_email_offload_plan(cfg, local_k10_metrics(), observations)


def write_email_offload_status(plan: dict[str, Any]) -> None:
    payload = dict(plan)
    payload["updated_at"] = now_iso()
    write_json_atomic(EMAIL_OFFLOAD_STATUS_PATH, payload)
    write_json_atomic(DASHBOARD_EMAIL_OFFLOAD_STATUS_PATH, payload)


def next_sequence_items(sequence: list[str], state: dict[str, Any], node_id: str, count: int) -> list[str]:
    key = f"seq_idx_{node_id}"
    idx = int(state.get(key) or 0)
    if not sequence:
        return []
    picked = [sequence[(idx + i) % len(sequence)] for i in range(count)]
    state[key] = idx + count
    return picked


def dispatch_shell(
    registry_id: str,
    job_type: str,
    command: str,
    timeout: int,
    token: str,
) -> dict[str, Any]:
    node = sjp.load_node(registry_id)
    base_url = sjp.worker_base_url(node)
    job = {
        "job_id": f"idle-{registry_id}-{job_type}-{uuid.uuid4().hex[:8]}",
        "type": "shell",
        "timeout_sec": timeout,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    result = sjp.dispatch_job(base_url, token, job, timeout)
    append_log({"node": registry_id, "job_type": job_type, "request": job, "result": result})
    return result


def dispatch_dynabook_dry_run(
    registry_id: str,
    category: str,
    timeout: int,
    token: str,
) -> dict[str, Any]:
    node = sjp.load_node(registry_id)
    base_url = sjp.worker_base_url(node)
    repo_root = node.get("cae_repo_root") or r"C:\dynabook_usb_pack"
    job = {
        "job_id": f"idle-dynabook-dry-{uuid.uuid4().hex[:8]}",
        "type": "cae_trial",
        "timeout_sec": timeout,
        "payload": {"category": category, "dry_run": True, "repo_root": repo_root},
        "report": {"mode": "sync"},
    }
    result = sjp.dispatch_job(base_url, token, job, timeout)
    append_log({"node": registry_id, "job_type": f"cae_dry_{category}", "request": job, "result": result})
    return result


def dispatch_node_jobs(
    node_id: str,
    node_cfg: dict[str, Any],
    policy: dict[str, Any],
    state: dict[str, Any],
    token: str,
) -> dict[str, Any]:
    registry_id = str(node_cfg.get("registry_id") or node_id)
    result: dict[str, Any] = {
        "node_id": node_id,
        "registry_id": registry_id,
        "decision": "skip",
        "jobs": [],
    }

    if is_daytime_blocked(policy, node_id):
        result["reason"] = "daytime_light_only"
        return result

    if node_cfg.get("skip_when_cae_loop_active") and is_cae_loop_active(node_cfg):
        result["reason"] = "cae_loop_active"
        return result

    ok_metrics, metrics, metrics_detail = fetch_metrics(registry_id)
    result["metrics_detail"] = metrics_detail
    if not ok_metrics:
        result["reason"] = f"metrics_unavailable: {metrics_detail}"
        return result

    thresholds = policy.get("idle_thresholds") or {}
    idle_ok, idle_reason = evaluate_idle(metrics, thresholds)
    result["metrics_snapshot"] = {
        "cpu_usage_percent": metrics.get("cpu_usage_percent"),
        "ram_usage_percent": metrics.get("ram_usage_percent"),
        "cpu_temp_celsius": metrics.get("cpu_temp_celsius"),
        "thermal_control_temp_c": metrics.get("thermal_control_temp_c"),
        "cpu_limit_percent": metrics.get("cpu_limit_percent"),
        "is_throttling": metrics.get("is_throttling"),
    }
    if not idle_ok:
        result["reason"] = idle_reason
        return result

    transport = node_cfg.get("transport") or "job_worker"
    if transport != "job_worker":
        result["reason"] = f"unsupported transport {transport}"
        return result

    node = sjp.load_node(registry_id)
    base_url = sjp.worker_base_url(node)
    worker_ok, worker_detail = sjp.probe_worker(base_url, token)
    if not worker_ok:
        result["reason"] = f"worker_offline: {worker_detail}"
        return result

    jobs_per_cycle = int(node_cfg.get("jobs_per_cycle") or 1)
    timeout = int((node.get("worker_flags") or {}).get("max_timeout_sec") or 120)
    dispatched = 0

    if node_id == "dynabook":
        categories = list(node_cfg.get("cae_dry_run_categories") or ["press_blanking"])
        cat_idx_key = "dynabook_cat_idx"
        cat_idx = int(state.get(cat_idx_key) or 0)
        category = categories[cat_idx % len(categories)]
        state[cat_idx_key] = cat_idx + 1
        dry_result = dispatch_dynabook_dry_run(registry_id, category, timeout, token)
        result["jobs"].append({"kind": "cae_dry_run", "category": category, "result": dry_result})
        dispatched += 1
        shell_seq = list(node_cfg.get("shell_job_sequence") or [])
        if dispatched < jobs_per_cycle and shell_seq:
            shell_map = job_cmds.NODE_COMMAND_MAP.get("dynabook") or {}
            for job_type in next_sequence_items(shell_seq, state, node_id, 1):
                cmd = shell_map.get(job_type)
                if not cmd:
                    continue
                shell_result = dispatch_shell(registry_id, job_type, cmd, min(timeout, 60), token)
                result["jobs"].append({"kind": "shell", "job_type": job_type, "result": shell_result})
                dispatched += 1
                break
    else:
        sequence = list(node_cfg.get("job_sequence") or [])
        cmd_map = job_cmds.NODE_COMMAND_MAP.get(registry_id) or job_cmds.NODE_COMMAND_MAP.get(node_id) or {}
        for job_type in next_sequence_items(sequence, state, node_id, jobs_per_cycle):
            cmd = cmd_map.get(job_type)
            if not cmd:
                result["jobs"].append({"kind": "shell", "job_type": job_type, "error": "command_missing"})
                continue
            shell_result = dispatch_shell(registry_id, job_type, cmd, timeout, token)
            result["jobs"].append({"kind": "shell", "job_type": job_type, "result": shell_result})
            dispatched += 1

    result["decision"] = "dispatch" if dispatched else "skip"
    result["reason"] = idle_reason
    result["jobs_dispatched"] = dispatched
    return result


def run_k10_local_harvest(policy: dict[str, Any], state: dict[str, Any]) -> dict[str, Any]:
    cfg = policy.get("k10_local_idle_harvest") or {}
    if not cfg.get("enabled", True):
        return {"decision": "skip", "reason": "k10_local_disabled"}

    sys.path.insert(0, str(WORKSPACE))
    try:
        import harvest_resource_coordinator as coord
    except Exception as exc:
        return {"decision": "error", "reason": str(exc)[:200]}

    ok, reason, metrics = coord.evaluate_resources(coord.load_policy())
    if not ok:
        state["k10_idle_streak"] = 0
        return {"decision": "skip", "reason": reason, "metrics": metrics}

    streak = int(state.get("k10_idle_streak") or 0) + 1
    state["k10_idle_streak"] = streak
    min_cycles = int(cfg.get("min_idle_cycles") or 2)
    if streak < min_cycles:
        return {
            "decision": "skip",
            "reason": f"idle_streak {streak}/{min_cycles}",
            "metrics": metrics,
        }

    script_rel = str(cfg.get("script") or "scripts/harvest_idle_slice.py")
    script = ROOT / script_rel
    if not script.exists():
        return {"decision": "error", "reason": f"missing {script}"}

    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        timeout=3600,
        encoding="utf-8",
        errors="replace",
    )
    state["k10_idle_streak"] = 0
    append_log({"k10_local_harvest": {"exit_code": proc.returncode, "tail": (proc.stdout or "")[-400:]}})
    return {
        "decision": "harvest" if proc.returncode == 0 else "failed",
        "exit_code": proc.returncode,
        "metrics": metrics,
        "tail": (proc.stdout or "")[-300:],
    }


def run_cycle(policy: dict[str, Any] | None = None) -> dict[str, Any]:
    policy = policy or load_policy()
    state = read_json(STATE_PATH)
    token = sjp.load_token()
    thresholds = policy.get("idle_thresholds") or {}
    nodes_cfg = policy.get("nodes") or {}

    cycle: dict[str, Any] = {
        "schema": "clawstack.fleet_idle_dispatch_cycle.v1",
        "at": now_iso(),
        "thresholds": thresholds,
        "node_results": [],
    }

    for node_id, node_cfg in nodes_cfg.items():
        if not node_cfg.get("enabled", True):
            cycle["node_results"].append({"node_id": node_id, "decision": "skip", "reason": "disabled"})
            continue
        try:
            node_result = dispatch_node_jobs(node_id, node_cfg, policy, state, token)
        except Exception as exc:
            node_result = {"node_id": node_id, "decision": "error", "reason": str(exc)[:300]}
        cycle["node_results"].append(node_result)

    try:
        cycle["email_postprocess_offload"] = evaluate_email_offload(policy, token)
        write_email_offload_status(cycle["email_postprocess_offload"])
    except Exception as exc:
        cycle["email_postprocess_offload"] = {
            "decision": "error",
            "mode": "observe",
            "reason": str(exc)[:300],
        }

    try:
        cycle["k10_local_harvest"] = run_k10_local_harvest(policy, state)
    except Exception as exc:
        cycle["k10_local_harvest"] = {"decision": "error", "reason": str(exc)[:300]}

    write_json_atomic(STATE_PATH, state)
    dispatched_total = sum(int(r.get("jobs_dispatched") or 0) for r in cycle["node_results"])
    eligible = sum(1 for r in cycle["node_results"] if r.get("decision") == "dispatch")
    cycle["summary"] = {
        "nodes_polled": len(cycle["node_results"]),
        "nodes_dispatched": eligible,
        "jobs_dispatched": dispatched_total,
    }
    append_log({"cycle": cycle})
    return cycle


def write_status(running: bool, cycle: dict[str, Any] | None, poll: int) -> None:
    payload = {
        "schema": "clawstack.fleet_idle_dispatch_status.v1",
        "updated_at": now_iso(),
        "running": running,
        "poll_interval_sec": poll,
        "policy_path": str(POLICY_PATH),
        "thresholds": (load_policy().get("idle_thresholds") or {}),
        "last_cycle": cycle,
    }
    write_json_atomic(STATUS_PATH, payload)
    write_json_atomic(DASHBOARD_STATUS_PATH, payload)
    try:
        import k10_fleet_node_workload_snapshot as workload_snap

        snap = workload_snap.build_snapshot()
        workload_snap.write_json(workload_snap.DASHBOARD_OUT, snap)
        workload_snap.write_json(workload_snap.OUT, snap)
    except Exception as exc:
        append_log({"workload_snapshot_error": str(exc)[:200]})


def main() -> int:
    parser = argparse.ArgumentParser(description="K10 central fleet idle dispatch")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=0)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--observe-email-offload", action="store_true")
    args = parser.parse_args()

    policy = load_policy()
    poll = args.poll_seconds or int(policy.get("poll_interval_sec") or 300)

    if args.observe_email_offload:
        plan = evaluate_email_offload(policy, sjp.load_token())
        write_email_offload_status(plan)
        print(json.dumps(plan, ensure_ascii=False, indent=2))
        return 0

    if args.once:
        cycle = run_cycle(policy)
        write_status(False, cycle, poll)
        if args.json:
            print(json.dumps(cycle, ensure_ascii=False, indent=2))
        else:
            s = cycle.get("summary") or {}
            print(
                f"[idle-dispatch] nodes={s.get('nodes_polled')} "
                f"dispatched={s.get('nodes_dispatched')} jobs={s.get('jobs_dispatched')}"
            )
        return 0

    write_status(True, None, poll)
    print(f"[idle-dispatch] central scheduler every {poll}s (Ctrl+C to stop)")
    while True:
        try:
            cycle = run_cycle(policy)
            write_status(True, cycle, poll)
            if not args.json:
                s = cycle.get("summary") or {}
                print(
                    f"[{now_iso()}] nodes={s.get('nodes_polled')} "
                    f"dispatched={s.get('nodes_dispatched')} jobs={s.get('jobs_dispatched')}",
                    flush=True,
                )
        except Exception as exc:
            write_status(True, {"decision": "error", "error": str(exc)[:300]}, poll)
            print(f"[NG] {exc}", file=sys.stderr)
        time.sleep(max(60, poll))


if __name__ == "__main__":
    raise SystemExit(main())
