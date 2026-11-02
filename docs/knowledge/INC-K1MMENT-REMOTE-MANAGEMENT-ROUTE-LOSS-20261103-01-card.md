# K1 management-route loss — 2026-11-03

Incident `INC-K1MMENT-REMOTE-MANAGEMENT-ROUTE-LOSS-20261103-01`. K10 live Tailscale reads at 07:49:42 and 07:58:39 JST: peer `DESKTOP-K1MMENT` (`100.67.170.15`) remained `Online=false`, `Active=true`, last seen 07:20:00 JST; bounded pings received no reply. At 08:02 JST, K10 also observed a pre-existing SSH process holding a TCP `Established` socket to K1 port 22; its parent was absent and no authenticated command response was verified. It was not reused or closed. This socket is not proof that K1 is live or controllable. Earlier fixed SSH/worker probe around 07:32 timed out. Current host power, LAN/Wi-Fi, Windows sign-in, jobs, solver, checkpoints and GUI state are UNKNOWN. Local browser automation had no browser session and its browser host was unavailable; no remote screen was observed. Cause UNKNOWN. No restart, task/job change or dispatch. Keep the layers separate, preserve prior work, and refresh tasks/checkpoints before recovery or dispatch. Related Beads: `orca-local-odt`; prior console-lock issue `orca-local-f5i`.


## Live route follow-up — 2026-11-03 08:08-08:11 JST

K10 Tailscale still showed K1 Online=false, no current address, last seen07:22:21 JST; two bounded pings timed out. K10 Wi-Fi was192.168.3.87/24. Candidate192.168.3.136 is a historical Tailscale endpoint, not verified as K1's current LAN identity; neighbor resolution was incomplete and bounded TCP22/3389/5985 checks failed. Browser list empty, browser access host unavailable, local Chrome minimized; CRD screen/login state not observed. Host power/jobs/worker/solver/checkpoints UNKNOWN. No K1 changes or dispatch. Cause UNKNOWN.


## Graphify capture limitation — 2026-11-03 08:12-08:13 JST

Graphify update failed with error28 after a same-volume45.94MB backup was created without free-space validation. Original graph SHA-256 remains unchanged and no node was added; D: free space was2.58MB at08:13:38. Exact same-hash backup cleanup was rejected by policy, so it remains. Local MCP card export and GitHub card sync succeeded; direct MCP retrieval, ByteRover and Turso remain unavailable/pending.


## Capacity-guard follow-up — 2026-11-03 08:20 JST

Local updater now refuses low-space rewrites before parse/backup, validates capacity for backup+replacement+32MiB reserve and source hash stability, and refuses an existing temp. Script hash `C687F8121F538D17A08F1634A11F5DE2FFA5A627F0B1FC002E82A605A4EEB0D1`. Not run: D: free1,638,400 bytes and prior temp/backup remain. Guard effectiveness and Graphify retrieval unvalidated.


## Guard-source hash correction — 2026-11-03 08:25 JST

The local updater now captures the graph hash before parsing and rechecks before backup. Current SHA-256 `D54065EB47FB3ACDD84C5E12A461723334440AE85550BE97790907D80C918872`; prior `C687...` is the previous revision. Not executed; D: free1,495,040 bytes and the earlier temp/backup remain.
