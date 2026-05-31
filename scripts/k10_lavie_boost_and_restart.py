# -*- coding: utf-8 -*-
"""Push LAVIE boost settings + queue remote restart + verify worker (run on K10)."""
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import httpx
import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync_base
import k10_sync_lavie_scripts_to_lavie as script_sync


def probe_worker(node: str) -> tuple[bool, str]:
    node_info = sjp.load_node(node)
    base = sjp.worker_base_url(node_info)
    ok, detail = sjp.probe_worker(base, sjp.load_token())
    return ok, f"{base} {detail}"


def main() -> int:
    parser = argparse.ArgumentParser(description="LAVIE boost: sync scripts + remote restart")
    parser.add_argument("--node", default="lavie")
    parser.add_argument("--skip-sync", action="store_true")
    parser.add_argument("--wait-sec", type=int, default=45)
    args = parser.parse_args()

    if not args.skip_sync:
        rc = script_sync.main()
        if rc != 0:
            return rc

    token = sjp.load_token()
    node_info = sjp.load_node(args.node)
    base = sjp.worker_base_url(node_info)
    cmd = (
        "powershell -NoProfile -ExecutionPolicy Bypass "
        "-File C:\\lavie_usb_pack\\scripts\\lavie_restart_remote.ps1 "
        "-RepoRoot C:\\lavie_usb_pack"
    )
    print("[boost] queue LAVIE restart (detached)...")
    result = sync_base.dispatch_shell(args.node, cmd, 60, token)
    stdout = result.get("stdout_tail") or ""
    if "RESTART_QUEUED_OK" not in stdout:
        print(f"[NG] restart queue failed: {stdout} {result.get('stderr_tail')}", file=sys.stderr)
        return 1
    print(stdout.strip())

    print(f"[boost] waiting {args.wait_sec}s for LAVIE to come back...")
    time.sleep(args.wait_sec)
    for attempt in range(6):
        ok, detail = probe_worker(args.node)
        if ok:
            print(f"[OK] LAVIE worker online: {detail}")
            print("\nRESULT: PASS")
            return 0
        time.sleep(10)
        print(f"[..] retry {attempt + 1}/6")

    print("[NG] LAVIE worker not back online yet", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
