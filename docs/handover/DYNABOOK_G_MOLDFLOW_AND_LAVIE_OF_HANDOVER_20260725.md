# Handover: Dynabook G: Moldflow inventory + Lavie OpenFOAM fill recovery (2026-07-25)

## Goal / context

- User asked to inventory Moldflow-related files on Dynabook Drive G, then classify keep vs discard.
- Same session recovered Lavie closed-cavity OpenFOAM fill (INC-161) and reproduced MFALIGN v3.
- Branch at commit time: `backup/openradioss-spm80-pre-rerun-20260725` (commits include `b8a8eb8da7`, `ce1a0a4a94`).

## Hosts / access

| Host | Role | Reach |
|---|---|---|
| Dynabook `DESKTOP-UOVCG4T` | Moldflow Synergy + MCP | Tailscale `100.98.133.40`, SSH `mec21` key `~/.ssh/moldflow_remote_ed25519`, MCP `:8765` |
| Red Lavie `DESKTOP-TFDRIPE` | OpenFOAM VOF | Satellite job API `100.87.244.46:5682`, exec pack `C:\lavie_usb_pack` |
| K10 | Orchestrator | `scripts/k10_tri_track_cae_orchestrator.py --continuous` |

Canonical Moldflow E2E: `docs/knowledge/dynabook_moldflow_end_to_end_runbook_20260720.md`  
Canonical synmesh launch (2026-07-26, Completed proven): `docs/knowledge/dynabook_moldflow_synmesh_canonical_route_20260726.md` (bd `moldflow-synmesh-canonical-route`, S020 / T076)

---

## Part A — Dynabook G: inventory (2026-07-25)

### Volume

- G: Size **465.75 GB**, Free **~397.6 GB**, Used **~68 GB** (NTFS).

### Top-level (Moldflow-relevant)

