# INC-187 follow-up - r12 TIMEOUT hid a living OpenFOAM orphan crawl

## Scope and evidence

| Item | Fact |
|---|---|
| Trial | `lavie-mfminusx-thermo-startup-r12-20260804` |
| Ledger | `verdict=TIMEOUT`, `Exceeded 7320s`, empty `defects_detected` at 21:48 JST 2026-08-04 |
| Orphan | Docker container `great_gates` still `Up` after client timeout |
| Orphan progress | `Time≈7.83e-5` vs `endTime=0.001`, `deltaT≈2.64e-9`, `maxCo=0.002`, Clock≈20466 s |
| ETA | ~70 h to finish the 0.001 s smoke at observed rate |
| Temperature | Energy solve remained stable (no `Negative initial temperature`) |
| Accuracy | `PROXY_GAP` |

## 5 Why

1. K10 recorded TIMEOUT because the job client hit 7320 s.
2. The OpenFOAM container kept running because only the docker client was killed.
3. `cae_te_engine._run_openfoam` lacked the container-side `timeout -k` already used for OpenRadioss (T050).
4. r12 intentionally set `maxCo=0.002` / `Trelax=0.01` after r11 negative-T, which made deltaT crawl.
5. Host run-dir inspection saw only `0/` because `writeInterval=0.0001` and time had not reached the first write.

## Decision rule

IF a thermo smoke uses maxCo so small that wall-clock ETA for `endTime` exceeds the job timeout by many hours,
THEN stop the orphan, preserve the run, and launch a fresh ID with balanced Co/relaxation,
BECAUSE ledger TIMEOUT alone is not solver death and blind full-fill promotion is forbidden.

IF OpenFOAM is launched via `docker run --rm`,
THEN wrap the case command in container-side `timeout -k 30 <timeout>`,
BECAUSE subprocess timeout does not stop the solver process tree.

## Countermeasures applied (2026-08-05)

1. Stopped orphan `great_gates`; r12 run dir preserved.
2. `scripts/cae_te_engine.py`: OpenFOAM path now uses container-side `timeout -k 30`.
3. Deployed to LAVIE `/repo/scripts/cae_te_engine.py` with backup `*.inc187_pre_r14_20260805` (SHA256 verified).
4. Fresh startup `lavie-mfminusx-thermo-startup-r14-20260805` with `maxCo=0.01`, `maxAlphaCo=0.02`, `deltaT0=5e-7`, `Trelax=0.05`.
5. Autopromote monitor `scripts/inc187_r14_autopromote_monitor.py` -> r15 full fill only on SUCCESS + time/T gates.

## Verification

- Deploy result: `DEPLOY_OK` / SHA256 `d48feaeed3609d09bd5be6f93eaf69e5e50040e8bd7706b66d46fe5910996dd9`
- Monitor state file: `data/state/lavie_mf_pipeline_monitor/inc187_r14_autopromote_status.json`
- r14/r15 remain `PROXY_GAP`; no Moldflow-equivalence claim

## r14 follow-up (2026-08-05)

| Item | Fact |
|---|---|
| r14 | `FAILED` / `Negative initial temperature T0: -0.00429575` after 4584 s |
| Agent gap | Monitor wrote terminal state at 02:52; agent did not observe until user asked at 05:37 |
| Process fix | `scripts/inc187_terminal_state_watchdog.py` + Telegram on terminal ledger/monitor states |
| Gate fix | `thermal_startup_smoke` keeps End+bounded-T SUCCESS from being failed solely for `fill_pct<50` |
| Next | staged `r16` (1e-4) -> `r17` (0.001) -> `r18` full fill; engine SHA `bb5d9e0f...` |
