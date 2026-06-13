# -*- coding: utf-8 -*-
"""Auto-recover Red LAVIE after connectivity outage (stability, monitor, worker)."""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
WORKSPACE = ROOT / "data" / "workspace"
RECOVERY_STATUS = WORKSPACE / "red_lavie_recovery_status.json"
JST = timezone(timedelta(hours=9))

if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import k10_red_lavie_stability_enforce as stability
import k10_satellite_dispatch as sjp
import k10_sync_cae_experiments_to_lavie as sync_base


def now_iso() -> str:
    return datetime.now(JST).isoformat()


def save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _step_ok(step: dict[str, Any], marker: str) -> bool:
    if step.get("ok"):
        return True
    if step.get("status") == "ok":
        return True
    if int(step.get("exit_code") or 1) == 0:
        return True
    result = step.get("result") or {}
    out = (step.get("stdout_tail") or "") + (step.get("stdout") or "")
    out += (result.get("stdout_tail") or "") + (result.get("stdout") or "")
    return marker in out


def restart_monitor_agent() -> dict[str, Any]:
    """Download monitor_agent from K10 if missing and start on :8111."""
    token = sjp.load_token()
    try:
        import k10_red_lavie_common as rl

        k10 = rl.k10_http_base()
    except Exception:
        k10 = "http://100.119.18.40:8123"
    agent = r"C:\clawstack_satellite\scripts\monitor_agent.py"
    ps = (
        f"$K10='{k10}'; $agent='{agent}'; "
        f"New-Item -ItemType Directory -Force -Path (Split-Path $agent) | Out-Null; "
        f"Invoke-WebRequest ($K10 + '/monitor_agent.py') -OutFile $agent -UseBasicParsing; "
        f"$pyw=$null; "
        f"try {{ $pyw = (& where.exe pythonw 2>$null | Select-Object -First 1) }} catch {{}}; "
        f"if (-not $pyw) {{ $pyw = Join-Path $env:LOCALAPPDATA 'Programs/Python/Python311/pythonw.exe' }}; "
        f"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.CommandLine -and ($_.CommandLine -match 'monitor_agent') }} | "
        f"ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}; "
        f"Start-Process -FilePath $pyw -ArgumentList ('\"' + $agent + '\"') -WindowStyle Hidden; "
        f"Start-Sleep -Seconds 5; "
        f"try {{ "
        f"  $r = Invoke-WebRequest 'http://127.0.0.1:8111/metrics' -UseBasicParsing -TimeoutSec 5; "
        f"  if ($r.StatusCode -eq 200) {{ Write-Output MONITOR_AGENT_RESTARTED }} "
        f"  else {{ Write-Error 'metrics not 200'; exit 1 }} "
        f"}} catch {{ Write-Error $_; exit 1 }}"
    )
    return sync_base.dispatch_shell("red_lavie", f'powershell -NoProfile -Command "{ps}"', 180, token)


def restart_job_worker() -> dict[str, Any]:
    token = sjp.load_token()
    ps = (
        "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'lavie_job_worker' } "
        "| ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; "
        "Start-Sleep 2; "
        "if (Test-Path C:\\clawstack_satellite\\scripts\\lavie_job_worker.py) { "
        "$p='C:\\clawstack_satellite\\scripts\\lavie_job_worker.py'; "
        "Start-Process pythonw.exe -ArgumentList $p -WindowStyle Hidden; "
        "Start-Sleep 3; Write-Output JOB_WORKER_RESTARTED } "
        "else { Write-Error 'lavie_job_worker.py not found'; exit 1 }"
    )
    return sync_base.dispatch_shell(
        "red_lavie",
        f'powershell -NoProfile -Command "{ps}"',
        120,
        token,
    )


def run_full_recovery(*, skip_power: bool = False) -> dict[str, Any]:
    reg = sjp.load_node("red_lavie")
    worker_url = sjp.worker_base_url(reg)
    token = sjp.load_token()

    result: dict[str, Any] = {
        "schema": "clawstack.red_lavie_auto_recovery.v1",
        "started_at": now_iso(),
        "steps": {},
    }

    pre_ok, pre_detail = sjp.probe_worker(worker_url, token)
    result["steps"]["pre_probe"] = {
        "ok": pre_ok,
        "url": worker_url,
        "detail": (pre_detail or "")[:300],
    }
    if not pre_ok:
        result["finished_at"] = now_iso()
        result["ok"] = False
        result["skipped_remote"] = True
        result["message"] = "red_lavie unreachable; remote recovery skipped (fail-fast)"
        save_json(
            RECOVERY_STATUS,
            {
                "node": "red_lavie",
                "recovered_at": result["finished_at"],
                "trigger": "k10_red_lavie_auto_recovery",
                "auto_recovery": result,
            },
        )
        return result

    if not skip_power:
        result["steps"]["host_stability"] = stability.enforce_on_red_lavie(push_monitor=True, timeout=180)
    result["steps"]["monitor_agent"] = restart_monitor_agent()
    result["steps"]["job_worker"] = restart_job_worker()

    worker_ok, worker_detail = sjp.probe_worker(worker_url, token)
    result["steps"]["worker_probe"] = {
        "ok": worker_ok,
        "url": worker_url,
        "detail": (worker_detail or "")[:300],
    }

    result["finished_at"] = now_iso()
    host_ok = (
        (result["steps"].get("host_stability") or {}).get("ok", True)
        if not skip_power
        else True
    )
    monitor_ok = _step_ok(result["steps"]["monitor_agent"], "MONITOR_AGENT_RESTARTED")
    result["ok"] = bool(host_ok and (monitor_ok or worker_ok))
    save_json(
        RECOVERY_STATUS,
        {
            "node": "red_lavie",
            "recovered_at": result["finished_at"],
            "trigger": "k10_red_lavie_auto_recovery",
            "auto_recovery": result,
        },
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Red LAVIE auto recovery from K10")
    parser.add_argument("--skip-power", action="store_true")
    args = parser.parse_args()

    result = run_full_recovery(skip_power=args.skip_power)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
