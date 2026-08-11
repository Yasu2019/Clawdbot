# -*- coding: utf-8 -*-
"""Send restart-safe FEM Impact progress notifications to Telegram."""
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
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
STATE_DIR = WORKSPACE / "fem_impact_progress"
ARTIFACT_DIR = WORKSPACE / "fem_impact_progress_artifacts"
RENDERER = ROOT / "scripts" / "impact_vtk_to_png.py"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
if str(WORKSPACE) not in sys.path:
    sys.path.insert(0, str(WORKSPACE))

from thinkpad_ssh_common import read_registry, run_ssh, ssh_target
from notify_image import send_telegram, send_telegram_text
import cae_workload_router as router
import impact_vtk_quality_gate as fem_qc

STAGES = tuple(range(5, 100, 5))
VTK_TIME_RE = re.compile(r"_surface_([0-9]+(?:\.[0-9]+)?)\.vtk$")
TELEGRAM_ALLOWED_INPUTS = frozenset(
    {"test_practical_doe01.in", "test_practical_doe01_x2.in", "test_practical_forming.in"}
)


def now_iso() -> str:
    return datetime.now(JST).isoformat(timespec="seconds")


def read_state(path: Path, trial_id: str) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"schema": "clawstack.fem_impact_progress.v1", "trial_id": trial_id, "sent": []}


def write_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    state["updated_at"] = now_iso()
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def remote_snapshot(
    case_dir: str,
    input_name: str,
    not_before_epoch: int,
) -> tuple[bool, str | None, float | None, str | None]:
    quoted = case_dir.replace("'", "'\"'\"'")
    inp = input_name.replace("'", "'\"'\"'")
    cmd = (
        f"CASE='{quoted}'; INP='{inp}'; "
        "if pgrep -f \"java.*[r]un.Impact.*$CASE/$INP\" >/dev/null; then echo RUNNING=1; "
        "else echo RUNNING=0; fi; "
        "INP_MTIME=$(stat -c %Y \"$CASE/$INP\" 2>/dev/null || echo 0); "
        "echo INPUT_MTIME=$INP_MTIME; "
        f"NOT_BEFORE={int(not_before_epoch)}; "
        "if [ \"$INP_MTIME\" -gt \"$NOT_BEFORE\" ]; then FRESH_AFTER=$INP_MTIME; "
        "else FRESH_AFTER=$NOT_BEFORE; fi; "
        "VTK=$(find \"$CASE\" -maxdepth 1 -type f "
        "-name \"${INP}_surface_*.vtk\" -newermt \"@$FRESH_AFTER\" 2>/dev/null "
        "| sort -V | tail -1 || true); "
        "if [ -n \"$VTK\" ]; then echo VTK=$VTK; echo VTK_MTIME=$(stat -c %Y \"$VTK\"); fi"
    )
    result = run_ssh(cmd, timeout=30)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "SSH snapshot failed")[-300:])
    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    running = "RUNNING=1" in lines
    vtk = next((line.split("=", 1)[1] for line in lines if line.startswith("VTK=")), None)
    input_mtime = next((int(line.split("=", 1)[1]) for line in lines if line.startswith("INPUT_MTIME=")), 0)
    vtk_mtime = next((int(line.split("=", 1)[1]) for line in lines if line.startswith("VTK_MTIME=")), 0)
    fresh_after = max(int(not_before_epoch), input_mtime)
    reason = None
    if vtk and vtk_mtime <= fresh_after:
        reason = f"stale VTK rejected: vtk_mtime={vtk_mtime} fresh_after={fresh_after}"
        vtk = None
    match = VTK_TIME_RE.search(vtk or "")
    return running, vtk, float(match.group(1)) if match else None, reason


def remote_quality_gate_and_stop(
    case_dir: str,
    input_name: str,
    remote_vtk: str,
    limits: dict,
) -> dict:
    """Run the mesh gate before notification and stop only this solver on explosion."""
    quoted = case_dir.replace("'", "'\"'\"'")
    inp = input_name.replace("'", "'\"'\"'")
    vtk = remote_vtk.replace("'", "'\"'\"'")
    qc_script = "/home/yasu/clawstack_satellite/scripts/impact_vtk_quality_gate.py"
    cmd = (
        f"CASE='{quoted}'; INP='{inp}'; VTK='{vtk}'; "
        f"QC=$(python3 '{qc_script}' \"$VTK\" "
        f"--max-bbox-diag {float(limits['max_bbox_diag']):g} "
        f"--max-coordinate-abs {float(limits['max_coordinate_abs']):g} "
        f"--max-displacement-abs {float(limits['max_displacement_abs']):g} 2>&1); "
        "QC_RC=$?; printf '%s\\n' \"$QC\"; echo QC_RC=$QC_RC; "
        "if printf '%s\\n' \"$QC\" | grep -q 'FEM_IMPACT_QC_VERDICT=FAILED_MESH_EXPLOSION'; then "
        "pkill -TERM -f \"java.*[r]un.Impact.*$CASE/$INP\" 2>/dev/null || true; sleep 2; "
        "if pgrep -f \"java.*[r]un.Impact.*$CASE/$INP\" >/dev/null; then "
        "pkill -KILL -f \"java.*[r]un.Impact.*$CASE/$INP\" 2>/dev/null || true; fi; "
        "echo FEM_IMPACT_AUTO_STOP=1; else echo FEM_IMPACT_AUTO_STOP=0; fi"
    )
    result = run_ssh(cmd, timeout=45)
    parsed = fem_qc.parse_qc_stdout(result.stdout or "")
    parsed["auto_stopped"] = "FEM_IMPACT_AUTO_STOP=1" in (result.stdout or "")
    parsed["command_ok"] = result.returncode == 0
    if result.returncode != 0:
        parsed["error"] = (result.stderr or "remote quality gate failed")[-300:]
    return parsed


