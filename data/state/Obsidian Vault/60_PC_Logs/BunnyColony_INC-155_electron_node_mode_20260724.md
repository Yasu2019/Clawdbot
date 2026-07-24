# Bunny Colony INC-155 - Electron forced into Node mode

## Incident summary

The packaged Bunny Colony executable exited during its first launch probe. A logged reproduction showed that the host's `ELECTRON_RUN_AS_NODE=1` setting forced Electron to execute as Node, making the Electron `app` API unavailable.

## QC sheet

| Gate | Evidence | Judgment |
|---|---|---|
| Package generation | `release/win-unpacked/Bunny Colony.exe` | PASS |
| Initial launch | Returned PID exited | FAIL |
| Logged reproduction | `app.setName` TypeError | FAIL |
| Environment | `ELECTRON_RUN_AS_NODE=1` | ROOT CAUSE |
| Source tests | 5/5 | PASS |
| Security audit | 0 vulnerabilities after update | PASS |
| Sanitized launch | Not yet run | HOLD |

## 5 Why / logical tree

The GUI exited because Electron APIs were unavailable; they were unavailable because the executable ran in Node mode; Node mode came from an inherited host variable; inheritance occurred because the probe did not sanitize its environment; the preflight omitted Electron-specific variables.

Source syntax, missing package files, and network access are not supported as causes.

## FMEA

| Failure mode | S | O | D | RPN | Control |
|---|---:|---:|---:|---:|---|
| Forced Node mode | 8 | 4 | 2 | 64 | Clear variable in child only |
| Global environment mutation | 8 | 3 | 4 | 96 | Prohibited |
| PID-only launch gate | 6 | 4 | 5 | 120 | Window/responding gate |
| Broad cleanup | 8 | 2 | 3 | 48 | Exact executable path |

## Approved-scope countermeasure

Use a single child shell with `ELECTRON_RUN_AS_NODE` removed, require a responsive `Bunny Colony` window after five seconds, and clean up exact test processes only. The persistent host environment must remain unchanged.

## Verification / rollback

Pass: a responsive titled window is observed. Rollback: no source rollback is needed because the fix is confined to the validation environment. If the check fails again, preserve the new failure signature and stop.
