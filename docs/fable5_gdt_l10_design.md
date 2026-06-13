# Fable5 GD&T L10 — PMI Import Design (Phase 2)

> **Beads:** `Clawdbot_Docker_20260125-np8` (CLOSED)  
> **Status:** L4 + L10 assembly + **Cetol full scaffold** (2026-06-13)  
> **North Star:** press-part 3D -> Cetol 6 Sigma-class tolerance -> progressive-die

---

## Maturity ladder

| Level | Clawstack state | Evidence |
|-------|-----------------|----------|
| L1 | Nominal-only (`--no-gdt`) | bbox + sheet thickness |
| L2 | GD&T proxy | `manifest_tolerance.merged_tolerance_dims` |
| L4 | STEP PMI read | `step_pmi_extract.py` |
| L10 | Assembly + Cp/Cpk + factory KPI | `tolerance_l10_assembly.py` |
| **L10_cetol_full** | FreeCAD 3D loop + measurement correlation + PLM | `tolerance_cetol_full.py` |

---

## Cetol full (commercial scaffold)

```powershell
python scripts/tolerance_cetol_full_run.py data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json --write-manifest
```

| Module | Role |
|--------|------|
| `freecad_tolerance_loop.py` | FreeCADCmd 3D loop (faces/holes/closure) |
| `tolerance_measurement_correlation.py` | Measured lot vs MC (`measured_lot_golden.json`) |
| `tolerance_plm_handoff.py` | PLM/QMS artifact -> `tolerance_plm_handoff.json` |
| `tolerance_cetol_full.py` | Orchestrator |

**Outputs (golden dir):**

- `tolerance_cetol_full_report.json`
- `tolerance_plm_handoff.json`
- manifest `cetol_full_enrichment.maturity_level=L10_cetol_full`

---

## Still deferred (true commercial Cetol)

- Elastic contact / soft-hard constraint solver
- ECN/CAPA auto-ticket to QMS DB
- Measured lot from CMM/MES live feed (not synthetic golden)

---

## Verification

```powershell
python scripts/tolerance_cetol_full_run.py data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json --write-manifest
python scripts/fable5_manifest_e2e.py --require-red-lavie --timeout 900
```
