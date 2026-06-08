# -*- coding: utf-8 -*-
"""K10 -> LAVIE continuous CAE trial-and-error loop with statistical feedback (24/365).

K10 selects categories (UCB1 bandit), proposes parameters, dispatches cae_trial jobs to
LAVIE, merges results into cae_te_log.json, and updates rolling statistics.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import random
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

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
JST = timezone(timedelta(hours=9))
STATE_PATH = WORKSPACE / "lavie_continuous_te_state.json"
STATUS_PATH = WORKSPACE / "lavie_continuous_te_status.json"
ALLOC_OVERRIDES_PATH = WORKSPACE / "lavie_te_allocation_overrides.json"
TE_LOG = ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

import httpx

import cae_failure_analysis as failure_analysis
import cae_workload_router as router
import k10_satellite_cae_dispatch as cae_dispatch
import k10_satellite_dispatch as sjp
from outbound_delivery_guard import (
    ensure_allowed_telegram_chat_id,
    initialize_guard_status,
)

OPENFOAM_CATEGORIES = {"resin_fill_cad", "resin_fill_vof"}
HEAVY_LAVIE_CATEGORIES = {"resin_fill_cad", "resin_fill_vof", "resin_fill"}
LAVIE_GUARD_TIMEOUT_THRESHOLD = 2
LAVIE_GUARD_WINDOW_MINUTES = 120
LAVIE_GUARD_COOLDOWN_MINUTES = 180
PP_PLATE_STEP = "data/cae_te_workspace/samples/moldflow/pp_plate/pp_plate_100x60x2.step"
PP_PLATE_GATE = "data/cae_te_workspace/samples/moldflow/pp_plate/gate_spec_pp_center.json"
MOLDFLOW_CAD_BASE: dict[str, Any] = {
    "physics_category": "resin_fill_closed_pack",
    "mesh_mode": "blockmesh_bbox",
    "mesh_nx": 40,
    "polymer_nu": 0.01,
    "pack_end_time": 0.32,
    "pack_pressure_MPa": 15.0,
    "pack_inlet_velocity": 0.06,
    "gate_count": 1,
    "gate_position": "center",
    "step_path": PP_PLATE_STEP,
    "gate_spec_path": PP_PLATE_GATE,
}
PARAM_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "resin_fill_cad": {
        "polymer_nu": (0.005, 0.02),
        "inlet_velocity": (0.6, 1.15),
        "pack_pressure_MPa": (5.0, 25.0),
        "pack_inlet_velocity": (0.03, 0.1),
    },
    "resin_fill_vof": {
        "polymer_nu": (0.005, 0.02),
        "inlet_velocity": (0.6, 1.15),
    },
    "press_blanking": {"clearance_pct": (3.0, 12.0), "punch_speed_mms": (2000.0, 8000.0)},
    "press_crushing": {"crush_ratio": (0.05, 0.25)},
    "press_bending": {"bend_angle_deg": (30.0, 120.0)},
    "press_blanking_stripper": {"stripper_force_kn": (5.0, 40.0)},
}


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def now_jst_text() -> str:
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")


def parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    raw = str(value).strip()
    for fmt in ("%Y-%m-%d %H:%M:%S JST", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            if fmt.endswith("JST"):
                return datetime.strptime(raw, fmt).replace(tzinfo=JST)
            return datetime.strptime(raw, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except Exception:
        return None


def load_telegram_config() -> tuple[str, str]:
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip('"').strip("'")
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip('"').strip("'")
    env_path = ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN=") and not bot:
                bot = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("TELEGRAM_CHAT_ID=") and not chat:
                chat = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not bot or not chat:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing")
    return bot, chat


def send_telegram(text: str) -> dict[str, Any]:
    bot, chat = load_telegram_config()
    chat_id = ensure_allowed_telegram_chat_id(chat, "lavie_continuous_te_loop.send_telegram")
    body = (text or "")[:4000]
    r = httpx.post(
        f"https://api.telegram.org/bot{bot}/sendMessage",
        data={"chat_id": chat_id, "text": body},
        timeout=20,
    )
    out: dict[str, Any] = {"http_status": r.status_code}
    try:
        out["response"] = r.json()
    except Exception:
        out["response_text"] = r.text[:300]
    return out


def should_notify(state: dict[str, Any], key: str, cooldown_minutes: int) -> bool:
    sent = (state.get("telegram_notifications") or {}).get(key, {})
    sent_at = parse_dt(sent.get("sent_at"))
    if sent_at is None:
        return True
    return (datetime.now(JST) - sent_at.astimezone(JST)) >= timedelta(minutes=cooldown_minutes)


def remember_notification(state: dict[str, Any], key: str, detail: str) -> None:
    state.setdefault("telegram_notifications", {})
    state["telegram_notifications"][key] = {"sent_at": now_jst_text(), "detail": detail[:200]}


def format_cycle_message(cycle: dict[str, Any], state: dict[str, Any], poll_seconds: int) -> str:
    rolling = rolling_lavie_summary(24)
    lines = [
        "LAVIE 24/365 CAE T&E",
        f"Time: {now_jst_text()}",
        f"Cycle: {state.get('total_cycles', 0)} (poll {poll_seconds}s)",
    ]
    if cycle.get("ok"):
        lines.append(
            f"Trial: {cycle.get('category')} / {cycle.get('verdict')} "
            f"dry={cycle.get('dry_run')} reward={cycle.get('reward')}"
        )
        if cycle.get("params"):
            lines.append(f"Params: {cycle.get('params')}")
        lines.append(f"Job: {cycle.get('trial_id')}")
    else:
        lines.append(f"WARN stage={cycle.get('stage')} detail={cycle.get('detail') or cycle.get('error')}")
    best = state.get("best_scores") or {}
    if best:
        top = max(best.items(), key=lambda kv: float(kv[1]))
        lines.append(f"Best UCB score: {top[0]}={top[1]:.3f}")
    lines.append(
        f"LAVIE 24h: trials={rolling.get('count')} success={rolling.get('success')} "
        f"dry={rolling.get('dry_run')} rate={rolling.get('success_rate_pct')}%"
    )
    return "\n".join(lines)


def dispatch_lavie_fill_video_telegram(
    trial_id: str,
    run_dir: str = "",
    *,
    cfg: dict[str, Any] | None = None,
    category: str = "resin_fill_cad",
    timeout_sec: int = 900,
) -> dict[str, Any]:
    """
    Send VOF fill MP4 after LAVIE SUCCESS.
    Prefer K10 pull render (pyvista/ffmpeg on K10); optional LAVIE local if tools ready.
    """
    import lavie_cae_video_support as lcv

    cfg = cfg or router.load_config()
    return lcv.send_fill_video_after_success(
        trial_id,
        category=category,
        run_dir=run_dir,
        cfg=cfg,
    )


def dispatch_lavie_paraview_telegram(
    trial_id: str,
    *,
    cfg: dict[str, Any] | None = None,
    timeout_sec: int = 240,
) -> dict[str, Any] | None:
    """Legacy |U| PNG -- skipped for moldflow; kept for non-VOF categories."""
    return None


def maybe_notify_telegram_photo(
    state: dict[str, Any],
    cycle: dict[str, Any],
    *,
    notify_cooldown_minutes: int = 60,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """After SUCCESS: 3D VOF fill MP4 or OpenRadioss video only (no 2D |U| ParaView)."""
    if not cycle.get("ok") or cycle.get("dry_run"):
        return None
    if str(cycle.get("verdict") or "") != "SUCCESS":
        return None
    category = str(cycle.get("category") or "")
    if category in ("resin_flow", "resin_flow_opt"):
        return None
    trial_id = str(cycle.get("trial_id") or "")
    try:
        import cae_te_visual_report as vis

        trial = vis.find_trial(trial_id=trial_id) if trial_id else vis.find_trial(category=category)
    except Exception:
        trial = None

    if trial and trial.get("fill_video_telegram_sent"):
        key = f"fill_video_{category}"
        remember_notification(state, key, trial_id)
        return {"ok": True, "source": "fill_video_on_host", "trial_id": trial_id}

    if trial and str(trial.get("solver") or "") == "openradioss" and trial_id:
        cat = str(trial.get("category") or "")
        if cat.startswith("press_"):
            key = f"or_video_{category}"
            if should_notify(state, key, notify_cooldown_minutes):
                try:
                    run_dir = str(trial.get("run_dir") or "")
                    repo = (cfg or router.load_config()).get("cae_workspace_sync", {}).get(
                        "lavie_repo_root", "C:/lavie_usb_pack"
                    )
                    workspace = (cfg or router.load_config()).get("cae_workspace_sync", {}).get(
                        "lavie_work_dir", "E:/clawstack_satellite/data/work/cae_te_workspace"
                    )
                    rd = run_dir or f"{workspace}\\runs\\{trial_id}"
                    cmd = (
                        f'cd /d "{repo}" && set CAE_PARAVIEW_TELEGRAM=0&& '
                        f'"{sys.executable}" scripts\\openradioss_vtk_video_telegram.py '
                        f'--run-dir "{rd}" --trial-id "{trial_id}" --category "{cat}" --host lavie'
                    )
                    token = sjp.load_token()
                    node_info = sjp.load_node("lavie")
                    base_url = sjp.worker_base_url(node_info)
                    job = {
                        "job_id": f"orvid-{trial_id[:40]}",
                        "type": "shell",
                        "timeout_sec": 600,
                        "payload": {"command": cmd},
                        "report": {"mode": "sync"},
                    }
                    result = sjp.dispatch_job(base_url, token, job, 630)
                    remember_notification(state, key, trial_id)
                    return {
                        "ok": True,
                        "source": "lavie_openradioss_video",
                        "trial_id": trial_id,
                        "worker": result,
                    }
                except Exception as exc:
                    print(f"[WARN] LAVIE OpenRadioss video dispatch failed: {exc}")

    if trial and str(trial.get("solver") or "") == "openfoam" and trial_id:
        cat = str(trial.get("category") or "")
        if cat in ("resin_fill_cad", "resin_fill_vof", "resin_fill_closed_pack", "resin_fill_pack"):
            key = f"fill_video_{category}"
            if should_notify(state, key, notify_cooldown_minutes):
                try:
                    run_dir = str(trial.get("run_dir") or "")
                    cat = str(trial.get("category") or cat)
                    result = dispatch_lavie_fill_video_telegram(
                        trial_id, run_dir, cfg=cfg, category=cat, timeout_sec=900
                    )
                    if result.get("ok"):
                        remember_notification(state, key, trial_id)
                        return {
                            "ok": True,
                            "source": result.get("source", "lavie_fill_video"),
                            "trial_id": trial_id,
                            "detail": result,
                        }
                    print(
                        f"[WARN] fill video not sent trial={trial_id}: "
                        f"{result.get('error', result)}",
                        flush=True,
                    )
                except Exception as exc:
                    print(f"[WARN] LAVIE fill video Telegram dispatch failed: {exc}")

    key = f"photo_{category}"
    if not should_notify(state, key, notify_cooldown_minutes):
        return None
    try:
        import cae_te_visual_report as vis

        if not trial:
            trial = vis.find_trial(trial_id=trial_id) if trial_id else vis.find_trial(category=category)
        if not trial:
            return None
        vis.send_trial_visual(trial, send_before=False, send_after=True)
        remember_notification(state, key, trial_id)
        return {"ok": True, "trial_id": trial_id, "source": "matplotlib"}
    except Exception as exc:
        print(f"[WARN] Telegram photo skipped: {exc}")
        return None


def maybe_notify_telegram(
    state: dict[str, Any],
    cycle: dict[str, Any],
    poll_seconds: int,
    *,
    notify_cooldown_minutes: int,
    startup: bool,
) -> dict[str, Any] | None:
    if startup:
        msg = (
            "LAVIE 24/365 CAE loop START\n"
            f"Time: {now_jst_text()}\n"
            f"Poll: {poll_seconds}s\n"
            "K10 -> LAVIE trial-and-error with UCB1 stats"
        )
        result = send_telegram(msg)
        remember_notification(state, "startup", "started")
        return result

    verdict = str(cycle.get("verdict") or "")
    if not cycle.get("ok"):
        key = f"warn_{cycle.get('stage') or 'fail'}"
        if should_notify(state, key, max(15, notify_cooldown_minutes // 2)):
            result = send_telegram(format_cycle_message(cycle, state, poll_seconds))
            remember_notification(state, key, key)
            return result
        return None

    if verdict == "SUCCESS":
        key = f"success_{cycle.get('category')}"
        if should_notify(state, key, max(30, notify_cooldown_minutes // 2)):
            result = send_telegram(format_cycle_message(cycle, state, poll_seconds))
            remember_notification(state, key, verdict)
            maybe_notify_telegram_photo(state, cycle, notify_cooldown_minutes=60)
            return result
        return None

    if should_notify(state, "cycle_summary", notify_cooldown_minutes):
        result = send_telegram(format_cycle_message(cycle, state, poll_seconds))
        remember_notification(state, "cycle_summary", verdict or "ok")
        return result
    return None


def load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    if not path.exists():
        return dict(default)
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return dict(default)


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_allocation_overrides() -> dict[str, Any]:
    if not ALLOC_OVERRIDES_PATH.exists():
        return {}
    try:
        return json.loads(ALLOC_OVERRIDES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def lavie_categories(cfg: dict[str, Any]) -> list[str]:
    overrides = load_allocation_overrides()
    active = overrides.get("active_categories") or []
    exclude = set(overrides.get("exclude_categories") or [])
    if active:
        return [c for c in active if c not in exclude]
    cats: list[str] = []
    for key in ("lavie_openfoam_categories", "light_categories"):
        for c in cfg.get(key) or []:
            if c not in cats and c not in exclude:
                cats.append(c)
    return cats or ["resin_fill_cad", "press_blanking"]


def verdict_reward(verdict: str) -> float:
    return {
        "SUCCESS": 1.0,
        "DRY_RUN": 0.35,
        "FAILED": 0.15,
        "SKIPPED": 0.1,
        "PREGATE_FAIL": 0.0,
        "ERROR": 0.0,
        "TIMEOUT": 0.0,
    }.get(verdict or "ERROR", 0.0)


def defect_bonus(trial: dict[str, Any]) -> float:
    defects = trial.get("defects_detected") or {}
    if not isinstance(defects, dict):
        return 0.0
    bonus = 0.0
    if "short_shot_risk" in defects:
        try:
            bonus += max(0.0, 0.2 * (1.0 - float(defects["short_shot_risk"])))
        except (TypeError, ValueError):
            pass
    if "pressure_drop_MPa" in defects:
        try:
            pd = float(defects["pressure_drop_MPa"])
            bonus += max(0.0, 0.1 * (1.0 - min(pd, 1.0)))
        except (TypeError, ValueError):
            pass
    return bonus


def pick_category_ucb1(state: dict[str, Any], categories: list[str]) -> str:
    stats = state.setdefault("category_stats", {})
    total = sum(int((stats.get(c) or {}).get("n", 0)) for c in categories) + 1
    best_cat = categories[0]
    best_score = -1.0
    for cat in categories:
        rec = stats.setdefault(cat, {"n": 0, "reward_sum": 0.0, "avg_reward": 0.0})
        n = int(rec.get("n") or 0)
        avg = float(rec.get("avg_reward") or 0.0)
        if n == 0:
            return cat
        ucb = avg + math.sqrt(2.0 * math.log(max(total, 2)) / n)
        if ucb > best_score:
            best_score = ucb
            best_cat = cat
    return best_cat


def suggest_params(category: str, state: dict[str, Any]) -> dict[str, float]:
    overrides = load_allocation_overrides()
    param_overrides = overrides.get("param_overrides") or {}
    ranges = dict(PARAM_RANGES.get(category, {}))
    for key, pair in (param_overrides.get(category) or {}).items():
        if isinstance(pair, (list, tuple)) and len(pair) == 2:
            ranges[key] = (float(pair[0]), float(pair[1]))
    if not ranges:
        return {}
    best = (state.get("best_params") or {}).get(category) or {}
    params: dict[str, float] = {}
    for key, (lo, hi) in ranges.items():
        if key in best:
            center = float(best[key])
            span = (hi - lo) * 0.15
            val = random.uniform(max(lo, center - span), min(hi, center + span))
        else:
            val = random.uniform(lo, hi)
        val = max(lo, min(hi, val))
        params[key] = round(val, 6)
    return params


def update_stats(state: dict[str, Any], category: str, trial: dict[str, Any]) -> None:
    reward = verdict_reward(str(trial.get("verdict") or "ERROR")) + defect_bonus(trial)
    stats = state.setdefault("category_stats", {})
    rec = stats.setdefault(category, {"n": 0, "reward_sum": 0.0, "avg_reward": 0.0})
    rec["n"] = int(rec.get("n") or 0) + 1
    rec["reward_sum"] = float(rec.get("reward_sum") or 0.0) + reward
    rec["avg_reward"] = rec["reward_sum"] / rec["n"]

    best = state.setdefault("best_params", {})
    best_scores = state.setdefault("best_scores", {})
    prev = float(best_scores.get(category) or -1.0)
    if reward > prev and trial.get("params"):
        best_scores[category] = reward
        best[category] = dict(trial.get("params") or {})

    state["total_cycles"] = int(state.get("total_cycles") or 0) + 1
    state["last_reward"] = reward
    state["last_verdict"] = trial.get("verdict")
    state["updated_at"] = now_iso()


def rolling_lavie_summary(hours: int = 24) -> dict[str, Any]:
    if not TE_LOG.exists():
        return {"count": 0, "success_rate_pct": 0.0}
    data = json.loads(TE_LOG.read_text(encoding="utf-8-sig"))
    cutoff = datetime.now(JST) - timedelta(hours=hours)
    rows = []
    for t in data.get("trials") or []:
        if t.get("host") != "lavie":
            continue
        ts = t.get("timestamp") or ""
        try:
            dt = datetime.fromisoformat(str(ts))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=JST)
        except Exception:
            dt = datetime.now(JST)
        if dt >= cutoff:
            rows.append(t)
    success = sum(1 for t in rows if t.get("verdict") == "SUCCESS")
    dry = sum(1 for t in rows if t.get("verdict") == "DRY_RUN")
    return {
        "count": len(rows),
        "success": success,
        "dry_run": dry,
        "success_rate_pct": round(success / len(rows) * 100, 1) if rows else 0.0,
        "window_hours": hours,
    }


def recent_lavie_failures(category: str, hours: float = 2.0) -> list[dict[str, Any]]:
    if not TE_LOG.exists():
        return []
    try:
        data = json.loads(TE_LOG.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    cutoff = datetime.now(JST) - timedelta(hours=hours)
    rows = []
    for trial in data.get("trials") or []:
        if trial.get("host") != "lavie":
            continue
        if str(trial.get("category") or "") != category:
            continue
        if str(trial.get("verdict") or "") not in {"TIMEOUT", "ERROR", "PREGATE_FAIL"}:
            continue
        ts = trial.get("logged_at") or trial.get("timestamp") or ""
        dt = parse_dt(str(ts))
        if dt is None:
            continue
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=JST)
        if dt.astimezone(JST) >= cutoff:
            rows.append(trial)
    return rows


def guard_until_dt(state: dict[str, Any], node: str) -> datetime | None:
    guards = state.get("workload_guards") or {}
    rec = guards.get(node) or {}
    return parse_dt(rec.get("until"))


def remember_workload_guard(state: dict[str, Any], node: str, reason: str) -> None:
    until = datetime.now(JST) + timedelta(minutes=LAVIE_GUARD_COOLDOWN_MINUTES)
    state.setdefault("workload_guards", {})
    state["workload_guards"][node] = {
        "active": True,
        "until": until.isoformat(),
        "reason": reason[:300],
        "updated_at": now_iso(),
    }


def clear_expired_workload_guard(state: dict[str, Any], node: str) -> None:
    guards = state.get("workload_guards") or {}
    rec = guards.get(node)
    if not rec:
        return
    until = parse_dt(rec.get("until"))
    if until is None or until.astimezone(JST) <= datetime.now(JST):
        rec["active"] = False
        rec["expired_at"] = now_iso()


def lavie_workload_guard(cfg: dict[str, Any], state: dict[str, Any], node: str) -> dict[str, Any]:
    clear_expired_workload_guard(state, node)
    guarded_until = guard_until_dt(state, node)
    if guarded_until and guarded_until.astimezone(JST) > datetime.now(JST):
        rec = ((state.get("workload_guards") or {}).get(node) or {})
        return {
            "active": True,
            "reason": rec.get("reason") or "cooldown active",
            "until": guarded_until.isoformat(),
            "source": "cooldown",
        }

    load_ok, load_reason, metrics = router.satellite_load_guard(cfg, node)
    if not load_ok:
        remember_workload_guard(state, node, load_reason)
        return {
            "active": True,
            "reason": load_reason,
            "until": ((state.get("workload_guards") or {}).get(node) or {}).get("until"),
            "source": "metrics",
            "metrics": metrics,
        }

    for category in HEAVY_LAVIE_CATEGORIES:
        streak = int((state.get("real_fail_streak") or {}).get(category) or 0)
        recent = recent_lavie_failures(category, hours=LAVIE_GUARD_WINDOW_MINUTES / 60)
        if streak >= LAVIE_GUARD_TIMEOUT_THRESHOLD or len(recent) >= LAVIE_GUARD_TIMEOUT_THRESHOLD:
            reason = (
                f"{category} unstable: streak={streak}, "
                f"recent_failures_{LAVIE_GUARD_WINDOW_MINUTES}m={len(recent)}"
            )
            remember_workload_guard(state, node, reason)
            return {
                "active": True,
                "reason": reason,
                "until": ((state.get("workload_guards") or {}).get(node) or {}).get("until"),
                "source": "recent_failures",
            }

    return {"active": False, "reason": load_reason, "source": "ok", "metrics": metrics}


def filter_guarded_categories(categories: list[str], guard: dict[str, Any]) -> list[str]:
    if not guard.get("active"):
        return categories
    return [cat for cat in categories if cat not in HEAVY_LAVIE_CATEGORIES]


def should_use_dry_run(category: str, state: dict[str, Any], force_dry: bool, allow_openfoam_real: bool) -> bool:
    if force_dry:
        return True
    if category in OPENFOAM_CATEGORIES and not allow_openfoam_real:
        return True
    fails = state.setdefault("real_fail_streak", {})
    streak = int(fails.get(category) or 0)
    # Import/build errors should not force perpetual dry_run; only solver failures count.
    if category in OPENFOAM_CATEGORIES and streak >= 5:
        return True
    if streak >= 4:
        return True
    return False


def run_one_cycle(
    *,
    node: str,
    cfg: dict[str, Any],
    state: dict[str, Any],
    timeout: int,
    force_dry: bool,
    allow_openfoam_real: bool,
) -> dict[str, Any]:
    token = sjp.load_token()
    node_info = sjp.load_node(node)
    base_url = sjp.worker_base_url(node_info)
    ok, detail = sjp.probe_worker(base_url, token)
    if not ok:
        return {"ok": False, "stage": "probe_fail", "detail": detail}

    guard = lavie_workload_guard(cfg, state, node)
    categories = filter_guarded_categories(lavie_categories(cfg), guard)
    if not categories:
        return {
            "ok": False,
            "stage": "workload_guard",
            "detail": guard.get("reason") or "all configured categories guarded",
            "guard": guard,
        }
    category = pick_category_ucb1(state, categories)
    params = suggest_params(category, state)
    if category in ("resin_fill_cad", "resin_fill_vof"):
        params = {**MOLDFLOW_CAD_BASE, **params}
    dry_run = should_use_dry_run(category, state, force_dry, allow_openfoam_real)
    trial_id = f"lavie365-{category}-{uuid.uuid4().hex[:8]}"

    bundle = cae_dispatch.run_lavie_trial(
        node=node,
        category=category,
        params=params or None,
        trial_id=trial_id,
        dry_run=dry_run,
        timeout=timeout,
        token=token,
        cfg=cfg,
    )
    trial = dict(bundle.get("trial_entry") or {})
    trial.setdefault("host", "lavie")
    if params and "params" not in trial:
        trial["params"] = params

    if trial.get("id"):
        cae_dispatch.merge_trial_into_log(trial)
        failure_analysis.record_from_trial(trial)
    cae_dispatch.append_cae_log(
        {
            "source": "lavie_continuous_te_loop",
            "category": category,
            "trial_id": trial_id,
            "dry_run": dry_run,
            "params": params,
            "trial_entry": trial,
        }
    )

    verdict = str(trial.get("verdict") or "ERROR")
    fails = state.setdefault("real_fail_streak", {})
    if not dry_run and verdict in {"ERROR", "PREGATE_FAIL", "TIMEOUT"}:
        fails[category] = int(fails.get(category) or 0) + 1
        if category in HEAVY_LAVIE_CATEGORIES and fails[category] >= LAVIE_GUARD_TIMEOUT_THRESHOLD:
            remember_workload_guard(state, node, f"{category} fail streak={fails[category]} after {verdict}")
    elif verdict in {"SUCCESS", "DRY_RUN", "FAILED"}:
        fails[category] = 0

    update_stats(state, category, trial)
    return {
        "ok": True,
        "category": category,
        "trial_id": trial_id,
        "verdict": verdict,
        "dry_run": dry_run,
        "params": params,
        "reward": state.get("last_reward"),
        "worker_status": (bundle.get("worker_result") or {}).get("status"),
        "guard": guard,
    }


def write_status(state: dict[str, Any], last_cycle: dict[str, Any], poll_seconds: int) -> None:
    payload = {
        "updated_at": now_iso(),
        "mode": "24x7_lavie_te",
        "poll_seconds": poll_seconds,
        "last_cycle": last_cycle,
        "state_summary": {
            "total_cycles": state.get("total_cycles"),
            "category_stats": state.get("category_stats"),
            "best_scores": state.get("best_scores"),
            "real_fail_streak": state.get("real_fail_streak"),
            "workload_guards": state.get("workload_guards"),
        },
        "rolling_24h": rolling_lavie_summary(24),
        "last_telegram": state.get("last_telegram"),
        "runbook": "docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md",
    }
    save_json(STATUS_PATH, payload)


def main() -> int:
    parser = argparse.ArgumentParser(description="K10->LAVIE continuous CAE T&E loop")
    parser.add_argument("--node", default="lavie")
    parser.add_argument("--poll-seconds", type=int, default=180)
    parser.add_argument("--timeout", type=int, default=600)
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run only")
    parser.add_argument(
        "--allow-openfoam-real",
        action="store_true",
        help="Allow non-dry OpenFOAM on LAVIE (requires opencfd/openfoam-dev image)",
    )
    parser.add_argument("--once", action="store_true", help="Single cycle then exit")
    parser.add_argument("--notify-cooldown-minutes", type=int, default=60)
    parser.add_argument("--no-telegram", action="store_true")
    args = parser.parse_args()

    initialize_guard_status("lavie_continuous_te_loop.startup")
    cfg = router.load_config()
    state = load_json(
        STATE_PATH,
        {"total_cycles": 0, "category_stats": {}, "best_params": {}, "best_scores": {}},
    )
    failure_analysis.seed_resin_best_params(state)
    save_json(STATE_PATH, state)
    print(f"[lavie365] start poll={args.poll_seconds}s dry_run_force={args.dry_run}")

    if not args.no_telegram:
        try:
            tg = maybe_notify_telegram(
                state,
                {},
                args.poll_seconds,
                notify_cooldown_minutes=args.notify_cooldown_minutes,
                startup=True,
            )
            state["last_telegram"] = tg
            save_json(STATE_PATH, state)
        except Exception as exc:
            print(f"[lavie365] telegram startup warn: {exc}")

    while True:
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=2.0)
            if cpu > 70.0:
                print(f"[lavie365] CPU too high ({cpu}% > 70%). Cooling down for 60s...", flush=True)
                time.sleep(60)
                continue
        except ImportError:
            pass

        cycle: dict[str, Any]
        try:
            cycle = run_one_cycle(
                node=args.node,
                cfg=cfg,
                state=state,
                timeout=args.timeout,
                force_dry=args.dry_run,
                allow_openfoam_real=args.allow_openfoam_real,
            )
        except Exception as exc:
            cycle = {"ok": False, "stage": "exception", "error": str(exc)[:300]}
            print(f"[lavie365] ERROR {exc}")

        save_json(STATE_PATH, state)
        write_status(state, cycle, args.poll_seconds)

        if not args.no_telegram:
            try:
                tg = maybe_notify_telegram(
                    state,
                    cycle,
                    args.poll_seconds,
                    notify_cooldown_minutes=args.notify_cooldown_minutes,
                    startup=False,
                )
                if tg is not None:
                    state["last_telegram"] = tg
                    save_json(STATE_PATH, state)
            except Exception as exc:
                print(f"[lavie365] telegram warn: {exc}")

        if cycle.get("ok"):
            print(
                f"[lavie365] cycle OK cat={cycle.get('category')} "
                f"verdict={cycle.get('verdict')} dry={cycle.get('dry_run')} "
                f"reward={cycle.get('reward')}"
            )
        else:
            print(f"[lavie365] cycle WARN {cycle}")

        if args.once:
            return 0 if cycle.get("ok") else 1

        time.sleep(max(30, args.poll_seconds))


if __name__ == "__main__":
    raise SystemExit(main())
