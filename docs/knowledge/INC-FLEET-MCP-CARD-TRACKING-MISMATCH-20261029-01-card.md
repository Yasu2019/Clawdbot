# Fleet MCP card tracking mismatch — 2026-10-29

Incident: `INC-FLEET-MCP-CARD-TRACKING-MISMATCH-20261029-01`; Beads `orca-local-j0x` (open, P2).

At 2026-10-29 01:14 JST, the Fleet manifest reported 126 entries and omitted the existing `INC-OPENFOAM-PHASE-MASS-BALANCE-20261028-01-card.md`. The destination remains present (SHA-256 `8FB97504100DA622977BB709A4544A291D285E42318471224BDB955CB751765A`). The allowlisted exporter refuses to overwrite this untracked/external card. Manifest export time is 01:10:22 JST; reason and writer are UNKNOWN. No destination, manifest, or index change was made by this investigation.

Do not infer overwrite permission. Reconcile manifest/index and hashes, identify the authorized writer, then add/retrieve a unique reviewed follow-up card only through a safe exporter path. GitHub content has been separately synchronized. ByteRover is queued but disconnected; Turso unavailable. Full evidence and FMEA/FTA/QC/Control Plan are in the linked incident record.


## Correction: safe export and partial retrieval restored — 2026-10-29 01:22 JST

A complete read-only audit of the 19-entry allowlist found two untracked/external mismatches: `INC-LAVIE5500U-HEALTH-HISTORY-WSL-20261028-2316-followup-card.md` (SHA-256 `c43de9e7344161e7222615165a1b4e8cadb2397d531d3fb8ce8d19e91a21884b`) and `INC-OPENFOAM-PHASE-MASS-BALANCE-20261028-01-card.md` (SHA-256 `8fb97504100da622977bb709a4544a291d285e42318471224bdb955cb751765a`). The exporter was changed to preflight all source/destination hashes before any writes and to preserve these two named files verbatim as `preserved-untracked-not-exported`. Temporary-directory regression tests passed 3/3, including refusal with zero partial changes and successful preservation/export behavior.

The reviewed phase-density card and this Fleet mismatch card were added to the allowlist. Export completed with 17 tracked cards and 2 preserved untracked cards; live manifest has 140 entries, `exported_at=2026-10-29T01:20:41.216608+09:00`. Phase-density card destination SHA-256 is `a6d96b3ddf43f703121e29d9cbf57bc1f7336cd05a10b7b605b1a886a1b60291`. Read-only Fleet MCP readback exactly matched the destination content and contains both the MULES/ALE evidence and 01:10 JST preflight. The two preserved cards remain untracked and their originating writer is still UNKNOWN. Local evidence: `artifacts/verification/fleet-mcp-preexport-20261029-0116/`, `...-0120/`, `...-0123/`; the folder suffixes were nominal labels, not observed times. Their embedded backup manifests should be read for actual creation times.

GitHub contains sanitized knowledge on branch `knowledge/openfoam-phase-density-live-gate-20261029`; latest verified remote ref before this correction is `43a6c0262dfce1df1c217c305e0804b402160e28`. ByteRover local queue is deduplicated but live `brv status` at ~01:11 JST showed expired/disconnected; delivery pending. Current tools expose no Turso connector/CLI, so no Turso write was attempted.


## Final export/readback correction — 2026-10-29 01:23 JST

A final rerun after updating the reviewed card completed at `manifest.exported_at=2026-10-29T01:23:29.482957+09:00`. The manifest has 140 entries. The 19-entry allowlist reports 17 tracked exports and 2 explicitly preserved, untracked files. Destination SHA-256: phase-density card `a6d96b3ddf43f703121e29d9cbf57bc1f7336cd05a10b7b605b1a886a1b60291`; Fleet incident card `ced8f08d78338e439a44819ac550751fe6006ce165fbb8645ac89ae50a4e2854`. Both are BOM-free. Read-only Fleet MCP returned exact normalized content for both cards, including MULES/ALE, the 01:10 preflight, and this sync incident. The older phase-mass card and LAVIE card remain byte-for-byte unchanged and are not counted as exported. Final manifest SHA-256 `cd9bca5c484929d94711ae56a0c567622c91e948f7a14a8ae5fb575a90d4115d`; INDEX SHA-256 `3ed8a73d3aa3ace5eb6ed30323ff2bf1ea36996f1cfc2d7c495a695dea8832be`.

Backup folder labels were nominal; correction metadata in their backup manifests records filesystem-observed times. Final pre-export snapshot is `artifacts/verification/fleet-mcp-preexport-20261029-012329/` (created 01:23:29 JST). The exporter tests are 3/3; log SHA-256 `A6ED83E04FEF57301DE782AA5D50C741D31730553A9F8E7659DA39FBA00E3FBE`. Root cause/owner for the two external manifest omissions is still UNKNOWN.
