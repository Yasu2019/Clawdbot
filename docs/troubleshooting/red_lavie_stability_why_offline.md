#Requires -Version 5.1
# INC-120: Red LAVIE monitor bringup pitfalls (SyntaxError gate, non-admin paths, self-kill filter).

## Node

| Field | Value |
|-------|-------|
| Tailscale | `100.99.145.3` |
| Hostname | `DESKTOP-DERCN1N` |
| monitor_agent | `:8111` |
| job_worker | `:5682` (Windows host -- powercfg works here) |
| exec_bridge | `:5679` (may timeout; not required for stability enforce) |

## Symptom

- Tailscale peer offline, or worker `:5682` unreachable together with monitor
- CAE T&E falls back to K10 when Red LAVIE is down

Pattern is usually **full-node sleep/reboot**, not a single flaky service.

## On Red LAVIE desktop (DESKTOP-DERCN1N)

**Do not use** `D:\Clawdbot_Docker_20260125\...` — that path is K10 only.

Admin PowerShell on Red LAVIE:

```powershell
$K10 = "http://100.119.18.40:8123"
$p = "$env:TEMP\red_lavie_local_bringup.ps1"
Invoke-WebRequest "$K10/red_lavie_local_bringup.ps1" -OutFile $p -UseBasicParsing
powershell -NoProfile -ExecutionPolicy Bypass -File $p -K10 $K10
```

**Bootstrap (bringup + monitor, one shot):** same `-ExecutionPolicy Bypass` required on Red LAVIE (default policy blocks `-File`):

```powershell
$K10 = "http://100.119.18.40:8123"
Invoke-WebRequest "$K10/red_lavie_bootstrap_from_k10.ps1" -OutFile $env:TEMP\bootstrap.ps1 -UseBasicParsing
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\bootstrap.ps1 -K10 $K10
```

If you see `スクリプトの実行が無効` / execution policy error, you omitted `Bypass` on the **outer** `powershell -File` call.

Token: read from `C:\clawstack_satellite\.env` automatically, or pass `-Token` if missing.

Verify locally:

```powershell
Invoke-WebRequest http://127.0.0.1:5682/healthz -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:8111/metrics -UseBasicParsing
```

Expected marker: `RED_LAVIE_LOCAL_BRINGUP_OK`

---

## Monitor only (`:8111` down, worker `:5682` OK) — INC-120 / T036

**Symptoms:** `8111/metrics` connection refused; worker health OK; `red_lavie_start_monitor.ps1` stops after `Saved:` with no `RED_LAVIE_MONITOR_OK`.

**Root causes (fixed 2026-06-15):**

| Cause | Fix |
|-------|-----|
| K10 served broken `monitor_agent.py` (SyntaxError) | `verify_fleet_script_server_gate.ps1` before `:8123` |
| Write to `C:\monitor_agent.py` as standard user | Use `C:\clawstack_satellite\scripts\monitor_agent.py` |
| Start script killed own PowerShell (`-AgentPath ...monitor_agent.py`) | Kill only `python(w).exe` running `monitor_agent.py` |
| Execution policy blocks `.ps1` | Always `powershell -ExecutionPolicy Bypass -File ...` |

**Correct one-shot on Red LAVIE:**

```powershell
$K10 = "http://100.119.18.40:8123"
Invoke-WebRequest "$K10/red_lavie_start_monitor.ps1" -OutFile "$env:TEMP\mon.ps1" -UseBasicParsing
powershell -ExecutionPolicy Bypass -File "$env:TEMP\mon.ps1" -K10 $K10
```

Expected: `RED_LAVIE_MONITOR_OK` + scheduled tasks `ClawstackRedLavieMonitor` / `ClawstackRedLavieMonitorWatchdog` + Startup VBS.

Daemon only (already installed):

```powershell
powershell -ExecutionPolicy Bypass -File C:\clawstack_satellite\scripts\red_lavie_monitor_daemon.ps1 -RegisterScheduledTasks
```

Logs: `C:\clawstack_satellite\logs\red_lavie_monitor.log`

