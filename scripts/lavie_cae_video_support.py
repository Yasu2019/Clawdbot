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


def normalize_lavie_run_dir(run_dir: str, trial_id: str, cfg: dict[str, Any] | None = None) -> str:
    """Accept /e/... or E:\\... from trial_entry; return Windows path on LAVIE."""
    if not run_dir:
        return lavie_run_dir(trial_id, cfg)
    rd = run_dir.strip().replace("/", "\\")
    if rd.lower().startswith("\\e\\"):
        rd = "E:" + rd[2:]
    elif len(rd) >= 2 and rd[1] == ":":
        pass
    elif rd.lower().startswith("e\\"):
        rd = "E:" + rd[1:]
    return rd


def probe_lavie_worker(cfg: dict[str, Any] | None = None) -> tuple[bool, str]:
    cfg = cfg or router.load_config()
    try:
        token = sjp.load_token()
        node = sjp.load_node("lavie")
        base = sjp.worker_base_url(node)
        return sjp.probe_worker(base, token)
    except Exception as exc:
        return False, str(exc)[:200]


LAVIE_RUN_VOL = "e:/clawstack_satellite/data/work/cae_te_workspace/runs"
LAVIE_TEMP_VOL = "c:/lavie_usb_pack/temp"


def lavie_bridge_ip(cfg: dict[str, Any] | None = None) -> str:
    cfg = cfg or router.load_config()
    return str((cfg.get("lavie") or {}).get("ip") or "100.87.244.46")


def bridge_cmd(ip: str, cmd: str, timeout: int = 600) -> tuple[bool, str]:
    import httpx

    url = f"http://{ip}:5679/webhook/exec_bridge"
    try:
        resp = httpx.post(url, json={"cmd": cmd}, timeout=timeout)
        if resp.status_code != 200:
            return False, f"http {resp.status_code} {resp.text[:300]}"
        body = resp.json()
        out = (body.get("stdout") or "") + (body.get("stderr") or "")
        ok = int(body.get("exitCode", 1)) == 0
        return ok, out
    except Exception as exc:
        return False, str(exc)[:300]


def satellite_bridge_ip(cfg: dict[str, Any], node: str) -> str:
    return str((cfg.get(node) or {}).get("ip") or "")


def pull_zip_from_satellite(
    node_ip: str,
    trial_id: str,
    *,
    zip_host_path: str = "",
    timeout: int = 900,
) -> Path | None:
    """Remote node PUT zip to K10 upload server; return local zip path."""
    import k10_sync_cae_experiments_to_lavie as sync

    zip_name = f"{trial_id}.zip"
    k10_ip = sync.detect_k10_tailscale_ip()
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
        if zip_host_path.startswith("/tmp/"):
            curl_sh = f"bash -lc 'curl -sS -T {zip_host_path} -X PUT {upload_url} && echo UPLOAD_OK'"
            ok, out = bridge_cmd(node_ip, curl_sh, timeout)
        else:
            curl_sh = (
                f"docker run --rm -v {LAVIE_TEMP_VOL}:/t curlimages/curl:latest "
                f"curl -sS -T /t/{zip_name} -X PUT {upload_url} && echo UPLOAD_OK"
            )
            ok, out = bridge_cmd(node_ip, curl_sh, timeout)
        if not ok or "UPLOAD_OK" not in out:
            print(f"[NG] satellite upload from {node_ip}: {out[-400:]}", flush=True)
            return None
        if "path" not in received:
            print("[NG] upload: K10 did not receive zip", flush=True)
            return None
        return received["path"]
    finally:
        server.shutdown()


