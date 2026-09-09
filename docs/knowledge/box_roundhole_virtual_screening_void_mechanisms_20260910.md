---
title: Box round-hole virtual screening: void mechanism inputs and acceptance
tags: [openfoam, calculix, injection-molding, void, pvt, cross-wlf, tait, screening]
status: screening-only
date: 2026-09-10
---

# Box round-hole virtual screening: void mechanism inputs and acceptance

## Verified result

The corrected four-vent 100 x 60 x 50 mm box case was rerun as E2E screening
run `virtual_e2e_20260910_r9`. Mean fill fraction is 0.9999999774. The
OpenFOAM-derived fields, virtual thermal/PVT fields, quality fields, void
mechanism fields, and CalculiX preparation/run/audit all completed. The gate is
`PASS_SCREENING`; this is not a measured-material or production prediction.

## Void mechanism contract

The quality output keeps separate fields for air entrapment, material gas,
PVT-shrink void, underpack, gate freeze, thick section, weld-adjacent risk,
cold fill, thermal degradation, and fiber-density/orientation heterogeneity.
The separate fields prevent a single unexplained “void score” from hiding the
physical cause.

## Material gas card

`config/virtual_material_pp_screening.json` now accepts:

- `gas_generation.moisture_ppm`
- `gas_generation.volatile_mass_fraction`
- `gas_generation.degradation_temperature_C`
- `gas_generation.data_status`

`scripts/derive_void_mechanisms.py --card <card.json>` converts those inputs
to `void_material_gas_risk`. The current virtual card deliberately uses zero
gas loading and reports `material_gas` as unknown without measurements. A
measured card must include moisture/volatile data and a TGA/degradation curve;
the resulting field remains screening-only until validated against experiment.

## Reproduction

```powershell
python scripts/run_virtual_e2e_screening.py `
  --source artifacts/box_roundhole_v5/virtual_e2e_20260909_r8/virtual_fields.vtu `
  --out artifacts/box_roundhole_v5/virtual_e2e_20260910_r9/virtual_fields.vtu `
  --quality-out artifacts/box_roundhole_v5/virtual_e2e_20260910_r9/quality `
  --case box100x60x50_virtual_material `
  --card config/virtual_material_pp_screening.json
```

Relevant artifacts are under
`artifacts/box_roundhole_v5/virtual_e2e_20260910_r9/`.

## Durable-storage routing

- GitHub: canonical Markdown and source code; commit `1025c59da5`.
- Obsidian: human-readable mirror under `data/state/Obsidian Vault/60_PC_Logs/`.
- ByteRover/auto-memory: curate context plus Git-tracked fallback mirror and
  retry queue; never rely on `.brv/` alone.
- Beads: operational decision and reproduction pointer.
- Turso: searchable `training_logs` record; credentials are never written to
  Markdown or logs.
- graphify: incremental graph update after the canonical note is added.

## Limitations

No measured PVT, rheology, TGA, moisture, pressure, cooling, or fiber data are
present. Therefore void magnitude, weld strength, sink depth, and warpage are
not release-grade predictions.