| Path | Size (approx) | Verdict |
|---|---:|---|
| `G:\moldflow_bridge` | **455 MB / 8575 files** | **KEEP** — live MCP hub |
| `G:\moldflow_bridge\work\` | (inside above) | **KEEP** — studies + results |
| `G:\MoldflowRemote` | 38.5 MB | **KEEP until reviewed** — separate remote workspace |
| `G:\moldflow_bridge_stage` | ~0 | **DISCARD candidate** — staging residue |
| `G:\moldflow_bridge_c387` | ~0 | **DISCARD candidate** — staging residue |
| `G:\moldflow_mcp_server.py` (G: root) | tiny | **DISCARD candidate** — orphan copy (2026-07-19) |
| `G:\claw_temp` | **~33 GB** | **NOT Moldflow work** — C: temp/Autodesk archives + Synergy launch cmds; capacity reclaim target |
| `G:\Program Files\TxGameAssistant` | — | Unrelated |

### `G:\moldflow_bridge` contents (keep)

- Live: `moldflow_mcp_server.py` (mtime 2026-07-20), `start_moldflow_mcp*.ps1`, `synapi.chm`, `api_reference/`, `work/`
- Many `moldflow_mcp_server.py.bak_*` and MCP `.log` / `.err.log` — history; keep a few recent bak, rotate logs
- Logs observed: `moldflow_mcp.log` / `moldflow_mcp.error.log` touched **2026-07-25**

### `work\` study folders

| Folder | Size | sdy | Role |
|---|---:|---:|---|
| `CLAW_MF_AUTOREPAIR_20260719_02` | **125 MB** | 44 | **Primary proven** Fill/Cool/Warp |
| `CLAW_MF_OFGATE_MATCH_20260724` | 30 MB | 2 | OF gate match |
| `CLAW_MF_REMESH_TEST_20260724` | 16 MB | 3 | Remesh test |
| `CLAW_MF_STRIP_COOL_V8_20260720` | 16 MB | 3 | Strip cool |
| `CLAW_MF_COOL_TUTORIAL_20260720` | 75 MB | 3 | Cool tutorial |
| `CLAW_MF_COOL_CPUBASE_20260720` | 4 MB | 2 | Cool cpu_base |
| `CLAW_MF_WARP_ORIG_20260720` | 6 MB | 1 | Warp origin |
| `CLAW_MF_STL_REPAIR_20260724` | 1.6 MB | 26 | Latest STL repair experiments (newest mtime 2026-07-24 19:46) |
| `CLAW_MF_STL_IMPORT_20260724` | 0.4 MB | 4 | STL import trials |
| `CLAW_MF_MATCFG_COPY_20260720` | 0.7 MB | 4 | Material/config copies |
| `cad` / `results` / `temp` | small | 0 | Review before delete |

Proven study path (runbook):

`G:\moldflow_bridge\work\CLAW_MF_AUTOREPAIR_20260719_02\mf_fc_strip_out_study_(copy).sdy`

### Artifact counts under `work\`

| Ext | n | MB |
|---|---:|---:|
| `.sdy` | 92 | 22.1 |
| `.of1` | 24 | 35.0 |
| `.op2` | 6 | 9.9 |
| `.oc1` | 5 | 1.7 |
| `.c2p` | 5 | 0.4 |
| `.ow3` | 8 | 1.0 |
| `.lsp` | 14 | 9.0 |
| `.png` | 24 | 0.8 |
| `.stl` | 7 | 0.2 |
| `.udm` | 5 | 3.1 |

### Answer to “were they all unnecessary?”

**No.** Valuable: live bridge + `CLAW_MF_AUTOREPAIR_*` + OF-gate / Cool / Warp evidence. Waste-ish: stage/c387, orphan root py, bak/log pile, and especially `claw_temp` (~33 GB).

Safe reclaim order (user approval):

1. Confirm contents of `G:\claw_temp\archive_*` then delete or move off-box.
2. Delete `moldflow_bridge_stage`, `moldflow_bridge_c387`, `G:\moldflow_mcp_server.py`.
3. Prune old `.bak_*` / MCP logs (keep last 2–3 bak).
4. Do **not** delete `CLAW_MF_AUTOREPAIR_20260719_02` without backup.

Audit scripts (K10):

- `D:\Clawdbot_Docker_20260125\.tmp\_dyna_g_mf_fast.ps1` (used successfully)
- Full recursive size pass was aborted as too slow.

---

## Part B — Lavie OpenFOAM cavity fill (INC-161 / T073 / S019)

### What was broken (stacked)

1. Lavie executes from `C:\lavie_usb_pack` (was 11 days stale).
2. Missing STL + silent `pp_plate` fallback despite `forbid_plate_geometry`.
3. BBox parser could not read STL (STEP-only).
4. `snappyhexmesh` branch never had a successful run (mm assumption, bbox-center `locationInMesh`).
5. `pack_end_time=0.32` overwrote fill horizon `analysis_end_time_s=1.24` in controlDict.
6. Orchestrator-only override: `tri_track_param_overrides.json` pinned `inlet_velocity=1.0` (auto-improver 2026-07-19) — manual dispatch never saw it.

### What was fixed

- Template: `data/cae_te_workspace/experiments/openfoam/mfalign_snappy_v001/` (force-added to git; directory otherwise gitignored).
- Proven STL: `data/cae_te_workspace/samples/moldflow/box_shell_phi20/Moldflow.stl` (1066 tri, watertight).
- Builder: `scripts/moldflow_step_case_builder.py` → `build_mfalign_snappy_case`.
- Engine: fail-closed plate + snappy 5-step mesh on K10 and Lavie USB pack.
- Params: `scripts/cae_tri_track_openfoam_params.py` aligns `pack_end_time` to fill horizon for `resin_fill_vof`.
- Override file: `data/workspace/tri_track_param_overrides.json` → `inlet_velocity: 6.51`.

### Proven reproduction

- Trial: `repro-mfalign-v3b-20260725`
- Lavie run dir: `E:\clawstack_satellite\data\work\cae_te_workspace\runs\repro-mfalign-v3b-20260725`
- Result: **SUCCESS** — fill 99.48%, fill_time 0.90 s (band 0.808–1.347), fill_complete true, End @ 1.24006 s

### Continuous track status at handover write

From `data/workspace/k10_tri_track_cae_status.json` (2026-07-25 21:23 JST):

- `openfoam_lavie`: running continuous, **fail_streak=4**, last `ERROR` `tri-lavie-resin_fill_cad-6e184dfe`
- meaning_gate threshold: 8 (`cae_workload_router.yaml`)
- OpenRadioss track: SKIP_LOAD (temp 80°C >= 76°C)

**Next session must:** inspect why auto trials still ERROR after U=6.51 / pack_end=1.24 (worker JSON parse `"Expecting value: line 1 column 1"` was seen earlier; some trials also short-shot when U was still 1.0). Diff effective params on the latest ERROR vs successful manual repro.

### Beads / docs

| ID | Topic |
|---|---|
| INC-161 | `docs/INCIDENT_LOG.md` |
| T073 | `data/workspace/memory/trouble_history.md` |
| S019 | `data/workspace/memory/success_cases.md` |
| Obsidian | `data/state/Obsidian Vault/60_PC_Logs/Moldflow_OpenFOAM_INC-161_T073_20260725.md` |
| bd `Clawdbot_Docker_20260125-6t03` | endTime precedence (params workaround in place) |
| bd `Clawdbot_Docker_20260125-83o9` | `cae_te_engine` 3-way version drift |
| bd `Clawdbot_Docker_20260125-ymp0` | generalize MFALIGN template beyond reference shell |

---

## Decision rules (reuse)

1. IF remote fix has no effect THEN verify **executing** file hash/path (`C:\lavie_usb_pack`), not the K10 repo copy.
2. IF manual dispatch passes but continuous fails THEN diff orchestrator overrides (`tri_track_param_overrides.json`) and effective params.
3. IF fill-only category THEN ensure `pack_end_time >= analysis_end_time_s` (engine ignores analysis_end for controlDict).
4. IF Drive G cleanup THEN keep `moldflow_bridge` + `CLAW_MF_AUTOREPAIR_*`; reclaim `claw_temp` / stage / orphan first.

## Config wiring (2026-07-25 evening) — use Drive G keep-set

| File | Change |
|---|---|
| `data/workspace/moldflow_bridge/dynabook_g_moldflow_paths.json` | Canonical keep-set + runner defaults |
| `data/workspace/moldflow_bridge/moldflow_mcp.env.ps1` | Deployed to `G:\moldflow_bridge\`; adds `MOLDFLOW_DEFAULT_STUDY` |
| `data/workspace/dynabook_node_registry.json` | `moldflow` block with use / do_not_use lists |
| `data/workspace/lavie_te_allocation_overrides.json` | `inlet_velocity` 6.0–7.0; `lavie_case` → v3; `mf_study_ref` + OFGATE path |
| `scripts/k10_moldflow_dynabook_runner.py` | Default `--study-path` / node / material from registry; STL → proven sample |

## Suggested next actions

1. Dynabook: user-approved cleanup of `G:\claw_temp` + stage/c387 + orphan py (optional).
2. Lavie OF: diagnose latest ERROR `tri-lavie-resin_fill_cad-6e184dfe` (params + worker stdout).
3. Confirm one continuous SUCCESS with U=6.51 and endTime=1.24 before claiming track healthy.
4. Sync/dist `cae_te_engine` three-way drift when touching Lavie again.
5. Restart Dynabook MCP once so the new `moldflow_mcp.env.ps1` is loaded by the interactive start task.

## Provenance

- Date: 2026-07-25 JST
- Audit: SSH `mec21@100.98.133.40` via `.tmp\_dyna_g_mf_fast.ps1`
- Related chat: Lavie resin-fill recovery + Drive G inventory
