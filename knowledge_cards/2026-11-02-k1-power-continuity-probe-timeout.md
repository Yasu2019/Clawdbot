# Managed Windows host continuity-probe timeout ? 2026-11-02 11:23?11:28 JST

Linked incident: `INC-K1MMENT-POWER-CONTINUITY-PROBE-TIMEOUT-20261102-01`.

- One bounded power/continuity probe succeeded at11:23:48: AC performance scheme, sleep/lid actions0, Wi-Fi and Internet Up, SSH/Tailscale services automatic; RDP service stopped. It showed a SYSTEM recovery task scheduled every minute.
- Two subsequent composite probes timed out at30s. A host-only authenticated SSH identity query succeeded; Tailscale was online and ping replied4ms; TCP22 open. TCP3389/5985 timed out. A later separate health sample succeeded: Wi-Fi/Internet Up, recovery `connected_no_action`, no restart actions, solver dispatch disabled. Composite timeout does not mean host offline.
- A WMI-free list showed two idle PowerShell processes (~53.7MiB Working Set each) whose start times aligned with the failed probes; they remained present at a second sample, with CPU times unchanged. They may be timeout residue, but process owner, parent and command line were not inspected. No process was stopped.
- At the same time, existing custom fill work remained CPU-active, with log step640 and no verified checkpoint. Preserve work; do not stop/restart. RAM/temperature vary; FEM dispatch remains disabled.

Assessment: host/network and authenticated SSH worked, but the composite probe timed out twice. Root cause and candidate process ownership remain UNKNOWN. Next control: keep route, health, worker and GUI layers separate, and verify exact PID identity before any cleanup. This card is sanitized; canonical notes retain raw evidence.
