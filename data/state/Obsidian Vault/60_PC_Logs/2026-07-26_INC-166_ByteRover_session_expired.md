# INC-166 ByteRover session expiration

## QC process record

| Process | Input | Check | Result | Disposition |
|---|---|---|---|---|
| Pre-work memory retrieval | Unity/Mixamo query | 65 s bounded execution | Timed out at 69 s | Stop and diagnose |
| Authentication check | `brv status` | Account state | `Session expired` | Do not retry |
| Process containment | Query CLI and agent child | Exact PID and command line | Two children stopped | PASS |
| Unrelated-work protection | Node/Python process families | Command-line ownership | Services and RL preserved | PASS |

## 5 Why / FTA

Top event: required memory query did not return.

1. Query agent produced no result.
2. ByteRover account session was expired.
3. Query did not fail fast on the expired state.
4. Outer timeout ended the shell but not both query children.
5. Exact command-line ownership was therefore required for safe containment.

FTA branches considered: authentication (confirmed), provider/network (not
needed), data corruption (not observed), broad host failure (ruled out by other
running services).

## Fishbone

- Method: status was checked after the query rather than before it.
- Tool: CLI did not fail fast and left children.
- Environment: Windows host and unrelated long-running Node/Python jobs.
- Data: local context tree, Beads, and Markdown records remained readable.
- Human: re-authentication requires account action; no credentials were guessed.

## FMEA and countermeasures

| Mode | Effect | S | O | D | RPN | Action |
|---|---|---:|---:|---:|---:|---|
| Expired session | Context query blocked | 5 | 6 | 2 | 60 | Check status, bound query |
| Orphan query child | Resource leak | 4 | 5 | 3 | 60 | Match exact command line |
| Broad Node kill | Service outage | 9 | 2 | 7 | 126 | Prohibit image-name cleanup |

Decision rule: IF ByteRover is expired and a bounded query times out, THEN stop
only the query-owned children and use Beads plus durable local records, BECAUSE
Unity import does not depend on ByteRover at runtime.

## Verification / recovery

The exact query children were absent after containment. The daemon, Telegram
bridge, unrelated Node processes, and RL training were kept. Recovery is
`brv login`; no retry is attempted until authentication is restored.

## Scope and provenance

No ByteRover cloud recovery was performed. No web search was needed because
local status was authoritative. Source: INC-166 and
`docs/quality_incident_report_20260726_byterover_session_expired.md`;
backup commit `e765bdedaf`; 2026-07-26 JST.
