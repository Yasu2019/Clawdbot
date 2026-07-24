# Bunny Colony INC-154 - Desktop dependency audit

## Summary

The first complete lockfile passed gameplay tests but failed the full npm security audit with 9 high and 1 critical finding. Packaging stopped. Production npm dependencies are empty and the production-only audit is clean, but Electron itself becomes the distributed runtime and therefore must be updated.

## QC process sheet

| Gate | Result | Judgment |
|---|---|---|
| Install | 383 packages, lockfile generated | PASS |
| Game rule tests | 5/5 | PASS |
| Full audit | 9 high, 1 critical | FAIL |
| Production-only audit | 0 | PASS |
| Production dependency tree | Empty | PASS |
| Windows packaging | Not run | HOLD |

## 5 Why / Fishbone

The manifest pinned an older Electron line and early electron-builder 26 release before advisory resolution. Their transitive build graph contains affected tar/cache/rebuild packages. The process cause was version selection before a lockfile security gate; the detection control worked as intended. There is no evidence that gameplay code caused the findings.

## FTA

- Shipped exposure
  - npm runtime dependency: ruled out.
  - embedded Electron runtime: possible; update required.
- Build-machine exposure
  - electron-builder graph: confirmed; update required.
- Published vulnerable build
  - prevented because packaging did not start.

## FMEA and countermeasure

| Mode | S | O | D | RPN | Action |
|---|---:|---:|---:|---:|---|
| Old Electron shipped | 8 | 4 | 2 | 64 | Pin 43.2.0 |
| Old builder graph | 6 | 4 | 2 | 48 | Pin 26.15.3 |
| Forced automatic rewrite | 6 | 3 | 4 | 72 | Prohibit `audit fix --force` |
| Dev/prod confusion | 8 | 3 | 5 | 120 | Preserve both audit results |

The proposed change is limited to the two direct dev dependency pins, followed by install, full audit, tests, package build, and launch verification.

## Rollback / scope limits

Revert the two pins and lockfile or remove the isolated game directory. Electron 43 compatibility is not yet proven. No claim of Steam-readiness is allowed until packaging and launch verification pass.
