# Moldflow-Class CAE Roadmap (OpenFOAM on LAVIE Fleet)

**Epic (Beads):** `Clawdbot_Docker_20260125-kwr`  
**Status:** Phase 2 verified (2026-06-01) -- LAVIE `moldflow-p2-vof-003` SUCCESS (`fill_fraction_pct` ~52%)  
**Canonical benchmark:** `data/workspace/commercial_benchmark_l10.json` -> product `MOLDFLOW`  
**Gemini / 次エージェント引き継ぎ:** [docs/handovers/moldflow_phase3plus_gemini_handover_20260601.md](handovers/moldflow_phase3plus_gemini_handover_20260601.md)

## Goal

Move from **Newtonian `icoFoam` proxy** (`resin_flow_v001`) toward **Moldflow-like fill physics**:

1. Non-Newtonian viscosity (Power Law -> Cross-WLF) -- Phase 1 done, Phase 3 adds temperature
2. Fill front (VOF / `interFoam`) -- Phase 2 done
3. Selective turbulence (runner/cooling, not thin cavity) -- Phase 4
4. Pack / cool / warpage (Phase 5-6+)

## Current stack (parallel)

| Category | Experiment | Solver | Physics | Status |
|----------|------------|--------|---------|--------|
| `resin_flow` | OF-FLOW-001 | `icoFoam` | Laminar Newtonian baseline (24/365) | production |
| `resin_fill` | OF-FILL-002 | `nonNewtonianIcoFoam` | Power-law non-Newtonian | Phase 1 OK |
| `resin_fill_vof` | OF-FILL-003 | `interFoam` | VOF polymer/air fill front | Phase 2 OK |

Templates:

- `data/cae_te_workspace/experiments/openfoam/resin_fill_v002/`
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v003/`

Router (LAVIE local, gitignored): `data/workspace/cae_workload_router.yaml` -> `lavie_openfoam_categories`

## Phase summary

| Phase | Deliverable | Benchmark (functionality) | Status |
|-------|-------------|---------------------------|--------|
| **0** | Categories + engine hooks + this doc | L2 | done |
| **1** | Power Law + `nonNewtonianIcoFoam` | L3-L4 non-Newtonian | **verified LAVIE** |
| **2** | `interFoam` VOF + fill % / time KPI | L5 VOF充填 | **verified K10+LAVIE** |
| **3** | Temperature + WLF viscosity proxy on VOF | L5-L6 | **verified K10** (3b semi-coupled) |
| **4** | Turbulence RAS k-omega SST (`resin_fill_turb` / v005) | L5 | **verified K10** (`local-p4-turb-003`) |
| **5** | Pack / hold pressure | L6 保圧 | planned |
| **6** | Cool + warpage proxy | L6-L7 冷却・収縮 | planned |
| **7** | STEP cavity mesh (`snappyHexMesh`) | model_size L4+ | planned |
| **8** | Multi-gate DOE + VOF | functionality L8 | planned |
| **9** | Benchmark dashboard / QMS hooks | operability L8+ | planned |
| **10** | Factory correlation, L10 sign-off | L10 | planned |

---

## Phase 3 -- Temperature + Cross-WLF (next)

**Intent:** Viscosity depends on temperature and shear rate (Moldflow-class), without breaking Phase 2 VOF.

| Work item | Detail |
|-----------|--------|
| Template | `resin_fill_v004/` (from `v003`) |
| Experiment | `OF-FILL-004`, category `resin_fill_thermo` (name TBD) |
| Solver | `interFoam` + thermal transport; `transportModel` CrossPowerLaw / Cross-WLF coeffs in `transportProperties` |
| New files | `0/T`, `constant/thermophysicalProperties` (or OF2512 equivalent) |
| Engine | `cae_te_engine.py` experiment block, injection keys, KPI (`T_max`, etc.) |
| Gates | Extend `precheck_openfoam_interfoam_case` |
| Regression | Re-run `resin_fill_vof` trial `moldflow-p2-vof-003` after changes |

**OpenFOAM 2512:** Reuse Phase 2 header rules (see handover doc). Run `foamDictionary` inside `opencfd/openfoam-dev:latest` to confirm model keyword names.

**Trial command:**

```bash
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_thermo --node lavie --timeout 1800 --trial-id moldflow-p3-thermo-001
```

---

## Phase 4 -- Selective turbulence

| Work item | Detail |
|-----------|--------|
| Scope | Runner / cooling line meshes only |
| Default | Cavity `resin_fill_vof` stays **laminar** (`turbulenceProperties`) |
| Implementation | Separate template or `param: use_turbulence` feature flag |
| Solver | `interFoam` + `k-omega SST` (or RAS) on runner subcase only |

**Acceptance:** Runner subcase completes; cavity regression still SUCCESS.

---

## Phase 5 -- Pack / hold pressure

| Work item | Detail |
|-----------|--------|
| Physics | Hold pressure after fill front stalls; PIMPLE / phase fraction BC updates |
| KPI | `pack_pressure_MPa`, update `short_shot_risk` from field data |
| Benchmark | functionality L6 "保圧・冷却" (pack portion) |

---

## Phase 6 -- Cool + warpage

| Work item | Detail |
|-----------|--------|
| Physics | Thermal shrinkage proxy; optional OpenRadioss structural path |
| KPI | `warpage_mm`, `cooling_time_s` (replace pure heuristics where possible) |
| Benchmark | evaluable_items L7 "冷却歪み" |

---

## Phase 7-10 -- CAD, DOE, operations, L10

| Phase | Focus |
|-------|--------|
| **7** | FreeCAD/STEP -> cavity mesh; move off `blockMesh` box |
| **8** | Integrate `resin_flow_opt` DOE with VOF categories |
| **9** | Auto-update `commercial_benchmark_l10.json` from `cae_te_log.json` |
| **10** | Measured correlation; Moldflow L10 criteria |

---

## Commands (Phase 1-2)

```bash
# Dry-run (parameter injection only)
python scripts/cae_te_remote_trial.py --category resin_fill --dry-run
python scripts/cae_te_remote_trial.py --category resin_fill_vof --dry-run

