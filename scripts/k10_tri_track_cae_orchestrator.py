# -*- coding: utf-8 -*-
"""K10 tri-track parallel CAE: OpenFOAM@lavie + OpenRadioss@red_lavie + FEM Impact@thinkpad.

Continuous trial-and-error with no idle gap between cycles (per-track loops).
"""
from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import threading
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
LOG_PATH = WORKSPACE / "k10_tri_track_cae_log.jsonl"
STATUS_PATH = WORKSPACE / "k10_tri_track_cae_status.json"
DASHBOARD_STATUS = WORKSPACE / "apps" / "growth_dashboard" / "k10_tri_track_cae_status.json"
FEM_VARIANT_INDEX = WORKSPACE / "thinkpad_fem_impact_variant_index.json"
PNG_SHELL_LOCAL = ROOT / "scripts" / "thinkpad_fem_impact_png.sh"
RENDER_SCRIPT_LOCAL = ROOT / "scripts" / "impact_vtk_to_png.py"
QC_SCRIPT_LOCAL = ROOT / "scripts" / "impact_vtk_quality_gate.py"
FEM_PROGRESS_SCRIPT = ROOT / "scripts" / "fem_impact_progress_telegram.py"
STORAGE_BLOCK_PATH = ROOT / "data" / "state" / "wsl_storage_guard" / "CAE_DISPATCH_BLOCKED.json"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import cae_trial_evolution_gate as evolution_gate
import cae_tri_track_openfoam_params as of_params
import impact_vtk_quality_gate as fem_qc
import k10_satellite_cae_dispatch as cae_dispatch
import k10_satellite_dispatch as sjp
import yaml

_stop = threading.Event()


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def load_tri_cfg() -> dict[str, Any]:
    cfg = yaml.safe_load((WORKSPACE / "cae_workload_router.yaml").read_text(encoding="utf-8")) or {}
    return cfg.get("tri_track_parallel") or {}


def append_log(entry: dict[str, Any]) -> None:
    entry = dict(entry)
    entry["logged_at"] = now_iso()
    LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with LOG_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def write_status(payload: dict[str, Any]) -> None:
    payload = dict(payload)
    payload["updated_at"] = now_iso()
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    STATUS_PATH.write_text(text, encoding="utf-8")
    DASHBOARD_STATUS.parent.mkdir(parents=True, exist_ok=True)
    DASHBOARD_STATUS.write_text(text, encoding="utf-8")


def _apply_llm_overrides(override_key: str, params: dict[str, Any]) -> dict[str, Any]:
    """meaning_gate_auto_improver が適用したパラメータ修正を反映 (P025改訂 2026-07-18)."""
    try:
        data = json.loads((WORKSPACE / "tri_track_param_overrides.json").read_text(encoding="utf-8"))
        overrides = (data.get(override_key) or {}).get("overrides") or {}
        for k, v in overrides.items():
            params[k] = v
    except Exception:
        pass
    return params


def random_or_params(tri: dict[str, Any]) -> dict[str, Any]:
    ranges = (tri.get("openradioss") or {}).get("param_ranges") or {}
    out: dict[str, Any] = {"case_label": str((tri.get("openradioss") or {}).get("case_label") or "4mmx4mm")}
    for key, bounds in ranges.items():
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            lo, hi = float(bounds[0]), float(bounds[1])
            out[key] = round(random.uniform(lo, hi), 4)
    return _apply_llm_overrides("openradioss", out)


def _maybe_cae_paraview_video_delivery(
    trial_entry: dict[str, Any],
    *,
    node: str,
    category: str,
    dry_run: bool,
    cfg: dict[str, Any],
) -> None:
    """ParaView MP4 -> Google Drive -> Telegram after CAE SUCCESS (T019)."""
    if dry_run or str(trial_entry.get("verdict") or "") != "SUCCESS":
        return
    if trial_entry.get("cae_video_paraview_sent"):
        return
    if os.environ.get("CAE_PARAVIEW_VIDEO_TELEGRAM", "1") != "1":
        return

    import cae_paraview_video_delivery as cpvd

    solver = cpvd.solver_for_category(category)
    if not solver:
        return

    trial_id = str(trial_entry.get("id") or "")
    if not trial_id:
        return

    try:
        result = cpvd.deliver_after_success(
            solver=solver,
            trial_entry=trial_entry,
            node=node,
            category=category,
            cfg=cfg,
        )
        if result.get("ok"):
            trial_entry["cae_video_paraview_sent"] = True
            trial_entry["cae_video_solver"] = solver
            trial_entry["cae_video_gdrive"] = (result.get("gdrive") or {}).get("gdrive_rel", "")
            trial_entry["cae_video_telegram_mode"] = (result.get("telegram") or {}).get("mode", "")
            trial_entry.pop("cae_video_paraview_error", None)
            if solver == "openfoam":
                trial_entry["fill_video_telegram_sent"] = True
                trial_entry["fill_video_source"] = "k10_pull_paraview"
        else:
            err = str(result.get("error") or result)[:200]
            trial_entry["cae_video_paraview_error"] = err
            if solver == "openfoam":
                trial_entry["fill_video_telegram_error"] = err
    except Exception as exc:
        trial_entry["cae_video_paraview_error"] = str(exc)[:200]
        print(f"[tri-track] paraview video non-fatal: {exc}", flush=True)


