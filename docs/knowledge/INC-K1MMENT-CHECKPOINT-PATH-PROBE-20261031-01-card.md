# Knowledge card — checkpoint audit path-assumption recurrence

Incident: `INC-K1MMENT-CHECKPOINT-PATH-PROBE-20261031-01`

On 2026-11-01, a first read-only OpenFOAM checkpoint probe again assumed root-level paths. The actual paths were in the case's `first/`, `resumed/`, and `known-good/` directories. The failed probe was an audit/path error, not evidence of file loss. A corrected bounded audit at 02:41 JST passed exact proof path, byte count, SHA-256, binary and native-proof checks for finite OpenFOAM 14, CalculiX 2.21, Elmer 26.2.1, and OpenRadioss qualification evidence. Preserved known-good copies matched their initial checkpoint hashes. No solver or job was changed or dispatched.

Recurrence control: use the exact proof-recorded paths or explicit, case-validated path mapping. Treat mismatch as an audit failure. Preserve both failed and corrected outputs. These finite tests do not establish arbitrary production-run resume readiness or authorize dispatch. RAM reconciliation and separate production authorization remain outstanding.

Evidence: `artifacts/new-lavie/solver-checkpoint-current-integrity-v2-20261101T0242.json` (SHA-256 `3BF581AEB64E000A1370BDDB54CA0BB3BDC049B93DD8F5A35D7D876ABCB09AEF`).
