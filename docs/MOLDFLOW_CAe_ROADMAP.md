# Moldflow-Class CAE Roadmap (OpenFOAM on LAVIE Fleet)

**Epic (Beads):** `Clawdbot_Docker_20260125-kwr`  
**Status:** Phase 2 verified (2026-06-01) -- LAVIE `moldflow-p2-vof-003` SUCCESS (`fill_fraction_pct` ~52%)  
**Canonical benchmark:** `data/workspace/commercial_benchmark_l10.json` -> product `MOLDFLOW`

## Goal

Move from **Newtonian `icoFoam` proxy** (`resin_flow_v001`) toward **Moldflow-like fill physics**:

1. Non-Newtonian viscosity (Power Law -> Cross-WLF)
2. Fill front (VOF / `interFoam`)
3. Selective turbulence (runner/cooling, not thin cavity)
4. Pack / cool / warpage (later)

## Current stack (parallel)

| Category | Experiment | Solver | Physics |
|----------|------------|--------|---------|
| `resin_flow` | OF-FLOW-001 | `icoFoam` | Laminar Newtonian baseline (24/365) |
| **`resin_fill`** | **OF-FILL-002** | **`nonNewtonianIcoFoam`** | **Power-law non-Newtonian (Phase 1)** |
| **`resin_fill_vof`** | **OF-FILL-003** | **`interFoam`** | **VOF fill front polymer/air (Phase 2)** |

Templates:
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v002/`
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v003/`

Router: `resin_fill` in `cae_workload_router.yaml` -> `lavie_openfoam_categories`

## Phases

| Phase | Deliverable | Benchmark level (functionality) |
|-------|-------------|----------------------------------|
| **0** | `resin_fill_v002`, engine category, this doc | L2 |
| **1** | Power Law + `nonNewtonianIcoFoam` + KPI | L3-L4 (LAVIE verified) |
| **2** | `interFoam` VOF fill front + fill % / time | L5 (K10 + LAVIE verified) |
| **3** | Temperature + Cross-WLF | L5-L6 |
| **4** | Turbulence (runner/cooling subcases) | L5 |
| **5+** | Pack, cool, warpage, STEP cavity | L7-L10 |

## Commands

```bash
# Dry-run (parameter injection only)
python scripts/cae_te_remote_trial.py --category resin_fill --dry-run
python scripts/cae_te_remote_trial.py --category resin_fill_vof --dry-run

# VOF fill trial (LAVIE, long timeout recommended)
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_vof --node lavie --timeout 1200

# Single trial (K10 or LAVIE)
python scripts/k10_satellite_cae_dispatch.py --category resin_fill --node lavie --timeout 600

# ParaView snapshot (after SUCCESS on LAVIE)
python scripts/cae_te_paraview_capture.py --trial-id <id> --workspace <LAVIE_WS> --send-telegram
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

## Not in scope yet

- Cross-WLF temperature -> Phase 3
- Commercial Moldflow parity / factory correlation -> Phase 5+

## References

- `scripts/inject_cae_know_how.py` (G5 openInjMoldSim / VOF know-how)
- `clawstack_v2/docs/knowledge/Moldflow_Knowledge.md`
- `docs/SATELLITE_CAE_ONE_SHOT_RUNBOOK.md`
