# INC-156 RCA: Host pagefile exhaustion during artifact inspection

## Facts

- Portable Windows build completed successfully before the incident.
- The next read-only PowerShell command terminated with `0x800705AF`.
- A following CIM query failed with `Thread failed to start`.
- `tasklist` remained available and showed:
  - `vmmemWSL`: approximately 9.5 GB.
  - Memory Compression: approximately 4.0 GB.
  - one `Code.exe`: approximately 3.3 GB.
  - Windows Terminal: approximately 2.0 GB.
  - many WSL, editor, Python, and agent processes.
- No Bunny Colony/Electron process remained from the launch test.
- Existing Docker/WSL/editor processes are outside the authorized cleanup scope.

## 5 Whys

1. Artifact inspection failed because PowerShell could not allocate required memory/thread state.
2. Allocation failed because Windows virtual-memory/pagefile commit was exhausted.
3. Commit was exhausted because several unrelated long-lived workloads consumed many gigabytes concurrently.
4. They were not stopped because they are existing user services and protected infrastructure.
5. The game build preflight did not include a free-commit-memory threshold.

## FTA / Fishbone

Top event: final release QA cannot continue.

- Game build failure: ruled out; build exited 0.
- Game process leak: ruled out; test processes were cleaned.
- Host resource exhaustion: confirmed by HRESULT, thread-start failure, and process inventory.
- Disk artifact loss: not observed.

Branches: machine/resource capacity (confirmed), existing workloads (confirmed), game source/network/security (not implicated).

## FMEA

| Failure mode | Effect | S | O | D | RPN | Countermeasure |
|---|---|---:|---:|---:|---:|---|
| Commit/pagefile exhaustion | Shell and QA failure | 8 | 5 | 3 | 120 | Free-memory preflight |
| Agent stops WSL/Docker | Production/service interruption | 10 | 3 | 4 | 120 | Explicit authorization required |
| Rebuild under pressure | Repeated failure/corruption risk | 7 | 4 | 3 | 84 | Hold all heavy work |
| Claim release complete without hash | Traceability gap | 6 | 4 | 5 | 120 | Keep release status pending |

## Countermeasure plan requiring user direction

1. User closes unneeded high-memory editor/WSL workloads, or names an exact process/service that may be stopped.
2. Confirm virtual-memory headroom using a lightweight check.
3. Detect a local SVG-to-ICO tool; if available, add a dedicated icon and rebuild once.
4. Compute SHA-256 and verify portable launch.
5. Complete documentation, commit, and push.

## Rollback and scope

Do not change the Windows pagefile, Docker configuration, WSL state, or user applications automatically. The existing portable artifact remains under `games/bunny-colony/release/` and the source remains isolated.

## External-search decision

Web search is unnecessary: Windows supplied the exact resource error, and the process inventory directly demonstrates host pressure. The recovery is local resource release, not a software workaround.
