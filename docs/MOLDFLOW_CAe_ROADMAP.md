# Moldflow-Class CAE Roadmap (OpenFOAM on LAVIE Fleet)

**Epic (Beads):** `Clawdbot_Docker_20260125-kwr`  
**Status:** Phase 8 verified (2026-06-01) -- `resin_fill_doe` 4-point DOE + RSM -> `gate_spec_optimal.json`  
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
| `resin_fill_pack` | OF-FILL-006 | `interFoam` | VOF fill + gate hold pressure (`resin_fill_v006`) | Phase 5 OK |
| `resin_fill_cool` | OF-FILL-007 | `compressibleInterFoam` | Thermo VOF + pack + cool/warpage KPI (`resin_fill_v007`) | Phase 6 OK |
| `resin_fill_cad` | OF-FILL-008 | dynamic | STEP bbox + `gate_spec.json` -> `physics_category` | Phase 7 OK |
| `resin_fill_doe` | OF-FILL-009 | dynamic | D-Optimal multi-gate on STEP+VOF | Phase 8 OK |

Templates:

- `data/cae_te_workspace/experiments/openfoam/resin_fill_v002/`
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v003/`
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v006/` (Phase 5 pack/hold)
- `data/cae_te_workspace/experiments/openfoam/resin_fill_v007/` (Phase 6 cool/warpage)
- Phase 7 (planned): per-job case under `data/cae_te_workspace/runs/<trial_id>/` from STEP + `gate_spec.json` (no fixed `resin_fill_v008` box until mesh pipeline stable)

Router (LAVIE local, gitignored): `data/workspace/cae_workload_router.yaml` -> `lavie_openfoam_categories`

## Phase summary

| Phase | Deliverable | Benchmark (functionality) | Status |
|-------|-------------|---------------------------|--------|
| **0** | Categories + engine hooks + this doc | L2 | done |
| **1** | Power Law + `nonNewtonianIcoFoam` | L3-L4 non-Newtonian | **verified LAVIE** |
| **2** | `interFoam` VOF + fill % / time KPI | L5 VOF充填 | **verified K10+LAVIE** |
| **3** | Temperature + WLF viscosity proxy on VOF | L5-L6 | **verified K10** (3b semi-coupled) |
| **4** | Turbulence RAS k-omega SST (`resin_fill_turb` / v005) | L5 | **verified K10** (`local-p4-turb-003`) |
| **5** | Pack / hold pressure | L6 保圧 | **verified** (`local-p5-pack-002`) |
| **6** | Cool + warpage proxy | L6-L7 冷却・収縮 | **verified** (`local-p6-cool-001`) |
| **7** | STEP import + gate patch + `resin_fill_*` hookup | model_size L4+ | **verified** (`local-p7-cad-001`) |
| **8** | Multi-gate DOE + VOF | functionality L8 | **verified** (`OF-FILL-009` DOE) |
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

## Phase 5 -- Pack / hold pressure (DONE 2026-06-01)

| Work item | Detail |
|-----------|--------|
| Physics | Gate `fixedValue` hold pressure on active inlet + extended `endTime` (0.25 s proxy) |
| Template | `resin_fill_v006` (laminar VOF; v003 unchanged) |
| KPI | `pack_pressure_achieved_MPa`, `pack_pressure_ratio`, `short_shot_risk` from fill + pack ratio |
| Trial | `local-p5-pack-002` SUCCESS (~56 s) |
| Benchmark | functionality L6 "保圧・冷却" (pack portion) -- proxy only |

```bash
python scripts/cae_te_remote_trial.py --category resin_fill_pack --timeout 900 --trial-id local-p5-pack-002
```

---

## Phase 6 -- Cool + warpage (DONE 2026-06-01)

| Work item | Detail |
|-----------|--------|
| Physics | `compressibleInterFoam` + wall cooling (`T_mold`) + gate pack pressure (from v006) |
| Template | `resin_fill_v007` (from v004 thermo + v006 pack BC) |
| KPI | `cooling_time_s` (mean T <= `T_eject` after fill start; else `cool_end_time`), `warpage_mm` (CTE * L * deltaT) |
| Params | `T_eject`, `cool_end_time`, `thermal_shrink_alpha`, `mold_length_mm` |
| Trial | `local-p6-cool-001` SUCCESS (~236 s): fill 100%, warpage **0.72 mm**, cooling **0.5 s** (eject not reached) |
| Benchmark | evaluable_items L7 "冷却歪み" -- field proxy only |

