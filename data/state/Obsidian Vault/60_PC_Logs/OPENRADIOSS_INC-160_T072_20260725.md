# INC-160 / T072 - OpenRadioss 4mm x 4mm ASSY 成功

## Goal / Context

- Goal: `OpenRadioss Lab` の4mm x 4mm打抜き解析を、履歴上の化粧SUCCESSではなく新規実行・物理ゲート・形状KPI付きで成功させる。
- Host: K10 fallback（Red LAVIE workerが隠れキューでbusy）。
- Solver: `clawstack-unified-openradioss:latest`
- Trial: `k10-press_blanking_assy-4mmx4mm-20260725-1221`
- Geometry: Punch / Die / Stripper / Material、TYPE25、workpiece thickness 0.5mm。
- Conditions: clearance 8%t、punch speed 5000mm/s、friction 0.10、`DT/NODA=8e-9s`、`t_stop=0.56ms`。

## Confirmed facts

| KPI | Result | Gate |
|---|---:|---:|
| Termination | NORMAL_TSTOP | PASS |
| Cycles | 70,000 | complete |
| Final time | 0.560ms | >=0.532ms |
| Velocity hard errors | 0 | PASS |
| Velocity warnings | 27 | <=40 |
| Negative volume | 0 | PASS |
| Actual deleted elements | 0 | <=8,000 |
| First material failure | 0.49868ms | expected cutting onset |
| Stable-window ERR | -0.7% | >-85% |
| Stable-window DM/M | 5.509% | evidence |
| Final DM/M | 8.856% | <10% |
| VTK | 3 files | PASS |
| Geometry KPI | PART_ID=1; theta1=90.0deg, theta2=145.0975deg | extracted |
| Corrected verdict | SUCCESS | PASS |

Raw run directory:
`data/cae_te_workspace/runs/k10-press_blanking_assy-4mmx4mm-20260725-1221`

## 5 Why

1. Why was a completed run shown as FAILED? Four meaning-gate reasons were computed from normal warning/header/fracture text.
2. Why were warnings errors? Matching used broad substring pairs instead of exact line semantics.
3. Why did energy fail? The 90%-of-final-time sample fell after topology-changing fracture.
4. Why did mesh instability fail? `FAILURE START` Gauss-point events were treated as deleted elements even though actual deleted count was zero.
5. Why was offline proof missing? The parser handled `NC=...` stdout but not the persisted cycle-table `.out` format.

## Fault tree / Fishbone

`false FAILED`

- Text classification
  - `MAY BE TOO HIGH` -> velocity hard error
  - `TIME-STEP` heading -> time-step error
- Physical-window selection
  - fracture starts at 0.49868ms
  - 90% sample at 0.504ms is already post-fracture
- Quantity semantics
  - failure initiation count != deleted-element count
- Data format
  - stdout format supported
  - saved cycle-table unsupported
- Dispatch
  - blocking lock silently queued HTTP requests

## FMEA

| Failure mode | S | O | D | RPN | Countermeasure |
|---|---:|---:|---:|---:|---|
| warning promoted to hard error | 8 | 8 | 4 | 256 | exact phrase / line scope |
| post-fracture ERR used | 8 | 10 | 4 | 320 | 99% of first-failure time |
| failure initiation treated as deletion | 8 | 9 | 5 | 360 | separate counters |
| hidden worker queue | 7 | 7 | 6 | 294 | immediate HTTP 409 busy |
| cycle-table not parsed | 7 | 8 | 5 | 280 | fallback parser + test |

## Corrective actions

1. `cae_self_growth_gates.py`
   - Parse persisted cycle-table output.
   - Match only `NODAL VELOCITY IS TOO HIGH` as hard failure.
   - Match time-step errors by explicit warning/error wording.
   - Evaluate ERR/DM/M in a stable window at or before 99% of first failure time.
2. `cae_te_engine.py`
   - Do not map `FAILURE START` count to actual deleted elements for ASSY blanking.
3. `lavie_job_worker.py`
   - Reject concurrent work immediately with HTTP 409 `worker_busy`.
4. UI status
   - Publish the verified SUCCESS evidence to `red_lavie_urgent_assy_run.json`.

## QC process / verification

1. Precheck deck and parameter application.
2. Monitor cycle, time-step, ERR, DM/M, velocity and negative volume.
3. Require NORMAL_TSTOP and final-time completion.
4. Convert animations to VTK.
5. Extract geometry KPI from PART_ID=1.
6. Re-assess saved raw `.out` with corrected gates.
7. Regression tests: 5/5 PASS.
8. API `/api/status` returns urgent verdict `SUCCESS`; portal page returns HTTP 200.

## Decision rule

IF a cutting analysis crosses the first material-failure event, THEN evaluate forming energy inside a buffered pre-failure window and preserve final DM/M as a separate boundedness gate, BECAUSE post-fracture topology changes invalidate direct comparison of the ERR column with intact-forming energy.

IF failure initiation is observed without an explicit deleted-element total, THEN record initiation as a material-response KPI and do not invent a deletion count.

## Recovery / rollback

- Backup branch: `backup/openradioss-4mm-pre-fix-20260725`
- Backup commit: `dc05788255`
- Do not delete the raw run directory; it is the reproducible evidence source.

## Scope limits / next experiment

- Geometry theta values are solver-derived, but shear/fracture percentages remain model estimates. Do not claim commercial-tool equivalence.
- Next smallest experiment: run the same fixed conditions once on Red LAVIE after deploying the non-queueing worker and compare termination, DM/M, and VTK KPI for cross-host reproducibility.

## Provenance

- Date: 2026-07-25 JST
- Incident: INC-160
- Trouble history: T072
- Success case: S018
- Beads: `Clawdbot_Docker_20260125-de46`
