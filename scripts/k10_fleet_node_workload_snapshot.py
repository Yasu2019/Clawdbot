# -*- coding: utf-8 -*-
"""Aggregate per-node current workload for Growth Dashboard fleet utilization board."""
from __future__ import annotations

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

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
OUT = WORKSPACE / "fleet_node_workload_snapshot.json"
DASHBOARD_OUT = WORKSPACE / "apps" / "growth_dashboard" / "fleet_node_workload_snapshot.json"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_satellite_dispatch as sjp


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def idle_jobs_summary(node_result: dict[str, Any]) -> list[str]:
    items: list[str] = []
    for job in node_result.get("jobs") or []:
        kind = job.get("kind") or "job"
        if kind == "cae_dry_run":
            items.append(f"idle:{job.get('category') or 'cae'}(dry)")
        elif kind == "shell":
            items.append(f"idle:{job.get('job_type') or 'shell'}")
        else:
            items.append(f"idle:{kind}")
    return items


def tri_track_for(registry_id: str, tri: dict[str, Any]) -> dict[str, Any] | None:
    mapping = {
        "lavie": "openfoam_lavie",
        "red_lavie": "openradioss_red_lavie",
        "thinkpad": "fem_impact_thinkpad",
    }
    key = mapping.get(registry_id)
    if not key:
        return None
    track = (tri.get("tracks") or {}).get(key) or {}
    last = track.get("last") or {}
    if not last:
        return None
    policy = (tri.get("policy") or {}).get(
        {"lavie": "openfoam", "red_lavie": "openradioss", "thinkpad": "fem_impact"}.get(registry_id, ""),
        "",
    )
    return {
        "running": bool(tri.get("running")),
        "policy": policy,
        "verdict": last.get("verdict"),
        "trial_id": last.get("trial_id"),
        "error": last.get("error"),
        "at": last.get("at"),
        "cycles": track.get("n"),
    }


def lavie_te_work(te: dict[str, Any]) -> dict[str, Any] | None:
    last = te.get("last_cycle") or {}
    if not last:
        return None
    return {
        "mode": te.get("mode"),
        "category": last.get("category"),
        "verdict": last.get("verdict"),
        "trial_id": last.get("trial_id"),
        "at": te.get("updated_at"),
    }


def thinkpad_work(tp_te: dict[str, Any], tp_ssh: dict[str, Any], dxf: dict[str, Any]) -> list[str]:
    out: list[str] = []
    last = (tp_te.get("last_cycle") or {}) if tp_te else {}
    if last.get("category"):
        out.append(f"TE:{last.get('category')} ({last.get('verdict') or '?'})")
    ssh_job = (tp_ssh.get("last_job") or {}) if tp_ssh else {}
    if isinstance(ssh_job, dict) and ssh_job.get("job_type"):
        out.append(f"SSH:{ssh_job.get('job_type')}")
    elif isinstance(ssh_job, str) and ssh_job:
        out.append(f"SSH:{ssh_job}")
    if dxf.get("running"):
        out.append("dxf2step loop")
    elif (dxf.get("last_cycle") or {}).get("job_id"):
        lc = dxf.get("last_cycle") or {}
        out.append(f"dxf2step:{lc.get('status') or lc.get('verdict') or 'last'}")
    return out


