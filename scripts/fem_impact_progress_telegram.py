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

STAGES = tuple(range(5, 100, 5))
VTK_TIME_RE = re.compile(r"_surface_([0-9]+(?:\.[0-9]+)?)\.vtk$")


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


def remote_snapshot(case_dir: str, input_name: str) -> tuple[bool, str | None, float | None]:
    quoted = case_dir.replace("'", "'\"'\"'")
    inp = input_name.replace("'", "'\"'\"'")
    cmd = (
        f"CASE='{quoted}'; INP='{inp}'; "
        "if pgrep -f \"java.*[r]un.Impact.*$CASE/$INP\" >/dev/null; then echo RUNNING=1; "
        "else echo RUNNING=0; fi; "
        "ls -1 \"$CASE/${INP}\"_surface_*.vtk 2>/dev/null | sort -V | tail -1 || true"
    )
    result = run_ssh(cmd, timeout=30)
    if result.returncode != 0:
        raise RuntimeError((result.stderr or "SSH snapshot failed")[-300:])
    lines = [line.strip() for line in (result.stdout or "").splitlines() if line.strip()]
    running = "RUNNING=1" in lines
    vtk = next((line for line in reversed(lines) if line.endswith(".vtk")), None)
    match = VTK_TIME_RE.search(vtk or "")
    return running, vtk, float(match.group(1)) if match else None


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
        [sys.executable, str(RENDERER), str(local_vtk), str(out_dir)],
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
    args = parser.parse_args()

    state_path = STATE_DIR / f"{args.trial_id}.json"
    state = read_state(state_path, args.trial_id)
    sent = {int(x) for x in state.get("sent", [])}
    state.update({"case_dir": args.case_dir, "input": args.input, "end_time": args.end_time})

    if 0 not in sent:
        caption = (
            "[FEM Impact 解析開始]\n"
            f"job={args.trial_id}\n"
            f"input={args.input}\n進捗=0% (初期)"
        )
        if send_telegram_text(caption):
            sent.add(0)
            state["sent"] = sorted(sent)
            write_state(state_path, state)

    missing_after_exit = 0
    while any(stage not in sent for stage in STAGES):
        try:
            running, vtk, simulation_time = remote_snapshot(args.case_dir, args.input)
            state.update(
                {
                    "running": running,
                    "latest_vtk": vtk,
                    "simulation_time": simulation_time,
                    "last_error": None,
                }
            )
            progress = 100.0 * simulation_time / args.end_time if simulation_time is not None else 0.0
            state["progress_percent"] = round(progress, 3)
            for stage in STAGES:
                if stage in sent or progress < stage or not vtk:
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
