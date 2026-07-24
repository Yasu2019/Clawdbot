# Bunny Colony INC-153 - npm install timeout

## Incident summary

On 2026-07-24 JST, the first bounded dependency installation for the new Steam-targeted Bunny Colony game exceeded 120 seconds. The npm child process continued after the shell timeout and was terminated by exact PID and command-line identity. Existing Node services were not touched.

## QC process sheet

| Process | Input | Control | Result | Judgment |
|---|---|---|---|---|
| Runtime preflight | Node/npm | Version check | v22.13.1 / 10.9.2 | PASS |
| Dependency acquisition | package.json | 120 s bound | Timeout | FAIL |
| Residual-process check | Windows process table | PID + command line | npm PID 73520 found | DETECTED |
| Containment | PID 73520 | Exact process only | Terminated | PASS |
| Registry check | npm registry | 15 s fetch setting | PONG 15.897 s | SLOW |
| Cache check | npm cache | Integrity verification | 1,025 valid entries | PASS |
| Unit test | source rules | Node test runner | Not yet run | HOLD |
| Windows packaging | Electron builder | Artifact gate | Not yet run | HOLD |

## 5 Why

1. Installation failed because it exceeded the 120-second harness bound.
2. It exceeded the bound because Electron desktop packaging has a large acquisition graph.
3. Acquisition was slow because direct registry latency measured approximately 15.9 seconds.
4. The job did not expose actionable staged progress because install and runtime download were combined.
5. The preflight omitted a registry-latency measurement before choosing the timeout.

## Fishbone / logical tree

- Network: registry reachable but slow.
- Package: Electron binary and electron-builder increase download size.
- Method: one fixed timeout; no staged acquisition.
- Monitoring: Windows child survived parent tool timeout.
- Machine: cache integrity passed, so corruption is not supported.
- Source: gameplay source is not implicated.

## FTA

Top event: no Steam-ready Windows artifact.

- Dependency gate fails
  - registry is unreachable (ruled out)
  - registry is slow (confirmed)
  - cache is corrupt (ruled out)
  - dependency graph exceeds bound (supported)
- Packaging gate fails
  - not tested; must not be claimed

## FMEA

| Mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Timeout | Packaging blocked | 6 | 5 | 2 | 60 | One latency-informed bounded retry |
| Orphan child | Resource/file contention | 5 | 4 | 5 | 100 | Exact PID cleanup after timeout |
| Retry loop | Time/network waste | 5 | 3 | 3 | 45 | One retry maximum, then fallback |
| Wrong-process termination | Existing service outage | 8 | 2 | 3 | 48 | Verify command line before stop |

## Countermeasures

1. Clean only the incomplete game-local `node_modules`.
2. Use explicit npm retry/fetch settings with a monitored 10-minute ceiling.
3. Run tests before packaging.
4. Fall back to a browser ZIP if the single retry fails.
5. Preserve the original ZIPs and all existing services.

## Verification and rollback

Pass requires a lockfile, passing rule tests, and a generated Windows artifact. Rollback is deletion of `games/bunny-colony`; the pre-change HEAD is preserved on `backup/pre-bunny-colony-20260724-041457`.

## Scope limit

No packaging defect, gameplay defect, or npm registry outage is proven. Only slow acquisition and insufficient initial timeout are proven.
