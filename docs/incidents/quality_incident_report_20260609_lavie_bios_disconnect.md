# Quality Incident Report: LAVIE BIOS Disconnect

## Summary

- Date: 2026-06-09 JST
- Node: NEC LAVIE / `desktop-tfdripe-lavie` / Tailscale `100.87.244.46`
- User observation: the physical LAVIE unit was found stopped at the BIOS screen.
- Fleet symptom: K10 could no longer reach LAVIE monitor, job worker, or n8n over Tailscale.

## Evidence From K10

| Time / Source | Evidence |
|---|---|
| 2026-06-09 02:58:36 JST / `data/workspace/lavie_continuous_te_status.json` | Telegram warning: `WARN stage=probe_fail detail=timed out`. |
| 2026-06-09 03:30:41 JST / `data/workspace/lavie_continuous_te_status.json` | Last cycle: `resin_fill_cad`, trial `lavie365-resin_fill_cad-4302dca7`, verdict `TIMEOUT`, worker status `failed`. |
| 2026-06-09 03:30:41 JST / `data/workspace/satellite_cae_log.jsonl` | Last logged LAVIE CAE job timed out after 1320 seconds. |
| 2026-06-09 20:22:04 JST / `data/workspace/fleet_operations_status.json` | Fleet status critical: `LAVIE job worker offline`, `LAVIE n8n offline`. |
| 2026-06-09 current check / `tailscale status` | `desktop-tfdripe-lavie` is offline from K10's point of view. |

## What Is Confirmed

1. The connection drop was not only a dashboard display problem.
2. The LAVIE Windows user-space stack was not running after the event, because Tailscale, monitor agent, job worker, and n8n were unreachable.
3. Immediately before the loss, LAVIE was repeatedly running `resin_fill_cad` CAE jobs that timed out.
4. The physical BIOS screen strongly indicates the machine rebooted, failed to continue to Windows, or entered firmware setup after an abnormal boot condition.

## Most Likely Cause Chain

1. LAVIE was assigned repeated heavy `resin_fill_cad` OpenFOAM/CAD proxy jobs.
2. The workload produced repeated 1320-second timeouts and a real failure streak for `resin_fill_cad`.
3. Around 2026-06-09 02:58 JST, K10 started seeing probe timeouts.
4. At 2026-06-09 03:30 JST, the last known LAVIE job was recorded as `TIMEOUT`.
5. After that, LAVIE did not return to Windows services and was later found on the BIOS screen.

The most likely technical triggers are thermal protection, power instability, forced reboot, firmware/Windows update reboot, boot device detection issue, or a BIOS prompt after an abnormal restart. K10 can prove the workload/offline sequence, but cannot prove the exact BIOS trigger until LAVIE's local event logs and BIOS state are checked.

## 5 Whys

| Why | Analysis |
|---|---|
| Why did K10 lose connection to LAVIE? | LAVIE stopped running Windows network services, including Tailscale and monitor agent. |
| Why did Windows services stop? | The machine was physically found in BIOS instead of Windows. |
| Why was it in BIOS? | Likely an abnormal reboot, boot interruption, firmware prompt, or boot device selection issue. |
| Why might abnormal reboot have occurred? | LAVIE had repeated heavy `resin_fill_cad` CAE timeouts and probe failures before the loss, increasing thermal/power/driver stress risk. |
| Why did the system keep stressing LAVIE? | The guard reduced some heavy routing but did not hard-quarantine normal LAVIE after repeated heavy CAE timeouts plus probe failures. |

## FTA

```text
Top event: LAVIE unavailable from K10 and found at BIOS
|
+-- Windows not running
|   +-- abnormal reboot or shutdown
|   |   +-- thermal protection under repeated CAE load
|   |   +-- power/AC/battery instability
|   |   +-- Windows update or firmware reboot
|   +-- boot interrupted after reboot
|       +-- boot device/SSD detection issue
|       +-- BIOS setup prompt or boot order issue
|       +-- key held during boot or firmware setting prompt
|
+-- Network-only issue
    +-- rejected because physical BIOS screen means OS services cannot run
```

## Immediate Countermeasures

1. Hold normal LAVIE from heavy CAE workloads until local logs are collected.
2. Prefer Red LAVIE, K10, Dynabook, or ThinkPad for heavier CAE jobs.
3. On physical LAVIE, boot Windows through `Windows Boot Manager` or exit BIOS without saving if settings look unchanged.
4. After boot, collect Windows Event Viewer logs for:
   - `Kernel-Power` event 41
   - `EventLog` event 6008
   - `Kernel-Boot`
   - `WHEA-Logger`
   - `WindowsUpdateClient`
   - thermal or ACPI-related events
5. Check BIOS boot order, SSD visibility, AC adapter, battery, fan/thermal condition, and BIOS date/time.

## Prevention Rule

If any fleet node has both repeated heavy-job timeouts and monitor probe failures, the router should place that node into `BIOS_RECOVERY_HOLD` or equivalent quarantine before assigning more heavy work. Recovery requires a fresh local boot confirmation and event-log review.

