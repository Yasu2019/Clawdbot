# -*- coding: utf-8 -*-
"""K10 -> ThinkPad DXF2STEP parameter trial-and-error loop (native FreeCAD)."""
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

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
CONFIG_PATH = WORKSPACE / "thinkpad_dxf2step_te_config.json"
STATE_PATH = WORKSPACE / "thinkpad_dxf2step_te_state.json"
STATUS_PATH = WORKSPACE / "thinkpad_dxf2step_te_status.json"
LOG_PATH = WORKSPACE / "thinkpad_dxf2step_te_log.jsonl"
PID_PATH = WORKSPACE / "thinkpad_dxf2step_te.pid"
ARCHIVE_ROOT = WORKSPACE / "thinkpad_dxf2step_history"
MANIFEST_PATH = ARCHIVE_ROOT / "manifest.json"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import thinkpad_ssh_common as tp_ssh
import thinkpad_ssh_metrics
import dxf2step_quality_gate as dxf_qc
import dxf2step_telegram_report as dxf_tg


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def append_log(entry: dict[str, Any]) -> None:
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_guard(cfg: dict[str, Any]) -> tuple[bool, list[str], dict[str, Any]]:
    thresholds = cfg.get("thresholds") or {}
    metrics = thinkpad_ssh_metrics.collect_metrics()
    reasons: list[str] = []
    if not metrics.get("ok"):
        return False, [f"ssh metrics unavailable: {metrics.get('error', 'unknown')}"], metrics
    cpu = float(metrics.get("cpu_usage_percent") or 0)
    ram = float(metrics.get("ram_usage_percent") or 0)
    temp = float(metrics.get("cpu_temp_celsius") or metrics.get("thermal_control_temp_c") or 0)
    if cpu > float(thresholds.get("max_cpu_percent", 80)):
        reasons.append(f"cpu={cpu:.1f}%")
    if ram > float(thresholds.get("max_ram_percent", 75)):
        reasons.append(f"ram={ram:.1f}%")
    if temp > float(thresholds.get("max_temp_c", 75)):
        reasons.append(f"temp={temp:.1f}C")
    return len(reasons) == 0, reasons, metrics


def pick_trial(cfg: dict[str, Any], state: dict[str, Any]) -> tuple[dict[str, Any], float, int]:
    samples = cfg.get("samples") or []
    grid = cfg.get("thickness_grid_mm") or [10.0]
    if not samples:
        raise RuntimeError("no DXF samples in thinkpad_dxf2step_te_config.json")
    idx = int(state.get("combo_index") or 0)
    n_grid = len(grid)
    sample_idx = idx // n_grid
    thick_idx = idx % n_grid
    sample = samples[sample_idx % len(samples)]
    thickness = float(grid[thick_idx % n_grid])
    return sample, thickness, idx + 1


def resolve_trial(
    cfg: dict[str, Any],
    state: dict[str, Any],
    *,
    force_sample: str | None = None,
    force_thickness: float | None = None,
) -> tuple[dict[str, Any], float, int]:
    if force_sample or force_thickness is not None:
        samples = cfg.get("samples") or []
        sample = next((s for s in samples if s.get("name") == force_sample), samples[0] if samples else {})
        thickness = float(force_thickness if force_thickness is not None else (cfg.get("thickness_grid_mm") or [10.0])[0])
        idx = int(state.get("combo_index") or 0)
        return sample, thickness, idx + (0 if force_sample or force_thickness is not None else 1)
    return pick_trial(cfg, state)


def scp_from_thinkpad(remote: str, local: Path, reg: dict[str, Any]) -> bool:
    target, key_path = tp_ssh.ssh_target(reg)
    local.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            "scp",
            "-i",
            str(key_path),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            f"{target}:{remote}",
            str(local),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    return proc.returncode == 0


def list_remote_files(remote_output: str, reg: dict[str, Any]) -> list[str]:
    run = tp_ssh.run_ssh(
        f"find {remote_output} -maxdepth 1 -type f -printf '%f\\n' 2>/dev/null || "
        f"ls -1 {remote_output} 2>/dev/null",
        timeout=30,
        registry=reg,
    )
    return [line.strip() for line in (run.stdout or "").splitlines() if line.strip()]


