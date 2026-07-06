# -*- coding: utf-8 -*-
"""T051: deploy cae_te_engine.py + cae_self_growth_gates.py to red_lavie as a PAIR.

Rule (T051): engine and gates MUST be deployed together with SHA256 verification.
Transport: red_lavie pulls from K10 fleet script server (:8123, serves scripts/)
via certutil, commanded through the red_lavie exec_bridge (POST {"cmd": ...}).

Usage (on K10):
    python scripts\\k10_red_lavie_deploy_t051_pair.py            # probe + deploy + verify
    python scripts\\k10_red_lavie_deploy_t051_pair.py --probe    # probe only, no changes
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import httpx

ROOT = Path(__file__).resolve().parents[1]
FILES = ["cae_te_engine.py", "cae_self_growth_gates.py"]
K10_HTTP = "http://100.119.18.40:8123"  # fleet script server (serves scripts/)
REGISTRY = ROOT / "data" / "workspace" / "red_lavie_node_registry.json"
# Candidate install dirs on red_lavie; probed before any change (no guessing, T008).
CANDIDATE_DIRS = [r"C:\clawstack_satellite\scripts", r"C:\lavie_usb_pack\scripts", r"C:\lavie_usb_pack"]


def local_sha256(name: str) -> str:
    return hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest().upper()


def bridge_url() -> str:
    reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
    url = reg.get("exec_bridge")
    if not url:
        raise RuntimeError("exec_bridge missing in red_lavie_node_registry.json")
    return url


def run(bridge: str, cmd: str, timeout: int = 120) -> str:
    r = httpx.post(bridge, json={"cmd": cmd}, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    return ((data.get("stdout") or "") + (data.get("stderr") or "")).strip()


def main() -> int:
    probe_only = "--probe" in sys.argv
    bridge = bridge_url()

    # 0. K10 side: files exist + :8123 serves them
    for name in FILES:
        p = ROOT / "scripts" / name
        if not p.exists():
            print(f"[FAIL] missing on K10: {p}")
            return 1
    try:
        for name in FILES:
            resp = httpx.get(f"http://127.0.0.1:8123/{name}", timeout=5)
            if resp.status_code != 200 or len(resp.content) < 1000:
                print(f"[FAIL] K10 :8123 does not serve {name} (start_k10_fleet_script_server.ps1)")
                return 1
    except Exception as exc:
        print(f"[FAIL] K10 :8123 probe error: {exc} -> run scripts\\start_k10_fleet_script_server.ps1")
        return 1
    local = {name: local_sha256(name) for name in FILES}
    for name in FILES:
        print(f"[K10] {name} SHA256={local[name]}")

    # 1. Probe: locate existing engine dir on red_lavie (marker: cae_te_engine.py)
    target = None
    for d in CANDIDATE_DIRS:
        out = run(bridge, f'cmd /c if exist "{d}\\cae_te_engine.py" (echo FOUND) else (echo NO)')
        print(f"[probe] {d}: {out[:40]}")
        if "FOUND" in out:
            target = d
            break
    if not target:
        print("[FAIL] cae_te_engine.py not found in candidate dirs on red_lavie - aborting (no guessing)")
        return 1
    print(f"[red_lavie] target dir: {target}")
    if probe_only:
        return 0

    # 2. Backup -> pull both -> verify hash + py_compile (PAIR, fail-closed)
    ok = True
    for name in FILES:
        dst = f"{target}\\{name}"
        run(bridge, f'cmd /c if exist "{dst}" copy /Y "{dst}" "{dst}.bak_t051" >nul & echo BACKUP_DONE')
        pull = run(
            bridge,
            f'cmd /c certutil -urlcache -split -f {K10_HTTP}/{name} "{dst}" >nul 2>&1 & '
            f'certutil -hashfile "{dst}" SHA256',
            timeout=180,
        )
        remote_hash = ""
        for line in pull.splitlines():
            s = line.strip().replace(" ", "")
            if len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s):
                remote_hash = s.upper()
        if remote_hash != local[name]:
            print(f"[FAIL] {name}: hash mismatch remote={remote_hash[:16]}... local={local[name][:16]}...")
            ok = False
            continue
        comp = run(bridge, f'cmd /c python -m py_compile "{dst}" && echo PY_COMPILE_OK', timeout=120)
        if "PY_COMPILE_OK" not in comp:
            print(f"[FAIL] {name}: py_compile failed on red_lavie: {comp[:200]}")
            ok = False
            continue
        print(f"[OK] {name}: deployed + SHA256 match + py_compile OK (backup .bak_t051)")

    if not ok:
        print("[RESULT] FAILED - restore from .bak_t051 if needed; do NOT restart worker")
        return 1
    print("[RESULT] PAIR DEPLOY OK")
    print("次: ワーカー再起動 -> exec_bridgeで: schtasks /Run /TN ClawstackRedLavieJobWorker (T050手順)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
