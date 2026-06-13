# -*- coding: utf-8 -*-
"""Sync lavie_usb_pack/scripts from K10 to LAVIE (Tailscale HTTP + shell job)."""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync_base


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync LAVIE scripts pack over Tailscale")
    parser.add_argument("--node", default="lavie")
    parser.add_argument(
        "--pack-dir",
        default=str(ROOT / "dist" / "lavie_usb_pack"),
        help="Full lavie_usb_pack (scripts + data samples)",
    )
    parser.add_argument("--dest", default="C:/lavie_usb_pack")
    parser.add_argument("--k10-ip", default="")
    parser.add_argument("--port", type=int, default=5683)
    parser.add_argument("--build-pack", action="store_true")
    args = parser.parse_args()

    pack_dir = Path(args.pack_dir)
    if args.build_pack or not pack_dir.exists():
        ps1 = ROOT / "scripts" / "lavie_usb_pack.ps1"
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(ps1)],
            cwd=str(ROOT),
            check=True,
        )

    if not pack_dir.exists():
        print(f"[NG] pack dir missing: {pack_dir}", file=sys.stderr)
        return 1

    with tempfile.TemporaryDirectory(prefix="lavie_scripts_") as tmp:
        zip_name = "lavie_scripts.zip"
        zip_path = Path(tmp) / zip_name
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(pack_dir.rglob("*")):
                if path.is_file():
                    arc = path.relative_to(pack_dir).as_posix()
                    zf.write(path, arc)
        print(f"[sync] packed scripts -> {zip_path.stat().st_size} bytes")

        k10_ip = sync_base.detect_k10_tailscale_ip(args.k10_ip)
        command = sync_base.build_lavie_pack_sync_command(k10_ip, args.port, zip_name, args.dest)

        server, _ = sync_base.serve_zip(zip_path, args.port)
        try:
            token = sjp.load_token()
            result = sync_base.dispatch_shell(args.node, command, 180, token)
            stdout = result.get("stdout_tail") or ""
            ok = result.get("status") == "ok" and "SYNC_SCRIPTS_OK" in stdout
            print(f"status={result.get('status')} exit={result.get('exit_code')}")
            if stdout:
                print(stdout[-1500:])
            print(f"\nRESULT: {'PASS' if ok else 'FAIL'}")
            if ok:
                boot = (
                    f'powershell -NoProfile -ExecutionPolicy Bypass -File '
                    f'"{args.dest.replace("/", "\\")}\\scripts\\lavie_bootstrap_cae_video.ps1"'
                )
                try:
                    br = sync_base.dispatch_shell(args.node, boot, 300, token)
                    tail = (br.get("stdout_tail") or "")[-500:]
                    if tail:
                        print(tail)
                except Exception as exc:
                    print(f"[WARN] bootstrap optional step skipped: {exc}")
            return 0 if ok else 1
        finally:
            server.shutdown()


if __name__ == "__main__":
    raise SystemExit(main())
