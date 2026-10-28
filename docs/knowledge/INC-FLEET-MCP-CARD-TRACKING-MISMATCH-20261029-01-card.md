# Fleet MCP card tracking mismatch — 2026-10-29

Incident: `INC-FLEET-MCP-CARD-TRACKING-MISMATCH-20261029-01`; Beads `orca-local-j0x` (open, P2).

At 2026-10-29 01:14 JST, the Fleet manifest reported 126 entries and omitted the existing `INC-OPENFOAM-PHASE-MASS-BALANCE-20261028-01-card.md`. The destination remains present (SHA-256 `8FB97504100DA622977BB709A4544A291D285E42318471224BDB955CB751765A`). The allowlisted exporter refuses to overwrite this untracked/external card. Manifest export time is 01:10:22 JST; reason and writer are UNKNOWN. No destination, manifest, or index change was made by this investigation.

Do not infer overwrite permission. Reconcile manifest/index and hashes, identify the authorized writer, then add/retrieve a unique reviewed follow-up card only through a safe exporter path. GitHub content has been separately synchronized. ByteRover is queued but disconnected; Turso unavailable. Full evidence and FMEA/FTA/QC/Control Plan are in the linked incident record.