# LAVIE dispatch
python scripts/k10_satellite_cae_dispatch.py --category resin_fill --node lavie --timeout 600
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_vof --node lavie --timeout 1200

# Sync to LAVIE after template/engine change
python scripts/k10_sync_cae_experiments_to_lavie.py
python scripts/k10_sync_lavie_scripts_to_lavie.py --build-pack

# ParaView (LAVIE only; image on satellite)
python scripts/cae_te_paraview_capture.py --trial-id moldflow-p2-vof-003 --send-telegram
```

## Parameters (OF-FILL-002)

| Param | Meaning |
|-------|---------|
| `power_law_nu0` | Consistency scale [m2/s] |
| `power_law_k` | Power-law coefficient |
| `power_law_n` | Flow index (<1 shear-thinning) |
| `inlet_velocity` | Gate speed [m/s] |
| `gate_position` | `left` / `center` / `right` |

## Parameters (OF-FILL-003)

| Param | Meaning |
|-------|---------|
| `polymer_nu` | Polymer kinematic viscosity [m2/s] |
| `inlet_velocity` | Gate speed [m/s] |
| `gate_position` | `left` / `center` / `right` |

## Parameters (Phase 3+ -- draft)

| Param | Phase | Meaning |
|-------|-------|---------|
| `T_melt` | 3 | Melt temperature [K] |
| `T_mold` | 3 | Mold wall temperature [K] |
| `cross_wlf_*` | 3 | Cross-WLF coefficients (see Moldflow material cards) |
| `use_turbulence` | 4 | Enable RAS only on runner subcase |
| `pack_pressure_MPa` | 5 | Hold pressure setpoint |
| `cooling_time_s` | 6 | Cooling phase duration |

## Protected / do not break

- `resin_flow` / `resin_flow_v001` -- 24/365 LAVIE baseline
- Phase 2 template without feature flag when adding Phase 3 files
- `docker-compose.yml` ports -- check before new services (PROMISES T008)

## References

- Handover: `docs/handovers/moldflow_phase3plus_gemini_handover_20260601.md`
- `scripts/inject_cae_know_how.py`
- `clawstack_v2/docs/knowledge/Moldflow_Knowledge.md`
- `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`
- Engine: `scripts/cae_te_engine.py`, gates: `scripts/cae_self_growth_gates.py`