def k10_workloads() -> list[str]:
    items: list[str] = []
    fo = read_json(WORKSPACE / "fleet_operations_status.json")
    if fo.get("mode"):
        items.append(f"fleet_ops:{fo.get('mode')}")
    idle = read_json(WORKSPACE / "fleet_idle_dispatch_status.json")
    if idle.get("running"):
        items.append("idle_dispatch:scheduler")
    offload = (idle.get("last_cycle") or {}).get("email_postprocess_offload") or read_json(
        WORKSPACE / "email_postprocess_offload_status.json"
    )
    if offload.get("decision") == "recommend" and offload.get("selected_node"):
        items.append(f"email_offload:recommend->{offload.get('selected_node')}")
    elif offload.get("decision") == "no_capacity":
        items.append("email_offload:no_capacity")
    email = read_json(WORKSPACE / "email_continuous_ingest_status.json")
    if email.get("running"):
        items.append("email_ingest")
    patrol = read_json(WORKSPACE / "central_patrol_status.json")
    if str(patrol.get("stage") or "").lower() not in {"", "idle", "done", "failed"}:
        items.append(f"patrol:{patrol.get('stage')}")
    tri = read_json(WORKSPACE / "k10_tri_track_cae_status.json")
    if tri.get("running"):
        items.append("tri_track:orchestrator")
    cae = read_json(WORKSPACE / "satellite_cae_live_status.json")
    eng = ((cae.get("k10") or {}).get("engine_status") or {})
    if eng.get("phase") not in {None, "", "DONE", "IDLE"}:
        items.append(f"cae_engine:{eng.get('phase')}")
    return items or ["監視・ダッシュボード・軽量サービス（重CAEなし）"]


def worker_online(registry_id: str, token: str) -> tuple[bool, str]:
    try:
        node = sjp.load_node(registry_id)
        url = sjp.worker_base_url(node)
        ok, detail = sjp.probe_worker(url, token)
        return ok, (detail or "")[:120]
    except Exception as exc:
        return False, str(exc)[:120]


def derive_cpu_low_reason(
    registry_id: str,
    state: str,
    labels: list[str],
    worker_ok: bool,
    idle_res: dict[str, Any],
) -> str | None:
    """Node-specific short reason; None = do not show per-row CPU-low line."""
    if not worker_ok:
        return None
    if registry_id == "k10":
        return "重CAEをサテライトへルーティングし、本機は監視・配信のみを行っている"
    if registry_id == "lavie":
        return "重CAEがDocker worker内で動作し、ホストCPU計測に載りにくい"
    if idle_res.get("decision") == "dispatch" or any(str(l).startswith("idle:") for l in labels):
        return "K10 idle dispatchの軽量dry-run/probeのみで本番CAEを回していない"
    if state in {"idle", "light"}:
        if any("DRY_RUN" in str(l) for l in labels):
            return "tri-track/TEがdry-runのみで本番CAEを実行していない"
        return "重いCAEジョブが未割当で待機中"
    return None