```bash
python scripts/cae_te_remote_trial.py --category resin_fill_cool --timeout 1200 --trial-id local-p6-cool-001
```

---

## Phase 7 -- STEP import + gate patch + `resin_fill_*` (DONE 2026-06-01)

| Item | Detail |
|------|--------|
| Category | `resin_fill_cad` (`OF-FILL-008`) |
| Scripts | `moldflow_step_case_builder.py`, `moldflow_gate_spec.py` |
| Sample | `samples/moldflow/gate_spec_center.json`, `cavity_plate_100x10x2.step` |
| Mesh | STEP bbox -> auto `blockMeshDict` (v003 topology); **or** `mesh_mode=gmsh_volume` (gmsh tet + gmshToFoam) |
| UI | `apps/moldflow_cae_studio/` (full GUI) + `scripts/moldflow_cae_studio_api.py` (:8776) |
| Trial | `local-p7-cad-001` SUCCESS (~4 s), fill **~59%**, bbox **100x10x2 mm** |

```bash
python scripts/cae_te_remote_trial.py --category resin_fill_cad --timeout 900 --trial-id local-p7-cad-001
python scripts/moldflow_step_case_builder.py --validate-only --gate-spec data/cae_te_workspace/samples/moldflow/gate_spec_center.json --ensure-sample-step
# Phase 7b: gmsh cavity mesh trial
python scripts/cae_te_remote_trial.py --category resin_fill_cad --timeout 1200 --trial-id local-p7-gmsh-001 --params-json "{\"mesh_mode\":\"gmsh_volume\",\"mesh_size_mm\":2.0}"
# CAE Studio API (STL preview + STEP upload + job export)
python scripts/moldflow_cae_studio_api.py --ensure-preview
```

---

## Phase 7b -- Cavity mesh + Gate Studio UI (DONE 2026-06-01)

| Item | Detail |
|------|--------|
| Cavity mesh | `scripts/moldflow_cavity_mesh.py` -- gmsh 3D volume, physical groups `inlet1/2/3`, `outlet`, `walls` |
| Builder | `mesh_mode`: `blockmesh_bbox` (default) or `gmsh_volume` in `moldflow_step_case_builder.build_case` |
| Engine | Skips `blockMesh` when `constant/polyMesh` exists; precheck accepts gmsh cases |
| Gate UI | `data/workspace/apps/moldflow_gate_studio/index.html` (Three.js STL + click-to-toggle gates) |
| API | `scripts/moldflow_gate_studio_api.py` on **127.0.0.1:8776** (not 8099 -- OpenClaw control UI) |
| Preview | `samples/moldflow/cavity_preview.stl` |

**Note:** Sample STEP is bbox-only (8 points); gmsh uses **bbox box** until a solid STEP is supplied.

---

## Phase 7 design reference (target scope)

**Goal (user-aligned):** Moldflow に近い入口として、ユーザーが **STEP 3D キャビティ** を渡し、**ゲート面を指定** し、既存 **Phase 2-6**（`resin_fill_vof` / `_thermo` / `_pack` / `_cool` 等）を **同じ KPI・ゲート** で回せるようにする。

| Layer | Deliverable | Reuse in repo |
|-------|-------------|---------------|
| **7a CAD** | STEP/STP/FCStd 取込、単位・BBox 検証 | `dxf2step` worker, FreeCADCmd, `gmsh` tessellation (dxf3d) |
| **7b Mesh** | キャビティ体積メッシュ + 境界パッチ命名 | `snappyHexMesh` または gmsh→`foamMeshToFluent`/converter；v003 から `0/U`, `p_rgh`, `alpha` をテンプレ化 |
| **7c Gate** | ユーザー指定ゲート面 → OpenFOAM `patch`（`gate_1`…） | 現行 `inlet1/2/3` + `gate_position` を **パッチ名リスト** に一般化 |
| **7d Run** | `cae_te_engine` が case ディレクトリを動的生成し既存カテゴリを実行 | `_inject_parameters_openfoam`, `precheck_openfoam_*`, LAVIE dispatch そのまま |

