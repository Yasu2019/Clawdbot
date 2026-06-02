# -*- coding: utf-8 -*-
"""LAVIE VOF fill video -> Telegram (K10 render path; avoids LAVIE ffmpeg/pyvista gaps)."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import shutil
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "cae_te_workspace"
INCOMING = ROOT / "dist" / "incoming"

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync

LAVIE_FILL_CATEGORIES = frozenset(
    {
        "resin_fill_cad",
        "resin_fill_vof",
        "resin_fill_closed_pack",
        "resin_fill_pack",
        "resin_fill_doe",
    }
)
UPLOAD_PORT = 5689


def lavie_run_dir(trial_id: str, cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or router.load_config()
    ws = (cfg.get("cae_workspace_sync") or {}).get(
        "lavie_work_dir", "E:/clawstack_satellite/data/work/cae_te_workspace"
    )
    return f"{ws}\\runs\\{trial_id}".replace("/", "\\")


def probe_lavie_worker(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    cfg = cfg or router.load_config()
    try:
        token = sjp.load_token()
        node = sjp.load_node("lavie")
        base = sjp.worker_base_url(node)
        return sjp.probe_worker(base, token)
    except Exception as exc:
        return False, str(exc)[:200]


def zip_run_on_lavie(trial_id: str, lavie_run_dir: str, *, timeout: int = 600) -> bool:
    lavie_temp = r"C:\lavie_usb_pack\temp"
    lavie_zip = f"{lavie_temp}\\{trial_id}.zip"
    zip_ps = (
        f"powershell -NoProfile -Command \""
        f"New-Item -ItemType Directory -Force -Path '{lavie_temp}' | Out-Null; "
        f"if (Test-Path '{lavie_zip}') {{ Remove-Item '{lavie_zip}' -Force }}; "
        f"Compress-Archive -LiteralPath '{lavie_run_dir}' -DestinationPath '{lavie_zip}' -Force; "
        f"Write-Host ZIP_DONE\""
    )
    r = sync.dispatch_shell("lavie", zip_ps, timeout, sjp.load_token())
    out = (r.get("stdout_tail") or "") + (r.get("stderr_tail") or "")
    return r.get("status") == "ok" and "ZIP_DONE" in out


def pull_zip_from_lavie(trial_id: str, *, timeout: int = 900) -> Path | None:
    """LAVIE PUT zip to K10 upload server; return local zip path."""
    k10_ip = sync.detect_k10_tailscale_ip()
    zip_name = f"{trial_id}.zip"
    lavie_zip = f"C:\\lavie_usb_pack\\temp\\{zip_name}"
    received: dict[str, Path] = {}

    class UploadHandler(BaseHTTPRequestHandler):
        def do_PUT(self):
            name = self.path.lstrip("/") or zip_name
            dest = INCOMING / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            length = int(self.headers.get("Content-Length", 0))
            dest.write_bytes(self.rfile.read(length))
            received["path"] = dest
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"OK")

        def log_message(self, fmt, *args):
            print(f"[upload] {fmt % args}", flush=True)

    INCOMING.mkdir(parents=True, exist_ok=True)
    server = HTTPServer(("0.0.0.0", UPLOAD_PORT), UploadHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        upload_url = f"http://{k10_ip}:{UPLOAD_PORT}/{zip_name}"
        put_ps = (
            f"powershell -NoProfile -Command \""
            f"Invoke-WebRequest -Uri '{upload_url}' -Method Put -InFile '{lavie_zip}' "
            f"-UseBasicParsing; Write-Host UPLOAD_OK\""
        )
        r = sync.dispatch_shell("lavie", put_ps, timeout, sjp.load_token())
        out = (r.get("stdout_tail") or "") + (r.get("stderr_tail") or "")
        if "UPLOAD_OK" not in out or "path" not in received:
            print(f"[NG] upload: {out[-400:]}", flush=True)
            return None
        return received["path"]
    finally:
        server.shutdown()


def extract_run_zip(zip_path: Path, trial_id: str) -> Path:
    local_run = WORKSPACE / "runs" / trial_id
    with tempfile.TemporaryDirectory(prefix="lavie_run_pull_") as td:
        extract_root = Path(td) / "extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(extract_root)
        nested = extract_root / trial_id
        src = nested if nested.is_dir() else extract_root
        if local_run.exists():
            shutil.rmtree(local_run, ignore_errors=True)
        shutil.copytree(src, local_run)
    return local_run


def send_fill_video_via_k10_pull(
    trial_id: str,
    *,
    run_dir: str = "",
    category: str = "resin_fill_cad",
    cfg: dict[str, Any] | None = None,
    delete_after: bool = True,
) -> dict[str, Any]:
    """
    Canonical path: zip on LAVIE -> upload to K10 -> pyvista+ffmpeg on K10 -> Telegram.
    Does not require ffmpeg/pyvista on LAVIE.
    """
    cfg = cfg or router.load_config()
    ok, detail = probe_lavie_worker(cfg)
    if not ok:
        return {"ok": False, "error": f"lavie_worker_offline: {detail}"}

    rd = run_dir.replace("/", "\\") if run_dir else lavie_run_dir(trial_id, cfg)
    if not zip_run_on_lavie(trial_id, rd):
        return {"ok": False, "error": "lavie_zip_failed"}

    zpath = pull_zip_from_lavie(trial_id)
    if not zpath or not zpath.exists():
        return {"ok": False, "error": "k10_pull_failed"}

    local_run = extract_run_zip(zpath, trial_id)
    import moldflow_fill_video_telegram as mfv

    sent = mfv.send_fill_video_for_run(
        local_run,
        trial_id,
        category=category,
        host="lavie",
        delete_after=delete_after,
    )
    try:
        zpath.unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": sent, "source": "k10_pull_render", "trial_id": trial_id, "run_dir": str(local_run)}


def try_lavie_local_fill_video(
    trial_id: str,
    run_dir: str,
    *,
    cfg: dict[str, Any] | None = None,
    timeout_sec: int = 900,
) -> dict[str, Any] | None:
    """Optional fast path when LAVIE has tools\\ffmpeg.exe + pyvista."""
    cfg = cfg or router.load_config()
    repo = (cfg.get("cae_workspace_sync") or {}).get("lavie_repo_root", "C:/lavie_usb_pack")
    rd = run_dir.replace("/", "\\") if run_dir else lavie_run_dir(trial_id, cfg)
    py = r"C:\Users\ysuzu\AppData\Local\Programs\Python\Python311\python.exe"
    cmd = (
        f'cmd.exe /c "set PATH={repo}\\tools;%PATH%&& cd /d \"{repo}\"&& '
        f'"{py}" scripts\\moldflow_fill_video_telegram.py '
        f'--run-dir \"{rd}\" --trial-id \"{trial_id}\""'
    )
    r = sync.dispatch_shell("lavie", cmd, timeout_sec, sjp.load_token())
    tail = (r.get("stdout_tail") or "") + (r.get("stderr_tail") or "")
    if r.get("status") == "ok" and "[telegram] sent=True" in tail:
        return {"ok": True, "source": "lavie_local_render", "trial_id": trial_id}
    return None


def send_fill_video_after_success(
    trial_id: str,
    *,
    category: str,
    run_dir: str = "",
    cfg: dict[str, Any] | None = None,
    k10_pull_only: bool = False,
) -> dict[str, Any]:
    """Try LAVIE local render; fallback K10 pull (always works if worker up)."""
    if category not in LAVIE_FILL_CATEGORIES and not category.startswith("resin_fill"):
        return {"ok": False, "error": "not_fill_category"}

    if not k10_pull_only:
        local = try_lavie_local_fill_video(trial_id, run_dir, cfg=cfg, timeout_sec=120)
        if local and local.get("ok"):
            return local

    return send_fill_video_via_k10_pull(
        trial_id, run_dir=run_dir, category=category, cfg=cfg, delete_after=True
    )


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Send LAVIE fill video via K10 pull")
    parser.add_argument("--trial-id", required=True)
    parser.add_argument("--category", default="resin_fill_cad")
    parser.add_argument("--run-dir", default="")
    args = parser.parse_args()

    result = send_fill_video_after_success(
        args.trial_id,
        category=args.category,
        run_dir=args.run_dir,
    )
    print(result, flush=True)
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
