# Myourenji_1 live route recheck — 2026-11-02 12:11 JST

Incident: `INC-MYOURENJI1-ROUTE-FLAG-FLUCTUATION-20261101-01`. Target `myourenji-1` / `100.111.176.93`; route and key path from the existing connection card. K10 is the only known host with the private key; key material was not read or displayed.

- At 12:02:19-12:02:25 JST, K10 `tailscale status --json` showed the peer `Online=false`; peer `LastSeen=2026-11-01T18:00:00.1Z` (2026-11-02 03:00 JST). This is tailnet control-plane evidence, not proof that the computer is powered off.
- At 12:11:06 JST, K10 `tailscale ping --c 2 100.111.176.93` received no replies (exit 1; both probes timed out).
- At 12:11 JST, K10 SSH alias `cae-myourenji-1`, BatchMode and six-second connect timeout: exit 255, TCP/22 connection timed out. SSH authentication was not reached. This is a network/path failure, not a credential rejection.
- No current RDP/WinRM or GUI/Google Remote Desktop probe was made in this recheck. The desktop/sign-in state, host power, monitoring endpoint, worker/dispatch endpoint, jobs and solver state remain UNKNOWN.

Disposition: remote control is not established as of these observations. Do not infer host power-off or clear any work. No remote setting, process, task, file or job was changed; no job was stopped/restarted/dispatched. Root cause remains UNKNOWN. For recovery, obtain fresh console-side network/service evidence or a directly observable authorized remote desktop session, then verify host, monitor, worker, application and existing tasks/checkpoints independently. Never store credentials or auto-unlock.
