---
incident: INC-187
date: 2026-08-04
machine: LAVIE
status: r11_running
accuracy: PROXY_GAP
beads: Clawdbot_Docker_20260125-270e
---

# INC-187 r8-r11 thermal recovery

## Confirmed facts

| Trial | Result | Evidence |
|---|---|---|
| r8 | FAILED | Initial T was 313.15-516.78 K; first energy solve produced `T0=-27.905 K` |
| r9 | PREGATE_FAIL | Missing generated guard exposed wrong runtime import-path deployment |
| r10 | FAILED | `limitTemperature` called unimplemented `twoPhaseMixtureThermo::he()` |
| r11 | RUNNING | Fresh ID; T relaxation and reduced time-step controls |

## 5 Why / FTA

1. r8 aborted because energy-to-temperature inversion received a negative guess.
2. The guess became negative after the first energy solve, not in the initial field.
3. A general temperature limiter was selected as the first numerical guard.
4. That option depends on `he()`, which v2512 two-phase mixture thermo does not implement.
5. Compatibility had been inferred from option availability instead of a solver-class execution test.

FTA branches: initialization was ruled out by bounded fields; deployment mismatch
was detected by r9 fail-closed behavior; r10 proved the limiter/thermo-class
incompatibility. The remaining main branch is first-step equation overshoot.

## FMEA and countermeasures

| Failure mode | Effect | Detection | Countermeasure |
|---|---|---|---|
| Energy overshoot | Negative T guess and abort | Fatal log plus bounded initial fields | T equation relaxation 0.1; initial deltaT 1e-6 s |
| Incompatible fvOption | Abort before time advancement | `he(): Not implemented` | Prohibit `limitTemperature` for this thermo stack |
| Wrong deployed import path | Local/remote behavior mismatch | Generated-case pregate | Probe `module.__file__`; deploy and hash `/repo/scripts` |
| False promotion | Dashboard overstates maturity | KPI gate | Keep PROXY_GAP until time, bounds, completion and MF comparison pass |

## QC process

1. Back up each deployed runtime file.
2. Verify SHA-256 against K10 source.
3. Use a fresh trial ID; never overwrite a failed evidence directory.
4. Require pregate success.
5. Require solver time greater than zero and bounded temperature fields.
6. Record limiter/relaxation use and do not claim Moldflow equivalence.

## Verification and rollback

Eleven focused unit/contract tests and Python compilation pass. r11 parameters:
maxCo 0.02, maxAlphaCo 0.05, initial deltaT 1e-6 s, T relaxation 0.1.
Rollback uses the `*.inc187_pre_r11_20260804_1720` files in `/repo/scripts`.
Failed r8-r10 run directories are evidence and must not be removed.

## Decision rule and next experiment

IF an fvOption requires a thermo accessor not implemented by the selected
two-phase thermo class, THEN do not use that option; stabilize the equation and
time step instead. r11 is the smallest experiment. Pass requires nonzero time
advance and temperatures inside declared physical bounds. A later MF KPI match
is still required for any maturity promotion.
