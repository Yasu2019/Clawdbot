# INC-153 RCA: Bunny Colony npm install timeout

## Scope and observed facts

- Goal: install locked desktop-build dependencies for `games/bunny-colony`.
- Host: Windows, Node v22.13.1, npm 10.9.2.
- Command: `npm install`, bounded to 120 seconds.
- Result: command timeout; generated npm process PID 73520 remained alive.
- Registry: `https://registry.npmjs.org/`; PONG after 15.897 seconds.
- Cache: valid, 1,025 entries and approximately 252 MB verified.
- Output state: partial `node_modules`; no `package-lock.json`.
- Existing Node processes for Telegram and ByteRover were identified and protected.

## 5 Whys

1. Why did the build gate fail? The dependency install did not return within 120 seconds.
2. Why was it slow? Electron and electron-builder require many packages and a desktop runtime binary.
3. Why did the fixed bound prove insufficient? Registry round-trip latency was approximately 15.9 seconds.
4. Why was no useful intermediate status available? The initial npm call was a single foreground command without verbose progress capture.
5. Why was this not predicted? Preflight verified runtime versions but not registry latency or local cache coverage.

## Fishbone

| Branch | Contributing factor |
|---|---|
| Network | High npm registry latency |
| Package | Large Electron binary/dependency graph |
| Method | Fixed 120-second ceiling without staged acquisition |
| Monitoring | Shell timeout left a child process running |
| Machine | Cache was healthy; no evidence of disk/cache corruption |
| Code | Game source and rule logic were not involved |

## Fault tree

`Windows package unavailable`

- OR: dependencies unavailable
  - install times out
    - registry latency is high
    - dependency graph is large
- OR: packaging fails after install
  - not yet tested

Only the first path is proven.

## FMEA

| Failure mode | Effect | S | O | D | RPN | Control |
|---|---|---:|---:|---:|---:|---|
| Dependency timeout | No Windows artifact | 6 | 5 | 2 | 60 | Latency preflight and bounded retry |
| Orphan npm process | Resource waste/file contention | 5 | 4 | 5 | 100 | Inspect command line and terminate exact PID |
| Repeated unlimited retries | Wasted time/network | 5 | 3 | 3 | 45 | One controlled retry, then fallback |
| Killing unrelated Node process | Service interruption | 8 | 2 | 3 | 48 | PID plus command-line identity gate |

## Countermeasure plan requiring confirmation

1. Remove only the incomplete `games/bunny-colony/node_modules` directory.
2. Retry once with explicit `--fetch-retries=2`, `--fetch-timeout=120000`, foreground progress, and a monitored 10-minute ceiling.
3. If it succeeds, run unit tests and Windows packaging.
4. If it fails, retain the fully playable browser build and generate a dependency-free ZIP; do not loop.
5. Record exact test/build evidence and update this incident.

## Verification criteria

- No orphan `npm install` process.
- `package-lock.json` exists.
- All Node rule tests pass.
- Windows artifact exists and launches, or fallback ZIP is explicitly labeled browser-only.

## Rollback

Remove the new `games/bunny-colony` directory. Existing systems remain unchanged. The pre-change repository state is on `backup/pre-bunny-colony-20260724-041457`.

## Web-search decision

A global web search was not useful at this stage because there was no npm error code or unknown failure signature. Direct registry latency, cache verification, and exact process evidence were enough to define the smallest next experiment.
