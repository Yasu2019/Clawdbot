#!/usr/bin/env python3
"""Capture OpenFOAM run screenshots via ParaView Docker (LAVIE / K10 host Docker)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
PV_SCRIPT = SCRIPTS / "pv_scripts" / "openfoam_run_screenshot.py"
PV_VOF_SCRIPT = SCRIPTS / "pv_scripts" / "openfoam_vof_screenshot.py"
def te_log_path() -> Path:
    ws = os.environ.get("CAE_TE_WORKSPACE", "").strip()
    if ws:
        return Path(ws) / "results" / "cae_te_log.json"
    return ROOT / "data" / "cae_te_workspace" / "results" / "cae_te_log.json"

PV_IMAGE = os.environ.get("CAE_PARAVIEW_IMAGE", "clawstack-unified-paraview:latest")
OPENFOAM_IMAGE = os.environ.get("CAE_OPENFOAM_IMAGE", "opencfd/openfoam-dev:latest")
OPENFOAM_BASHRC = "/usr/lib/openfoam/openfoam2512/etc/bashrc"
PVPYTHON = os.environ.get("CAE_PARAVIEW_PVPYTHON", "/opt/paraview/install/bin/pvpython")


def _docker_mount_path(run_dir: Path) -> str:
    return str(run_dir.resolve()).replace("\\", "/").replace("d:", "/d").replace("D:", "/d")


def _ensure_case_foam(run_dir: Path) -> Path:
    foam = run_dir / "case.foam"
    if not foam.exists():
        foam.write_text(
            "FoamFile\n{\n    version     2.0;\n    format      ascii;\n    class       dictionary;\n    object      foamFile;\n}\n",
            encoding="utf-8",
        )
    return foam


def _has_time_dirs(run_dir: Path) -> bool:
    for child in run_dir.iterdir():
        if not child.is_dir():
            continue
        name = child.name
        try:
            float(name)
            if (child / "U").exists() or (child / "p").exists():
                return True
        except ValueError:
            continue
    return False


def _foam_to_vtk(run_dir: Path, mount: str, timeout: int = 120) -> bool:
    cmd = [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{mount}:/workspace",
        "-w",
        "/workspace",
        OPENFOAM_IMAGE,
        "bash",
        "-c",
        f"source {OPENFOAM_BASHRC} && cd /workspace && foamToVTK -latestTime 2>&1",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    return proc.returncode == 0 and (run_dir / "VTK").is_dir()


MIN_GOOD_PNG_BYTES = 10_000


def capture_openfoam_run_dir(
    run_dir: Path,
    out_name: str = "paraview_snapshot.png",
    *,
    timeout: int = 180,
    skip_if_exists: bool = True,
    vtk_first: bool = True,
) -> Path | None:
    """Render pressure/velocity field at latest time. Returns PNG path or None."""
    run_dir = run_dir.resolve()
    if not run_dir.is_dir():
        return None
    out_path = run_dir / out_name
    if (
        skip_if_exists
        and out_path.exists()
        and out_path.stat().st_size >= MIN_GOOD_PNG_BYTES
    ):
        return out_path
    if not _has_time_dirs(run_dir):
        return None

    _ensure_case_foam(run_dir)
    mount = _docker_mount_path(run_dir)
    if vtk_first:
        _foam_to_vtk(run_dir, mount, timeout=timeout)

    is_vof = (run_dir / "0" / "alpha.polymer").exists() or any(
        (run_dir / t / "alpha.polymer").exists()
        for t in ("0",)
    )
    for child in run_dir.iterdir():
        if child.is_dir() and (child / "alpha.polymer").exists():
            is_vof = True
            break
    pv_script = PV_VOF_SCRIPT if is_vof and PV_VOF_SCRIPT.exists() else PV_SCRIPT
    pv_entry = f"/pvscripts/{pv_script.name}"

    cmd = [
        "docker",
        "run",
        "--rm",
        "-e",
        "MESA_GL_VERSION_OVERRIDE=3.3",
        "-e",
        "LIBGL_ALWAYS_SOFTWARE=1",
        "--entrypoint",
        PVPYTHON,
        "-v",
        f"{mount}:/workspace",
        "-v",
        f"{pv_script.parent.resolve()}:/pvscripts:ro",
        "-w",
        "/workspace",
        PV_IMAGE,
        pv_entry,
        "/workspace",
        f"/workspace/{out_name}",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
    if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size < MIN_GOOD_PNG_BYTES:
        if not vtk_first and _foam_to_vtk(run_dir, mount, timeout=timeout):
            proc2 = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, encoding="utf-8", errors="replace")
            if (
                proc2.returncode == 0
                and out_path.exists()
                and out_path.stat().st_size >= MIN_GOOD_PNG_BYTES
            ):
                return out_path
        err = (proc.stderr or proc.stdout or "")[-800:]
        print(f"[paraview-capture] failed: {err}")
        if out_path.exists() and out_path.stat().st_size > 1000:
            print(f"[paraview-capture] warn: small PNG {out_path.stat().st_size} bytes")
        return out_path if out_path.exists() and out_path.stat().st_size >= MIN_GOOD_PNG_BYTES else None
    return out_path


def find_trial(trial_id: str | None = None, category: str | None = None) -> dict | None:
    log_path = te_log_path()
    if not log_path.exists():
        return None
    trials = json.loads(log_path.read_text(encoding="utf-8")).get("trials") or []
    if trial_id:
        for t in trials:
            if t.get("id") == trial_id:
                return t
        return None
    for t in trials:
        if category and t.get("category") != category:
            continue
        if t.get("verdict") == "SUCCESS":
            return t
    return None


def resolve_run_dir(trial: dict, workspace: Path) -> Path | None:
    rd = trial.get("run_dir") or trial.get("artifact_path") or ""
    if rd:
        p = Path(str(rd))
        if p.is_dir():
            return p
    tid = trial.get("id")
    if tid:
        candidate = workspace / "runs" / str(tid)
        if candidate.is_dir():
            return candidate
    return None


def _load_telegram_env() -> tuple[str, str]:
    candidates = [
        Path(os.environ.get("SATELLITE_INSTALL_ROOT", "")) / ".env",
        Path("C:/clawstack_satellite/.env"),
        Path("E:/clawstack_satellite/.env"),
        ROOT / ".env",
    ]
    bot = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    for env_path in candidates:
        if not env_path or not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line.startswith("TELEGRAM_BOT_TOKEN=") and not bot:
                bot = line.split("=", 1)[1].strip().strip('"').strip("'")
            if line.startswith("TELEGRAM_CHAT_ID=") and not chat:
                chat = line.split("=", 1)[1].strip().strip('"').strip("'")
    if not bot or not chat:
        raise RuntimeError("TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID missing")
    return bot, chat


def _send_telegram_direct(png_path: Path, caption: str) -> bool:
    import json
    import mimetypes
    import uuid
    import urllib.request

    bot, chat = _load_telegram_env()
    chat_id = chat
    body_caption = caption
    for guard_dir in (ROOT / "data" / "workspace", SCRIPTS.parent / "data" / "workspace"):
        guard_py = guard_dir / "outbound_delivery_guard.py"
        if not guard_py.exists():
            continue
        sys.path.insert(0, str(guard_dir))
        try:
            from outbound_delivery_guard import (  # noqa: WPS433
                ensure_allowed_telegram_chat_id,
                prepare_telegram_message,
            )

            chat_id = ensure_allowed_telegram_chat_id(chat, "cae_te_paraview_capture.send_photo")
            body_caption = prepare_telegram_message(caption, "LAVIE")
            break
        except Exception:
            pass

    boundary = f"----paraview{uuid.uuid4().hex}"
    body: list[bytes] = []
    for key, val in (("chat_id", chat_id), ("caption", body_caption[:1024])):
        body.append(f"--{boundary}\r\n".encode())
        body.append(f'Content-Disposition: form-data; name="{key}"\r\n\r\n'.encode())
        body.append(f"{val}\r\n".encode())
    mime = mimetypes.guess_type(png_path.name)[0] or "image/png"
    body.append(f"--{boundary}\r\n".encode())
    body.append(
        f'Content-Disposition: form-data; name="photo"; filename="{png_path.name}"\r\n'.encode()
    )
    body.append(f"Content-Type: {mime}\r\n\r\n".encode())
    body.append(png_path.read_bytes())
    body.append(f"\r\n--{boundary}--\r\n".encode())
    payload = b"".join(body)
    url = f"https://api.telegram.org/bot{bot}/sendPhoto"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        data = json.loads(resp.read().decode("utf-8", errors="replace"))
    if data.get("ok"):
        print(f"[OK] Telegram photo sent: {png_path.name}")
        return True
    print(f"[ERR] Telegram: {data.get('description', data)}")
    return False


def send_png_telegram(png_path: Path, caption: str) -> bool:
    try:
        sys.path.insert(0, str(SCRIPTS))
        import cae_te_visual_report as vis

        return vis.send_telegram_photo(png_path, caption)
    except Exception:
        return _send_telegram_direct(png_path, caption)


def main() -> int:
    parser = argparse.ArgumentParser(description="ParaView OpenFOAM snapshot + optional Telegram")
    parser.add_argument("--run-dir", default="", help="OpenFOAM case run directory")
    parser.add_argument("--trial-id", default="", help="Trial id (lookup run under workspace)")
    parser.add_argument("--workspace", default="", help="CAE_TE_WORKSPACE")
    parser.add_argument("--send-telegram", action="store_true")
    parser.add_argument("--force", action="store_true", help="Re-capture even if PNG exists")
    args = parser.parse_args()

    workspace = Path(args.workspace or os.environ.get("CAE_TE_WORKSPACE", str(ROOT / "data" / "cae_te_workspace")))
    trial = None
    if args.trial_id:
        trial = find_trial(trial_id=args.trial_id)
    run_dir = Path(args.run_dir) if args.run_dir else None
    if trial and not run_dir:
        run_dir = resolve_run_dir(trial, workspace)
    if not run_dir or not run_dir.is_dir():
        print(json.dumps({"ok": False, "error": "run_dir not found"}, ensure_ascii=False))
        return 1

    png = capture_openfoam_run_dir(run_dir, skip_if_exists=not args.force)
    if not png:
        print(json.dumps({"ok": False, "error": "capture_failed", "run_dir": str(run_dir)}, ensure_ascii=False))
        return 1

    payload = {"ok": True, "run_dir": str(run_dir), "paraview_png": str(png)}
    if args.send_telegram:
        tid = (trial or {}).get("id") or run_dir.name
        cat = (trial or {}).get("category") or "openfoam"
        cap = (
            f"[ParaView] {tid}\n"
            f"Category: {cat}\n"
            f"Real OpenFOAM |U| field (latest time)\n"
            f"Run: {run_dir.name}"
        )
        payload["telegram_sent"] = send_png_telegram(png, cap)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