def _maybe_k10_fill_video_after_lavie_success(
    trial_entry: dict[str, Any],
    *,
    node: str,
    category: str,
    dry_run: bool,
    cfg: dict[str, Any],
) -> None:
    """Backward-compatible alias -> unified ParaView delivery."""
    _maybe_cae_paraview_video_delivery(
        trial_entry, node=node, category=category, dry_run=dry_run, cfg=cfg
    )


def run_satellite_trial(
    *,
    node: str,
    category: str,
    params: dict | None,
    dry_run: bool,
    timeout: int,
) -> dict[str, Any]:
    token = sjp.load_token()
    trial_id = f"tri-{node}-{category}-{uuid.uuid4().hex[:8]}"
    bundle = cae_dispatch.run_lavie_trial(
        node=node,
        category=category,
        params=params,
        trial_id=trial_id,
        dry_run=dry_run,
        timeout=timeout,
        token=token,
        cfg=router.load_config(),
    )
    trial_entry = bundle["trial_entry"]
    trial_entry.setdefault("host", node)
    cfg = router.load_config()
    _maybe_cae_paraview_video_delivery(
        trial_entry,
        node=node,
        category=category,
        dry_run=dry_run,
        cfg=cfg,
    )
    cae_dispatch.merge_trial_into_log(trial_entry)
    cae_dispatch.append_cae_log(
        {
            "source": "k10_tri_track_cae",
            "node": node,
            "category": category,
            "trial_id": trial_id,
            "trial_entry": trial_entry,
        }
    )
    return {"trial_id": trial_id, "verdict": trial_entry.get("verdict"), "trial_entry": trial_entry}


def run_satellite_trial_gated(
    track: str,
    *,
    node: str,
    category: str,
    params: dict | None,
    dry_run: bool,
    timeout: int,
) -> dict[str, Any]:
    result = run_satellite_trial(
        node=node,
        category=category,
        params=params,
        dry_run=dry_run,
        timeout=timeout,
    )
    return evolution_gate.apply_evolution_gate(track, result)


def _fem_bench_variant(fem: dict[str, Any], cycle_n: int) -> dict[str, Any] | None:
    sched = fem.get("bench_schedule") or {}
    if not sched.get("enabled"):
        return None
    every = int(sched.get("every_n_cycles") or 0)
    if every <= 0 or cycle_n <= 0 or (cycle_n % every) != 0:
        return None
    bench_list = list(sched.get("variants") or [])
    if not bench_list:
        return None
    idx_path = WORKSPACE / "fem_impact_bench_index.json"
    idx = 0
    if idx_path.exists():
        try:
            idx = int(json.loads(idx_path.read_text(encoding="utf-8")).get("index") or 0)
        except Exception:
            idx = 0
    variant = bench_list[idx % len(bench_list)]
    idx_path.write_text(
        json.dumps({"index": (idx + 1) % len(bench_list), "last": variant, "cycle_n": cycle_n}, ensure_ascii=False),
        encoding="utf-8",
    )
    return dict(variant)


def _fem_active_variants(fem: dict[str, Any]) -> list[dict[str, Any]]:
    variants = list(fem.get("variants") or [])
    if fem.get("production_only", True):
        variants = [v for v in variants if v.get("enabled", True) is not False]
    return variants


def _pick_fem_variant(variants: list[dict[str, Any]]) -> dict[str, Any]:
    if not variants:
        raise RuntimeError("no fem_impact variants configured")
    idx = 0
    if FEM_VARIANT_INDEX.exists():
        try:
            idx = int(json.loads(FEM_VARIANT_INDEX.read_text(encoding="utf-8")).get("index") or 0)
        except Exception:
            idx = 0
    variant = variants[idx % len(variants)]
    FEM_VARIANT_INDEX.write_text(
        json.dumps({"index": (idx + 1) % len(variants), "last": variant, "updated_at": now_iso()}, ensure_ascii=False),
        encoding="utf-8",
    )
    return variant


