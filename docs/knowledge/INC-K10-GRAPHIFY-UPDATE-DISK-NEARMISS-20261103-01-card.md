# K10 Graphify update disk-space near-miss — 2026-11-03

Incident `INC-K10-GRAPHIFY-UPDATE-DISK-NEARMISS-20261103-01`; linked K1 route incident `INC-K1MMENT-REMOTE-MANAGEMENT-ROUTE-LOSS-20261103-01`.

At08:12-08:13 JST, a Graphify update created a same-volume45,939,922-byte copy of `graph.json` before measuring free space. The following temp rewrite failed with Windows error28. At08:13:38 D: had2,576,384 bytes free. Original graph SHA-256 is `001D177671D935CF7132836E71504C6BCA143805F270190EB445E04F2367360D`, unchanged; no node was added. Cause of pre-existing low capacity UNKNOWN. A zero-byte temp file and the exact same-hash backup remain because cleanup was rejected by automatic approval review (`blocked by policy`). No older project/calculation data was touched.

Prevention: measure target free space and expected backup/rewrite size before any large graph snapshot; stop before writing if capacity with reserve is uncertain. Graphify retrieval remains pending. Local MCP export and isolated GitHub card update are verified; direct MCP retrieval unavailable, ByteRover auth expired, Turso CLI/tool unavailable. Control effectiveness pending.
