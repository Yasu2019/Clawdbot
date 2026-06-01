# Moldflow Phase 3 -- Implementation Decisions (canonical)

**Status:** Approved direction for Gemini / ChatGPT / Cursor (2026-06-01)  
**Supersedes:** open questions in Antigravity `implementation_plan.md` (Phase 3)  
**Related:** [MOLDFLOW_CAe_ROADMAP.md](MOLDFLOW_CAe_ROADMAP.md), [handovers/moldflow_phase3plus_gemini_handover_20260601.md](handovers/moldflow_phase3plus_gemini_handover_20260601.md)

---

## 1. Solver choice (answered)

| Option | Decision |
|--------|----------|
| `interFoam` + `0/T` only | **No** -- `interFoam` is isothermal; `T` will not couple to viscosity without forking the solver. |
| `interFoam` + `CrossPowerLaw` in `transportProperties` | **No** -- `CrossPowerLaw` in OF2512 is a shear-rate model, **not** Moldflow Cross-WLF; still no energy equation. |
| **`compressibleInterFoam`** | **Yes (Phase 3 default)** -- present in `opencfd/openfoam-dev:latest` on K10/LAVIE; supports VoF + thermophysical transport. |
| `multiphaseEulerFoam` / custom solver | **Defer** -- higher integration cost; use only if `compressibleInterFoam` case fails acceptance. |

**Engine change:** `OF-FILL-004` uses `solver_binary: compressibleInterFoam` (not `interFoam`).

**Regression:** Do **not** modify `resin_fill_v003` / category `resin_fill_vof`. New template `resin_fill_v004` + category `resin_fill_thermo` only.

---

## 2. Density / thermodynamics (answered)

| Question | Decision |
|----------|----------|
| Full compressible density coupling? | **Yes, minimal compressible setup** -- use `thermophysicalProperties` per phase (polymer / air) with sensible enthalpy formulation as required by `compressibleInterFoam`. |
| Strictly isothermal density + thermal viscosity only? | **No** -- that path needs a custom solver; out of scope for Phase 3. |
| Gravity | Start from **v003** (`g = (0 0 0)`); enable gravity in Phase 6+ if needed. |

---

## 3. Viscosity model (Cross-WLF vs OpenFOAM)

**Fact:** OpenFOAM 2512 (incompressible library) includes `CrossPowerLaw`, `powerLaw`, `Arrhenius`, `BirdCarreau`, etc. It does **not** include Autodesk Moldflow **Cross-WLF** ($D_1, D_2, D_3, A_1, \tilde{A}_2$) as a built-in keyword.

**Phased viscosity approach:**

| Step | Model | Purpose |
|------|--------|---------|
| **3a (this sprint)** | **`Arrhenius`** (or temperature-tabulated `mu` via `thermophysicalProperties` if Arrhenius does not fit VoF setup) | Prove **T -> viscosity -> fill** pipeline on LAVIE with measurable KPI. |
| **3b (2026-06-01)** | **WLF semi-coupled proxy** -- `viscosity_model=wlf` injects `mu = WLF(T_melt)` into const transport; KPI `mu_proxy_melt/mold`, `kpi_source=wlf_semi_coupled_proxy`. Native OF `WLF` transport FPE on `twoPhaseMixtureThermo` (OF2512); full field-coupled WLF deferred. |
| **3b+ (later)** | Tabulated `mu(T)` with registered `hConst+rhoConst` combo, or custom solver | Moldflow-class field-coupled viscosity. |

Do **not** label `CrossPowerLaw` as "Cross-WLF" in docs or KPIs.

---

## 4. Default parameters (placeholders -- NOT factory material data)

Use for template + injection tests only. Replace when a real material card is available.

| Param | Symbol | Default | Unit | Notes |
|-------|--------|---------|------|-------|
| Melt temperature | `T_melt` | **513** | K | ~240 C, generic PP order-of-magnitude |
| Mold temperature | `T_mold` | **323** | K | ~50 C |
| Reference / gate inlet T | `T_inlet` | `T_melt` | K | Same as melt at gate |
| Wall T | `T_wall` | `T_mold` | K | All mold walls |
| Power-law index (carry-over) | `power_law_n` | **0.6** | - | From Phase 1 sweep mid-value |
| Arrhenius | per `ArrheniusCoeffs` in OF | see `foamDictionary` in container | - | Implementer must copy **valid** coeffs from OF2512 `Arrhenius` model docs after `v004` scaffold |

**Cross-WLF (Moldflow) placeholders for JSON/router only (not used until 3b):**

```yaml
cross_wlf_D1: 3.0e11    # Pa.s -- placeholder
cross_wlf_D2: 0.0
cross_wlf_D3: 0.0
cross_wlf_A1: 30.0      # K
cross_wlf_A2: 51.6      # K
```

Mark `kpi_source: arrhenius_proxy` until correlated.

---

## 5. Template `resin_fill_v004` (minimum file set)

Copy from `resin_fill_v003`, then:

| Path | Action |
|------|--------|
| `0/T` | **NEW** -- volScalarField; full banner header; **no** `arch`/`location` on field files (Phase 2 rule). |
| `constant/thermophysicalProperties` | **NEW** -- two-phase thermo for `compressibleInterFoam`. |
| `constant/transportProperties` | **MODIFY** -- align with compressible thermo (do not duplicate conflicting models). |
| `system/fvSchemes` / `fvSolution` | **MODIFY** -- add `T` / `e` / `h` discretization per solver requirement. |
| `system/controlDict` | `application compressibleInterFoam`; `endTime` start **0.15** (match v003 tuning). |
| `*.ascii` backups | Keep for `fvSchemes`, `fvSolution`, `controlDict` + restore loop in engine (extend restore to `compressibleInterFoam`). |

---

## 6. Engine / gates (confirmed in Gemini plan)

- `cae_te_engine.py`: `OF-FILL-004`, `resin_fill_thermo`, inject `T_melt`, `T_mold`, Arrhenius coeffs.
- `cae_self_growth_gates.py`: `precheck_openfoam_thermo_case` -- require `0/T` + `thermophysicalProperties`.
- KPI: `T_max`, `T_min`, `fill_fraction_pct` (reuse fixed parser), `viscosity_proxy` optional.

---

## 7. Verification (unchanged)

```bash
python scripts/cae_te_remote_trial.py --category resin_fill_thermo --dry-run
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_thermo --node lavie --timeout 1800 --trial-id moldflow-p3-thermo-001
```

**Acceptance:** `returncode=0`, log contains `End`, `fill_fraction_pct > 10%`, latest time has `T` and `alpha.polymer`.

**Regression after Phase 3 merge:**

```bash
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_vof --node lavie --timeout 1200 --trial-id moldflow-p2-vof-regression-001
```

---

## 8. What to tell Gemini (one paragraph)

Use **`compressibleInterFoam`** on new template **`resin_fill_v004`** and category **`resin_fill_thermo`**. Do not add temperature to **`interFoam`** / **v003**. Viscosity: implement **temperature-dependent proxy (Arrhenius or thermo-tabulated mu)** first; true **Cross-WLF** is Phase 3b. Defaults: `T_melt=513` K, `T_mold=323` K. Read [moldflow_phase3plus_gemini_handover_20260601.md](handovers/moldflow_phase3plus_gemini_handover_20260601.md) for OF2512 header pitfalls.
