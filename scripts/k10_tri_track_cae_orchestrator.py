# -*- coding: utf-8 -*-
"""K10 tri-track parallel CAE: OpenFOAM@lavie + OpenRadioss@red_lavie + FEM Impact@thinkpad.

Continuous trial-and-error with no idle gap between cycles (per-track loops).
"""
from __future__ import annotations

import json
import os
import random
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

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
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


def random_or_params(tri: dict[str, Any]) -> dict[str, Any]:
    ranges = (tri.get("openradioss") or {}).get("param_ranges") or {}
    out: dict[str, Any] = {"case_label": str((tri.get("openradioss") or {}).get("case_label") or "4mmx4mm")}
    for key, bounds in ranges.items():
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            lo, hi = float(bounds[0]), float(bounds[1])
            out[key] = round(random.uniform(lo, hi), 4)
    return out


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
    qc = fem.get("quality_gate") or {}
    qc_max_bbox = float(qc.get("max_bbox_diag") or 100000.0)
    qc_max_coord = float(qc.get("max_coordinate_abs") or 100000.0)
    qc_max_disp = float(qc.get("max_displacement_abs") or 100000.0)
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
            "command_preview": f"java run.Impact {case_dir}/{inp} (Impact FEM, not OpenRadioss)",
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
        f'test -f "$CASE_DIR/$INP"\n'
        f'pkill -f "java.*run.Impact.*$CASE_DIR/$INP" 2>/dev/null || true\n'
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
            f'VTK_N=$(ls -1 "$CASE_DIR/{inp}"_*.vtk 2>/dev/null | wc -l)\n'
            f'PNG_N=$(ls -1 "$CASE_DIR/{inp}"*.png 2>/dev/null | wc -l)\n'
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
        f'java -Xmx4096m -Xss2m -cp .:doc:bin run.Impact "$CASE_DIR/$INP"\n'
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
    result = sjp.dispatch_job(base_url, token, job, job_timeout)
    stdout = result.get("stdout_tail") or ""
    ok = (
        (
            result.get("status") == "ok"
            or "FEM_IMPACT_SKIP_RECOMPUTE" in stdout
            or "FEM_IMPACT_REUSE_VTK" in stdout
        )
        and (
            int(result.get("exit_code") or 1) == 0
            or "FEM_IMPACT_SKIP_RECOMPUTE" in stdout
            or "FEM_IMPACT_REUSE_VTK" in stdout
        )
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
    verdict = "SUCCESS" if ok else ("FAILED_MESH_EXPLOSION" if "FAILED_MESH_EXPLOSION" in stdout else "FAILED")
    entry = {
        "id": trial_id,
        "category": "fem_impact",
        "verdict": verdict,
        "host": "thinkpad",
        "variant": variant,
        "case_dir": case_dir,
        "worker_result": {k: result.get(k) for k in ("status", "exit_code", "stdout_tail", "stderr_tail")},
    }
    cae_dispatch.merge_trial_into_log(entry)
    append_log({"track": "fem_impact", "trial": entry})
    _maybe_cae_paraview_video_delivery(
        entry,
        node="thinkpad",
        category="fem_impact",
        dry_run=False,
        cfg=router.load_config(),
    )
    return {"trial_id": trial_id, "verdict": verdict, "trial_entry": entry}


def track_loop(
    name: str,
    fn,
    state: dict[str, Any],
    *,
    dry_run: bool,
    continuous: bool,
    poll_seconds: int = 0,
) -> None:
    track_state = state.setdefault("tracks", {}).setdefault(name, {"n": 0, "last": None})
    while not _stop.is_set():
        try:
            result = fn()
            track_state["n"] = int(track_state.get("n") or 0) + 1
            track_state["last"] = {
                "at": now_iso(),
                "verdict": result.get("verdict"),
                "trial_id": result.get("trial_id"),
            }
            append_log({"track": name, "result": result})
            write_status(state)
        except Exception as exc:
            track_state["last"] = {"at": now_iso(), "verdict": "ERROR", "error": str(exc)[:300]}
            append_log({"track": name, "error": str(exc)})
            write_status(state)
        if not continuous:
            break
        if poll_seconds > 0:
            time.sleep(poll_seconds)


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
        return run_satellite_trial(
            node=str(of_cfg.get("host") or "lavie"),
            category=str(of_cfg.get("category") or "resin_fill_vof"),
            params=None,
            dry_run=dry_run,
            timeout=timeout,
        )

    def or_fn():
        return run_satellite_trial(
            node=str(or_cfg.get("host") or "red_lavie"),
            category=str(or_cfg.get("category") or "press_blanking"),
            params=random_or_params(tri),
            dry_run=dry_run,
            timeout=timeout,
        )

    def impact_fn():
        return run_thinkpad_impact(tri, dry_run=dry_run, timeout=timeout)

    fem_poll = int((tri.get("fem_impact") or {}).get("poll_interval_sec") or 0)
    threads = [
        threading.Thread(target=track_loop, args=("openfoam_lavie", of_fn, state), kwargs={"dry_run": dry_run, "continuous": continuous}, daemon=True),
        threading.Thread(target=track_loop, args=("openradioss_red_lavie", or_fn, state), kwargs={"dry_run": dry_run, "continuous": continuous}, daemon=True),
        threading.Thread(
            target=track_loop,
            args=("fem_impact_thinkpad", impact_fn, state),
            kwargs={"dry_run": dry_run, "continuous": continuous, "poll_seconds": fem_poll},
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