def build_node(registry_id: str, ctx: dict[str, Any]) -> dict[str, Any]:
    token = ctx["token"]
    idle_by_node = ctx["idle_by_node"]
    tri = ctx["tri"]
    labels: list[str] = []
    state = "idle"
    detail_parts: list[str] = []

    if registry_id == "k10":
        labels = k10_workloads()
        state = "running" if len(labels) > 1 or "重CAE" in " ".join(labels) else "light"
        return {
            "registry_id": registry_id,
            "state": state,
            "label": " / ".join(labels[:3]),
            "tasks": labels,
            "cpu_low_reason": derive_cpu_low_reason(registry_id, state, labels, True, {}),
        }

    worker_ok, worker_detail = worker_online(registry_id, token)
    if not worker_ok:
        state = "offline"
        detail_parts.append(f"worker offline ({worker_detail})")

    idle_res = idle_by_node.get(registry_id) or {}
    if idle_res.get("reason") == "cae_loop_active":
        state = "blocked"
        labels.append("CAEループ稼働中のためidle配信スキップ")
    elif idle_res.get("decision") == "dispatch":
        labels.extend(idle_jobs_summary(idle_res))
        state = "running"
    elif idle_res.get("reason"):
        detail_parts.append(str(idle_res.get("reason")))

    tt = tri_track_for(registry_id, tri)
    if tt:
        if tt.get("running"):
            state = "running"
            labels.append(f"tri-track:{tt.get('policy')}")
        elif tt.get("verdict"):
            labels.append(f"tri-track:{tt.get('policy')} last={tt.get('verdict')}")

    if registry_id == "lavie":
        te = lavie_te_work(ctx["lavie_te"])
        if te and te.get("category"):
            labels.append(f"TE:{te.get('category')} ({te.get('verdict') or '?'})")
            if te.get("verdict") not in {None, "DRY_RUN"}:
                state = "running"

    if registry_id == "red_lavie":
        rl = ctx["red_loop"]
        if rl.get("running"):
            labels.append("red_lavie非CAEループ")
        lc = rl.get("last_cycle") or {}
        if lc.get("decision") == "skip_guard":
            detail_parts.append("guard:" + ",".join(lc.get("guard_reasons") or [])[:80])

    if registry_id == "thinkpad":
        labels.extend(thinkpad_work(ctx["thinkpad_te"], ctx["thinkpad_ssh"], ctx["thinkpad_dxf"]))

    if registry_id == "dynabook" and not labels and worker_ok:
        labels.append("待機（次のidle CAE dry-run待ち）")

    if not labels:
        if state == "offline":
            labels = ["オフライン / ジョブ受付不可"]
        else:
            labels = ["待機中（重いCAEジョブなし）"]

    cpu_low_reason = derive_cpu_low_reason(registry_id, state, labels, worker_ok, idle_res)

    return {
        "registry_id": registry_id,
        "state": state,
        "worker_online": worker_ok,
        "label": " / ".join(labels[:4]),
        "tasks": labels,
        "detail": " · ".join(detail_parts)[:200] if detail_parts else "",
        "cpu_low_reason": cpu_low_reason,
        "idle_decision": idle_res.get("decision"),
        "idle_reason": idle_res.get("reason"),
    }


def build_snapshot() -> dict[str, Any]:
    idle = read_json(WORKSPACE / "fleet_idle_dispatch_status.json")
    idle_by_node: dict[str, dict[str, Any]] = {}
    for row in (idle.get("last_cycle") or {}).get("node_results") or []:
        key = str(row.get("registry_id") or row.get("node_id") or "").lower()
        if key:
            idle_by_node[key] = row

    ctx = {
        "token": sjp.load_token(),
        "idle_by_node": idle_by_node,
        "tri": read_json(WORKSPACE / "k10_tri_track_cae_status.json"),
        "lavie_te": read_json(WORKSPACE / "lavie_continuous_te_status.json"),
        "red_loop": read_json(WORKSPACE / "red_lavie_continuous_loop_status.json"),
        "thinkpad_te": read_json(WORKSPACE / "thinkpad_continuous_te_status.json"),
        "thinkpad_ssh": read_json(WORKSPACE / "thinkpad_continuous_loop_status.json"),
        "thinkpad_dxf": read_json(WORKSPACE / "thinkpad_dxf2step_te_status.json"),
    }

    registry_ids = [
        "k10",
        "vivobook",
        "dynabook",
        "thinkpad",
        "g3",
        "lavie",
        "red_lavie",
        "hp_watchdog",
    ]
    nodes = {rid: build_node(rid, ctx) for rid in registry_ids}
    return {
        "schema": "clawstack.fleet_node_workload_snapshot.v1",
        "updated_at": now_iso(),
        "cpu_low_fleet_note": (
            "フリート全体のCPUが低く見えるのは正常なことが多いです。"
            "K10 Idle Dispatchは「CPU70%未満のときだけ」数秒の軽量probeを配信します。"
            "OpenFOAM/OpenRadioss等の重CAEは別ループ(tri-track / continuous TE)で、"
            "停止中・dry-run・workerオフライン時はCPUはほぼアイドルです。"
        ),
        "nodes": nodes,
    }


def main() -> int:
    payload = build_snapshot()
    write_json(OUT, payload)
    write_json(DASHBOARD_OUT, payload)
    print(json.dumps({"ok": True, "written": str(DASHBOARD_OUT), "nodes": len(payload["nodes"])}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