**Debug (show errors):**

```powershell
cd C:\clawstack_satellite\scripts
& "$env:LOCALAPPDATA\Programs\Python\Python311\python.exe" .\monitor_agent.py
```

Do **not** close this window until scheduled tasks are registered (one-time setup; reboot-safe after that).

---

## Job worker (`:5682`) — window-close safe daemon (INC-120+)

**Problem:** `python.exe` in PowerShell dies when the window closes. `pythonw` via broken `ArgumentList` also exited silently.

**Fix:** `red_lavie_job_worker_daemon.ps1` — detached `pythonw` with array args + scheduled tasks.

```powershell
$K10 = "http://100.119.18.40:8123"
Invoke-WebRequest "$K10/red_lavie_start_job_worker.ps1" -OutFile "$env:TEMP\jw.ps1" -UseBasicParsing
$Token = ""
Get-Content C:\clawstack_satellite\.env | ForEach-Object { if ($_ -match '^SATELLITE_JOB_TOKEN=(.+)$') { $Token = $Matches[1].Trim() } }
powershell -ExecutionPolicy Bypass -File "$env:TEMP\jw.ps1" -K10 $K10 -Token $Token
```

Registers `ClawstackRedLavieJobWorker` (logon) + `ClawstackRedLavieJobWorkerWatchdog` (5 min).

Daemon only (already installed):

```powershell
powershell -ExecutionPolicy Bypass -File C:\clawstack_satellite\scripts\red_lavie_job_worker_daemon.ps1 -RegisterScheduledTasks
```

Logs: `C:\clawstack_satellite\logs\red_lavie_job_worker.log`

---

Run on **K10** (`D:\Clawdbot_Docker_20260125`). Any working directory is OK.

**One-time (recommended):** add `bin` to PATH:

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\install_k10_fleet_path.ps1
```

Then from **any folder**:

```powershell
k10_red_lavie_stability_enforce
k10_red_lavie_connectivity_watch --once
k10_red_lavie_connectivity_summary
```

**Or** unified CLI:

```powershell
powershell -File D:\Clawdbot_Docker_20260125\scripts\k10_fleet.ps1 red-lavie stability
powershell -File D:\Clawdbot_Docker_20260125\scripts\k10_fleet.ps1 red-lavie watch --once
powershell -File D:\Clawdbot_Docker_20260125\scripts\k10_fleet.ps1 red-lavie summary
```

**Or** full path to Python (also works from any folder):

```powershell
python D:\Clawdbot_Docker_20260125\scripts\k10_red_lavie_stability_enforce.py
python D:\Clawdbot_Docker_20260125\scripts\k10_red_lavie_connectivity_watch.py --once
```

Watchdog (background):

```powershell
powershell -ExecutionPolicy Bypass -File D:\Clawdbot_Docker_20260125\scripts\start_k10_red_lavie_connectivity_watchdog.ps1
```

Expected marker: `RED_LAVIE_HOST_STABILITY_OK`

## Channels (INC-116)

| Channel | Plane | Use |
|---------|-------|-----|
| `monitor_agent :8111/host_stability/apply` | Windows host | Preferred when monitor is up to date |
| `job_worker :5682` shell | Windows host | Fallback: runs `red_lavie_host_stability.ps1` (powercfg OK) |
| `exec_bridge :5679` | Often down | Do not rely on for stability |

Unlike main LAVIE, Red LAVIE job worker runs on **Windows**, so K10 can apply power settings via worker dispatch.

## Monitoring artifacts

| File | Purpose |
|------|---------|
| `data/workspace/red_lavie_connectivity_log.jsonl` | 5-min probes |
| `data/workspace/red_lavie_connectivity_24h_summary.json` | Uptime %, hints |
| `data/workspace/red_lavie_stability_status.json` | Last enforce |
| `data/workspace/red_lavie_recovery_status.json` | Post-outage recovery |

## Scheduled task on Red LAVIE

`ClawstackRedLavieKeepalive` -- every 5 min renews execution state + heartbeat file under `C:\ProgramData\Clawstack\stability\`.
