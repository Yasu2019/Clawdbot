# K10 Graphify update disk-space near-miss — 2026-11-03

Incident `INC-K10-GRAPHIFY-UPDATE-DISK-NEARMISS-20261103-01`; linked K1 route incident `INC-K1MMENT-REMOTE-MANAGEMENT-ROUTE-LOSS-20261103-01`.

At08:12-08:13 JST, a Graphify update created a same-volume45,939,922-byte copy of `graph.json` before measuring free space. The following temp rewrite failed with Windows error28. At08:13:38 D: had2,576,384 bytes free. Original graph SHA-256 is `001D177671D935CF7132836E71504C6BCA143805F270190EB445E04F2367360D`, unchanged; no node was added. Cause of pre-existing low capacity UNKNOWN. A zero-byte temp file and the exact same-hash backup remain because cleanup was rejected by automatic approval review (`blocked by policy`). No older project/calculation data was touched.

Prevention: measure target free space and expected backup/rewrite size before any large graph snapshot; stop before writing if capacity with reserve is uncertain. Graphify retrieval remains pending. Local MCP export and isolated GitHub card update are verified; direct MCP retrieval unavailable, ByteRover auth expired, Turso CLI/tool unavailable. Control effectiveness pending.


## Capacity-guard follow-up — 2026-11-03 08:20 JST

Local updater now refuses low-space rewrites before parse/backup, validates capacity for backup+replacement+32MiB reserve and source hash stability, and refuses an existing temp. Script hash `C687F8121F538D17A08F1634A11F5DE2FFA5A627F0B1FC002E82A605A4EEB0D1`. Not run: D: free1,638,400 bytes and prior temp/backup remain. Guard effectiveness and Graphify retrieval unvalidated.


## Control-document targeting correction — 2026-11-03 08:23 JST



## Control-document targeting correction — 2026-11-03 08:23 JST

A first capture-helper version appended the K10 near-miss paragraph to K1 route draft files due to a wrong path prefix. This was detected and append-only corrected; the authoritative K10 FMEA/FTA/QC/Control Plan drafts are now separate and mirrored to Obsidian with matching hashes. No history was deleted.


## Guard-source hash correction — 2026-11-03 08:25 JST

The local updater now captures the graph hash before parsing and rechecks before backup. Current SHA-256 `D54065EB47FB3ACDD84C5E12A461723334440AE85550BE97790907D80C918872`; prior `C687...` is the previous revision. Not executed; D: free1,495,040 bytes and the earlier temp/backup remain.
