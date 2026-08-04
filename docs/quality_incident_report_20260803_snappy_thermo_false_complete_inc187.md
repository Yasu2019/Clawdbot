# INC-187 - snappy thermo case omitted physics files and waiter reported false completion

## Scope and evidence

| Item | Fact |
|---|---|
| Detected | 2026-08-03 18:54 JST, trial `lavie-mfminusx-thermo-fill-20260803` |
| Solver evidence | OpenFOAM v2512: `cannot find file "/workspace/constant/thermophysicalProperties"` |
| Result | verdict `FAILED`, return code 1, fill 0.01%, duration 99.87 s |
| Reporting defect | dispatch process returned 0 and the waiter wrote `submitted_or_completed`; monitor then displayed `thermo_fill_completed` |
| Accuracy | `PROXY_GAP`; no Moldflow equivalence claim |

## 5 Why

1. The thermal solver stopped because `constant/thermophysicalProperties` was absent.
2. It was absent because the snappy builder always copied the non-thermal MFALIGN template.
3. `physics_category=resin_fill_cool` selected the solver but did not overlay its thermal dictionaries and initial fields.
4. The generated-case contract was not tested for the combination `snappyhexmesh + resin_fill_cool`.
5. The failure appeared complete because the waiter trusted the dispatcher process code instead of `trial_entry.verdict`.

## FTA / fishbone summary

- Case generation: physics category and mesh template selection were coupled incorrectly.
- Validation: fixture coverage omitted the thermo/snappy combination; deployed LAVIE code did not enforce the current post-generation gate.
- Observation: worker transport success and CAE calculation success were represented by one return code.
- Operations: monitor mapped an ambiguous state name directly to completion.

## FMEA

| Failure mode | Effect | Existing detection | Countermeasure |
|---|---|---|---|
| Missing thermal dictionary | Solver stops before time step 1 | OpenFOAM fatal log | Overlay required thermo files; fail closed if source is incomplete |
| Wrong boundary schema | Field read failure or invalid physics | Generated-file test | Generate `T` and `p` with MFALIGN `gate/vent/moldflow` patches |
| False completion | Cooling restart may start from invalid fill | Manual log inspection | Parse `trial_entry.verdict`; only SUCCESS/DRY_RUN is completion |
| Stale remote code | Local test passes but LAVIE repeats defect | Hash/version comparison | Verify deployed file hashes before retry |

## Correction and prevention

- `scripts/moldflow_step_case_builder.py`: for `resin_fill_cool` and
  `resin_fill_thermo`, overlay the three thermophysical dictionaries, thermal
  solver dictionaries, and MFALIGN-compatible `0/T` and `0/p`.
- `scripts/k10_lavie_wait_dispatch_inc187_thermo.py`: decode the JSON result and
  treat any verdict other than SUCCESS/DRY_RUN as failure.
- Tests cover thermal overlay, non-thermal non-regression, and transport-success /
  CAE-failure separation.
- Retry attempt 1 exposed a second transport edge: a busy response also carries
  nested verdict `ERROR`. The waiter now classifies `worker_busy` before verdict
  failure, so normal contention remains a bounded wait rather than a false job
  failure. No solver was started by that attempt.
- Retry must use a new trial ID and may start only after deployed hashes and the
  generated-case contract pass. The failed run directory remains evidence.

## Verification

- `python -m unittest scripts.test_moldflow_snappy_thermo_overlay scripts.test_k10_lavie_wait_dispatch_inc187_thermo scripts.test_cae_worker_contract -v`: 9/9 PASS.
- `python -m py_compile ...`: PASS.
- Real LAVIE rerun and Moldflow KPI comparison remain pending; therefore this is
  a code-path correction, not solver validation.

## Decision rule

IF mesh mode is snappy and physics is thermal, THEN require all thermal
dictionaries plus `T/p` fields in the final generated case and verify the remote
hash before dispatch, BECAUSE solver selection alone does not populate physics
files. IF dispatcher transport succeeds, THEN still read the CAE verdict,
BECAUSE process return code 0 only proves that the response was collected.

## Web knowledge decision

No web search was used. The exact missing path, local template contents, and
branch logic reproduce the fault deterministically; public sources cannot reveal
this private deployment mismatch.

## Rollback and next experiment

- Backup: remote branch `backup/inc187-before-thermo-overlay-20260803`, commit
  `49e1b837fd`.
- Rollback: restore the four INC-187 code/test files from that backup; do not
  delete the failed run.
- Next: deploy verified code, generate a fresh `r2` case, run thermo fill, require
  nonzero time advancement and valid temperature/phase/pressure fields, then
  build the closed-gate cooling restart.

## r2 follow-up and r3 recovery

- r2 acquired the worker at 21:29 JST but failed closed before solver launch:
  the LAVIE repo did not contain the `resin_fill_v007` thermo source template.
- Before r3, all nine required source files were copied to LAVIE through temporary
  names, SHA-256 verified, and atomically promoted; any pre-existing target was
  preserved as `*.inc187_pre_r3_20260803`.
- r3 uses the new ID `lavie-mfminusx-thermo-fill-r3-20260803`. Its bounded waiter
  started at 23:26 JST and correctly reports `waiting_worker_busy`; it does not
  stop or supersede tri-track.

## Overnight continuation: r3 to r4

- r3 acquired the worker at 00:02 JST and failed closed before solver launch.
  The files had been synchronized to `C:/lavie_usb_pack/data/...`, while the
  worker exports `CAE_TE_WORKSPACE=/e/clawstack_satellite/data/work/...`.
- The same nine files were therefore synchronized to the E: workspace with
  temporary downloads, SHA-256 checks, and recoverable
  `*.inc187_pre_r4_20260804` backups.
- A fresh ID `lavie-mfminusx-thermo-fill-r4-20260804` was started at 00:08 JST.
  Its waiter PID is 21996, retry interval 30 s, maximum 900 attempts (7.5 h).
- System sleep is inhibited, without forcing the display on, until 06:00 JST by
  `scripts/keep_awake_until_0600_inc187.ps1`. PID 42320 and a one-minute status
  heartbeat verify the guard. The first guard start exposed signed hexadecimal
  conversion in PowerShell; explicit UInt32 decimal flags corrected it before
  the active guard was established.

## r5-r8 recovery and first real execution

- The actual worker environment was proven inside `lavie-sjp-worker-c` as
  `CAE_TE_WORKSPACE=/c/clawstack_satellite/data/work/cae_te_workspace`.
  r5 synchronized and verified the nine thermo files there, then exposed a stale
  `cae_self_growth_gates.py`; that module was backed up and hash-verified after sync.
- r6 passed case generation/precheck and reached OpenFOAM, which rejected
  `writeControl timeStep` with fractional `writeInterval=0.05`.
- The builder now updates both `controlDict` and `controlDict.ascii`, selects
  `adjustableRunTime`, and has a regression test. r7 then exposed that the source
  `endTime` is a placeholder rather than numeric; replacement now accepts either
  form and remains semicolon-bounded.
- Ten regression/contract tests pass. r8
  `lavie-mfminusx-thermo-fill-r8-20260804` was accepted at 12:01 JST and launched
  OpenFOAM container `jovial_bassi`. Initial evidence shows active snappy mesh
  generation; solver time advancement and KPI validation remain pending.
