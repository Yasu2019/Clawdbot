# Bunny Colony INC-156 - Host pagefile exhaustion

## Summary

After the Bunny Colony portable Windows build completed, a read-only artifact/tool inspection failed with Windows HRESULT `0x800705AF`: the pagefile was too small. Further CIM inspection could not start a thread. A lightweight process inventory confirmed extreme host memory pressure from existing WSL, editor, terminal, and development workloads.

## QC process sheet

| Gate | Result | Judgment |
|---|---|---|
| Portable build | electron-builder exited 0 | PASS |
| Gameplay tests | 5/5 | PASS |
| Dependency audit | 0 | PASS |
| Unpacked GUI launch | Responsive titled window | PASS |
| Artifact inspection | PowerShell `0x800705AF` | FAIL |
| Final SHA-256 | Not completed | HOLD |
| Dedicated game icon | Not completed | HOLD |

## 5 Why / FTA

PowerShell failed because Windows could not allocate commit/thread resources. Commit pressure came from several unrelated multi-gigabyte workloads. Those workloads are not game processes and are protected from automatic termination. The game build itself had already completed, so application source and packaging are not the root cause.

Top-event branches:

- application build failure: ruled out;
- test-process leak: ruled out;
- host virtual-memory exhaustion: confirmed;
- artifact integrity: not yet verified.

## FMEA

| Mode | S | O | D | RPN | Control |
|---|---:|---:|---:|---:|---|
| Pagefile exhaustion | 8 | 5 | 3 | 120 | Commit-headroom preflight |
| Unauthorized WSL/Docker stop | 10 | 3 | 4 | 120 | User approval gate |
| Heavy retry | 7 | 4 | 3 | 84 | Hold |
| Missing final hash | 6 | 4 | 5 | 120 | Pending-release label |

## Recovery plan

The user frees memory or authorizes an exact bounded target. Then perform only lightweight headroom confirmation, icon conversion and one rebuild if feasible, final SHA-256, portable launch, and repository closeout.

## Protected systems

Do not modify the pagefile, Docker configuration, docker-compose files, WSL state, editors, or unrelated services without explicit authorization.