def fetch_and_render(remote_vtk: str, trial_id: str, stage: int) -> Path:
    out_dir = ARTIFACT_DIR / trial_id / f"{stage:02d}"
    out_dir.mkdir(parents=True, exist_ok=True)
    local_vtk = out_dir / Path(remote_vtk).name
    registry = read_registry()
    target, key_path = ssh_target(registry)
    proc = subprocess.run(
        [
            "scp", "-q", "-i", str(key_path), "-o", "BatchMode=yes",
            "-o", "ConnectTimeout=10", f"{target}:{remote_vtk}", str(local_vtk),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=180,
    )
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or "SCP failed")[-300:])
    render = subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            str(local_vtk),
            str(out_dir),
            "--camera",
            "iso",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    if render.returncode != 0:
        raise RuntimeError((render.stderr or render.stdout or "render failed")[-500:])
    images = sorted(out_dir.glob(f"{local_vtk.stem}_*.png"))
    if not images:
        raise RuntimeError("renderer produced no PNG")
    return next((p for p in images if p.name.endswith("_vonmises.png")), images[0])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--case-dir", required=True)
    parser.add_argument("--input", required=True)
    parser.add_argument("--end-time", required=True, type=float)
    parser.add_argument("--poll-seconds", type=max_int, default=30)
    parser.add_argument("--not-before-epoch", type=int, default=0)
    parser.add_argument(
        "--wait-start-seconds",
        type=int,
        default=300,
        help="Wait this long for a queued solver to start before sending the 0%% notice.",
    )
    args = parser.parse_args()
    job_not_before = args.not_before_epoch or int(time.time())

    state_path = STATE_DIR / f"{args.trial_id}.json"
    state = read_state(state_path, args.trial_id)
    if args.input not in TELEGRAM_ALLOWED_INPUTS:
        state.update(
            {
                "case_dir": args.case_dir,
                "input": args.input,
                "end_time": args.end_time,
                "notification_blocked": True,
                "last_error": "input_not_approved_for_telegram",
            }
        )
        write_state(state_path, state)
        return 0
    sent = {int(x) for x in state.get("sent", [])}
    state.update({"case_dir": args.case_dir, "input": args.input, "end_time": args.end_time})

    missing_after_exit = 0
    seen_running = False
    limits = fem_qc.limits_from_router_cfg(router.load_config())
    wait_deadline = time.monotonic() + max(0, args.wait_start_seconds)
    while any(stage not in sent for stage in STAGES):
        try:
            running, vtk, simulation_time, rejection_reason = remote_snapshot(
                args.case_dir, args.input, job_not_before
            )
            if running:
                seen_running = True
            if vtk:
                quality = remote_quality_gate_and_stop(
                    args.case_dir, args.input, vtk, limits
                )
                state["quality_gate"] = quality
                if quality.get("verdict") == "FAILED_MESH_EXPLOSION":
                    state.update(
                        {
                            "running": False,
                            "latest_vtk": vtk,
                            "simulation_time": simulation_time,
                            "mesh_explosion_detected": True,
                            "auto_stopped": bool(quality.get("auto_stopped")),
                            "last_error": "FAILED_MESH_EXPLOSION",
                        }
                    )
                    write_state(state_path, state)
                    reasons = ", ".join(quality.get("reasons") or []) or "quality limit exceeded"
                    send_telegram_text(
                        "[FEM Impact メッシュ爆発・自動停止]\n"
                        f"job={args.trial_id}\ninput={args.input}\n"
                        f"解析時刻={simulation_time:.6g}/{args.end_time:.6g}\n"
                        f"原因={reasons}"
                    )
                    break
            if 0 not in sent and running:
                caption = (
                    "[FEM Impact 解析開始]\n"
                    f"job={args.trial_id}\n"
                    f"input={args.input}\n進捗=0% (初期)"
                )
                if send_telegram_text(caption):
                    sent.add(0)
                    state["sent"] = sorted(sent)
                    write_state(state_path, state)
            state.update(
                {
                    "running": running,
                    "latest_vtk": vtk,
                    "simulation_time": simulation_time,
                    "last_error": rejection_reason,
                }
            )
            progress = 100.0 * simulation_time / args.end_time if simulation_time is not None else 0.0
            state["progress_percent"] = round(progress, 3)
            for stage in STAGES:
                if stage in sent or progress < stage or not vtk or not seen_running:
                    continue
                image = fetch_and_render(vtk, args.trial_id, stage)
                caption = (
                    f"[FEM Impact 解析進捗 {stage}%]\n"
                    f"job={args.trial_id}\ninput={args.input}\n"
                    f"解析時刻={simulation_time:.6g}/{args.end_time:.6g}"
                )
                if send_telegram(image, caption):
                    sent.add(stage)
                    state["sent"] = sorted(sent)
                    state[f"stage_{stage}_vtk"] = vtk
                    write_state(state_path, state)
            if not seen_running and args.wait_start_seconds > 0:
                state["queued_waiting_for_solver"] = True
                missing_after_exit = 0
                if time.monotonic() >= wait_deadline:
                    state["last_error"] = "queued solver did not start before wait deadline"
                    write_state(state_path, state)
                    break
            else:
                state["queued_waiting_for_solver"] = False
                missing_after_exit = 0 if running else missing_after_exit + 1
            write_state(state_path, state)
            if not running and missing_after_exit >= 3:
                break
        except Exception as exc:
            state["last_error"] = str(exc)[:500]
            write_state(state_path, state)
        time.sleep(args.poll_seconds)
    return 0


def max_int(value: str) -> int:
    return max(5, int(value))


if __name__ == "__main__":
    raise SystemExit(main())
