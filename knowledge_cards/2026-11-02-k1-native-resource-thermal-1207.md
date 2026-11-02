# K1 RAM gate live resource and thermal follow-up — 12:07 JST

Incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01`. K10 authenticated fixed-probe observations on DESKTOP-K1MMENT (`100.67.170.15`):

- WorkerStatus observed 2026-11-02 12:07:16.934 JST; embedded health sample 12:06:19.372 JST. CPU 12.42% across all 12 Windows logical processors over 2.016s; six physical cores. Dispatch endpoint was not probed and dispatch_enabled=false. No active WSL solver processes in a separate solver probe at 12:07:21.194 JST.
- Host OS available RAM 1,398,358,016 B (about 1.30 GiB) at the WorkerStatus sample. This is a point value, not a capacity budget. WSL config remains 10GB/12 processors/2GB swap; guest availability is not combined with host availability.
- Scheduled tasks observed at 12:06:12.044 JST included `Clawstack_Lavie5500U_Health_20261024` and `OF76_f3A`. Exact owner, worker progress, and checkpoint validity were not queried in this snapshot. Preserve the task and its work; do not stop, restart, or reuse it.
- ThermalGate observed 12:07:31.166 JST: accepted=true using a time-weighted trailing 5-minute mean of seven fresh one-minute `Core (Tctl/Tdie)` samples, mean 85.870 C against existing 95 C average limit; current sample 86.125 C. This is a Tctl/Tdie proxy, not LibreHardwareMonitor Core Average. Cooling policy readback was AC/DC Active; fan RPM and Core Average unavailable.
- A nearby WorkerStatus instantaneous `Core (Tctl/Tdie)` value was 92.125 C; its source/time differs from ThermalGate's 12:07:31 sample, so retain as separate observation rather than substituting it into the average.
- The installed-versus-visible RAM difference remains 637,833,216 B, cause UNKNOWN (12:04:53.554 JST native API readback). Low volatile host availability and unresolved memory attribution keep FEM dispatch held, despite thermal gate acceptance. No settings, jobs, or processes changed; no FEM dispatched.

Evidence sources: `scripts/Invoke-K1WslReadOnly.ps1` fixed probes `WorkerStatus`, `SolverProcesses`, `ThermalGate`; dispatch endpoint, active-job owner, and checkpoint were not verified here. Do not infer worker control or recoverability from a healthy host/health producer.
