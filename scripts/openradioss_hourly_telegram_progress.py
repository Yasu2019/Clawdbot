import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import datetime
import json
import re
import subprocess
import tempfile
import time
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import cae_te_paraview_capture
import cae_telegram_video_notify
import openradioss_vtk_video_telegram


TRIAL_ID = "k10-openradioss-4mmx4mm-spm80-20260725-v3"
RUN_DIR = ROOT / "data" / "cae_te_workspace" / "runs" / TRIAL_ID
ENGINE_OUT = RUN_DIR / "4mmx4mm_ASSY_20260105_0001.out"
ANIMATION_PREFIX = "4mmx4mm_ASSY_20260105A"
STATUS_PATH = (
    ROOT
    / "data"
    / "workspace"
    / "openradioss_urgent_k10"
    / "telegram_progress_status_spm80.json"
)
TARGET_TIME_S = 0.03790598403909747
TIME_STEP_S = 8.0e-9
TOTAL_CYCLES = int(round(TARGET_TIME_S / TIME_STEP_S))


def now_jst() -> str:
    return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).isoformat()


def write_status(payload: dict) -> None:
    STATUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp = STATUS_PATH.with_suffix(".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATUS_PATH)


def parse_latest_progress() -> dict:
    if not ENGINE_OUT.exists():
        raise FileNotFoundError(ENGINE_OUT)
    text = ENGINE_OUT.read_text(encoding="utf-8", errors="replace")
    matches = re.findall(
        r"(?m)^\s*(\d+)\s+([\d.E+\-]+)\s+([\d.E+\-]+)\s+\S+\s+\d+\s+([-\d.]+)%"
        r".*?\s([\d.E+\-]+)\s+([\d.E+\-]+)\s+([\d.E+\-]+)\s*$",
        text,
    )
    if not matches:
        raise RuntimeError("OpenRadioss cycle line not found")
    cycle, time_s, dt_s, error_pct, mass_error, total_mass, mass_added = matches[-1]
    cycle_value = int(cycle)
    progress_pct = min(100.0, cycle_value / TOTAL_CYCLES * 100.0)
    return {
        "cycle": cycle_value,
        "time_s": float(time_s),
        "dt_s": float(dt_s),
        "error_pct": float(error_pct),
        "mass_error_ratio": float(mass_error),
        "total_mass": float(total_mass),
        "mass_added": float(mass_added),
        "progress_pct": progress_pct,
    }


def estimate_remaining_hours(progress: dict, started_at: float) -> float | None:
    cycle = int(progress["cycle"])
    if cycle <= 0:
        return None
    elapsed = max(1.0, time.time() - started_at)
    cycles_per_second = cycle / elapsed
    if cycles_per_second <= 0:
        return None
    return max(0.0, (TOTAL_CYCLES - cycle) / cycles_per_second / 3600.0)


def stable_animation() -> Path | None:
    now = time.time()
    candidates = sorted(RUN_DIR.glob(f"{ANIMATION_PREFIX}*"))
    stable = [
        path
        for path in candidates
        if path.is_file() and path.stat().st_size > 1000 and now - path.stat().st_mtime >= 120
    ]
    return stable[-1] if stable else None


def build_latest_png(animation: Path) -> Path | None:
    with tempfile.TemporaryDirectory(prefix="openradioss_progress_") as temp_dir:
        temp = Path(temp_dir)
        animation_copy = temp / animation.name
        animation_copy.write_bytes(animation.read_bytes())
        command = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{temp.as_posix()}:/workspace",
            "-w",
            "/workspace",
            "clawstack-unified-openradioss:latest",
            "anim_to_vtk_linux64_gf",
            animation_copy.name,
        ]
        converted = subprocess.run(command, capture_output=True, timeout=180)
        if converted.returncode != 0 or len(converted.stdout) < 1000:
            return None
        vtk_path = temp / f"{animation.stem}.vtk"
        vtk_path.write_bytes(converted.stdout)
        png_path = temp / "openradioss_progress.png"
        if not openradioss_vtk_video_telegram._render_vonmises_png(vtk_path, png_path):
            return None
        persistent_png = STATUS_PATH.parent / "openradioss_spm80_latest.png"
        persistent_png.write_bytes(png_path.read_bytes())
        return persistent_png


def caption(progress: dict, remaining_hours: float | None, image_name: str = "") -> str:
    remaining = "calculating" if remaining_hours is None else f"{remaining_hours:.1f} h"
    lines = [
        "OpenRadioss 4x4 mm hourly progress",
        f"Trial: {TRIAL_ID}",
        f"Cycle: {progress['cycle']:,} / {TOTAL_CYCLES:,}",
        f"Physical time: {progress['time_s'] * 1000.0:.4f} / {TARGET_TIME_S * 1000.0:.4f} ms",
        f"Progress: {progress['progress_pct']:.2f}%",
        f"Energy error: {progress['error_pct']:.1f}%",
        f"Mass change: {progress['mass_error_ratio'] * 100.0:.2f}%",
        f"Estimated remaining: {remaining}",
        "Targets: punch Z=-2.000 mm, stripper Z=-0.190 mm",
    ]
    if image_name:
        lines.append(f"Image source: {image_name}")
    return "\n".join(lines)


def send_once(started_at: float, dry_run: bool = False) -> dict:
    progress = parse_latest_progress()
    remaining = estimate_remaining_hours(progress, started_at)
    animation = stable_animation()
    png = build_latest_png(animation) if animation else None
    text = caption(progress, remaining, animation.name if animation else "")
    if dry_run:
        ok = True
        mode = "dry_run"
    elif png and png.exists():
        ok = cae_te_paraview_capture.send_png_telegram(png, text)
        mode = "photo"
    else:
        ok = cae_telegram_video_notify.send_telegram_message(text)
        mode = "message"
    result = {
        "ok": bool(ok),
        "mode": mode,
        "sent_at": now_jst(),
        "progress": progress,
        "remaining_hours": remaining,
        "animation": str(animation) if animation else "",
        "png": str(png) if png else "",
    }
    write_status(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Hourly OpenRadioss progress to Telegram")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--interval-sec", type=int, default=3600)
    parser.add_argument("--solver-pid", type=int, default=20644)
    args = parser.parse_args()
    started_at = datetime.datetime.fromisoformat("2026-07-25T15:57:02+09:00").timestamp()
    while True:
        try:
            result = send_once(started_at, dry_run=args.dry_run)
            print(
                f"[telegram-progress] ok={result['ok']} mode={result['mode']} "
                f"cycle={result['progress']['cycle']}",
                flush=True,
            )
        except Exception as exc:
            write_status({"ok": False, "error": str(exc), "at": now_jst()})
            print(f"[telegram-progress] error={exc}", flush=True)
        if args.once:
            return 0
        try:
            import psutil

            if not psutil.pid_exists(args.solver_pid):
                return 0
        except ImportError:
            pass
        time.sleep(max(60, args.interval_sec))


if __name__ == "__main__":
    raise SystemExit(main())
