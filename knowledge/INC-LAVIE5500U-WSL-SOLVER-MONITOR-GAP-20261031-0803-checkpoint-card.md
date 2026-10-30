# New LAVIE checkpoint preservation follow-up - 2026-10-31

Incident: INC-LAVIE5500U-WSL-SOLVER-MONITOR-GAP-20261031-01. Evidence is a timestamped follow-up, not live telemetry after the noted observation times.

On 2026-10-31 07:51-07:54 JST, Tailscale and authenticated SSH reached DESKTOP-K1MMENT. The exact LIG07 task remained Disabled; HealthHistory completed with result 0. The WSL-aware guest log recorded six foamRun ranks and one engine_k10. The Windows snapshot showed dispatch disabled. Core (Tctl/Tdie) was 77.25 C; Core Average was unavailable. A 2.036-second host CPU sample was 67.18% across 12 logical processors. The installed-versus-visible RAM gap remained 637833216 bytes, cause UNKNOWN. Host and WSL guest memory were kept separate.

OpenFOAM decomposed checkpoint 0.31 included 72 files across six ranks, 12 per rank, totaling 97155461 bytes. Two metadata snapshots five seconds apart and a post-hash metadata read matched. All 72 files have SHA-256 in the local manifest `openfoam-checkpoint-031-manifest-20261031-0758.json` (SHA-256 FEB8E1E05504E21CA2DB72E6CC50CEB52C8CDBC84108E01157FF1E2714F436CC). The controlDict, run script and input manifest hashes were re-read and matched. This verifies a stable content-hashed checkpoint candidate, not restart acceptance.

At 08:03:05 JST, the OpenRadioss engine log explicitly reported an RFILE write at cycle 45000. The 287111939-byte source restart and a unique non-overwriting preserved copy matched SHA-256 `6090adc0bc005d0e0f1396547b493b24f2736cc90320f125dfa1dd90bc5d0255`; source metadata remained stable. Earlier preservation copies remain. No calculation was stopped, resumed, deleted or newly dispatched. Restart acceptance remains unproven; production dispatch remains held pending separate approval and RAM reconciliation.

Detailed evidence: `artifacts/new-lavie/live-continuation-audit-20261031-0754.md`. Human job initiator remains UNKNOWN.

## 08:06 JST update

OpenFOAM checkpoint 0.32 has 72 stable files across six ranks (12 per rank), 97,155,461 bytes; all SHA-256 values and pre/post metadata match are recorded in `openfoam-checkpoint-032-manifest-20261031-0807.json` (manifest SHA-256 `50FBD5BFE7F6FF9AD68A84D1BE3AF64B8CE35E5E4A118609D7C63E060DAAF6DD`). Provenance hashes still match. This is checkpoint integrity only; restart acceptance remains open. The 08:06 guest row again recorded six foamRun and engine_k10; task stayed Disabled and dispatch false. RAM reconciliation and separate production approval remain open.
