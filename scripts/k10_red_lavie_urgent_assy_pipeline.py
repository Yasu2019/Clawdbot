# -*- coding: utf-8 -*-
"""Wait for Red LAVIE worker, apply limits, sync ASSY assets, dispatch press_blanking_assy."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WS = ROOT / "data" / "workspace"
STATUS_PATH = WS / "red_lavie_urgent_assy_run.json"
JST = timezone(timedelta(hours=9))

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import httpx
import k10_satellite_dispatch as sjp

PING_CMD = 'cmd /c "echo PING_OK"'
INLINE_LIMITS_CMD = (
    'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
    "$paths=@('C:\\clawstack_satellite\\.env','C:\\lavie_usb_pack\\.env'); "
    "$kv=@('CAE_DOCKER_CPUS=3','CAE_DOCKER_MEMORY=8g','CAE_OPENRADIOSS_NTHREAD=2',"
    "'RED_LAVIE_CAE_RESOURCE_PROFILE=conservative_3cpu_2thread'); "
    "foreach($p in $paths){"
    "  if(-not(Test-Path $p)){New-Item -ItemType File -Path $p -Force|Out-Null}; "
    "  $lines=@(); if(Test-Path $p){$lines=Get-Content $p -Encoding UTF8}; "
    "  foreach($line in $kv){$k=$line.Split('=')[0]; "
    "    $found=$false; $out=@(); foreach($l in $lines){"
    "      if($l.Trim().StartsWith(\"$k=\")){$out+=$line; $found=$true} else {$out+=$l}}; "
    "      if(-not $found){$out+=$line}; $lines=$out}; "
    "  [IO.File]::WriteAllText($p,($lines -join \"`r`n\")+\"`r`n\","
    "    (New-Object Text.UTF8Encoding $false))}; "
    "Write-Host RED_LAVIE_CAE_LIMITS_OK"
    '"'
)


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def save_status(payload: dict) -> None:
    WS.mkdir(parents=True, exist_ok=True)
    payload["updated_at"] = now_iso()
    STATUS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def worker_ping(token: str, timeout_sec: int = 15) -> bool:
    node = sjp.load_node("red_lavie")
    base = sjp.worker_base_url(node)
    job = {
        "job_id": f"ping-{uuid.uuid4().hex[:6]}",
        "type": "shell",
        "timeout_sec": timeout_sec,
        "payload": {"command": PING_CMD},
        "report": {"mode": "sync"},
    }
    try:
        result = sjp.dispatch_job(base, token, job, timeout_sec)
        out = (result.get("stdout_tail") or "") + (result.get("stderr_tail") or "")
        return result.get("status") == "ok" and "PING_OK" in out
    except Exception:
        return False


def dispatch_shell(token: str, command: str, timeout: int, job_id: str = "") -> dict:
    node = sjp.load_node("red_lavie")
    base = sjp.worker_base_url(node)
    job = {
        "job_id": job_id or f"urgent-{uuid.uuid4().hex[:8]}",
        "type": "shell",
        "timeout_sec": timeout,
        "payload": {"command": command},
        "report": {"mode": "sync"},
    }
    return sjp.dispatch_job(base, token, job, timeout)


def run_py(script: str, *args: str, timeout: int = 3600) -> tuple[int, str]:
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
        cwd=str(ROOT),
    )
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out[-4000:]


def wait_for_worker(token: str, max_wait_sec: int, poll_sec: int) -> bool:
    deadline = time.time() + max_wait_sec
    n = 0
    while time.time() < deadline:
        n += 1
        cpu = None
        try:
            r = httpx.get("http://100.99.145.3:8111/metrics", timeout=8)
            cpu = r.json().get("cpu_usage_percent")
        except Exception:
            pass
        print(f"[wait] attempt={n} cpu={cpu} ping...", flush=True)
        if worker_ping(token):
            print("[OK] worker accepts jobs", flush=True)
            return True
        save_status({"phase": "waiting_worker", "attempt": n, "cpu_percent": cpu})
        time.sleep(poll_sec)
    return False


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--max-wait", type=int, default=7200)
    parser.add_argument("--poll", type=int, default=45)
    parser.add_argument("--trial-timeout", type=int, default=10800)
    parser.add_argument("--skip-wait", action="store_true")
    args = parser.parse_args()

    token = sjp.load_token()
    trial_id = f"tri-red_lavie-press_blanking_assy-urgent-{uuid.uuid4().hex[:6]}"
    params = json.dumps(
        {
            "case_label": "4mmx4mm_ASSY",
            "clearance_pct": 8.0,
            "punch_speed_mms": 5000.0,
            "friction_mu": 0.10,
        },
        ensure_ascii=False,
    )

    save_status({"phase": "started", "trial_id": trial_id})

    if not args.skip_wait:
        if not wait_for_worker(token, args.max_wait, args.poll):
            save_status({"phase": "failed", "error": "worker_wait_timeout", "trial_id": trial_id})
            print("[NG] worker still busy after max wait", flush=True)
            return 1

    print("[step] apply limits inline", flush=True)
    lim = dispatch_shell(token, INLINE_LIMITS_CMD, 120, "urgent-limits")
    lim_ok = "RED_LAVIE_CAE_LIMITS_OK" in ((lim.get("stdout_tail") or "") + (lim.get("stderr_tail") or ""))
    save_status({"phase": "limits", "ok": lim_ok, "trial_id": trial_id})
    print(f"[limits] ok={lim_ok}", flush=True)

    print("[step] sync experiments", flush=True)
    rc, out = run_py("k10_sync_cae_experiments_to_lavie.py", "--node", "red_lavie", "--timeout", "600")
    save_status({"phase": "sync_experiments", "rc": rc, "tail": out[-500:]})
    if rc != 0:
        print(f"[NG] experiments sync rc={rc}\n{out}", flush=True)
        return 1

    print("[step] sync assy scripts", flush=True)
    rc, out = run_py("k10_sync_openradioss_assy_to_satellite.py", "--node", "red_lavie")
    save_status({"phase": "sync_scripts", "rc": rc, "tail": out[-500:]})
    if rc != 0:
        print(f"[NG] assy scripts sync rc={rc}\n{out}", flush=True)
        return 1

    print(f"[step] dispatch ASSY trial {trial_id}", flush=True)
    rc, out = run_py(
        "k10_satellite_cae_dispatch.py",
        "--host",
        "red_lavie",
        "--category",
        "press_blanking_assy",
        "--trial-id",
        trial_id,
        "--params-json",
        params,
        "--timeout",
        str(args.trial_timeout),
    )
    save_status({"phase": "dispatch", "rc": rc, "trial_id": trial_id, "tail": out[-1500:]})
    print(out[-2000:], flush=True)
    ok = rc == 0
    save_status({"phase": "done" if ok else "dispatch_failed", "ok": ok, "trial_id": trial_id, "rc": rc})
    print(f"\nRESULT: {'PASS' if ok else 'FAIL'} trial_id={trial_id}", flush=True)
    print(f"status: {STATUS_PATH}", flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
