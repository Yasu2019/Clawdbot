# Managed FEM host live resource and recovery follow-up ? 2026-11-02 11:12?11:14 JST

Linked incident: `INC-K1MMENT-RAM-PROBE-MISMATCH-20261031-01`.

- A pre-existing long-running custom fill worker remained active and its progress log advanced from step 620 to 640 between 11:02:53 and 11:10:32 JST. This confirms activity, not engineering correctness or completion. Registration author/human initiator remain unknown; preserve the worker.
- The bounded output inventory contained only the progress log; no checkpoint candidate was visible. The pinned source audit did not verify an in-case restart path. Do not stop or claim resumability.
- Host health at 11:12:19: CPU 12.87% over 2.001s / 12 logical processors; available RAM 2.27 GiB; package proxy Tctl/Tdie 78.75 C. Later independent host counters at 11:13:02 showed OS free 4.35 GiB, PerfOS 4.37 GiB, PSAPI 4.37 GiB. Available RAM is volatile; the earlier health snapshot differs by time.
- Commit counters at the later sample disagree materially: PerfOS 24.23 / 27.62 GB; PSAPI 27.62 / 27.69 GB (difference 3.392 GB decimal / 3.16 GiB). Cause UNKNOWN; do not select the more favorable counter. OS-free vs PerfOS/PSAPI available values differ about 24?25 MiB; PerfOS and PSAPI agree within 4.9 MiB.
- Installed memory is 16 GiB (2x8 GiB); OS-visible 15.42 GiB. Guest memory is reported separately and is never added to host memory. Radeon driver-reported 512 MiB does not prove a fixed UMA reservation. Cause of the installed/visible gap remains UNKNOWN.
- Thermal gate accepted a trailing five-minute Tctl/Tdie mean 86.48 C / 95 C; point 78.75 C. Core Average and fan telemetry are unavailable. This is not proof that cooling hardware is at maximum.
- Existing FEM dispatch remains disabled. Preserve current work; no new dispatch, restart, setting change, or reboot.
- ByteRover local curation ended in error: `ECONNREFUSED 127.0.0.1:11434`; no knowledge records added and no retry/service restart.

Durable local evidence includes exact source timestamps, counters and process/task identity; this shared card intentionally omits those identifiers. Arithmetic corrections were appended to the canonical note and retained with timestamp.
