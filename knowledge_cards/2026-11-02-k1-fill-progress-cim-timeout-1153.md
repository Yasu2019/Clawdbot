# K1 fixed progress probe WMI timeout — 2026-11-02 11:50-11:53 JST

Linked incident: `INC-K1MMENT-FILL-PROGRESS-CIM-TIMEOUT-20261102-01`.

- Exact-PID CIM/WMI progress audit exceeded30s; K10 ended only its local SSH client. Remote completion/state at timeout was UNOBSERVED; exact slow subcall/root cause UNKNOWN. Do not infer host offline or an orphan.
- The helper was revised to remove WMI, owner, parent and command-line queries; start-time matching now allows 0.01ms precision tolerance. WMI-free validation passed at11:52:06. It confirmed a Python PID/start-time match only; task state was Running/S4U, but owner, progress log and checkpoint path were unresolved.
- Two process snapshots 26s apart showed large drops in process private/working-set counters while the task remained Running. Host available RAM later measured3.575GB; FEM dispatch false and no solver processes. Memory fluctuation does not prove completion or recovery.
- No process/task/job/settings changes. Preserve existing task and calculations; cause UNKNOWN.

Full evidence and exact values remain in the canonical restricted workspace note.
