# Quality Incident Report: ThinkPad L590 Sleep Outage

## Summary

- **Date**: 2026-06-15 JST
- **Node**: ThinkPad L590 / `yasu-thinkpad-l590` / Tailscale `100.66.63.9`
- **User observation**: ThinkPad is offline. Monitor Agent (port 8111) is not running.
- **Fleet symptom**: Tailscale indicates ThinkPad went offline (last seen ~5 hours ago). SSH connection timed out.

## Evidence From K10

| Time / Source | Evidence |
|---|---|
| 2026-06-14 18:39:40 JST / `data/workspace/thinkpad_recovery_status.json` | Stability enforcement step failed: `stderr_tail: /home/yasu/clawstack_satellite/scripts/thinkpad_host_stability.sh: line 4: set: pipefail\n: invalid option name` (exit code 2) |
| 2026-06-15 14:47:14 JST / `tailscale status` command | `100.66.63.9 yasu-thinkpad-l590 ... offline, last seen 5h ago` |

## What Is Confirmed

1. ThinkPad L590 is physically offline/suspended.
2. The stability enforcement script (`thinkpad_host_stability.sh`) failed to run on the node.
3. The failure was caused by Windows-style CRLF (`\r\n`) line endings in the bash script. Git on Windows checked out the scripts with CRLF, and they were transferred to the Linux (Ubuntu) host via SCP without conversion.
4. As a result, bash failed to execute the script at line 4 (`set -euo pipefail\r` causing `pipefail\r: invalid option name`), preventing the script from disabling systemd sleep targets and blocking Lid switch actions.
5. The ThinkPad subsequently suspended/slept automatically.

## 5 Whys (なぜなぜ分析)

| Why | Analysis |
|---|---|
| 1. Why is ThinkPad offline? | The machine entered a suspend (sleep) state and stopped networking/SSH services. |
| 2. Why did it enter suspend state? | The Lid (フタ) was closed or the machine went idle, and the OS auto-suspend was not inhibited. |
| 3. Why was the auto-suspend not inhibited? | The host stability script (`thinkpad_host_stability.sh`), which configures lid/sleep settings, crashed with exit code 2. |
| 4. Why did the script crash? | The script contained Windows CRLF (`\r\n`) line endings, causing bash to interpret the command as `set -euo pipefail\r`, which is an invalid option. |
| 5. Why did the script have CRLF endings on Ubuntu? | Git on Windows (K10) checked out the scripts using Windows line endings (CRLF), and they were transferred directly to Linux via SCP without line ending conversion (LF). |

## FTA (Fault Tree Analysis)

```text
Top event: ThinkPad L590 offline (suspended)
|
+-- OS entered suspend (sleep) state
|   +-- Lid was closed or idle timeout reached
|   +-- Suspend inhibition settings not applied
|       +-- thinkpad_host_stability.sh failed to run
|           +-- Syntax error in script execution
|               +-- Carriage Return (\r) in "set -euo pipefail\r"
|                   +-- Git checkout CRLF configuration on K10
|
+-- Hardware power failure or network switch issue
    +-- Rejected: Tailscale was working fine on other nodes, and thinkpad_recovery_status.json explicitly showed script execution failure.
```

## FMEA (Failure Mode and Effects Analysis)

| Component | Failure Mode | Effect on System | Core Cause | Mitigation / Action |
|---|---|---|---|---|
| `thinkpad_host_stability.sh` / `thinkpad_lid_no_sleep.sh` | Windows CRLF line endings transferred to Linux | Host stability settings (sleep inhibition) are not applied, leading to node suspend (offline). | Git auto-crlf behavior on Windows host. | 1. Convert all shell scripts to LF endings on K10.<br>2. Run Python setup script to re-push LF scripts and restart services once online.<br>3. Commit Git configuration to avoid future auto-conversion. |

## Immediate Countermeasures

1. **User Action**: Physically wake up the ThinkPad L590 (open the lid or press the power button).
2. **K10 Deployment**: Once ThinkPad is online, run the deploy script on K10 to push the corrected LF scripts:
   `python D:\Clawdbot_Docker_20260125\scripts\k10_thinkpad_fleet_setup.py`
3. **Verification**: Confirm Monitor Agent is running on port 8111 (`http://100.66.63.9:8111/metrics` responds with 200).

## Prevention Rule

All shell scripts (`.sh`) pushed from Windows hosts to Linux nodes must be explicitly converted to LF line endings, or Git attributes should be set (`.gitattributes` with `* text eol=lf` or specific rules for `*.sh`) to force LF endings during checkout.
