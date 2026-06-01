# Moldflow Phase 3+ Handover (Gemini / 次エージェント向け)

**Date:** 2026-06-01  
**Epic (Beads):** `Clawdbot_Docker_20260125-kwr`  
**Canonical roadmap:** [docs/MOLDFLOW_CAe_ROADMAP.md](../MOLDFLOW_CAe_ROADMAP.md)  
**Do NOT break:** `resin_flow` (icoFoam 24/365 baseline on LAVIE)

---

## Verified baseline (do not regress)

| Phase | Category | Template | Solver | LAVIE trial |
|-------|----------|----------|--------|-------------|
| 1 | `resin_fill` | `resin_fill_v002` | `nonNewtonianIcoFoam` | `moldflow-p1-test-005` SUCCESS |
| 2 | `resin_fill_vof` | `resin_fill_v003` | `interFoam` | `moldflow-p2-vof-003` SUCCESS (~52% fill) |

Git: `2581fb29` on `backup/progressive-die-optimization-cae`

---

## OpenFOAM 2512 pitfalls (mandatory)

1. **System dicts** (`fvSchemes`, `fvSolution`, `controlDict`): FoamFile needs `arch "LSB;label=32;scalar=64"` and `location "system"`. Keep `*.ascii` backups; after `blockMesh`/`setFields` run restore loop (see `cae_te_engine.py` `_run_openfoam`).
2. **Volume fields** (`0/U`, `0/p_rgh`, `0/alpha.polymer`): use **full OpenFOAM banner**; do **not** add `arch`/`location` on fields (double-read FATAL at EOF).
3. **interFoam** `divSchemes` must include: `div(phi,alpha)`, `div(rhoPhi,U)`, `div(phirb,alpha)`, `div(((rho*nuEff)*dev2(T(grad(U)))))`.
4. **KPI** `_parse_alpha_volume_fraction`: parse `internalField` only until `boundaryField` (naive `find(')')` breaks).
5. **Docker mount (Windows):** use `/d/...` from `Path.resolve().as_posix()` (engine already fixed).

---

## Phase 3 -- Temperature + Cross-WLF (thermo + viscosity)

**Goal:** Functionality L6 in `commercial_benchmark_l10.json` (保圧・冷却の前段: 温度依存粘度).

**Suggested deliverables**

| Item | Path / ID | Notes |
|------|-----------|--------|
| Template | `resin_fill_v004/` (copy from `v003`) | New experiment `OF-FILL-004` |
| Category | `resin_fill_thermo` | Add to `EXPERIMENTS` in `scripts/cae_te_engine.py` |
| Solver | `interFoam` + `transportModel CrossPowerLaw` or dedicated thermo solver | OF2512: confirm model name in container (`foamDictionary -doc`) |
| Fields | `0/T`, `thermophysicalProperties`, `thermoType` | Couple T to viscosity |
| Params | `T_melt`, `T_mold`, `n`, `tau`, `Cross-WLF coeffs` | Inject via `_inject_parameters_openfoam` |
| KPI | `T_max`, `T_weld`, `viscosity_at_wall` | Extend `_extract_vof_fill_kpis` or new helper |
| Gate | `precheck_openfoam_interfoam_case` + thermo file checks | `cae_self_growth_gates.py` |

**Acceptance (minimal)**

- LAVIE trial SUCCESS (`End` in log, `returncode=0`).
- `fill_fraction_pct` > 10% (proxy; tune `endTime` if needed).
- `T` field written at latest time; KPI JSON artifact present.

**Commands**

```bash
python scripts/cae_te_remote_trial.py --category resin_fill_thermo --dry-run
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_thermo --node lavie --timeout 1800 --trial-id moldflow-p3-thermo-001
python scripts/k10_sync_cae_experiments_to_lavie.py
python scripts/k10_sync_lavie_scripts_to_lavie.py --build-pack
```

**Router (gitignored):** `data/workspace/cae_workload_router.yaml` -- add category under `lavie_openfoam_categories` on LAVIE manually or via sync doc.

---

## Phase 4 -- Selective turbulence

**Goal:** Runner / cooling channels only; **thin cavity fill stays laminar** (`turbulenceProperties` laminar in v003).

| Item | Notes |
|------|--------|
| Subcase flag | `use_turbulence: false` default for cavity; `true` for runner mesh variant |
| Template | `resin_fill_v004_runner/` or region-based `LES/RAS` in separate case |
| Solver | Still `interFoam`; enable `k-epsilon` / `k-omega` only in runner template |
| Risk | Do not change `resin_fill_vof` default template without feature flag |

**Acceptance:** Runner subcase runs with turbulence; cavity category unchanged and still SUCCESS on `moldflow-p2-vof-003` regression.

---

## Phase 5 -- Pack / hold pressure

| Item | Notes |
|------|--------|
| Physics | VOF + pressure hold after fill (`fvSolution` PIMPLE tuning, optional separate phase) |
| KPI | `pack_pressure_MPa`, `sink_mark_risk` calibration vs heuristic |
| Benchmark | functionality L6 "保圧・冷却" |

---

## Phase 6 -- Cool + warpage proxy

| Item | Notes |
|------|--------|
| Solver chain | `chtMultiRegionFoam` or simplified thermal stress proxy (OpenRadioss optional) |
| KPI | `warpage_mm`, `cooling_time_s` -- align with `cae_te_engine.py` defect heuristics |
| Benchmark | evaluable_items L7+ |

---

## Phase 7-10 -- CAD / factory / L10

| Phase | Deliverable |
|-------|-------------|
| 7 | STEP/STP cavity from FreeCAD -> `snappyHexMesh` or imported mesh |
| 8 | Multi-gate `resin_flow_opt` DOE integration with VOF |
| 9 | QMS / benchmark dashboard auto-update from `cae_te_log.json` |
| 10 | Factory correlation + `commercial_benchmark_l10.json` L10 sign-off |

---

## Files to read first

1. `docs/MOLDFLOW_CAe_ROADMAP.md`
2. `scripts/cae_te_engine.py` (`OF-FILL-002`, `OF-FILL-003`, `_run_openfoam`, `_extract_vof_fill_kpis`)
3. `scripts/cae_self_growth_gates.py`
4. `data/cae_te_workspace/experiments/openfoam/resin_fill_v003/`
5. `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`
6. `data/workspace/commercial_benchmark_l10.json` (product `MOLDFLOW`)

---

## If implementation fails -- return to Cursor

Bring back:

- `trial_id`, `run_dir`, last 80 lines of solver log
- `failure_tags` / `failure_evidence` from `cae_te_log.json`
- What was changed (file list)

This minimizes re-debug tokens on the next agent.

---

## Beads

- Epic: `Clawdbot_Docker_20260125-kwr` (open)
- Closed: `Clawdbot_Docker_20260125-jt8` (Phase 2)
- Create before Phase 3 work: `bd create "Moldflow Phase 3: thermo Cross-WLF" -t task -p 1 --deps discovered-from:Clawdbot_Docker_20260125-kwr`