def should_sync_file(name: str, archive_cfg: dict[str, Any]) -> bool:
    lower = name.lower()
    if lower == "build_log.json":
        return bool(archive_cfg.get("retain_build_log", True))
    if lower == "part_manifest.json":
        return True
    if lower.endswith(".fcstd"):
        return bool(archive_cfg.get("retain_fcstd", True))
    if lower.endswith(".step"):
        return bool(archive_cfg.get("retain_step", True))
    if lower.endswith(".png"):
        return bool(archive_cfg.get("retain_png", True))
    return lower.endswith(".cleaned.dxf")


def sync_trial_archive(
    *,
    job_id: str,
    remote_output: str,
    reg: dict[str, Any],
    cycle: dict[str, Any],
    build_log: dict[str, Any],
    cfg: dict[str, Any],
) -> dict[str, Any]:
    archive_cfg = cfg.get("archive") or {}
    if not archive_cfg.get("sync_to_k10", True):
        return {"synced": False, "reason": "sync_to_k10 disabled"}

    local_root = ROOT / str(archive_cfg.get("local_root") or "data/workspace/thinkpad_dxf2step_history")
    local_job = local_root / job_id
    local_job.mkdir(parents=True, exist_ok=True)

    synced: list[str] = []
    failed: list[str] = []
    local_src = cycle.get("local_dxf")
    if local_src:
        src = ROOT / str(local_src)
        sample_dest = local_job / "sample.dxf"
        if src.is_file() and not sample_dest.is_file():
            try:
                import shutil

                shutil.copy2(src, sample_dest)
                synced.append("sample.dxf")
            except OSError:
                failed.append("sample.dxf")
    for name in list_remote_files(remote_output, reg):
        if not should_sync_file(name, archive_cfg):
            continue
        if scp_from_thinkpad(f"{remote_output}/{name}", local_job / name, reg):
            synced.append(name)
        else:
            failed.append(name)

    fcstd_files = sorted([n for n in synced if n.lower().endswith(".fcstd")])
    step_files = sorted([n for n in synced if n.lower().endswith(".step")])
    png_files = sorted([n for n in synced if n.lower().endswith(".png")])

    orig_png = dxf_tg.ensure_original_dxf_png(
        local_job,
        local_dxf=(ROOT / str(local_src)) if local_src and (ROOT / str(local_src)).is_file() else None,
    )
    if orig_png and orig_png.name not in png_files:
        png_files = sorted(png_files + [orig_png.name])

    trial_record = {
        "schema": "clawstack.thinkpad_dxf2step_trial.v1",
        "job_id": job_id,
        "timestamp": cycle.get("timestamp"),
        "sample": cycle.get("sample"),
        "thickness_mm": cycle.get("thickness_mm"),
        "verdict": cycle.get("verdict"),
        "kpi": cycle.get("kpi"),
        "remote_output": remote_output,
        "archive_dir": str(local_job.relative_to(ROOT)).replace("\\", "/"),
        "fcstd_files": fcstd_files,
        "step_files": step_files,
        "png_files": png_files,
        "primary_fcstd": fcstd_files[0] if fcstd_files else (build_log.get("combined_fcstd") or None),
        "combined_fcstd": build_log.get("combined_fcstd"),
        "build_log": build_log,
        "edit_hint": "Open *.FCStd in FreeCAD on ThinkPad or copy from archive_dir to edit parametric history",
    }
    (local_job / "trial_record.json").write_text(
        json.dumps(trial_record, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    manifest = load_json(MANIFEST_PATH, {"schema": "clawstack.thinkpad_dxf2step_history.v1", "trials": []})
    trials = [t for t in (manifest.get("trials") or []) if t.get("job_id") != job_id]
    trials.append(
        {
            "job_id": job_id,
            "timestamp": cycle.get("timestamp"),
            "sample": cycle.get("sample"),
            "thickness_mm": cycle.get("thickness_mm"),
            "verdict": cycle.get("verdict"),
            "archive_dir": trial_record["archive_dir"],
            "fcstd_files": fcstd_files,
            "primary_fcstd": trial_record["primary_fcstd"],
        }
    )
    manifest["trials"] = trials[-200:]
    manifest["updated_at"] = now_iso()
    manifest["trial_count"] = len(manifest["trials"])
    save_json(MANIFEST_PATH, manifest)

    return {
        "synced": True,
        "archive_dir": trial_record["archive_dir"],
        "files": synced,
        "failed": failed,
        "fcstd_files": fcstd_files,
        "primary_fcstd": trial_record["primary_fcstd"],
    }


def scp_to_thinkpad(local: Path, remote: str, reg: dict[str, Any]) -> bool:
    target, key_path = tp_ssh.ssh_target(reg)
    proc = subprocess.run(
        [
            "scp",
            "-i",
            str(key_path),
            "-o",
            "BatchMode=yes",
            "-o",
            "ConnectTimeout=15",
            str(local),
            f"{target}:{remote}",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=120,
    )
    return proc.returncode == 0


def evaluate_build_log(build_log: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    layers = build_log.get("layers") or {}
    n_total = len(layers)
    n_done = sum(1 for v in layers.values() if (v or {}).get("status") == "done")
    has_combined = bool(build_log.get("combined_step"))
    kpi = {
        "layers_total": n_total,
        "layers_done": n_done,
        "layer_success_rate": (n_done / n_total) if n_total else 0.0,
        "has_combined_step": has_combined,
        "reconstruction_status": build_log.get("reconstruction_status"),
        "combined_quality_ok": build_log.get("combined_quality_ok"),
    }
    if build_log.get("reconstruction_warning") or build_log.get("reconstruction_status") == "compound_fallback":
        return "FAILED", kpi
    if build_log.get("closed_loop_qc_failures"):
        kpi["closed_loop_qc_failures"] = build_log.get("closed_loop_qc_failures")
        return "FAILED", kpi
    if build_log.get("hole_cut_qc_failures"):
        kpi["hole_cut_qc_failures"] = build_log.get("hole_cut_qc_failures")
        return "FAILED", kpi
    if build_log.get("profile_qc_failures"):
        kpi["profile_qc_failures"] = build_log.get("profile_qc_failures")
        return "FAILED", kpi
    if build_log.get("reconstruction_status") == "closed_loop_qc_fail":
        return "FAILED", kpi
    if build_log.get("reconstruction_status") == "hole_cut_qc_fail":
        return "FAILED", kpi
    if build_log.get("reconstruction_status") == "profile_qc_fail":
        return "FAILED", kpi
    if build_log.get("combined_quality_ok") is False and has_combined:
        return "FAILED", kpi
    if n_total and n_done == n_total and has_combined:
        verdict = "SUCCESS"
    elif n_total and n_done == n_total:
        verdict = "PARTIAL"
    elif n_done > 0:
        verdict = "PARTIAL"
    else:
        verdict = "FAILED"
    return verdict, kpi


def run_cycle(
    cfg: dict[str, Any] | None = None,
    *,
    force_sample: str | None = None,
    force_thickness: float | None = None,
    advance_index: bool = True,
) -> dict[str, Any]:
    cfg = cfg or load_json(CONFIG_PATH, {})
    state = load_json(STATE_PATH, {"combo_index": 0, "cycle_count": 0})
    reg = tp_ssh.read_registry()

    guard_ok, guard_reasons, metrics = load_guard(cfg)
    cycle: dict[str, Any] = {
        "schema": "clawstack.thinkpad_dxf2step_cycle.v1",
        "timestamp": now_iso(),
        "guard_ok": guard_ok,
        "guard_reasons": guard_reasons,
        "metrics": {
            "cpu_usage_percent": metrics.get("cpu_usage_percent"),
            "ram_usage_percent": metrics.get("ram_usage_percent"),
            "cpu_temp_celsius": metrics.get("cpu_temp_celsius"),
        },
    }

    if not guard_ok:
        cycle["decision"] = "skip_guard"
        append_log(cycle)
        save_json(STATUS_PATH, {"updated_at": now_iso(), "running": True, "last_cycle": cycle})
        return cycle

    sample, thickness, next_idx = resolve_trial(
        cfg, state, force_sample=force_sample, force_thickness=force_thickness
    )
    local_dxf = ROOT / str(sample.get("local_dxf") or "")
    if not local_dxf.exists():
        cycle["decision"] = "skip_missing_sample"
        cycle["error"] = f"missing {local_dxf}"
        append_log(cycle)
        return cycle

    job_id = f"tp-dxf-{uuid.uuid4().hex[:8]}"
    remote_jobs = cfg.get("remote_jobs_root") or "/home/yasu/clawstack_satellite/dxf2step/jobs"
    remote_apps = cfg.get("remote_apps_dir") or "/home/yasu/clawstack_satellite/apps/dxf2step"
    remote_job = f"{remote_jobs}/{job_id}"
    remote_input = f"{remote_job}/input/sample.dxf"
    remote_output = f"{remote_job}/output"
    archive_cfg = cfg.get("archive") or {}
    local_job = ROOT / str(archive_cfg.get("local_root") or "data/workspace/thinkpad_dxf2step_history") / job_id

    trial_plan = {
        "job_id": job_id,
        "sample": sample.get("name"),
        "thickness_mm": thickness,
        "local_dxf": str(sample.get("local_dxf") or ""),
        "thickness_grid_mm": cfg.get("thickness_grid_mm") or [10.0],
        "sample_list": [s.get("name") for s in (cfg.get("samples") or []) if s.get("name")],
        "node": "thinkpad",
    }

    try:
        preflight_rec = dxf_qc.run_preflight_gate(trial_plan, archive_dir=local_job)
        cycle["quality_preflight"] = {
            "ok": preflight_rec.get("gate_ok"),
            "trial_id": job_id,
            "failure_class": None,
            "fmea_rows": len((preflight_rec.get("analysis") or {}).get("fmea") or []),
        }
    except dxf_qc.Dxf2StepQualityGateError as exc:
        cycle["decision"] = "skip_quality_preflight"
        cycle["job_id"] = job_id
        cycle["sample"] = sample.get("name")
        cycle["thickness_mm"] = thickness
        cycle["error"] = str(exc)
        append_log(cycle)
        save_json(STATUS_PATH, {"updated_at": now_iso(), "running": True, "last_cycle": cycle})
        return cycle

    # This loop is strictly single-slot. If a previous controller timed out or
    # restarted, reap only its orphaned DXF2STEP/FreeCAD workers before launch.
    orphan_cleanup = tp_ssh.run_ssh(
        (
            "N=$(pgrep -fc '[d]xf2step_worker.py|[f]reecadcmd.*clawstack_satellite/dxf2step/jobs' || true); "
            "pkill -f '[d]xf2step_worker.py' 2>/dev/null || true; "
            "pkill -f '[f]reecadcmd.*clawstack_satellite/dxf2step/jobs' 2>/dev/null || true; "
            "echo DXF2STEP_ORPHANS_REAPED=$N"
        ),
        timeout=30,
        registry=reg,
    )
    cycle["orphan_cleanup"] = (orphan_cleanup.stdout or "").strip()

    tp_ssh.run_ssh(f"mkdir -p {remote_job}/input {remote_output}", timeout=60, registry=reg)
    if not scp_to_thinkpad(local_dxf, remote_input, reg):
        cycle["decision"] = "skip_scp_failed"
        append_log(cycle)
        return cycle

    # Autonomic parameter adjustment based on FMEA history
    t_junction_tol = 0.02
    timeout_sec = int(cfg.get("worker_timeout_sec") or 300)
    
    sample_name = sample.get("name")
    try:
        past_trials = dxf_qc.fetch_past_analyses(sample=sample_name, limit=5)
        has_open_loops = False
        has_timeout = False
        for p in past_trials:
            verdict_str = str(p.get("verdict") or "").upper()
            fc = str(p.get("failure_class") or "").lower()
            if verdict_str in ("FAILED", "PARTIAL", "ERROR", "TIMEOUT") or fc in ("open_loop_profile", "tjunction_no_outer_edges", "hole_filled_defect"):
                if fc in ("open_loop_profile", "tjunction_no_outer_edges") or "open" in fc or "loop" in fc:
                    has_open_loops = True
                if fc == "timeout" or verdict_str == "TIMEOUT":
                    has_timeout = True
        if has_open_loops:
            t_junction_tol = 0.08  # Increase T-junction tolerance for the next attempt
            print(f"[autonomic] sample {sample_name} previously failed due to open loops, increasing T-junction tolerance to {t_junction_tol}", flush=True)
        if has_timeout:
            timeout_sec *= 2  # Double timeout
            print(f"[autonomic] sample {sample_name} previously timed out, doubling timeout to {timeout_sec}s", flush=True)
    except Exception as e:
        print(f"[autonomic] error fetching past analyses for FMEA adaptation: {e}", flush=True)

    worker_cmd = (
        f"source ~/.clawstack_dxf2step_env 2>/dev/null || "
        f"export DXF2STEP_FREECAD_MODE=native FREECAD_CMD=freecad.cmd; "
        f"export DXF2STEP_FREECAD_TIMEOUT_SEC={timeout_sec}; "
        f"python3 {remote_apps}/dxf2step_worker.py "
        f"--input {remote_input} --output {remote_output} --thickness {thickness} "
        f"--t-junction-tol {t_junction_tol}"
    )
    run = tp_ssh.run_ssh(worker_cmd, timeout=timeout_sec + 60, registry=reg)
    stdout = (run.stdout or "").strip()
    stderr = (run.stderr or "").strip()

    build_log: dict[str, Any] = {}
    log_fetch = tp_ssh.run_ssh(f"cat {remote_output}/build_log.json 2>/dev/null || true", timeout=30, registry=reg)
    if log_fetch.stdout and log_fetch.stdout.strip().startswith("{"):
        try:
            build_log = json.loads(log_fetch.stdout)
        except json.JSONDecodeError:
            build_log = {}

    verdict, kpi = evaluate_build_log(build_log)
    cycle.update(
        {
            "decision": "trial_complete",
            "job_id": job_id,
            "sample": sample.get("name"),
            "thickness_mm": thickness,
            "local_dxf": str(sample.get("local_dxf") or ""),
            "exit_code": run.returncode,
            "verdict": verdict,
            "kpi": kpi,
            "stdout_tail": stdout[-800:],
            "stderr_tail": stderr[-400:],
        }
    )

    archive = sync_trial_archive(
        job_id=job_id,
        remote_output=remote_output,
        reg=reg,
        cycle=cycle,
        build_log=build_log,
        cfg=cfg,
    )
    cycle["archive"] = archive

    post_trial = {
        **cycle,
        "build_log": build_log,
        "thickness_grid_mm": cfg.get("thickness_grid_mm"),
        "sample_list": trial_plan.get("sample_list"),
    }
    mf_path = local_job / "part_manifest.json"
    if mf_path.exists():
        post_trial["part_manifest_path"] = str(mf_path.resolve())
    postmortem_rec = dxf_qc.run_postmortem_gate(post_trial, archive_dir=local_job)
    if not postmortem_rec.get("gate_ok"):
        cycle["verdict"] = "FAILED"
        cycle["error"] = f"Quality gate rejected part: {postmortem_rec.get('analysis', {}).get('_validation', {}).get('issues')}"
    
    cycle["quality_postmortem"] = {
        "ok": postmortem_rec.get("gate_ok"),
        "failure_class": (postmortem_rec.get("analysis") or {}).get("failure_class"),
        "next_experiment": ((postmortem_rec.get("analysis") or {}).get("doe") or {}).get("next_experiment"),
        "countermeasures": ((postmortem_rec.get("analysis") or {}).get("countermeasures") or [])[:3],
    }

    cycle["telegram"] = dxf_tg.send_dxf2step_trial_report(cycle, local_job, cfg)

    if advance_index:
        state["combo_index"] = next_idx
    state["cycle_count"] = int(state.get("cycle_count") or 0) + 1
    state["last_verdict"] = verdict
    # T048/ip4 meaning gate: count consecutive completed-trial failures.
    # Skip paths (skip_load / skip_offline / skip_scp_failed etc.) return earlier and are NOT counted.
    if verdict == "SUCCESS":
        state["fail_streak"] = 0
    else:
        state["fail_streak"] = int(state.get("fail_streak") or 0) + 1
    state["updated_at"] = now_iso()
    save_json(STATE_PATH, state)
    append_log(cycle)

    status = load_json(STATUS_PATH, {})
    status.update(
        {
            "updated_at": now_iso(),
            "running": True,
            "mode": "24x7_thinkpad_dxf2step_te",
            "poll_seconds": int(cfg.get("poll_seconds") or 600),
            "last_cycle": cycle,
            "state_summary": {
                "cycle_count": state["cycle_count"],
                "combo_index": state["combo_index"],
            },
        }
    )
    save_json(STATUS_PATH, status)
    return cycle


def _meaning_gate_threshold(cfg: dict[str, Any]) -> int:
    # T048/ip4: fail-closed default 8 (same as tri-track meaning_gate_max_fail_streak).
    # Set meaning_gate_max_fail_streak=0 in config to disable explicitly.
    try:
        return int(cfg.get("meaning_gate_max_fail_streak", 8))
    except Exception:
        return 8


def _notify_meaning_gate_stop(streak: int, threshold: int) -> None:
    msg = (
        f"⛔ dxf2step meaning gate: thinkpad DXF2STEPループを自動停止しました\n"
        f"実行トライアル連続失敗 {streak} 回 (しきい値 {threshold})。\n"
        f"T019/T048/P026: 全件失敗のまま巨大記録を書き続ける空回り(D:枯渇の再発条件)を防止。\n"
        f"復旧: 根本原因を修正後、--clear-meaning-gate 付きで再起動。"
    )
    try:
        import cae_telegram_video_notify as tg

        tg.send_telegram_message(msg)
    except Exception as exc:
        print(f"[meaning_gate] telegram notify failed: {exc}", flush=True)


def daemon_loop(poll_seconds: int) -> None:
    state = load_json(STATE_PATH, {})
    gate = state.get("meaning_gate") or {}
    if gate.get("stopped"):
        # T048: watchdog/auto-restart must NOT silently resume a runaway loop.
        print(
            "[thinkpad_dxf2step] REFUSING TO START: meaning gate stop flag is set "
            f"(at={gate.get('at')}, fail_streak={gate.get('fail_streak')}). "
            "Fix the root cause, then restart with --clear-meaning-gate. (T048/ip4)",
            flush=True,
        )
        return
    PID_PATH.write_text(str(__import__("os").getpid()), encoding="utf-8")
    cfg = load_json(CONFIG_PATH, {})
    poll = int(cfg.get("poll_seconds") or poll_seconds)
    threshold = _meaning_gate_threshold(cfg)
    if threshold <= 0:
        status = load_json(STATUS_PATH, {})
        status.pop("meaning_gate", None)
        if status.get("last_verdict") == "STOPPED_MEANING_GATE":
            status.pop("last_verdict", None)
        status.update({"updated_at": now_iso(), "running": True, "poll_seconds": poll})
        save_json(STATUS_PATH, status)
    print(f"[thinkpad_dxf2step] daemon poll={poll}s meaning_gate_max_fail_streak={threshold}", flush=True)
    while True:
        try:
            cycle = run_cycle(cfg)
            print(
                f"[thinkpad_dxf2step] decision={cycle.get('decision')} "
                f"verdict={cycle.get('verdict')} sample={cycle.get('sample')}",
                flush=True,
            )
            state = load_json(STATE_PATH, {})
            streak = int(state.get("fail_streak") or 0)
            if threshold > 0 and cycle.get("decision") == "trial_complete" and streak >= threshold:
                gate_rec = {
                    "stopped": True,
                    "at": now_iso(),
                    "fail_streak": streak,
                    "threshold": threshold,
                }
                state["meaning_gate"] = gate_rec
                save_json(STATE_PATH, state)
                status = load_json(STATUS_PATH, {})
                status.update(
                    {
                        "updated_at": now_iso(),
                        "running": False,
                        "last_verdict": "STOPPED_MEANING_GATE",
                        "meaning_gate": gate_rec,
                    }
                )
                save_json(STATUS_PATH, status)
                append_log({"meaning_gate_stop": streak, "threshold": threshold, "at": now_iso()})
                # Notify last: stop must happen even if Telegram fails (fail-closed).
                _notify_meaning_gate_stop(streak, threshold)
                print("[thinkpad_dxf2step] meaning gate stop: daemon exiting (T048/ip4)", flush=True)
                return
        except Exception as exc:
            print(f"[thinkpad_dxf2step] cycle error: {exc}", flush=True)
        time.sleep(poll)


def main() -> int:
    parser = argparse.ArgumentParser(description="ThinkPad DXF2STEP T&E loop from K10")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--daemon", action="store_true")
    parser.add_argument("--poll-seconds", type=int, default=600)
    parser.add_argument("--sample", help="force sample name (e.g. heatsink)")
    parser.add_argument("--thickness", type=float, help="force thickness mm")
    parser.add_argument(
        "--clear-meaning-gate",
        action="store_true",
        help="clear the T048/ip4 meaning-gate stop flag (use only after fixing the root cause)",
    )
    args = parser.parse_args()

    if args.clear_meaning_gate:
        state = load_json(STATE_PATH, {})
        if state.get("meaning_gate"):
            state.pop("meaning_gate", None)
            state["fail_streak"] = 0
            state["updated_at"] = now_iso()
            save_json(STATE_PATH, state)
            print("[thinkpad_dxf2step] meaning gate flag cleared (fail_streak reset)", flush=True)
        else:
            print("[thinkpad_dxf2step] no meaning gate flag to clear", flush=True)

    if args.daemon:
        daemon_loop(args.poll_seconds)
        return 0

    cycle = run_cycle(
        force_sample=args.sample,
        force_thickness=args.thickness,
        advance_index=not (args.sample or args.thickness is not None),
    )
    print(json.dumps(cycle, ensure_ascii=False, indent=2))
    return 0 if cycle.get("decision") != "skip_missing_sample" else 1


if __name__ == "__main__":
    raise SystemExit(main())
# T048/ip4 meaning gate added 2026-07-06
