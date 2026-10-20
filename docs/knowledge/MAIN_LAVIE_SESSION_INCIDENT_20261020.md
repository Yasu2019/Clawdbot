# Main LAVIE session and connection incident

Incident: MAIN-LAVIE-SESSION-20261020-2235. Beads: h49j.

## Verified observations
Direct authenticated SSH to DESKTOP-TFDRIPE succeeded on 2026-10-20 at22:34-22:35 JST. Last boot was2026-10-19 17:34:41 JST. chromoting, sshd and WinRM were Running. WTS API at22:35:17 JST reported console session1, active, has_user=true, raw_session_flags=1, unlocked. No screen was observed by the agent. The user reported Google Remote Desktop visibility and suspected an earlier sign-in screen.

Provider-filtered System queries for the preceding24hours found no matching Kernel-Power41/42/107/109/506/507, Power-Troubleshooter1 or EventLog6005/6006/6008 records. This is absence of supporting records, not proof that all historical power/network behavior is known. Security4800/4801/4778/4779 queries returned no records despite the log being enabled; earlier lock/unlock time and cause remain UNKNOWN. WLAN events alone did not establish a disconnect or its cause. Current unlocked state must never be backdated to the earlier incident.

## Reusable procedure
1. Failed SSH/VPN/monitor probes do not establish power-off. Record host reachability, independent LAN/relay routes, monitor, authenticated worker, actual solver progress, OS session and visible GUI separately.
2. Require observation time, timezone, source and exact host identity for every current-state claim.
3. Filter event logs by provider AND event ID. Broad ID1 queries were saturated by unrelated Configuration-Change-Monitor entries and could not establish absence of sleep events.
4. When quser is unavailable, use read-only WTS APIs. A long EncodedCommand failed; a compressed in-memory bootstrap successfully executed the same read-only script. No execution-policy change was needed.
5. A remoting process or SSH success does not prove authenticated GUI control or solver progress. A locked screen does not imply stopped calculations or a powered-off host.
6. Preserve existing processes, tasks, queues, watchdogs and valid checkpoints. Do not blindly reboot, stop WSL or restart jobs. Never weaken authentication or enable auto-login.

## Evidence and limits
Local evidence: artifacts/main-lavie-session-20261020/windows-live.json, targeted-events.json, wts-session.json, wlan-details.json.
Procedure: docs/knowledge/REMOTE_ACCESS_FALLBACK_20261020.md.
Read-only investigation; no service/task/power/audit/registry changes, no process signals, job restart or deletion. Existing P1r41f autoresume and memory-guard WSL wrappers were preserved and were not treated as solver-progress proof. Root cause remains unconfirmed. No passwords, PINs, OTPs or authentication tokens are included.
