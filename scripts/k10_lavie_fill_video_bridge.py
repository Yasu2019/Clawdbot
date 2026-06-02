# -*- coding: utf-8 -*-
"""Send LAVIE fill MP4 via exec_bridge + docker zip/curl (no job worker shell)."""

from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import argparse
import json
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "cae_te_workspace"
INCOMING = ROOT / "dist" / "incoming"
UPLOAD_PORT = 5689

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import cae_workload_router as router
import k10_sync_cae_experiments_to_lavie as sync


def bridge_cmd(ip: str, cmd: str, timeout: int = 600) -> tuple[bool, str]:
    url = f"http://{ip}:5679/webhook/exec_bridge"
    try:
        r = httpx.post(url, json={"cmd": cmd}, timeout=timeout)
        if r.status_code != 200:
            return False, f"http {r.status_code} {r.text[:300]}"
        body = r.json()
        out = (body.get("stdout") or "") + (body.get("stderr") or "")
        ok = int(body.get("exitCode", 1)) == 0
        return ok, out
    except Exception as exc:
        return False, str(exc)[:300]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trial-id", default="lavie365-resin_fill_cad-live01")
    parser.add_argument("--category", default="resin_fill_cad")
    args = parser.parse_args()

    cfg = router.load_config()
    ip = (cfg.get("lavie") or {}).get("ip") or "100.87.244.46"
    k10_ip = sync.detect_k10_tailscale_ip()
    trial_id = args.trial_id
    zip_name = f"{trial_id}.zip"

    run_host = r"E:\clawstack_satellite\data\work\cae_te_workspace\runs"
    temp_host = r"C:\lavie_usb_pack\temp"
    run_vol = "e:/clawstack_satellite/data/work/cae_te_workspace/runs"
    temp_vol = "c:/lavie_usb_pack/temp"

    print(f"[bridge] list runs on LAVIE...", flush=True)
    ok, out = bridge_cmd(
        ip,
        f"docker run --rm -v {run_vol}:/runs alpine ls /runs",
        120,
    )
    print(out.strip()[-800:], flush=True)
    if not ok:
        print("[NG] cannot list runs volume", file=sys.stderr)
        return 1
    if trial_id not in out:
        # pick latest resin_fill_cad run if live01 gone
        candidates = [ln.strip() for ln in out.splitlines() if "resin_fill" in ln]
        if candidates:
            trial_id = sorted(candidates)[-1]
            print(f"[bridge] using latest run: {trial_id}", flush=True)
            zip_name = f"{trial_id}.zip"
        else:
            print("[NG] no resin_fill run on LAVIE", file=sys.stderr)
            return 1

    print("[bridge] zip via docker (FEM containers untouched)...", flush=True)
    zip_sh = (
        f"docker run --rm -v {run_vol}:/runs -v {temp_vol}:/out alpine "
        f"sh -c \"apk add -q zip >/dev/null 2>&1; rm -f /out/{zip_name}; "
        f"cd /runs && zip -r -q /out/{zip_name} {trial_id} && echo ZIP_DONE\""
    )
    ok, out = bridge_cmd(ip, zip_sh, 900)
    print(out.strip()[-400:], flush=True)
    if not ok or "ZIP_DONE" not in out:
        print("[NG] zip failed", file=sys.stderr)
        return 1

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

    upload_url = f"http://{k10_ip}:{UPLOAD_PORT}/{zip_name}"
    print(f"[bridge] curl PUT -> {upload_url}...", flush=True)
    curl_sh = (
        f"docker run --rm -v {temp_vol}:/t curlimages/curl:latest "
        f"curl -sS -T /t/{zip_name} -X PUT {upload_url} && echo UPLOAD_OK"
    )
    try:
        ok, out = bridge_cmd(ip, curl_sh, 900)
        print(out.strip()[-300:], flush=True)
    finally:
        server.shutdown()

    if not ok or "UPLOAD_OK" not in out or "path" not in received:
        print("[NG] upload failed", file=sys.stderr)
        return 1

    zpath = received["path"]
    local_run = WORKSPACE / "runs" / trial_id
    with tempfile.TemporaryDirectory(prefix="lavie_run_pull_") as td:
        extract_root = Path(td) / "extract"
        extract_root.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(zpath, "r") as zf:
            zf.extractall(extract_root)
        nested = extract_root / trial_id
        src = nested if nested.is_dir() else extract_root
        if local_run.exists():
            import shutil

            shutil.rmtree(local_run, ignore_errors=True)
        import shutil

        shutil.copytree(src, local_run)

    import moldflow_fill_video_telegram as mfv

    print(f"[k10] render + telegram from {local_run}...", flush=True)
    sent = mfv.send_fill_video_for_run(
        local_run,
        trial_id,
        category=args.category,
        host="lavie",
        delete_after=True,
    )
    try:
        zpath.unlink(missing_ok=True)
    except OSError:
        pass
    print(json.dumps({"ok": sent, "trial_id": trial_id}, ensure_ascii=False), flush=True)
    return 0 if sent else 1


if __name__ == "__main__":
    raise SystemExit(main())
