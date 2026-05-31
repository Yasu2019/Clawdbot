# -*- coding: utf-8 -*-
"""Push CAE experiments/ from K10 to LAVIE over Tailscale (SJP-2 workspace sync)."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
import threading
import uuid
import zipfile
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

os.environ.setdefault("PGCLIENTENCODING", "UTF8")

import httpx
import yaml

ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = ROOT / "data" / "workspace" / "cae_workload_router.yaml"
DEFAULT_SRC = ROOT / "data" / "cae_te_workspace" / "experiments"
DEFAULT_SERVE_PORT = 5682

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_satellite_dispatch as sjp


def load_router() -> dict[str, Any]:
    if not ROUTER_PATH.exists():
        return {}
    return yaml.safe_load(ROUTER_PATH.read_text(encoding="utf-8")) or {}


def detect_k10_tailscale_ip(explicit: str = "") -> str:
    if explicit:
        return explicit.strip()
    cfg = load_router()
    k10_cfg = cfg.get("k10") or {}
    for key in ("tailscale_ip", "ts_ip", "ip_tailscale"):
        val = (k10_cfg.get(key) or "").strip()
        if val:
            return val
    env_ip = os.environ.get("K10_TAILSCALE_IP", "").strip()
    if env_ip:
        return env_ip
    try:
        proc = subprocess.run(
            ["tailscale", "ip", "-4"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        if proc.returncode == 0:
            line = proc.stdout.strip().splitlines()[0].strip()
            if line.startswith("100."):
                return line
    except Exception:
        pass
    raise RuntimeError(
        "K10 Tailscale IP unknown. Set k10.tailscale_ip in cae_workload_router.yaml "
        "or pass --k10-ip"
    )


def build_experiments_zip(src: Path, dest_zip: Path) -> dict[str, Any]:
    if not src.exists():
        raise RuntimeError(f"experiments source missing: {src}")
    files: list[str] = []
    dest_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(dest_zip, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            arcname = path.relative_to(src.parent).as_posix()
            zf.write(path, arcname)
            files.append(arcname)
    size = dest_zip.stat().st_size
    return {"files": len(files), "bytes": size, "zip": str(dest_zip), "entries": files}


class _ZipHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args: Any, directory: str = "", **kwargs: Any) -> None:
        super().__init__(*args, directory=directory, **kwargs)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[sync-serve] {self.address_string()} {fmt % args}", flush=True)


def serve_zip(zip_path: Path, port: int, bind: str = "0.0.0.0") -> tuple[ThreadingHTTPServer, threading.Thread]:
    handler = lambda *args, **kwargs: _ZipHandler(*args, directory=str(zip_path.parent), **kwargs)
    server = ThreadingHTTPServer((bind, port), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def lavie_dest_dir(cfg: dict[str, Any], override: str = "") -> str:
    if override:
        return override.replace("/", "\\").rstrip("\\")
    sync_cfg = cfg.get("cae_workspace_sync") or {}
    work = sync_cfg.get("lavie_work_dir") or "E:/clawstack_satellite/data/work/cae_te_workspace"
    return str(Path(work)).replace("/", "\\")


def build_download_command(k10_ip: str, port: int, zip_name: str, dest_dir: str) -> str:
    url = f"http://{k10_ip}:{port}/{zip_name}"
    ps = (
        f"$dest='{dest_dir}'; "
        f"New-Item -ItemType Directory -Force -Path $dest | Out-Null; "
        f"$zip=Join-Path $env:TEMP '{zip_name}'; "
        f"Invoke-WebRequest -Uri '{url}' -OutFile $zip -UseBasicParsing; "
        f"Expand-Archive -Path $zip -DestinationPath $dest -Force; "
        f"if (Test-Path (Join-Path $dest 'experiments')) {{ Write-Host SYNC_OK experiments=(Get-ChildItem (Join-Path $dest 'experiments') -Recurse -File | Measure-Object).Count }} "
        f"else {{ Write-Error 'experiments folder missing after extract'; exit 1 }}"
    )
    return f'powershell -NoProfile -ExecutionPolicy Bypass -Command "{ps}"'


def dispatch_shell(node: str, command: str, timeout: int, token: str) -> dict[str, Any]:
    node_info = sjp.load_node(node)
    base_url = sjp.worker_base_url(node_info)
    job = {
        "job_id": f"sync-{uuid.uuid4().hex[:8]}",
        "type": "shell",
        "timeout_sec": timeout,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    return sjp.dispatch_job(base_url, token, job, timeout)


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync CAE experiments K10 -> LAVIE")
    parser.add_argument("--node", default="lavie")
    parser.add_argument("--src", default=str(DEFAULT_SRC))
    parser.add_argument("--k10-ip", default="", help="K10 Tailscale IP for LAVIE download")
    parser.add_argument("--port", type=int, default=DEFAULT_SERVE_PORT)
    parser.add_argument("--dest", default="", help="LAVIE cae_te_workspace path override")
    parser.add_argument("--dry-run", action="store_true", help="Only build zip, no network push")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    src = Path(args.src)
    cfg = load_router()

    with tempfile.TemporaryDirectory(prefix="cae_sync_") as tmp:
        zip_name = "cae_experiments.zip"
        zip_path = Path(tmp) / zip_name
        meta = build_experiments_zip(src, zip_path)
        print(f"[sync] packed {meta['files']} files ({meta['bytes']} bytes) -> {zip_path.name}")

        if args.dry_run:
            print(json.dumps(meta, ensure_ascii=False, indent=2))
            return 0

        k10_ip = detect_k10_tailscale_ip(args.k10_ip)
        dest_dir = lavie_dest_dir(cfg, args.dest)
        print(f"[sync] serve http://{k10_ip}:{args.port}/{zip_name}")
        print(f"[sync] lavie dest={dest_dir}")

        server, _thread = serve_zip(zip_path, args.port)
        try:
            token = sjp.load_token()
            command = build_download_command(k10_ip, args.port, zip_name, dest_dir)
            result = dispatch_shell(args.node, command, args.timeout, token)
            stdout = (result.get("stdout_tail") or "").strip()
            stderr = (result.get("stderr_tail") or "").strip()
            ok = result.get("status") == "ok" and "SYNC_OK" in stdout
            print(f"status={result.get('status')} exit_code={result.get('exit_code')}")
            if stdout:
                print(stdout[-1500:])
            if stderr:
                print(stderr[-1500:], file=sys.stderr)
            print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
            return 0 if ok else 1
        finally:
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
