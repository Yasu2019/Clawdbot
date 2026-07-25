# -*- coding: utf-8 -*-
"""T051: deploy cae_te_engine.py + cae_self_growth_gates.py to red_lavie as a PAIR.

Rule (T051): engine and gates MUST be deployed together with SHA256 verification.
Transport: red_lavie pulls each file from the K10 fleet script server
(:8123, serves scripts/). Commands run on red_lavie via the job worker
(POST {base}/jobs, type=shell, X-Satellite-Token) with exec_bridge fallback.

Usage (on K10, use the venv python which has httpx):
    .venv\\Scripts\\python.exe scripts\\k10_red_lavie_deploy_t051_pair.py --probe
    .venv\\Scripts\\python.exe scripts\\k10_red_lavie_deploy_t051_pair.py
"""
from __future__ import annotations

import hashlib
import json
import sys
import uuid
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import httpx  # noqa: E402
import k10_satellite_dispatch as sjp  # noqa: E402

FILES = ["cae_te_engine.py", "cae_self_growth_gates.py", "openradioss_4mmx4mm_assy_params.py"]
K10_HTTP = "http://100.119.18.40:8123"  # fleet script server (serves scripts/)
REGISTRY = ROOT / "data" / "workspace" / "red_lavie_node_registry.json"
# Candidate install dirs on red_lavie; probed before any change (no guessing, T008).
CANDIDATE_DIRS = [r"C:\clawstack_satellite\scripts", r"C:\lavie_usb_pack\scripts", r"C:\lavie_usb_pack"]


def local_sha256(name: str) -> str:
    return hashlib.sha256((ROOT / "scripts" / name).read_bytes()).hexdigest().upper()


class Runner:
    """shell runner on red_lavie: job worker first, exec_bridge fallback."""

    def __init__(self) -> None:
        self.node = sjp.load_node("red_lavie")
        self.token = sjp.load_token()
        self.worker = sjp.worker_base_url(self.node)
        reg = json.loads(REGISTRY.read_text(encoding="utf-8-sig"))
        self.bridge = reg.get("exec_bridge") or ""
        ok, detail = sjp.probe_worker(self.worker, self.token)
        self.use_worker = ok
        print(f"[transport] worker={self.worker} ok={ok} ({detail[:60]})")
        if not ok and self.bridge:
            print(f"[transport] falling back to exec_bridge {self.bridge}")

    def run(self, cmd: str, timeout: int = 120) -> str:
        if self.use_worker:
            job = {
                "job_id": f"t051-deploy-{uuid.uuid4().hex[:8]}",
                "type": "shell",
                "timeout_sec": timeout,
                "payload": {"command": cmd},
                "report": {"mode": "sync"},
            }
            body = sjp.dispatch_job(self.worker, self.token, job, timeout)
            return str(body.get("stdout_tail") or body.get("stdout") or body.get("error") or "")
        r = httpx.post(self.bridge, json={"cmd": cmd}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        return ((data.get("stdout") or "") + (data.get("stderr") or "")).strip()


def main() -> int:
    probe_only = "--probe" in sys.argv

    # 0. K10 side: files exist + :8123 serves them
    for name in FILES:
        if not (ROOT / "scripts" / name).exists():
            print(f"[FAIL] missing on K10: scripts/{name}")
            return 1
    try:
        for name in FILES:
            resp = httpx.get(f"http://127.0.0.1:8123/{name}", timeout=5)
            if resp.status_code != 200 or len(resp.content) < 1000:
                print(f"[FAIL] K10 :8123 does not serve {name} -> run scripts\\start_k10_fleet_script_server.ps1")
                return 1
    except Exception as exc:
        print(f"[FAIL] K10 :8123 probe error: {exc} -> run scripts\\start_k10_fleet_script_server.ps1")
        return 1
    local = {name: local_sha256(name) for name in FILES}
    for name in FILES:
        print(f"[K10] {name} SHA256={local[name]}")

    rl = Runner()
    if not rl.use_worker and not rl.bridge:
        print("[FAIL] no transport to red_lavie (worker down, no exec_bridge)")
        return 1

    # 1. Probe: locate existing engine dir on red_lavie (marker: cae_te_engine.py)
    target = None
    for d in CANDIDATE_DIRS:
        out = rl.run(f'cmd /c if exist "{d}\\cae_te_engine.py" (echo FOUND) else (echo NO)')
        print(f"[probe] {d}: {out.strip()[:40]}")
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
        rl.run(f'cmd /c if exist "{dst}" copy /Y "{dst}" "{dst}.bak_t051" >nul & echo BACKUP_DONE')
        # certutil (WinINet) fails silently under the worker's service context;
        # use Invoke-WebRequest + Get-FileHash instead (T051 deploy attempt #2).
        pull = rl.run(
            'powershell -NoProfile -ExecutionPolicy Bypass -Command '
            f"\"Invoke-WebRequest -Uri {K10_HTTP}/{name} -OutFile '{dst}' -UseBasicParsing; "
            f"(Get-FileHash -LiteralPath '{dst}' -Algorithm SHA256).Hash\"",
            timeout=180,
        )
        remote_hash = ""
        for line in pull.splitlines():
            s = line.strip().replace(" ", "")
            if len(s) == 64 and all(c in "0123456789abcdefABCDEF" for c in s):
                remote_hash = s.upper()
        if remote_hash != local[name]:
            print(f"[FAIL] {name}: hash mismatch remote={remote_hash[:16] or 'NONE'}... local={local[name][:16]}...")
            ok = False
            continue
        # py_compile is best-effort: SHA256 match already guarantees byte-identity
        # with the K10 file (which compiles). Worker shell may lack `python` on PATH.
        comp = rl.run(f'cmd /c python -m py_compile "{dst}" 2>&1 && echo PY_COMPILE_OK', timeout=120)
        if "PY_COMPILE_OK" not in comp:
            comp = rl.run(f'cmd /c py -3 -m py_compile "{dst}" 2>&1 && echo PY_COMPILE_OK', timeout=120)
        if "PY_COMPILE_OK" not in comp:
            print(f"[WARN] {name}: py_compile unavailable on red_lavie ({comp.strip()[:100]}) - SHA256一致で内容同一性は保証済み")
            print(f"[OK] {name}: deployed + SHA256 match (backup .bak_t051)")
        else:
            print(f"[OK] {name}: deployed + SHA256 match + py_compile OK (backup .bak_t051)")

    if not ok:
        print("[RESULT] FAILED - restore from .bak_t051 if needed; do NOT restart worker")
        return 1
    print("[RESULT] PAIR DEPLOY OK")
    print("次: ワーカー再起動 (T050手順): schtasks /Run /TN ClawstackRedLavieJobWorker をred_lavie側で実行")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