def _ensure_fem_png_scripts() -> bool:
    """Fast scp of PNG helpers (60s cap). Skip when ThinkPad offline."""
    if not PNG_SHELL_LOCAL.exists() or not RENDER_SCRIPT_LOCAL.exists() or not QC_SCRIPT_LOCAL.exists():
        return False
    try:
        import k10_thinkpad_fem_impact_deploy as fem_deploy

        result = fem_deploy.sync_render_script(dry_run=False)
        return bool(result.get("ok"))
    except Exception as exc:
        print(f"[fem_impact] png script sync skipped: {exc}", flush=True)
        return False


def _fem_job_timeout(fem: dict[str, Any], variant: dict[str, Any], default_timeout: int) -> int:
    per = int(variant.get("max_timeout_sec") or 0)
    cap = int(fem.get("trial_timeout_sec") or default_timeout)
    if per > 0:
        return min(per, cap) if cap > 0 else per
    return cap or default_timeout


def run_thinkpad_impact(tri: dict[str, Any], dry_run: bool, timeout: int) -> dict[str, Any]:
    fem = tri.get("fem_impact") or {}
    variants = _fem_active_variants(fem)
    if not variants:
        return {"verdict": "ERROR", "error": "no enabled fem_impact variants (production_only)"}
    track_n = 0
    tri_status = WORKSPACE / "k10_tri_track_cae_status.json"
    if tri_status.exists():
        try:
            track_n = int(
                json.loads(tri_status.read_text(encoding="utf-8"))
                .get("tracks", {})
                .get("fem_impact_thinkpad", {})
                .get("n")
                or 0
            )
        except Exception:
            track_n = 0
    bench = _fem_bench_variant(fem, track_n + 1)
    variant = bench if bench else _pick_fem_variant(variants)
    job_timeout = _fem_job_timeout(fem, variant, timeout)
    skip_png_n = int(fem.get("skip_if_png_count") or 3)
    reuse_vtk = bool(fem.get("reuse_vtk_for_png", True))
    qc_limits = fem_qc.limits_from_fem_cfg(fem)
    qc_max_bbox = float(qc_limits["max_bbox_diag"])
    qc_max_coord = float(qc_limits["max_coordinate_abs"])
    qc_max_disp = float(qc_limits["max_displacement_abs"])
    cpu_affinity = str(fem.get("cpu_affinity") or "").strip()
    nice_level = max(0, min(19, int(fem.get("nice_level") or 0)))
    java_prefix = ""
    if cpu_affinity:
        if not all(part.isdigit() or part in {",", "-"} for part in cpu_affinity):
            raise ValueError(f"invalid fem_impact cpu_affinity: {cpu_affinity!r}")
        java_prefix += f"taskset -c {cpu_affinity} "
    if nice_level:
        java_prefix += f"nice -n {nice_level} "
    remote_bundle = str(
        fem.get("remote_bundle_root")
        or "/home/yasu/clawstack_satellite/impact_bundle/AUTO_FIX_ORIENTATION_20250804"
    )
    impact_home = f"{remote_bundle}/Impact"
    panel_root = str(fem.get("remote_root") or f"{impact_home}/160um_Panel_20250725")
    subdir = variant.get("subdir") or "Rough_Mesh"
    inp = variant.get("input") or "test.in"
    if "/" in subdir:
        case_dir = f"{impact_home}/{subdir}".replace("\\", "/")
    elif subdir in {"Rough_Mesh", "Normal_Mesh"}:
        case_dir = f"{panel_root}/{subdir}".replace("\\", "/")
    else:
        case_dir = f"{impact_home}/{subdir}".replace("\\", "/")
    trial_id = f"tri-thinkpad-fem_impact-{uuid.uuid4().hex[:8]}"

    if dry_run:
        return {
            "trial_id": trial_id,
            "verdict": "DRY_RUN",
            "variant": variant,
            "job_timeout_sec": job_timeout,
            "command_preview": (
                f"{java_prefix}java -Xmx4096m -Xss2m -cp .:doc:bin "
                f"run.Impact {case_dir}/{inp} (Impact FEM, not OpenRadioss)"
            ),
        }

    if not dry_run:
        _ensure_fem_png_scripts()

    lib_path = f"{impact_home}/lib_j3d/linux_amd64:{impact_home}/lib"
    png_shell = "/home/yasu/clawstack_satellite/scripts/thinkpad_fem_impact_png.sh"
    qc_script = "/home/yasu/clawstack_satellite/scripts/impact_vtk_quality_gate.py"
    # Heredoc avoids nested bash -lc quoting bugs under worker shell=True (INC-122).
    impact_script = (
        f"set -euo pipefail\n"
        f"IMPACT_HOME={impact_home}\n"
        f"CASE_DIR={case_dir}\n"
        f"INP={inp}\n"
        f"export LD_LIBRARY_PATH={lib_path}:${{LD_LIBRARY_PATH:-}}\n"
        f'cd "$IMPACT_HOME"\n'
        f"if [ ! -f bin/run/Impact.class ]; then ant -q compile; fi\n"
        f'if [ ! -f "$CASE_DIR/$INP" ]; then echo "FEM_IMPACT_INPUT_MISSING=$CASE_DIR/$INP"; exit 7; fi\n'
        # One FEM slot per ThinkPad. Any run.Impact process visible here is an
        # orphan from a previous timed-out/restarted controller.
        f'pkill -f "java.*[r]un.Impact" 2>/dev/null || true\n'
        f"sleep 1\n"
        f"latest_vtk() {{\n"
        f'  VTK="$(ls -1 "$CASE_DIR/${{INP}}"_surface_*.vtk 2>/dev/null | sort -V | tail -1 || true)"\n'
        f'  if [ -z "$VTK" ]; then VTK="$(ls -1 "$CASE_DIR/${{INP}}"_*.vtk 2>/dev/null | grep -v surface | sort -V | tail -1 || true)"; fi\n'
        f'  if [ -z "$VTK" ]; then echo FEM_IMPACT_QC_VTK_MISSING; return 6; fi\n'
        f'  echo "$VTK"\n'
        f"}}\n"
        f"run_qc() {{\n"
        f"  VTK_QC=$(latest_vtk)\n"
        f'  echo "FEM_IMPACT_QC_VTK=$VTK_QC"\n'
        f'  python3 "{qc_script}" "$VTK_QC" --max-bbox-diag {qc_max_bbox:g} --max-coordinate-abs {qc_max_coord:g} --max-displacement-abs {qc_max_disp:g}\n'
        f"}}\n"
    )
    if reuse_vtk:
        impact_script += (
            # T049: set -euo pipefail下で対象0件だとls exit2が代入文に伝播し無言即死する。|| true必須
            f'VTK_N=$(ls -1 "$CASE_DIR/{inp}"_*.vtk 2>/dev/null | wc -l || true)\n'
            f'PNG_N=$(ls -1 "$CASE_DIR/{inp}"*.png 2>/dev/null | wc -l || true)\n'
            f'if [ "$PNG_N" -ge {skip_png_n} ]; then\n'
            f"  run_qc\n"
            f"  echo FEM_IMPACT_SKIP_RECOMPUTE=png_exists\n"
            f"  echo FEM_IMPACT_PNG_COUNT=$PNG_N\n"
            f'  ls -1 "$CASE_DIR/{inp}"*.png 2>/dev/null | tail -3 || true\n'
            f"  exit 0\n"
            f"fi\n"
            f'if [ "$VTK_N" -gt 0 ]; then\n'
            f"  echo FEM_IMPACT_REUSE_VTK count=$VTK_N\n"
            f"  run_qc\n"
            f'  pkill -f "java.*run.Impact.*$CASE_DIR/$INP" 2>/dev/null || true\n'
            f'  bash {png_shell} "$CASE_DIR" "$INP"\n'
            f"  exit $?\n"
            f"fi\n"
        )
    impact_script += (
        f'{java_prefix}java -Xmx4096m -Xss2m -cp .:doc:bin run.Impact "$CASE_DIR/$INP"\n'
        f"run_qc\n"
        f'bash {png_shell} "$CASE_DIR" "$INP"\n'
    )
    run_cmd = "bash <<'FEMIMPACT_EOF'\n" + impact_script + "FEMIMPACT_EOF\n"
    node = sjp.load_node("thinkpad")
    base_url = sjp.worker_base_url(node)
    token = sjp.load_token()
    job = {
        "job_id": trial_id,
        "type": "shell",
        "timeout_sec": job_timeout,
        "payload": {"command": run_cmd},
        "report": {"mode": "sync"},
    }
    end_time = float(variant.get("end_time") or fem.get("progress_end_time") or 0.0)
    if end_time <= 0:
        try:
            inp_text = subprocess.run(
                [
                    "ssh",
                    "-i",
                    str(sjp.load_node("thinkpad").get("ssh_key_path") or Path.home() / ".ssh" / "id_ed25519"),
                    f"{sjp.load_node('thinkpad').get('ssh_user') or 'yasu'}@{sjp.load_node('thinkpad').get('ssh_host')}",
                    f"sed -n '1,30p' '{case_dir}/{inp}'",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=30,
            ).stdout
            match = re.search(r"run\s+from\s+\S+\s+to\s+([0-9.eE+-]+)", inp_text, re.IGNORECASE)
            end_time = float(match.group(1)) if match else 0.0
        except Exception:
            end_time = 0.0
    if end_time > 0:
        subprocess.Popen(
            [
                sys.executable,
                str(FEM_PROGRESS_SCRIPT),
                "--trial-id",
                trial_id,
                "--case-dir",
                case_dir,
                "--input",
                inp,
                "--end-time",
                str(end_time),
            ],
            cwd=str(ROOT),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    result = sjp.dispatch_job(base_url, token, job, job_timeout)
    stdout = result.get("stdout_tail") or ""

    def _worker_exit_ok(res: dict[str, Any]) -> bool:
        ec = res.get("exit_code")
        return ec is not None and int(ec) == 0

    ok = (
        (
            result.get("status") == "ok"
            or "FEM_IMPACT_SKIP_RECOMPUTE" in stdout
            or "FEM_IMPACT_REUSE_VTK" in stdout
        )
        # T049追補: kill(-15)/timeout中断ジョブがREUSE/SKIPマーカーだけでSUCCESS化する偽PASS防止。
        # 正規のSKIP/REUSEパスは必ずexit 0なので厳格チェックで問題ない
        and _worker_exit_ok(result)
        and (
            ".png" in stdout
            or "impact-vtk-png" in stdout
            or "FEM_IMPACT_PNG_COUNT=" in stdout
            or "FEM_IMPACT_SKIP_RECOMPUTE" in stdout
            or "FEM_IMPACT_REUSE_VTK" in stdout
        )
        and "FEM_IMPACT_QC_VERDICT=PASS" in stdout
        and "FAILED_MESH_EXPLOSION" not in stdout
    )
    if "FEM_IMPACT_INPUT_MISSING=" in stdout:
        verdict = "FAILED_INPUT_MISSING"
    else:
        verdict = "SUCCESS" if ok else ("FAILED_MESH_EXPLOSION" if "FAILED_MESH_EXPLOSION" in stdout else "FAILED")
    qc_metrics = fem_qc.parse_qc_stdout(stdout).get("metrics") or {}
    entry = {
        "id": trial_id,
        "category": "fem_impact",
        "verdict": verdict,
        "host": "thinkpad",
        "variant": variant,
        "case_dir": case_dir,
        "params": {"subdir": variant.get("subdir"), "input": variant.get("input")},
        "defects_detected": {
            f"qc_{k}": v for k, v in qc_metrics.items() if isinstance(v, (int, float))
        },
        "worker_result": {k: result.get(k) for k in ("status", "exit_code", "stdout_tail", "stderr_tail")},
    }
    gated = evolution_gate.apply_evolution_gate(
        "fem_impact_thinkpad",
        {"trial_id": trial_id, "verdict": verdict, "trial_entry": entry},
    )
    entry = gated.get("trial_entry") or entry
    verdict = str(gated.get("verdict") or entry.get("verdict") or verdict)
    try:
        cae_dispatch.merge_trial_into_log(entry)
    except Exception as exc:
        print(f"[fem_impact] merge_trial_into_log skipped: {exc}", flush=True)
    append_log({"track": "fem_impact", "trial": entry})
    if verdict == "SUCCESS":
        try:
            _maybe_cae_paraview_video_delivery(
                entry,
                node="thinkpad",
                category="fem_impact",
                dry_run=False,
                cfg=router.load_config(),
            )
        except Exception as exc:
            entry["cae_video_paraview_error"] = str(exc)[:200]
            print(f"[fem_impact] paraview video non-fatal: {exc}", flush=True)
    return gated


def _backoff_list(tri: dict[str, Any]) -> list[int]:
    raw = tri.get("error_backoff_sec") or [60, 120, 300, 600]
    out: list[int] = []
    for item in raw:
        try:
            sec = int(item)
        except (TypeError, ValueError):
            continue
        if sec > 0:
            out.append(sec)
    return out or [60, 120, 300, 600]


def _track_poll_seconds(tri: dict[str, Any], track_key: str, track_cfg: dict[str, Any]) -> int:
    if track_cfg.get("poll_interval_sec") is not None:
        return max(0, int(track_cfg.get("poll_interval_sec") or 0))
    return max(0, int(tri.get("poll_interval_sec") or 60))


def _storage_dispatch_gate() -> tuple[bool, str]:
    """Block only new dispatches while the host storage guard is active."""
    if not STORAGE_BLOCK_PATH.exists():
        return True, "storage guard clear"
    try:
        gate = json.loads(STORAGE_BLOCK_PATH.read_text(encoding="utf-8"))
        return False, str(gate.get("reason") or "host storage capacity is critical")
    except Exception as exc:
        return False, f"storage guard marker is unreadable: {exc}"


def _preflight_satellite(
    node_id: str,
    tri: dict[str, Any],
    *,
    thinkpad_idle_only: bool = False,
) -> tuple[bool, str, str]:
    """Return (may_dispatch, verdict_label, detail)."""
    cfg = router.load_config()
    skip_offline = bool(tri.get("skip_dispatch_if_offline", True))
    skip_overloaded = bool(tri.get("skip_dispatch_if_overloaded", True))

    if node_id == "thinkpad":
        if not skip_offline and not skip_overloaded:
            return True, "OK", "preflight disabled"
        ok, reason, _metrics = router.thinkpad_load_guard(cfg)
        if not ok:
            if "unavailable" in reason.lower() or "ssh" in reason.lower():
                return False, "SKIP_OFFLINE", reason
            if skip_overloaded or thinkpad_idle_only:
                return False, "SKIP_LOAD", reason
        return True, "OK", reason

    if skip_offline:
        online, _metrics, detail = router.probe_satellite_metrics(cfg, node_id)
        if not online:
            return False, "SKIP_OFFLINE", detail
    if skip_overloaded:
        load_ok, load_reason, _metrics = router.satellite_load_guard(cfg, node_id)
        if not load_ok:
            if "metrics unavailable" in load_reason:
                return False, "SKIP_OFFLINE", load_reason
            return False, "SKIP_LOAD", load_reason
    return True, "OK", "preflight passed"


def _sleep_for_track(
    tri: dict[str, Any],
    *,
    poll_seconds: int,
    fail_streak: int,
    last_verdict: str,
) -> int:
    backoffs = _backoff_list(tri)
    if last_verdict in ("SKIP_OFFLINE", "ERROR"):
        idx = min(max(fail_streak, 1) - 1, len(backoffs) - 1)
        return backoffs[idx]
    if last_verdict == "SKIP_LOAD":
        return max(poll_seconds, 30)
    if poll_seconds > 0:
        return poll_seconds
    return 0


def _notify_meaning_gate_stop(track: str, streak: int, threshold: int) -> None:
    msg = (
        f"⏸️ tri-track meaning gate: {track} を一時停止(連続失敗 {streak}/{threshold})\n"
        f"T019/P026: 無進化の再試行によるリソース空回りを防止。\n"
        f"🤖 P025-R1: Auto-Improverが10分以内にローカルLLMで原因分析→パラメータ修正→自動再開します。\n"
        f"(ローカルで改善しない場合は deepseek-v4-pro へ自動昇格。ユーザー対応は不要です)"
    )
    try:
        import cae_telegram_video_notify as tg

        tg.send_telegram_message(msg)
    except Exception as exc:
        print(f"[meaning_gate] telegram notify failed: {exc}", flush=True)


def track_loop(
    name: str,
    fn,
    state: dict[str, Any],
    *,
    dry_run: bool,
    continuous: bool,
    poll_seconds: int = 0,
    node_id: str | None = None,
    tri_cfg: dict[str, Any] | None = None,
    thinkpad_idle_only: bool = False,
) -> None:
    tri = tri_cfg or {}
    track_state = state.setdefault("tracks", {}).setdefault(
        name,
        {"n": 0, "last": None, "fail_streak": 0, "poll_seconds": poll_seconds},
    )
    track_state["poll_seconds"] = poll_seconds
    fail_streak = int(track_state.get("fail_streak") or 0)
    last_verdict = "OK"

    while not _stop.is_set():
        storage_ok, storage_detail = _storage_dispatch_gate()
        if not dry_run and not storage_ok:
            track_state["last"] = {
                "at": now_iso(),
                "verdict": "SKIP_STORAGE",
                "error": storage_detail[:300],
                "fail_streak": fail_streak,
            }
            append_log({"track": name, "skip": "SKIP_STORAGE", "detail": storage_detail})
            write_status(state)
            if not continuous:
                break
            time.sleep(max(poll_seconds, 60))
            continue

        if node_id and not dry_run:
            may_dispatch, pre_verdict, detail = _preflight_satellite(
                node_id,
                tri,
                thinkpad_idle_only=thinkpad_idle_only,
            )
            if not may_dispatch:
                fail_streak = fail_streak + 1 if pre_verdict == "SKIP_OFFLINE" else fail_streak
                track_state["fail_streak"] = fail_streak
                track_state["last"] = {
                    "at": now_iso(),
                    "verdict": pre_verdict,
                    "error": detail[:300],
                    "fail_streak": fail_streak,
                }
                append_log({"track": name, "skip": pre_verdict, "detail": detail, "node": node_id})
                write_status(state)
                last_verdict = pre_verdict
                if not continuous:
                    break
                delay = _sleep_for_track(tri, poll_seconds=poll_seconds, fail_streak=fail_streak, last_verdict=last_verdict)
                if delay > 0:
                    time.sleep(delay)
                continue

        try:
            result = fn()
            track_state["n"] = int(track_state.get("n") or 0) + 1
            verdict = str(result.get("verdict") or "UNKNOWN")
            track_state["last"] = {
                "at": now_iso(),
                "verdict": verdict,
                "trial_id": result.get("trial_id"),
                "fail_streak": fail_streak,
            }
            append_log({"track": name, "result": result})
            write_status(state)
            if verdict in ("ERROR", "FAILED", "FAILED_MESH_EXPLOSION", "FAILED_NO_EVOLUTION", "FAILED_SHORT_SHOT", "FAILED_MEANING_GATE", "FAILED_INPUT_MISSING"):
                fail_streak += 1
                last_verdict = "ERROR" if verdict == "ERROR" else verdict
            else:
                fail_streak = 0
                last_verdict = "OK"
            track_state["fail_streak"] = fail_streak
            track_state["last"]["fail_streak"] = fail_streak
            # T019/P026 meaning gate: 実行トライアルの連続失敗がしきい値到達でトラック自動停止
            # (SKIP_OFFLINE等のpreflightスキップはカウント外)
            track_cfg = tri.get("fem_impact") or {} if name == "fem_impact_thinkpad" else {}
            meaning_gate_max = int(
                track_cfg.get(
                    "meaning_gate_max_fail_streak",
                    tri.get("meaning_gate_max_fail_streak") or 0,
                )
                or 0
            )
            if meaning_gate_max > 0 and fail_streak >= meaning_gate_max:
                track_state["meaning_gate"] = {
                    "stopped": True,
                    "at": now_iso(),
                    "fail_streak": fail_streak,
                    "threshold": meaning_gate_max,
                }
                track_state["last"]["verdict"] = "STOPPED_MEANING_GATE"
                append_log({"track": name, "meaning_gate_stop": fail_streak, "threshold": meaning_gate_max})
                write_status(state)
                _notify_meaning_gate_stop(name, fail_streak, meaning_gate_max)
                break
        except Exception as exc:
            fail_streak += 1
            last_verdict = "ERROR"
            track_state["fail_streak"] = fail_streak
            track_state["last"] = {
                "at": now_iso(),
                "verdict": "ERROR",
                "error": str(exc)[:300],
                "fail_streak": fail_streak,
            }
            append_log({"track": name, "error": str(exc)})
            write_status(state)

        if not continuous:
            break
        delay = _sleep_for_track(tri, poll_seconds=poll_seconds, fail_streak=fail_streak, last_verdict=last_verdict)
        if delay > 0:
            time.sleep(delay)


def run_parallel_session(
    *,
    dry_run: bool,
    timeout: int,
    continuous: bool,
    sync_impact: bool,
) -> dict[str, Any]:
    tri = load_tri_cfg()
    if not tri.get("enabled", True):
        raise RuntimeError("tri_track_parallel disabled in cae_workload_router.yaml")

    if sync_impact and not dry_run:
        sync_script = ROOT / "scripts" / "k10_sync_impact_to_thinkpad.py"
        if sync_script.exists():
            subprocess.run([sys.executable, str(sync_script)], cwd=str(ROOT), check=False)

    of_cfg = tri.get("openfoam") or {}
    or_cfg = tri.get("openradioss") or {}
    state: dict[str, Any] = {
        "schema": "clawstack.k10_tri_track_cae.v1",
        "running": True,
        "continuous": continuous,
        "dry_run": dry_run,
        "policy": {
            "openfoam": f"{of_cfg.get('category')}@{of_cfg.get('host')}",
            "openradioss": f"{or_cfg.get('category')}@{or_cfg.get('host')}",
            "fem_impact": f"fem_impact@{tri.get('fem_impact', {}).get('host')}",
        },
        "tracks": {},
    }
    write_status(state)

    def of_fn():
        cycle_n = 0
        if STATUS_PATH.exists():
            try:
                cycle_n = int(
                    json.loads(STATUS_PATH.read_text(encoding="utf-8"))
                    .get("tracks", {})
                    .get("openfoam_lavie", {})
                    .get("n")
                    or 0
                )
            except Exception:
                cycle_n = 0
        params = _apply_llm_overrides("openfoam", of_params.build_openfoam_cad_params(cycle_n + 1))
        return run_satellite_trial_gated(
            "openfoam_lavie",
            node=str(of_cfg.get("host") or "lavie"),
            category=str(of_cfg.get("category") or "resin_fill_cad"),
            params=params,
            dry_run=dry_run,
            timeout=timeout,
        )

    def or_fn():
        return run_satellite_trial_gated(
            "openradioss_red_lavie",
            node=str(or_cfg.get("host") or "red_lavie"),
            category=str(or_cfg.get("category") or "press_blanking"),
            params=random_or_params(tri),
            dry_run=dry_run,
            timeout=timeout,
        )

    def impact_fn():
        return run_thinkpad_impact(tri, dry_run=dry_run, timeout=timeout)

    fem_poll = _track_poll_seconds(tri, "fem_impact", tri.get("fem_impact") or {})
    of_poll = _track_poll_seconds(tri, "openfoam", of_cfg)
    or_poll = _track_poll_seconds(tri, "openradioss", or_cfg)
    fem_idle_only = bool(((tri.get("fem_impact") or {}).get("bench_schedule") or {}).get("only_when_thinkpad_idle"))
    of_node = str(of_cfg.get("host") or "lavie")
    or_node = str(or_cfg.get("host") or "red_lavie")
    threads = [
        threading.Thread(
            target=track_loop,
            args=("openfoam_lavie", of_fn, state),
            kwargs={
                "dry_run": dry_run,
                "continuous": continuous,
                "poll_seconds": of_poll,
                "node_id": of_node,
                "tri_cfg": tri,
            },
            daemon=True,
        ),
        threading.Thread(
            target=track_loop,
            args=("openradioss_red_lavie", or_fn, state),
            kwargs={
                "dry_run": dry_run,
                "continuous": continuous,
                "poll_seconds": or_poll,
                "node_id": or_node,
                "tri_cfg": tri,
            },
            daemon=True,
        ),
        threading.Thread(
            target=track_loop,
            args=("fem_impact_thinkpad", impact_fn, state),
            kwargs={
                "dry_run": dry_run,
                "continuous": continuous,
                "poll_seconds": fem_poll,
                "node_id": "thinkpad",
                "tri_cfg": tri,
                "thinkpad_idle_only": fem_idle_only,
            },
            daemon=True,
        ),
    ]
    for t in threads:
        t.start()
    try:
        while any(t.is_alive() for t in threads):
            time.sleep(2)
    except KeyboardInterrupt:
        _stop.set()
    state["running"] = False
    write_status(state)
    return state


def _default_trial_timeout() -> int:
    tri = load_tri_cfg()
    return int(tri.get("trial_timeout_sec") or 10800)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Tri-track parallel CAE orchestrator")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--timeout",
        type=int,
        default=None,
        help=f"Per-trial timeout sec (default: tri_track_parallel.trial_timeout_sec, now {_default_trial_timeout()})",
    )
    parser.add_argument("--once", action="store_true", help="Single parallel burst (one trial per track)")
    parser.add_argument("--continuous", action="store_true", help="No rest between trials per track")
    parser.add_argument("--poll-seconds", type=int, default=0, help="Sleep between continuous bursts (0=none)")
    parser.add_argument("--no-sync-impact", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    timeout = int(args.timeout) if args.timeout is not None else _default_trial_timeout()

    continuous = args.continuous and not args.once
    if args.once:
        state = run_parallel_session(
            dry_run=args.dry_run,
            timeout=timeout,
            continuous=False,
            sync_impact=not args.no_sync_impact,
        )
        if args.json:
            print(json.dumps(state, ensure_ascii=False, indent=2))
        return 0

    if continuous:
        run_parallel_session(
            dry_run=args.dry_run,
            timeout=timeout,
            continuous=True,
            sync_impact=not args.no_sync_impact,
        )
        try:
            while True:
                time.sleep(60)
        except KeyboardInterrupt:
            _stop.set()
        return 0

    state = run_parallel_session(
        dry_run=args.dry_run,
        timeout=timeout,
        continuous=False,
        sync_impact=not args.no_sync_impact,
    )
    if args.json:
        print(json.dumps(state, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