### User / agent workflow (target)

```mermaid
flowchart LR
  STEP[STEP or FCStd] --> CAD[7a validate BBox]
  CAD --> GATE[7c gate_faces.json]
  GATE --> MESH[7b cavity mesh]
  MESH --> CASE[OpenFOAM case dir]
  CASE --> FILL[resin_fill_vof / thermo / pack / cool]
  FILL --> KPI[fill % pack warpage ...]
```

### Gate specification (draft contract)

`gate_spec.json`（case ルートまたは実験 params）例:

```json
{
  "gates": [
    {"id": "gate_1", "patch": "gate_inlet_A", "role": "injection", "T_K": 513},
    {"id": "gate_2", "patch": "gate_inlet_B", "role": "injection", "enabled": false}
  ],
  "vents": [{"patch": "vent_outlet", "role": "outlet"}],
  "walls": [{"patch": "mold_wall", "T_K": 323}]
}
```

Engine は `gate_position` の left/center/right の代わりに **`gates[].patch`** を `0/U`, `0/p_rgh`, `0/T` の `boundaryField` にマッピング（後方互換で v003 箱メッシュは従来どおり）。

### Phase 7 vs Phase 8

| Phase | ユーザー操作 | 解析 |
|-------|--------------|------|
| **7** | STEP + **ゲート面指定**（1〜N） | 既存 `resin_fill_*` 1 ケース実行 |
| **8** | 同上 + DOE パラメータ | 多ゲート・粘度・速度の **自動スイープ**（`resin_flow_opt` 統合） |

### Acceptance (Phase 7 MVP)

1. サンプル STEP（または FCStd エクスポート STEP）からメッシュ生成し `checkMesh` PASS。
2. `gate_spec.json` で指定したパッチに `inlet_velocity` / `pack_pressure` が注入される。
3. `resin_fill_vof` を **動的 case** で 1 回 SUCCESS（`fill_fraction_pct` 取得）。
4. `resin_fill_v003` 箱メッシュ回帰は **変更なし** で PASS。

### Out of scope for Phase 7 MVP

- ブラウザ上の 3D ゲートピッカー UI（まず JSON / CLI；UI は Portal 拡張で後追い可）
- 完全自動 `snappyHexMesh` チューニング（最初は単純キャビティ or 手動支援メッシュ可）
- OpenRadioss 構造反り（Phase 6 proxy のまま）

---

## Phase 8 -- Multi-gate DOE + VOF + CAD (DONE 2026-06-01)

| Item | Detail |
|------|--------|
| Category | `resin_fill_doe` (`OF-FILL-009`) |
| Script | `scripts/moldflow_doe.py` |
| DOE factors | `gate_count`, `gate_position`, `polymer_nu`, `inlet_velocity` |
| Case build | `gate_count` -> auto `gate_spec.generated.json` + STEP bbox mesh (Phase 7) |
| Post-run | RSM on `fill_fraction_pct` / `short_shot_risk` -> `cae_te_optimal_vof_doe.json`, `gate_spec_optimal.json` |
| Trial | 4-point DOE: 2 SUCCESS / 2 FAILED; RSM recommends **3 gates, center** (example run) |

```bash
python scripts/cae_te_engine.py --category resin_fill_doe --max-trials 6 --timeout 900
python scripts/moldflow_doe.py --n-trials 6
```

---

## Phase 9-10 -- operations, L10

| Phase | Focus |
|-------|--------|
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
| `cooling_time_s` | 6 | Time to reach `T_eject` (mean T), else `cool_end_time` |
| `T_eject` | 6 | Ejection temperature threshold [K] |
| `thermal_shrink_alpha` | 6 | Linear CTE proxy [1/K] |
| `mold_length_mm` | 6 | Characteristic length for warpage [mm] |
| `cool_end_time` | 6 | Total simulation end time [s] |

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