def zip_run_on_node(
    node: str,
    trial_id: str,
    run_dir: str,
    cfg: dict[str, Any] | None = None,
    *,
    timeout: int = 600,
) -> bool:
    cfg = cfg or router.load_config()
    ip = satellite_bridge_ip(cfg, node)
    if not ip:
        return False
    zip_name = f"{trial_id}.zip"
    zip_sh = (
        f"docker run --rm -v {LAVIE_RUN_VOL}:/runs -v {LAVIE_TEMP_VOL}:/out alpine "
        f"sh -c \"apk add -q zip >/dev/null 2>&1; rm -f /out/{zip_name}; "
        f"cd /runs && zip -r -q /out/{zip_name} {trial_id} && echo ZIP_DONE\""
    )
    ok, out = bridge_cmd(ip, zip_sh, timeout)
    if ok and "ZIP_DONE" in out:
        return True
    ws_unix = "/e/clawstack_satellite/data/work/cae_te_workspace/runs"
    bash_zip = (
        f"bash -lc 'mkdir -p /tmp/lavie_fill_zip && rm -f /tmp/lavie_fill_zip/{zip_name} && "
        f"cd {ws_unix} && zip -r -q /tmp/lavie_fill_zip/{zip_name} {trial_id} && echo ZIP_DONE'"
    )
    r = sync.dispatch_shell(node, bash_zip, timeout, sjp.load_token())
    out2 = (r.get("stdout_tail") or "") + (r.get("stderr_tail") or "")
    return r.get("status") == "ok" and "ZIP_DONE" in out2


def zip_run_on_lavie(trial_id: str, lavie_run_dir: str, *, timeout: int = 600) -> bool:
    return zip_run_on_node("lavie", trial_id, lavie_run_dir, timeout=timeout)


def pull_zip_via_worker(
    node: str,
    trial_id: str,
    zip_path_on_node: str,
    *,
    timeout: int = 900,
) -> Path | None:
    import k10_sync_cae_experiments_to_lavie as sync

    zip_name = f"{trial_id}.zip"
    k10_ip = sync.detect_k10_tailscale_ip()
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
        put_cmd = (
            f"bash -lc 'curl -sS -T {zip_path_on_node} -X PUT {upload_url} && echo UPLOAD_OK'"
        )
        r = sync.dispatch_shell(node, put_cmd, timeout, sjp.load_token())
        out = (r.get("stdout_tail") or "") + (r.get("stderr_tail") or "")
        if "UPLOAD_OK" not in out:
            print(f"[NG] worker upload from {node}: {out[-400:]}", flush=True)
            return None
        return received.get("path")
    finally:
        server.shutdown()


def pull_zip_from_lavie(trial_id: str, *, timeout: int = 900) -> Path | None:
    """LAVIE PUT zip to K10 upload server; return local zip path."""
    cfg = router.load_config()
    ip = lavie_bridge_ip(cfg)
    zpath = pull_zip_from_satellite(ip, trial_id, timeout=timeout)
    if zpath:
        return zpath
    zip_name = f"{trial_id}.zip"
    return pull_zip_via_worker("lavie", trial_id, f"/tmp/lavie_fill_zip/{zip_name}", timeout=timeout)


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

    rd = normalize_lavie_run_dir(run_dir, trial_id, cfg) if run_dir else lavie_run_dir(trial_id, cfg)
    if not zip_run_on_lavie(trial_id, rd):
        return {"ok": False, "error": "lavie_zip_failed"}

    zpath = pull_zip_from_lavie(trial_id)
    if not zpath or not zpath.exists():
        return {"ok": False, "error": "k10_pull_failed"}

    local_run = extract_run_zip(zpath, trial_id)
    import cae_paraview_video_delivery as cpvd

    result = cpvd.deliver_local_run(
        "openfoam",
        local_run,
        trial_id,
        category=category,
        host="lavie",
        delete_after=True,
    )
    try:
        zpath.unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": bool(result.get("ok")), "source": "k10_pull_paraview", "trial_id": trial_id, "run_dir": str(local_run), "detail": result}


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
    rd = normalize_lavie_run_dir(run_dir, trial_id, cfg) if run_dir else lavie_run_dir(trial_id, cfg)
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
