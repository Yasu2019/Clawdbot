# Incident Log 窶・繝医Λ繝悶Ν險倬鹸繝ｻ蜀咲匱髦ｲ豁｢蜿ｰ蟶ｳ

譛ｬ繝輔ぃ繧､繝ｫ縺ｯ縲√す繧ｹ繝・Β縺ｫ逋ｺ逕溘＠縺滄囿螳ｳ縺ｻ荳榊・蜷医→縺昴・譬ｹ譛ｬ蜴溷屏繝ｻ菫ｮ豁｣蜀・ｮｹ繝ｻ蜀咲匱髦ｲ豁｢遲悶ｒ險倬鹸縺励∪縺吶€・菫ｮ豁｣繧定｡後▲縺溷ｴ蜷医・縲∝ｿ・★縺薙・繝輔ぃ繧､繝ｫ縺ｫ繧ｨ繝ｳ繝医Μ繧定ｿｽ蜉縺励※縺上□縺輔＞縲・
------

------

## INC-131: DXF2STEP hole-vs-island audit misclassification on D3 busbar (extends INC-130)

| Field | Detail |
|---|---|
| **Date** | 2026-06-28 JST |
| **Detection** | User manufacturing review: 2D "islands" on `tp-dxf-0430c2ca` are **hole machining** (124 CIRCLE), not separate parts. Agent had labeled GEOMETRY_PARTIAL_OK without visual PNG inspection. |
| **Impact** | False downgrade blocked CAE confidence; user distrust of automated TOP VIEW narrative. |
| **Root Cause (5 Why)** | **Why1**: User corrected island reading. **Why2**: Dense holes/cutouts look like blobs in 2D. **Why3**: INC-130 "8-plate grid" wording reused for hole arrays. **Why4**: DXF-QC09 lacked outer-profile-only rule. **Why5**: No mandatory visual gate on `original_dxf.png`. |
| **Fix** | Revise `tp-dxf-0430c2ca` -> GEOMETRY_OK. Add DXF-QC17/18 to checklist. Cross-audit `audit_dxf2step_hole_vs_island_misclass.py`. Register INC-131/T042. |
| **Files** | `quality_incident_report_20260628_dxf2step_hole_vs_island_audit_inc131.md`; `scripts/register_dxf2step_hole_vs_island_inc131.py`; `scripts/audit_dxf2step_hole_vs_island_misclass.py`; `data/workspace/dxf2step_hole_vs_island_audit_20260628.json`; `combined_geometry_audit.json` (0430c2ca) |
| **Verification** | Cross-scan 443 archives: **1** mis-adjudication file (0430c2ca, corrected); **28** hole-heavy SUCCESS (heuristic OK); **82** separate frame+part SUSPECT/NG (INC-124/125 class, not hole confusion). |
| **Prevention** | DXF-QC17 outer profile vs holes. DXF-QC18 visual PNG gate. bd remember `dxf2step-hole-vs-island-inc131`. trouble_history [T042]. |

------

## INC-130: DXF2STEP D3 multi-layout false SUCCESS -- nest strip + profile + pitch grid (extends INC-125)

| Field | Detail |
|---|---|
| **Date** | 2026-06-27 JST |
| **Detection** | Formal audit `audit_dxf2step_combined_geometry.py` + DXF-QC09 manual TOP VIEW review on `tp-dxf-959d5e60` (D3 @ 15mm). Manifest SUCCESS but three separate outline groups on TOP. |
| **Impact** | False SUCCESS shipped to Telegram/dashboard. Combined STEP unusable for Moldflow/OpenRadioss until geometry gate passes. |
| **Root Cause (5 Why)** | **Why1**: TOP shows 3 outline groups. **Why2**: Layer5 nest strip + H-profile + 8-plate grid all extruded via single_profile_extrude. **Why3**: INC-125 `_keep_largest_connected_cluster` X-column rule over-merged layout islands. **Why4**: No nest-strip / pitch-grid filter for progressive-die layouts. **Why5**: Success KPI (layers_done + has_combined_step) without mandatory DXF-QC09 audit. |
| **Fix** | `dxf2step_worker.py`: `_pick_part_cluster_segs` + `largest_non_strip_cluster` (drop aspect>10 strips >120mm, fragments <8% max area). NG registry entry for `tp-dxf-959d5e60`. Per-trial `combined_geometry_audit.json`. Retry `tp-dxf-0430c2ca` -> GEOMETRY_PARTIAL_OK (2 groups). |
| **Files** | `data/workspace/apps/dxf2step/dxf2step_worker.py`; `data/workspace/dxf2step_geometry_ng_trials.json`; `data/workspace/thinkpad_dxf2step_history/tp-dxf-959d5e60/combined_geometry_audit.json`; `data/workspace/thinkpad_dxf2step_history/tp-dxf-0430c2ca/combined_geometry_audit.json`; `quality_incident_report_20260627_dxf2step_d3_multi_layout_inc130.md`; `scripts/register_dxf2step_d3_multi_layout_inc130.py` |
| **Verification** | `tp-dxf-0430c2ca` SUCCESS with `cluster_pick_mode=largest_non_strip_cluster`, bbox 298x188x15mm. Audit adjudication GEOMETRY_PARTIAL_OK vs prior GEOMETRY_NG. Failed retry `tp-dxf-998a6e44` (smallest_part_cluster) documented as anti-pattern. |
| **Prevention** | Mandatory DXF-QC09 before CAE handoff. Do not trust manifest SUCCESS without `combined_geometry_audit.json`. bd remember `dxf2step-d3-multi-layout-inc130`. trouble_history [T041]. Remaining: filter 8-plate pitch grid for single-part GEOMETRY_OK. |

------

## INC-129: FEM Impact mesh explosion false SUCCESS -- stale PNG/VTK accepted

| Field | Detail |
|---|---|
| **Date** | 2026-06-24 JST |
| **Detection** | User visually inspected Fem_Impact PNGs and reported mesh explosion. K10 tri-track had repeatedly logged `SUCCESS` with `FEM_IMPACT_SKIP_RECOMPUTE=png_exists` and `FEM_IMPACT_PNG_COUNT=3`. |
| **Impact** | ThinkPad `fem_impact` produced false CAE success evidence. Existing PNG/video artifacts for `Rough_Mesh/test.in` and `no_solid_reqtangle_sample_20250806/test.in` are invalid until revalidated. |
| **Root Cause (5 Why)** | **Why1**: Bad FEM output was marked SUCCESS. **Why2**: Success only required exit status plus PNG/count markers. **Why3**: Cached PNG path skipped recompute and did not validate the source VTK. **Why4**: INC-122/123 fixed script sync and shell quoting but did not add a mesh plausibility gate. **Why5**: The operator checked logs/counts without opening the rendered images. |
| **Fix** | Added `scripts/impact_vtk_quality_gate.py`, a pure-Python legacy VTK QC gate. Updated `scripts/k10_tri_track_cae_orchestrator.py` so cached PNG, reused VTK, and fresh solve paths all run QC before PNG success is accepted. Updated `scripts/k10_thinkpad_fem_impact_deploy.py` to sync the QC script to ThinkPad with the PNG/render helpers. |
| **Files** | `scripts/impact_vtk_quality_gate.py`; `scripts/k10_tri_track_cae_orchestrator.py`; `scripts/k10_thinkpad_fem_impact_deploy.py`; `quality_incident_report_20260624_fem_impact_mesh_explosion.md`; `data/state/Obsidian Vault/60_PC_Logs/FEM_Impact_INC129_mesh_explosion_false_success_20260624.md` |
| **Verification** | `py_compile` passed for the changed Python files. Synthetic exploded VTK failed with `FAILED_MESH_EXPLOSION`; synthetic small VTK passed. ThinkPad known-bad `Rough_Mesh/test.in_surface_0.002000.vtk` failed with bbox `52376491.47`, coordinate max `26836835.69`, displacement max `26993307.77`. ThinkPad known-bad sample VTK failed with bbox `1668049955.59`, coordinate max `807003989.11`, displacement max `863948636.94`. Live `run_thinkpad_impact` returned `FAILED_MESH_EXPLOSION` before recompute. |
| **Prevention** | Fem_Impact success now requires `FEM_IMPACT_QC_VERDICT=PASS`; `FAILED_MESH_EXPLOSION` cannot be reported as SUCCESS. Cached PNGs are no longer trusted without source VTK numeric QC. Beads issue `Clawdbot_Docker_20260125-g3k`; rule captured with `bd remember --key fem-impact-mesh-explosion-inc129`. |

------

## INC-128: Robot L20 autonomous launcher used same stdout/stderr redirect path

| Field | Detail |
|---|---|
| **Date** | 2026-06-20 JST |
| **Detection** | First run of `start_robot_l20_autonomous_loop.ps1` failed with PowerShell error: `RedirectStandardOutput` and `RedirectStandardError` are same. |
| **Impact** | Bounded autonomous Robot L20 loop did not start on the first launcher attempt. |
| **Root Cause (5 Why)** | **Why1**: `Start-Process` rejected the command. **Why2**: stdout and stderr were redirected to the same log file. **Why3**: Windows PowerShell requires distinct redirect files. **Why4**: The launcher had no smoke execution before use. **Why5**: The urgency to start self-running development compressed validation. |
| **Fix** | Split logs into `robot_l20_autonomous_loop_stdout.log` and `robot_l20_autonomous_loop_stderr.log`, then relaunched successfully. |
| **Files** | `data/workspace/apps/motion_lab/05_quality_check/start_robot_l20_autonomous_loop.ps1`; `quality_incident_report_20260620_robot_l20_launcher_redirect_bug.md` |
| **Verification** | Launcher created `robot_l20_autonomous_launcher_status.json` with PID `19316`; autonomous status reached `state=running`, `cycles_completed=1`. |
| **Prevention** | PowerShell launchers must use separate stdout/stderr log paths when both redirect parameters are supplied. |

------

## INC-127: Robot L20 trial generator wrote to nested data/data path on first run

| Field | Detail |
|---|---|
| **Date** | 2026-06-20 JST |
| **Detection** | First execution of `run_robot_l20_motion_trials.py` failed with `FileNotFoundError` while writing `robot_l20_motion_trial_status.json`. |
| **Impact** | The urgent L20 trial loop produced no dashboard evidence on the first attempt, delaying the robot natural-motion iteration. |
| **Root Cause (5 Why)** | **Why1**: Output path was `D:\Clawdbot_Docker_20260125\data\data\workspace\...`. **Why2**: `ROOT = parents[4]` resolved to the repo `data` directory. **Why3**: The script lives under `data/workspace/apps/motion_lab/05_quality_check`, so repo root is `parents[5]`. **Why4**: `py_compile` only checked syntax and did not verify runtime output paths. **Why5**: No smoke test existed for generated dashboard-output scripts. |
| **Fix** | Changed `ROOT` to `Path(__file__).resolve().parents[5]`. Re-ran the L20 trial loop successfully and generated JSON, HTML, and Markdown evidence. |
| **Files** | `data/workspace/apps/motion_lab/05_quality_check/run_robot_l20_motion_trials.py`; `quality_incident_report_20260620_robot_l20_trial_path_bug.md`; `data/workspace/apps/growth_dashboard/robot_l20_motion_trial_status.json`; `data/workspace/apps/growth_dashboard/robot_l20_motion_trials.html` |
| **Verification** | `py_compile` passed. `run_robot_l20_motion_trials.py` completed successfully: 120 trials, best score 100, 24 L20 proxy candidates, all best-task scores >= 82.4. Telegram text and HTML document delivery succeeded. |
| **Prevention** | For generated dashboard-output scripts, run a smoke execution after syntax checks and verify absolute output paths stay under repo root, never nested `data/data`. |

------

## INC-126: CP-018 publishing catalog item had no concrete Kindle/note/BOOTH pages

| Field | Detail |
|---|---|
| **Date** | 2026-06-20 JST |
| **Detection** | User reported that KindleUnlimited, note, and BOOTH book pages could not be found after CP-018 robot publishing topic was added. |
| **Impact** | Growth Dashboard could list the publishing idea, but the user had no concrete page drafts to open or reuse for publishing. |
| **Root Cause (5 Why)** | **Why1**: Only the catalog item was added. **Why2**: The work was interpreted as topic registration rather than page creation. **Why3**: Existing CP items use `cp-*_book_draft.html` and `.md`, but CP-018 did not follow that asset pattern. **Why4**: There was no validation requiring Kindle/note/BOOTH items to have concrete page assets. **Why5**: Final verification checked JSON validity, not asset completeness. |
| **Fix** | Added `cp-018_book_draft.html`, `cp-018_book_draft.md`, and platform drafts under `publishing/cp018_robot_training/` for Kindle Unlimited, note, and BOOTH. Updated CP-018 `asset_paths`. |
| **Files** | `data/workspace/apps/growth_dashboard/content_publishing_catalog.json`; `data/workspace/apps/growth_dashboard/cp-018_book_draft.html`; `data/workspace/apps/growth_dashboard/cp-018_book_draft.md`; `data/workspace/apps/growth_dashboard/publishing/cp018_robot_training/*`; `quality_incident_report_20260620_cp018_book_pages_missing.md` |
| **Verification** | CP-018 asset existence validation PASS. HTML structure validation PASS. `localhost:8088` route check timed out, which is separate dashboard server availability. |
| **Prevention** | When adding a publishing catalog item with Kindle/note/BOOTH platforms, create concrete page assets and validate that every non-external `asset_paths` entry exists. |

------

## INC-125: DXF2STEP combined geometry false SUCCESS -- P38 / A3 sheet / auxiliary views (extends INC-124)

| Field | Detail |
|---|---|
| **Date** | 2026-06-19 -- 2026-06-20 JST |
| **Detection** | User: P38 TOP multiple outlines (`tp-dxf-5941a119`). Full audit: 21+ trials SUSPECT_NG; PARTIAL P4,P5,P6,P7,P9,P47,S1; FAILED P46. |
| **Impact** | False SUCCESS on Growth Dashboard; unusable combined.step for progressive-die / Moldflow handoff; operator re-work. |
| **Root Cause (5 Why)** | **Why1**: TOP double/multiple silhouettes. **Why2**: Layout layers (A4 208x293, A3 420x297, A2 594x420) extruded; same-layer side views on P38 L7. **Why3**: INC-124 fix used 20x-only frame rule; no A3 skip; no island filter; multiview fail -> PARTIAL. **Why4**: No mandatory PNG silhouette audit; old trials remained dashboard best. **Why5**: KPI layers_done + has_combined_step only. |
| **Fix** | 1. `_is_layout_layer_bbox` (A4+A3+A2) extrude skip.<br>2. `_keep_largest_connected_cluster` X-column filter.<br>3. multiview fail -> `_pick_part_layer_for_combined` fallback.<br>4. Smallest non-layout layer preferred for combined.<br>5. Batch rescan 8 PARTIAL + P46; audit + NG registry sync.<br>6. Full QC record: `quality_incident_report_20260620_dxf2step_combined_geometry_inc125.md`. |
| **Files** | `dxf2step_worker.py`, `dxf2step_combined_geometry_qc_checklist.md`, `dxf2step_geometry_ng_trials.json`, `register_dxf2step_combined_geometry_inc125.py` |
| **Verification** | P38 `tp-dxf-8e205f0e` single TOP; P4 `tp-dxf-1c5a1c9d`; P46 `tp-dxf-fcf3cc4c` SUCCESS; audit archives=166. |
| **Prevention** | [T040]; DXF-QC02/04/07/09; read checklist before worker changes; `bd remember --key dxf2step-combined-geometry-inc125`; never ship double TOP outline. |

------

## INC-124: DXF2STEP S11 false SUCCESS -- overlapping TOP VIEW profiles (frame layer as front)

| Field | Detail |
|---|---|
| **Date** | 2026-06-19 JST |
| **Detection** | User reported `tp-dxf-9d04f260` (S11, t=10mm) Telegram SUCCESS but `combined_views.png` TOP VIEW shows two unrelated overlapping outlines (drawing frame rectangle + busbar profile). |
| **Impact** | False SUCCESS to Telegram; `combined.FCStd` unusable for Moldflow/OpenRadioss/progressive-die handoff; operator trust erosion. |
| **Root Cause (5 Why)** | **Why1**: TOP VIEW double silhouette. **Why2**: Layer1 (208x293mm frame) auto-assigned front + Layer3 (12x17.6mm busbar) top -> multiview compound/intersection. **Why3**: `_assign_views_auto` uses sheet Y-cluster only, not engineering view semantics. **Why4**: No frame-layer filter; compound fallback still exported combined.step. **Why5**: `evaluate_build_log` only required `layers_done==n_total` and `has_combined_step`. |
| **Fix** | 1. `_filter_frame_layers` (>20x area vs smallest profile).<br>2. `_export_single_layer_combined` when one valid layer remains.<br>3. `compound_fallback` -> `combined_quality_ok=false` -> verdict FAILED.<br>4. Checklist `dxf2step_combined_geometry_qc_checklist.md` (DXF-QC10-14).<br>5. `register_dxf2step_s11_multiview_overlap_inc124.py` -> growth DB, FMEA registry, quality JSONL/SQLite, Obsidian, Turso, Beads, ByteRover. |
| **Files** | `data/workspace/apps/dxf2step/dxf2step_worker.py`, `scripts/k10_thinkpad_dxf2step_loop.py`, `scripts/dxf2step_quality_gate.py`, `scripts/register_dxf2step_s11_multiview_overlap_inc124.py` |
| **Verification** | Bad: `tp-dxf-9d04f260/combined_views.png` (NG). Good: `tp-dxf-dc852457` -- `reconstruction_frame_layers_dropped:["1"]`, `single_profile_extrude`, single TOP VIEW outline. |
| **Prevention** | [T039]; read checklist before DXF2STEP multiview changes; `bd remember --key dxf2step-s11-multiview-overlap-inc124`; never ship combined when TOP VIEW shows double outline. |

------

## INC-122: ThinkPad fem_impact Rough_Mesh tri-track -- PNG script missing, timeout orphans java

| Field | Detail |
|---|---|
| **Date** | 2026-06-18 JST |
| **Detection** | `k10_tri_track_cae_status.json` fem_impact_thinkpad FAILED; worker stderr `thinkpad_fem_impact_png.sh: No such file or directory` (exit 127); second trial timeout exit 124 at 10800s with zero VTK for `auto_revised_mesh.in`. |
| **Impact** | ~44 min Impact compute wasted from orchestrator verdict (test.in); duplicate java on ThinkPad; no PNG/Telegram artifacts for Rough_Mesh panel case. |
| **Root Cause (5 Why)** | **Why1**: Tri-track marked fem_impact FAILED. **Why2**: PNG step never ran successfully. **Why3**: `thinkpad_fem_impact_png.sh` not deployed (`--no-sync-impact`); glob used `test_*` not `test.in_*`; Docker vtk crashed on bulk VTK. **Why4**: `auto_revised_mesh.in` end time 0.015s vs test.in 0.0021s exceeds 3h worker timeout; timeout kills bash only and orphans java. **Why5**: No preflight sync of satellite scripts; no process-group kill on timeout; variant pool includes unbenchmarked long cases. |
| **Fix** | 1. `start_k10_tri_track_cae_watchdog.ps1` runs `--sync-script` before orchestrator.<br>2. `thinkpad_fem_impact_png.sh`: `test.in_*` glob, prefer surface VTK, host venv fallback.<br>3. Deployed scripts to ThinkPad; killed orphan `run.Impact`; generated 3 PNG from existing VTK.<br>4. `register_thinkpad_fem_impact_rough_mesh_inc122.py` -> growth DB, ops_trial_history, cae_failure_analysis, Obsidian, Turso (if creds). |
| **Files** | `scripts/thinkpad_fem_impact_png.sh`, `scripts/start_k10_tri_track_cae_watchdog.ps1`, `scripts/register_thinkpad_fem_impact_rough_mesh_inc122.py`, `data/workspace/memory/trouble_history.md` [T038] |
| **Verification** | ThinkPad: `thinkpad_fem_impact_png.sh` present +x; Rough_Mesh `png_count=3` (`test.in_surface_0.002000_*.png`); no concurrent `run.Impact` after cleanup. |
| **Prevention** | [T038]; bd `thinkpad-fem-impact-rough-mesh-inc122`; ByteRover curate; read T038 before fem_impact tri-track changes. Pending: worker timeout process-group kill; benchmark timeout per variant. |

------

## INC-123: ThinkPad fem_impact worker shell quoting -- bash -lc exit 1 / test unbound variable

| Field | Detail |
|---|---|
| **Date** | 2026-06-18 JST |
| **Detection** | Autonomous loop + `run_thinkpad_impact` FAILED with `bash: line 1: test: unbound variable` and empty stdout; worker exit 1 despite `FEM_IMPACT_SKIP_RECOMPUTE` in stdout when PNG already exists. |
| **Impact** | fem_impact_thinkpad track stuck at n=0; wasteful re-dispatch attempts; tri-track could not mark SUCCESS on completed cases. |
| **Root Cause (FTA / 5Why / Fishbone)** | **FTA**: FAILED verdict -> worker exit!=0 -> nested `bash -lc '...'` under worker `shell=True` misparsed -> `CASE_DIR`/`INP` unset -> `test -f` triggers `test: unbound variable`. **5Why**: Why FAILED? exit 1. Why exit 1? nested single-quote script broken by outer sh -c. Why nested? historical `bash -lc` pattern. Why not caught? success gate required exit 0 only. **Fishbone**: Method=bash -lc quoting; Machine=lavie_job_worker shell=True; Environment=SSH sync timeouts concurrent. |
| **Fix** | 1. `k10_tri_track_cae_orchestrator.py`: dispatch Impact via `bash <<'FEMIMPACT_EOF'` heredoc (no nested -lc). 2. `pkill` targets `java.*run.Impact` only (not job shell). 3. SUCCESS if `FEM_IMPACT_SKIP_RECOMPUTE` or `FEM_IMPACT_REUSE_VTK` in stdout. 4. `thinkpad_fem_impact_autonomous_loop.py` for RCA/retry/record. |
| **Files** | `scripts/k10_tri_track_cae_orchestrator.py`, `scripts/thinkpad_fem_impact_autonomous_loop.py` |
| **Verification** | Both production variants SUCCESS exit 0: `no_solid_reqtangle_sample_20250806/test.in`, `Rough_Mesh/test.in` (skip recompute, PNG count=3). Autonomous loop finished 2026-06-18T09:28:13+09:00 all SUCCESS. |
| **Prevention** | Never use nested `bash -lc '...'` for ThinkPad worker shell jobs; use heredoc or remote script file. bd `fem-impact-worker-heredoc-inc123`. |

------

## INC-121: Fleet-wide post-reset satellite setup failed repeatedly (daemon, Defender, CRLF, operator)

| Field | Detail |
|---|---|
| **Date** | 2026-06-07 JST |
| **Detection** | After Windows Update reboots, user repeated manual setup on Red LAVIE, Main LAVIE, G3, Dynabook, HP, ThinkPad. Each node failed multiple times before fleet-wide daemon pattern succeeded. |
| **Impact** | Fleet uptime dropped; CAE tri-track could not dispatch to lavie / red_lavie / thinkpad; hours of manual recovery per reboot cycle. |
| **Root Cause (5 Why)** | **Why1**: Satellites did not self-heal after reboot. **Why2**: No unified logon + 5min watchdog scheduled tasks. **Why3**: Prior scripts used console-bound python, broken `Start-Process -ArgumentList`, or VBS-only startup without watchdog. **Why4**: Node-specific bugs compounded: INC-120 monitor SyntaxError/self-kill; HP Defender blocked `%TEMP%` ps1; ThinkPad CRLF in `.sh`; G3 `pythonw` missing when monitor already healthy; user ran cmd with placeholder URL. **Why5**: No single SOP, no K10 compile gate, no post-change `-ProbeOnly` gate -- recovery was ad-hoc per machine. |
| **Fix** | 1. Generic `fleet_satellite_setup.ps1` + `satellite_*_daemon.ps1` + `satellite_common.ps1` for lavie/red_lavie/dynabook/g3.<br>2. `fleet_satellite_setup_auto.ps1` node auto-detect.<br>3. `k10_fleet_satellite_setup_all.ps1 -ProbeOnly` from K10.<br>4. HP: `C:\clawstack_hp` + `hp_local_bringup.ps1` + `hp_watchdog.py` (patrol only, no CAE).<br>5. ThinkPad: `thinkpad_satellite_setup.sh` systemd + CRLF fix in `thinkpad_ssh_common.py`.<br>6. `verify_fleet_script_server_gate.ps1` before :8123 (extends INC-120).<br>7. CAE policy doc `docs/cae_tri_track_dispatch_policy.md` + `cae_workload_router.yaml` `cae_compute_policy`. |
| **Files** | `scripts/fleet_satellite_setup.ps1`, `scripts/satellite_common.ps1`, `scripts/satellite_job_worker_daemon.ps1`, `scripts/satellite_monitor_daemon.ps1`, `scripts/hp_local_bringup.ps1`, `scripts/hp_watchdog.py`, `scripts/thinkpad_ssh_common.py`, `data/workspace/cae_workload_router.yaml`, `docs/troubleshooting/fleet_satellite_daemon_setup.md`, `docs/cae_tri_track_dispatch_policy.md` |
| **Verification** | Per-node: `FLEET_SATELLITE_SETUP_OK` / `RED_LAVIE_JOB_WORKER_OK` / `HP_LOCAL_BRINGUP_OK`; K10 `k10_fleet_satellite_setup_all.ps1 -ProbeOnly` worker+monitor 200 on lavie, red_lavie, dynabook, g3; ThinkPad SSH deploy OK. |
| **Lessons Learned** | Post-reset recovery must be one command per node, not rediscovered each time. Never run setup ps1 from `%TEMP%` on Defender-heavy hosts. Linux deploy pipeline must normalize LF. K10 serves fleet scripts -- compile gate is mandatory. |
| **Prevention** | [T037] in `trouble_history.md`; bd `fleet-post-reset-recovery-inc121`; bd issue `Clawdbot_Docker_20260125-a83`; universal_growth.db domain `FLEET_OPS`; ByteRover curate; agents read T037 before any satellite bringup. Commercial evolution gates G1-G5 in `docs/cae_tri_track_dispatch_policy.md`. |

### FMEA (selected)

| Mode | Effect | RPN driver | Control |
|---|---|---|---|
| SyntaxError in served script | All nodes fail monitor | High | G1 py_compile gate |
| Self-kill in start script | Silent exit after "Saved" | High | Narrow Stop-Process filter |
| Defender blocks TEMP ps1 | HP bringup fails | Med | Permanent `C:\clawstack_hp` |
| CRLF on ThinkPad .sh | systemd unit fails | Med | sed in SSH push |
| Wrong shell/URL | 404 / policy block | Med | SOP: PowerShell + K10 :8123 only |
| No watchdog after reboot | Offline until manual login | High | Logon task + 5min watchdog |

### FTA (summary)

```
Fleet post-reset pain
+-- Script quality (SyntaxError, ArgumentList) --> G1 compile gate
+-- Host security (Defender, ExecutionPolicy) --> permanent dirs + Bypass
+-- OS mismatch (CRLF) --> deploy pipeline LF fix
+-- No automation (no scheduled tasks) --> satellite_*_daemon.ps1
+-- Operator error (cmd, placeholder) --> fleet_satellite_setup_auto + probe doc
```

---

## INC-120: Red LAVIE monitor recovery failed repeatedly (SyntaxError, path, self-kill)

| Field | Detail |
|---|---|
| **Date** | 2026-06-15 JST |
| **Detection** | User could not bring Red LAVIE monitor `:8111` online after multiple attempts. Worker `:5682` OK intermittently. |
| **Impact** | Red LAVIE excluded from fleet metrics/thermal/stability; K10 could not observe or recover host; CAE dispatch degraded. |
| **Root Cause (5 Why)** | **A SyntaxError:** Why1: monitor would not bind :8111. Why2: `monitor_agent.py` SyntaxError at line 155. Why3: third `try` in `get_cpu_usage()` missing `except`. Why4: Deployed via K10 :8123 without compile gate. Why5: No pre-serve `py_compile` on fleet script server.<br>**B Path:** Why1: `setup_monitor_node.ps1` download failed. Why2: WebClient wrote to `C:\monitor_agent.py`. Why3: User `yns-lavie` is non-admin. Why4: Default AgentPath was drive root.<br>**C Self-kill:** Why1: `red_lavie_start_monitor.ps1` exited silently after `Saved:`. Why2: Stop-Process matched running PowerShell because `-AgentPath ...monitor_agent.py` appeared in CommandLine. Why3: Filter was `-match 'monitor_agent'` too broad.<br>**D Policy:** Red LAVIE default ExecutionPolicy blocked `-File` without Bypass. |
| **Fix** | 1. Fixed `monitor_agent.py` missing except/return.<br>2. Added `verify_fleet_script_server_gate.ps1` + hook in `start_k10_fleet_script_server.ps1`.<br>3. Narrowed process kill to `python(w).exe` + `monitor_agent.py` path in `red_lavie_start_monitor.ps1`, `setup_monitor_node.ps1`, `k10_red_lavie_auto_recovery.py`.<br>4. Default AgentPath -> `C:\clawstack_satellite\scripts\monitor_agent.py`.<br>5. Startup VBS registration in `red_lavie_start_monitor.ps1`.<br>6. Documented SOP in `trouble_history.md` [T036] and `red_lavie_stability_why_offline.md`. |
| **Files** | `scripts/monitor_agent.py`, `scripts/red_lavie_start_monitor.ps1`, `scripts/setup_monitor_node.ps1`, `scripts/verify_fleet_script_server_gate.ps1`, `scripts/start_k10_fleet_script_server.ps1`, `scripts/k10_red_lavie_auto_recovery.py`, `data/workspace/memory/trouble_history.md`, `docs/troubleshooting/red_lavie_stability_why_offline.md` |
| **Verification** | Red LAVIE local: `:8111/metrics` 200 + `:5682/healthz` 200; `RED_LAVIE_MONITOR_OK`; K10 gate: `FLEET_SCRIPT_SERVER_GATE_OK`. |
| **Lessons Learned** | Never serve Python fleet scripts without `py_compile`. Never kill processes with broad CommandLine match when script args include the target filename. Standard-user satellites must not default to `C:\` paths. |
| **Prevention** | Mandatory gate before :8123; bd key `red-lavie-monitor-recovery-inc120`; ByteRover curate; agents must read [T036] before Red LAVIE monitor work. |

---

## INC-119: ThinkPad L590 offline due to bash syntax error (CRLF) in stability script

| Field | Detail |
|---|---|
| **Date** | 2026-06-15 JST |
| **Detection** | Tailscale node registry indicated yasu-thinkpad-l590 went offline (~5h ago) and Monitor Agent (port 8111) was unreachable. |
| **Impact** | ThinkPad L590 was suspended (slept), making it unavailable for CAE/job offloading. |
| **Root Cause (5 Why)** | Why1: ThinkPad entered suspend state. Why2: Auto-suspend (lid close / idle) was not inhibited. Why3: Stability enforcement script (`thinkpad_host_stability.sh`) crashed with exit code 2. Why4: Script had Windows CRLF line endings, causing syntax error (`set: pipefail\r: invalid option name`). Why5: Git checkout CRLF settings on K10, and files were sent via SCP without conversion. |
| **Fix** | 1. Converted all scripts under `D:\Clawdbot_Docker_20260125\scripts\` to LF line endings.<br>2. Created quality incident report file.<br>3. Prepared deployment via `k10_thinkpad_fleet_setup.py` once ThinkPad is physically woken up. |
| **Files** | `scripts/thinkpad_host_stability.sh`, `scripts/thinkpad_lid_no_sleep.sh`, `quality_incident_report_20260615_thinkpad_sleep_outage.md` |
| **Verification** | Pending: Requires user to physically wake up ThinkPad, after which `k10_thinkpad_fleet_setup.py` will redeploy and verify. |
| **Lessons Learned** | Linux target scripts checked out on Windows must be explicitly converted to LF or verified before SSH/SCP deployment. |
| **Prevention** | Verify `.gitattributes` forces LF for `*.sh` files. Build automated LF conversion checks inside the deploy/SSH utility functions. |

---

## INC-118: Uptime drop below 70% on satellite nodes (LAVIE, Red LAVIE, G3)

| Field | Detail |
|---|---|
| **Date** | 2026-06-14 JST |
| **Detection** | Connectivity audit 24h summaries showed low estimated uptime (LAVIE: 41.7%, Red LAVIE: 0.8%, G3: 0.0%). |
| **Impact** | Dedicated compute power from core worker nodes was unavailable for heavy CAE simulations and DXF-to-3D reconstructions, causing K10 to handle workloads sequentially or queue them. |
| **Root Cause (5 Why)** | **LAVIE**: Why1: Monitor agent stopped for 86h. Why2: Host rebooted/slept. Why3: Startup task scheduler missing or misconfigured.<br>**Red LAVIE**: Why1: Job worker port offline. Why2: Host rebooted and worker process not running. Why3: VBS startup script StartRedLavieJobWorker.vbs crashed on launch. Why4: Script used Chr(34) executable wrapping with arguments which fails under WScript.Shell.Run. Why5: Remote setup script red_lavie_start_job_worker.ps1 was not boot-tested.<br>**G3**: Why1: n8n and IATF offline. Why2: Docker containers not running. Why3: Docker engine didn't start containers at boot (Docker Desktop requires user login or quiet/service mode). Why4: G3 node lacks persistent keepalive/startup scheduler for compose. |
| **Fix** | 1. Corrected `red_lavie_start_job_worker.ps1` VBScript runner generation to use powershell-mediated hidden execution (resolves quoting syntax error).<br>2. Deployed corrected Startup scripts for Red LAVIE and Main LAVIE.<br>3. Scheduled keepalive watchdogs on K10 reboot to automatically recover offline nodes.<br>4. Prepared local startup tasks for G3 docker compose up. |
| **Files** | `scripts/red_lavie_start_job_worker.ps1`, `data/workspace/memory/trouble_history.md` |
| **Verification** | 1. PowerShell syntax verification passed on `red_lavie_start_job_worker.ps1`.<br>2. Connectivity summaries updated on K10 showing monitor metrics online. |
| **Lessons Learned** | 1. Windows startup scripts using WScript.Shell.Run should wrap executable and arguments cleanly, preferably calling powershell.exe to handle complex paths.<br>2. Every node needs both local service auto-start (Scheduled Tasks) and remote watchdog auto-recovery. |
| **Prevention** | Run connectivity watchdogs as startup tasks on K10 boot (registered via `register_cae_loops_startup_tasks.ps1`). Enforce 6h host-stability sweeps. |

---

## INC-117: Gemma4 7PC Honki ZIP partially adopted into fleet role planner

| Field | Detail |
|---|---|
| **Date** | 2026-06-11 JST |
| **Detection** | User requested adoption of `Gemma4_7PC_AI_Company_FullStack_Honki.zip` if valuable. |
| **Impact** | Without mapping, 7PC kit docs were disconnected from live K10/LAVIE/Red LAVIE/ThinkPad fleet. |
| **Root Cause (5 Why)** | **Why1**: Kit was generic 7-PC template. **Why2**: Clawstack already has LiteLLM, n8n, RAG. **Why3**: Full zip deploy would duplicate ai_gateway and obsidian_rag. **Why4**: No fleet-specific role map existed. **Why5**: Gemma4 remains eval-only per prior bd decision. |
| **Fix** | ADOPT_PARTIAL: `fleet_7pc_role_map.yaml`, `k10_fleet_7pc_role_plan.py`, prompts under `data/workspace/prompts/gemma4_7pc/`, reference at `protocols/gemma4_7pc_honki/`, `k10_fleet.ps1 7pc plan`. Skipped ai_gateway, obsidian_rag sample, default Gemma4 promotion. |
| **Files** | `data/workspace/fleet_7pc_role_map.yaml`, `scripts/k10_fleet_7pc_role_plan.py`, `docs/adoption/gemma4_7pc_fullstack_ADOPTION.md`, `protocols/gemma4_7pc_honki/` |
| **Verification** | `k10_fleet.ps1 7pc plan` writes `fleet_7pc_role_plan.json` from K10 any cwd. |
| **Lessons Learned** | Honki ZIPs: extract role/policy/prompts; wire to fleet; never duplicate LiteLLM gateway. |
| **Prevention** | Adoption doc lists skipped duplicates; model_policy keeps gpu_buy_now false. |

---

## INC-116: Red LAVIE lacked K10-side stability enforce and connectivity watch

| Field | Detail |
|---|---|
| **Date** | 2026-06-11 JST |
| **Detection** | User requested Red LAVIE connection stabilization and stronger monitoring. Monitor `:8111` was healthy but `/host_stability/apply` returned 404 (old agent). `exec_bridge :5679` timed out while worker `:5682` was OK. |
| **Impact** | Sleep/reboot could drop Red LAVIE from fleet; no 24h RCA log or auto-recovery on return. |
| **Root Cause (5 Why)** | **Why1**: No Red LAVIE-specific stability/watch scripts. **Why2**: Main LAVIE pattern not replicated. **Why3**: Red LAVIE monitor_agent not refreshed with host_stability endpoint. **Why4**: exec_bridge unreliable on Red LAVIE. **Why5**: Red LAVIE Windows job worker was not used as stability channel (unlike main LAVIE Linux worker). |
| **Fix** | Added `red_lavie_host_stability.ps1`, `k10_red_lavie_stability_enforce.py` (monitor -> refresh -> worker PS1 fallback), `k10_red_lavie_connectivity_watch.py`, `k10_red_lavie_auto_recovery.py`, fleet watchdog. |
| **Files** | `scripts/red_lavie_host_stability.ps1`, `scripts/k10_red_lavie_common.py`, `scripts/k10_red_lavie_stability_enforce.py`, `scripts/k10_red_lavie_connectivity_watch.py`, `scripts/k10_red_lavie_auto_recovery.py`, `scripts/start_k10_red_lavie_connectivity_watchdog.ps1`, `docs/troubleshooting/red_lavie_stability_why_offline.md` |
| **Verification** | `python scripts/k10_red_lavie_stability_enforce.py` -> `RED_LAVIE_HOST_STABILITY_OK`; connectivity summary `overall_now=online`. |
| **Lessons Learned** | Windows satellites: job_worker is a valid host-ops channel when exec_bridge is down. Label channel in artifacts. |
| **Prevention** | Fleet 24x7 start includes Red LAVIE connectivity watchdog; 6h stability re-enforce; offline->online auto-recovery (30m cooldown). |

---

## INC-115: ThinkPad L590 lid-close suspend broke SSH/Tailscale/RDP fleet access

| Field | Detail |
|---|---|
| **Date** | 2026-06-11 JST |
| **Detection** | User clarified Gemini RCA targeted ThinkPad (`100.66.63.9`), not main LAVIE. Lid-close suspend and GNOME RDP conflicts caused recurring SSH loss. |
| **Impact** | K10 could not dispatch CAE/jobs to ThinkPad during suspend; RDP unreliable when lid closed. |
| **Root Cause (5 Why)** | **Why1**: SSH dropped when lid closed. **Why2**: systemd-logind default suspends on lid. **Why3**: No fleet-wide enforce from K10. **Why4**: Existing `thinkpad_lid_no_sleep.sh` was not wired to watchdog/recovery. **Why5**: GNOME Remote Desktop competed with xrdp on 3389. |
| **Fix** | Added `thinkpad_host_stability.sh`, `k10_thinkpad_stability_enforce.py`, `k10_thinkpad_connectivity_watch.py`, `k10_thinkpad_auto_recovery.py`, fleet watchdog starter. Masks sleep targets, xrdp+XFCE, disables gnome-remote-desktop, 5-min heartbeat timer, 6h re-enforce while online. |
| **Files** | `scripts/thinkpad_host_stability.sh`, `scripts/thinkpad_ssh_common.py`, `scripts/k10_thinkpad_stability_enforce.py`, `scripts/k10_thinkpad_connectivity_watch.py`, `scripts/k10_thinkpad_auto_recovery.py`, `scripts/start_k10_thinkpad_connectivity_watchdog.ps1`, `docs/troubleshooting/thinkpad_stability_why_offline.md` |
| **Verification** | `python scripts/k10_thinkpad_stability_enforce.py` prints `THINKPAD_HOST_STABILITY_OK`; connectivity summary shows `overall_now=online`. |
| **Lessons Learned** | Ubuntu fleet nodes need the same K10-side enforce + watch pattern as Windows LAVIE, via SSH not exec_bridge. |
| **Prevention** | Fleet 24x7 start includes ThinkPad connectivity watchdog; recovery runs on offline->online transition with 30m cooldown. |

---

## INC-114: Main LAVIE recovery applied power settings to Linux job worker instead of Windows host

| Field | Detail |
|---|---|
| **Date** | 2026-06-11 JST |
| **Detection** | Auto-recovery reported 401 on monitor/docker steps; stability enforce returned `/bin/sh: powershell: not found`. |
| **Impact** | Anti-sleep powercfg and scheduled keepalive never reached Windows host; outages continued (~28% 24h uptime). |
| **Root Cause (5 Why)** | **Why1**: powercfg did not run on LAVIE. **Why2**: Commands went to job worker `:5682`. **Why3**: Worker container is Linux (`/bin/sh`). **Why4**: Recovery used `dispatch_shell` with wrong token source (`router.auth` empty -> 401) and wrong execution plane. **Why5**: Windows host control path (`exec_bridge :5679`) was not used for stability scripts. |
| **Fix** | Added `k10_lavie_exec_bridge.py`, `lavie_host_stability.ps1`, `k10_lavie_stability_enforce.py` (HTTP deploy + inline powercfg fallback). `k10_lavie_auto_recovery.py` uses exec_bridge for host ops + `SATELLITE_JOB_TOKEN` for worker ops. Connectivity watch enforces stability every 6h while online. |
| **Files** | `scripts/k10_lavie_exec_bridge.py`, `scripts/lavie_host_stability.ps1`, `scripts/k10_lavie_stability_enforce.py`, `scripts/k10_lavie_auto_recovery.py`, `scripts/k10_lavie_connectivity_watch.py`, `scripts/k10_verify_satellite_node.py` |
| **Verification** | Pending LAVIE online window: `python scripts/k10_lavie_stability_enforce.py` should print `LAVIE_HOST_STABILITY_OK` and create scheduled task `ClawstackLavieKeepalive`. |
| **Lessons Learned** | Satellite has two execution planes: Linux job worker vs Windows exec_bridge. Power/network stability must target Windows host. |
| **Prevention** | All host stability/recovery docs and scripts label channel explicitly (`exec_bridge_windows_host` vs `job_worker_linux`). |

---

## INC-113: Red LAVIE job worker could not be started remotely because execution ingress was closed

| Field | Detail |
|---|---|
| **Date** | 2026-06-10 JST |
| **Detection** | User requested starting Red LAVIE `job_worker :5682`. K10 probes showed Red LAVIE monitor-agent `:8111` was reachable and healthy, but `:5682` worker and `:5679` exec_bridge timed out. |
| **Impact** | K10 could classify Red LAVIE as a dedicated medium-heavy worker, but could not actually dispatch jobs until a worker process was started on Red LAVIE. |
| **Root Cause (5 Why)** | **Why1**: K10 could not start the worker remotely. **Why2**: The existing remote execution paths (`exec_bridge :5679`, `job_worker :5682`) were not listening. **Why3**: SMB/RPC/remote task attempts returned Access Denied, WinRM/SSH were unavailable, and `monitor_agent :8111` intentionally exposes metrics/diagnostics only. **Why4**: The fleet bootstrap relied on one-time local PowerShell setup for command-ingress services. **Why5**: Red LAVIE's monitor path was restored before its command-ingress path, leaving an observable but not controllable node. |
| **Fix** | Added `scripts/red_lavie_start_job_worker.ps1`, a one-time Red LAVIE bootstrap that downloads `lavie_job_worker.py` from K10, writes the satellite token to Red LAVIE local `.env`, opens firewall TCP `5682`, starts the worker hidden, and registers startup VBS. |
| **Files** | `scripts/red_lavie_start_job_worker.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | K10 served `http://100.119.18.40:8123/red_lavie_start_job_worker.ps1` with HTTP 200. PowerShell parser check passed. Live worker verification remains pending until the command is run once on the Red LAVIE desktop. |
| **Lessons Learned** | A monitor-only node is visible but not controllable. Every dedicated worker needs both health telemetry and a command ingress bootstrap path. |
| **Prevention** | Keep node bootstrap scripts available from K10 `:8123`. For future Windows workers, install monitor-agent and job-worker startup in the same setup pass, then verify both `:8111/metrics` and `:5682/healthz`. |

---

## INC-112: Red LAVIE promoted to unrestricted dedicated medium-heavy worker policy

| Field | Detail |
|---|---|
| **Date** | 2026-06-10 JST |
| **Detection** | User clarified that Red LAVIE is not used for business work and can be used freely by K10. |
| **Impact** | Before this policy update, Red LAVIE was preferred for several categories but heavy routing still depended on K10 being busy or resource pressured. This left a dedicated Core i7-class node underused while K10 could remain CPU-bound. |
| **Root Cause (5 Why)** | **Why1**: Red LAVIE did not always receive work first. **Why2**: The router treated it as a preferred candidate, not a dedicated worker. **Why3**: Previous assumptions protected user-facing PCs from daytime heavy load. **Why4**: Red LAVIE's user context was not explicitly encoded. **Why5**: Fleet policy mixed hardware capacity with human-usage assumptions instead of storing both separately. |
| **Fix** | Added `red_lavie.user_business_use: false`, `profile: dedicated_medium_heavy`, and `red_lavie_dedicated_categories` to `data/workspace/cae_workload_router.yaml`. Added `data/workspace/red_lavie_node_registry.json` so dispatch can resolve the Red LAVIE worker URL once the worker is started. Updated `scripts/cae_workload_router.py` so healthy Red LAVIE receives dedicated medium/heavy CAE categories first, while preserving CPU/RAM/temperature guards and blocking fallback to regular LAVIE for heavy work when Red LAVIE is unavailable. |
| **Files** | `data/workspace/cae_workload_router.yaml`, `data/workspace/red_lavie_node_registry.json`, `scripts/cae_workload_router.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts\cae_workload_router.py` passed. Mocked router checks selected `red_lavie` for `press_drawing` and `resin_fill_cad` when Red LAVIE was dispatchable, and selected `k10` instead of regular LAVIE when Red LAVIE was unavailable. |
| **Lessons Learned** | Fleet routing must encode both machine capability and human-usage constraints. Dedicated PCs should be promoted explicitly, but thermal/load guards remain non-negotiable. |
| **Prevention** | Keep business-use metadata per node. Do not send heavy work to regular LAVIE as a fallback unless explicitly re-enabled after stability evidence. |

---

## INC-109: Fleet nodes needed 24-hour local diagnostics for post-outage RCA

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User requested that LAVIE and other PCs keep detailed local logs for root cause analysis and stable continuous operation after LAVIE was found stopped at BIOS. |
| **Impact** | K10-side logs can show loss of connectivity, worker timeouts, and uploaded evidence, but if a node reboots, loses Tailscale, or stops before upload, the last local facts may remain only on the affected PC. This weakens RCA and delays safe workload recovery. |
| **Root Cause (5 Why)** | **Why1**: BIOS/power/thermal failures can stop Windows services and upload paths. **Why2**: Existing fleet evidence was useful but centered on periodic K10 uplink and 6-hour event summaries. **Why3**: Nodes did not expose a first-class local 24-hour diagnostic endpoint. **Why4**: Metrics, thermal actions, agent lifecycle, upload failure, and Windows event summaries were not all tied together in a bounded local JSONL stream. **Why5**: Logging design optimized for dashboard visibility more than node-side black-box recovery. |
| **Fix** | Extended `scripts/monitor_agent.py` with node-local diagnostics under `%ProgramData%\Clawstack\monitor_agent\node_diagnostics\<hostname>\diagnostic_YYYYMMDD.jsonl` by default. Added 24-hour retention pruning, `agent_start`/`agent_stop`, periodic metrics snapshots, high CPU/RAM/temp/disk/LHM alerts, thermal throttle events, harvester watchdog events, fleet evidence upload status, and `/diagnostics` HTTP output. |
| **Files** | `scripts/monitor_agent.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts\monitor_agent.py` passed. A local scratch test with `NODE_DIAGNOSTIC_DIR=scratch\node_diag_test` wrote one `self_test` event, reported one diagnostic file, read one recent record, and then cleaned up the scratch directory. |
| **Lessons Learned** | For remote fleet stability, every node needs its own short-retention black-box log. K10 upload is valuable, but local evidence must survive transient network/service loss. |
| **Prevention** | Keep 24-hour diagnostics enabled by default on all monitor-agent nodes. During incident recovery, check both `http://localhost:8111/diagnostics` on the affected PC and the uploaded K10 fleet evidence. |

---

## INC-107: ThinkPad GNOME RDP Connection Required Credential, Desktop Path, and Lock-State Fixes

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User reported that the ThinkPad RDP window either did not appear, was not on the visible desktop, or opened briefly and closed immediately before finally displaying successfully. |
| **Impact** | User could not access the Ubuntu ThinkPad screen through Windows Remote Desktop despite SSH and TCP 3389 being reachable. Repeated manual attempts could have led to unnecessary Chrome Remote Desktop installation or unsafe display-manager changes. |
| **Root Cause (5 Why)** | Why1: The RDP window closed immediately or did not appear to the user. Why2: The shortcut was initially created under `C:\Users\yasu\Desktop`, while the actual visible desktop was `C:\Users\yasu\OneDrive\デスクトップ`. Why3: After the shortcut was visible, Windows saved TERMSRV credentials and RDP settings caused GNOME RDP errors: `NTLM MIC verification failed` and `client authentication failure`. Why4: After clearing credentials, GNOME still rejected sessions with `Session creation inhibited`. Why5: The active GNOME Wayland session had screen lock/idle lock state that inhibited remote desktop session creation. |
| **Fix** | Created backups and rollback script first. Enabled GNOME Remote Desktop RDP over Tailscale without installing Chrome Remote Desktop or changing GDM/GRUB. Recreated `ThinkPad-L590.rdp` on the actual OneDrive desktop. Cleared Windows saved `TERMSRV/100.66.63.9` credentials. Disabled GNOME screen lock/idle lock temporarily, unlocked the local session, and restarted `gnome-remote-desktop`. |
| **DB Record** | Stored full structured trial history in `data/workspace/universal_growth.db` table `ops_trial_history` with `record_id=ops-thinkpad-rdp-20260609`; also mirrored to `data/workspace/ops_trial_history.jsonl`. |
| **Verification** | `grdctl status` showed RDP enabled and active; `ss` showed port 3389 listening; K10 `Test-NetConnection 100.66.63.9 -Port 3389` succeeded; user confirmed the ThinkPad screen displayed successfully. |
| **Vivobook Rollout** | User later confirmed Vivobook could also open the ThinkPad screen after using a deterministic `C:\ThinkPad_RDP` folder and creating both `ThinkPad-L590.rdp` and `ThinkPad L590.lnk`. The reusable password was stored in Windows Credential Manager on the client side, not in the tracked MD/JSONL records. This avoided OneDrive/Desktop path ambiguity on Vivobook. |
| **Lessons Learned** | For Ubuntu GNOME Wayland, prefer GNOME Remote Desktop RDP before Chrome Remote Desktop. Always resolve the actual Windows desktop folder before creating visible shortcuts. Clear saved RDP credentials when GNOME reports NTLM MIC failures. If GNOME logs `Session creation inhibited`, unlock the session and disable idle/screen lock before retrying. |
| **Prevention** | Keep SSH as recovery path, create rollback scripts before remote-desktop changes, avoid GDM/GRUB edits for first-pass screen sharing, persist all remote-access trial-and-error records into `ops_trial_history`, and use a fixed visible folder such as `C:\ThinkPad_RDP` when a Windows client's desktop location is unclear. |

## INC-106: ThinkPad L590 Ubuntu Added as SSH-Controlled Medium Fleet Node

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User requested that the newly SSH-connected Ubuntu ThinkPad be added to the Growth Dashboard and receive work from K10. |
| **Impact** | Before this change, ThinkPad was visible on Tailscale and SSH-reachable but not part of K10 fleet status, workload allocation, or guarded job dispatch. K10 could not safely use its spare CPU/RAM capacity. |
| **Root Cause (5 Why)** | Why1: ThinkPad did not appear in the dashboard or router. Why2: Existing fleet nodes were modeled as Windows monitor-agent or HTTP job-worker nodes. Why3: Ubuntu SSH control was not represented as a first-class transport. Why4: The dashboard expected `:8111/metrics` rather than K10-collected SSH metrics. Why5: No registry or guarded dispatch path existed for Linux SSH satellites. |
| **Fix** | Added `data/workspace/thinkpad_node_registry.json`; added `scripts/thinkpad_ssh_metrics.py` to collect CPU/RAM/temperature over SSH and write dashboard JSON; added `scripts/k10_thinkpad_ssh_dispatch.py` for allow-listed SSH jobs; updated `scripts/fleet_node_registry.py`, `scripts/update_fleet_operations_status.py`, `scripts/cae_workload_router.py`, `data/workspace/cae_workload_router.yaml`, and `data/workspace/apps/growth_dashboard/index.html` to include ThinkPad as a guarded medium SSH node. |
| **Verification** | `python -m py_compile` passed for modified Python files. `python scripts\thinkpad_ssh_metrics.py --json` returned ThinkPad metrics: i7-8565U, 4C/8T, RAM 14.79GB, CPU about 0.4%, RAM 13.8%, temp about 40C. `python scripts\k10_thinkpad_ssh_dispatch.py --job-type health_snapshot --json` completed successfully. `python scripts\cae_workload_router.py --category qms_iatf_analysis --json` selected `host=thinkpad` with SSH load guard OK. |
| **Lessons Learned** | Linux SSH satellites need a distinct transport model. Treating every node as a Windows monitor-agent endpoint hides usable capacity. |
| **Prevention** | Keep SSH nodes behind registry metadata, load guards, allow-listed jobs, and explicit blocked workload lists. Do not send heavy solvers or long renders until a real worker and thermal history are proven. |

## INC-105: YouTube IATF Analysis Dashboard Showed Samples Without Pipeline Progress

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User reported that the Growth Dashboard "YouTube IATF Analysis" section had no visible progress. |
| **Impact** | The dashboard hid actual pipeline status: indexed videos, analyzed DB summaries, summary failures, and transcript-missing cases were not visible. |
| **Root Cause (5 Why)** | Why1: The section only showed representative rows. Why2: `iatf_youtube_summary.json` used a legacy list-only format. Why3: `export_knowledge_history.py` could overwrite the summary with the old 20-row export. Why4: The dashboard did not reconcile channel index, processed IDs, and DB records. Why5: No freshness/progress metrics were required for recurring data pipelines. |
| **Fix** | Rebuilt `scripts/export_iatf_dashboard.py` to export v2 JSON with progress counts, missing summary examples, and up to 80 rows. Updated `scripts/export_knowledge_history.py` to delegate YouTube export to the new script. Updated `data/workspace/apps/growth_dashboard/index.html` to show indexed/analyzed/processed/failed/missing counts. Refreshed the YouTube index. |
| **Files** | `scripts/export_iatf_dashboard.py`, `scripts/export_knowledge_history.py`, `data/workspace/apps/growth_dashboard/index.html`, `data/workspace/apps/growth_dashboard/iatf_youtube_summary.json`, `data/workspace/iatf_auditing_youtube_index.json`, `quality_incident_report_20260609_iatf_youtube_dashboard_stale.md` |
| **Verification** | `python -m py_compile scripts\export_iatf_dashboard.py scripts\export_knowledge_history.py`; `python scripts\update_iatf_auditing_youtube_index.py` produced `videos=349 total=349`; `python scripts\export_iatf_dashboard.py` produced `items=80 analyzed=346 indexed=349 failed=28`; HTTP checks returned 200 for dashboard page and JSON. |
| **Lessons Learned** | A recurring analysis panel must show freshness and progress, not just sample content. Otherwise working pipelines look idle. |
| **Prevention** | Require pipeline dashboards to expose indexed, processed, analyzed, failed, missing, and generated-at fields. |

## INC-104: Growth Dashboard Autonomous Improvements Feed Did Not Reflect Recent AI Commits

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User reported that the Growth Dashboard "Autonomous Code Improvements" section was not adding recent entries, creating concern that collected web knowledge was low-value. |
| **Impact** | Recent AI implementation work, including dashboard source counts, fleet routing, source scouting, and LAVIE guard improvements, was invisible in the improvement-history panel. |
| **Root Cause (5 Why)** | Why1: Recent improvements were not displayed. Why2: `autonomous_improvements.json` was only written by `scripts/autonomous_coder.py`. Why3: That flow only covers a narrow Moldflow/Cross-WLF automation path. Why4: Normal AI implementation commits were not exported to the dashboard. Why5: The dashboard wording implied broad AI improvement tracking while the data feed was narrow. |
| **Fix** | Added `scripts/export_autonomous_improvements_from_git.py` to generate dashboard entries from recent Git implementation commits while preserving legacy autonomous-coder entries. Regenerated `data/workspace/apps/growth_dashboard/autonomous_improvements.json`. |
| **Files** | `scripts/export_autonomous_improvements_from_git.py`, `data/workspace/apps/growth_dashboard/autonomous_improvements.json`, `quality_incident_report_20260609_autonomous_improvements_not_updating.md` |
| **Verification** | `python -m py_compile scripts\export_autonomous_improvements_from_git.py`; `python scripts\export_autonomous_improvements_from_git.py` produced `git_records=16 total_records=20`. |
| **Lessons Learned** | A dashboard panel must reflect the real operational path. If AI coding happens through normal commits, Git history must be part of the evidence feed. |
| **Prevention** | Keep source collection, implementation commits, and dashboard evidence connected through explicit exporters and freshness checks. |

## INC-103: Regular LAVIE continued receiving heavy CAE while Red LAVIE had spare capacity but worker entry was offline

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User observed that work could be shifted from LAVIE to Red LAVIE. Live checks showed Red LAVIE monitor metrics were healthy (`:8111/metrics` HTTP 200, CPU about 8%, RAM about 23.6%, temp about 60.9C), but Red LAVIE CAE job worker `:5682/healthz` timed out. Regular LAVIE was still the only dispatchable worker and could receive `resin_fill_cad`. |
| **Impact** | Heavy OpenFOAM/Moldflow-style CAE could keep landing on regular LAVIE, increasing timeout and disconnect risk, while Red LAVIE had capacity but lacked an active worker entry. |
| **Root Cause (5 Why)** | **Why1**: Regular LAVIE still received heavy work. **Why2**: Red LAVIE priority existed only when its worker was reachable. **Why3**: When Red LAVIE was unavailable, the router allowed fallback to any dispatchable satellite, including regular LAVIE. **Why4**: Continuous T&E used a fixed `lavie` node path and did not honor `red_lavie` routing as a first-class satellite host. **Why5**: CAE dispatch used regular LAVIE workspace defaults instead of node-specific `cae_workspace` and `cae_repo_root`, making Red LAVIE promotion fragile. |
| **Fix** | Added `red_lavie_preferred_categories`, `lavie_heavy_fallback_enabled: false`, and controlled `lavie_fallback_categories` to `data/workspace/cae_workload_router.yaml`. Updated `scripts/cae_workload_router.py` to route preferred categories to Red LAVIE first and block heavy fallback to regular LAVIE when Red LAVIE is unavailable. Updated `scripts/k10_satellite_cae_dispatch.py` to treat `red_lavie` as a valid satellite host and use node-specific workspace/repo paths. Updated `scripts/k10_lavie_continuous_te_loop.py` default node selection to `auto`, so continuous CAE honors router decisions and records the selected node. |
| **Verification** | `python -m py_compile scripts\cae_workload_router.py scripts\k10_satellite_cae_dispatch.py scripts\k10_lavie_continuous_te_loop.py` passed. A mocked healthy Red LAVIE selected `red_lavie` for `resin_fill_cad` and `press_bending`. Live router with Red LAVIE worker offline returned `host=k10` for `resin_fill_cad` with reason `red_lavie preferred but unavailable; regular lavie heavy fallback disabled`. A once-run continuous loop stopped at `route_guard` rather than dispatching the heavy job to regular LAVIE. |
| **Lessons Learned** | Capacity headroom is only useful if the execution entry is online and the scheduler treats the node as a first-class target. Heavy fallback should be explicit, not accidental. |
| **Prevention** | Keep Red LAVIE as preferred for `resin_fill_*` and medium press categories, require monitor-agent and worker health before dispatch, and do not send heavy OpenFOAM jobs to regular LAVIE unless explicitly re-enabled. |

## INC-102: Scribd pipeline mixed source scouting, downloading, ingestion, and autonomous code edits

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User requested more active collection of related Scribd materials. Review found that `run_scribd_pipeline.ps1` invoked `scribd_downloader.py`, `scribd_ingestion.py`, and `autonomous_coder.py` in one scheduled flow. |
| **Impact** | The pipeline could mix legitimate source discovery with browser-driven downloads and automatic code changes, increasing copyright/ToS risk and operational risk. It also lacked a metadata-first report for Moldflow, CETOL, press die, and IATF source discovery. |
| **Root Cause (5 Why)** | **Why1**: Scribd collection was built as a direct download pipeline. **Why2**: The daily job had no safe metadata-only stage. **Why3**: Download and autonomous code modification were enabled by default in the same flow. **Why4**: The pipeline optimized for acquiring files rather than lawful source triage and evidence traceability. **Why5**: There was no explicit no-bypass/no-unauthorized-download safety policy in the script outputs. |
| **Fix** | Added `scripts/scribd_related_source_scout.py` to inventory existing downloads, score them by target domain, and generate Scribd search URLs without downloading. Updated `scripts/run_scribd_pipeline.ps1` so downloads require `SCRIBD_ENABLE_AUTHORIZED_DOWNLOAD=1` and autonomous code edits require `SCRIBD_ENABLE_AUTONOMOUS_CODER=1`. Updated the scheduled task description via `scripts/install_scribd_pipeline_schedule.ps1`. |
| **Verification** | `python -m py_compile scripts\scribd_related_source_scout.py` passed. Scout run wrote `data/workspace/scribd_related_source_scout_status.json` and `.md`, inventorying 38 local documents and 17 priority search candidates. Scheduled task `Clawstack_Scribd_Daily_Pipeline` was re-registered successfully. |
| **Lessons Learned** | Source scouting, authorized downloading, ingestion, and autonomous code changes must be separate gates. Metadata-first collection gives useful direction without increasing legal or operational exposure. |
| **Prevention** | Keep Scribd downloads and autonomous code edits opt-in. Use the scout report for active prioritization, then ingest only user-authorized/local documents. |

## INC-101: LAVIE RCA logs lacked event categories and job resource snapshots

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | After INC-100, the user asked whether current log type and volume were sufficient. Review showed fleet evidence could detect offline status and TIMEOUTs, but could not reliably distinguish sleep, service failure, network drop, or resource exhaustion at job boundaries. |
| **Impact** | Next LAVIE disconnect could still require manual local Windows inspection because K10 did not receive compact event category summaries, before/after CAE job resource snapshots, or durable workload-guard activation records. |
| **Root Cause (5 Why)** | **Why1**: Logs showed symptoms but not enough transition context. **Why2**: Existing Windows event capture stored raw events, including message text that can mojibake on Japanese Windows. **Why3**: CAE job dispatch did not capture resource state before and after the job. **Why4**: Workload guard activation was visible in state JSON but not appended to an audit-style history. **Why5**: Logging was optimized for liveness, not post-incident root-cause classification. |
| **Fix** | Added compact Windows event summaries to `scripts/monitor_agent.py`, preserving event ID, provider, level, category, and counts for the last 6 hours. Added before/after monitor-agent resource snapshots to `scripts/lavie_job_worker.py` and returned them through `scripts/k10_satellite_cae_dispatch.py`. Added durable guard activation/expiry JSONL logging to `scripts/k10_lavie_continuous_te_loop.py`. |
| **Verification** | Static compile checks passed for all modified Python files. Targeted unit smoke checks verified event summary classification, resource snapshot failure-safe behavior, and guard log JSONL writing. |
| **Lessons Learned** | For distributed Windows fleet RCA, store compact typed facts rather than verbose localized messages. Job-boundary snapshots and guard-action history provide high diagnostic value with low log volume. |
| **Prevention** | Keep event summaries bounded by time and count, keep resource snapshots compact, and write guard changes as append-only JSONL so future disconnects can be reconstructed without excessive log volume. |

## INC-100: LAVIE disconnected after repeated resin_fill_cad TIMEOUTs and lacked a workload guard

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User reported that LAVIE became unreachable around 13:47. K10 logs showed Tailscale last seen at 13:50 JST, monitor evidence stopped at 12:44 JST, and `lavie365-resin_fill_cad-aac22e92` recorded TIMEOUT around 13:48 JST after repeated `resin_fill_cad` TIMEOUTs. |
| **Impact** | LAVIE became unavailable for fleet CAE work. The 24/365 loop continued probing and reporting `probe_fail`, while the previous allocation policy had no automatic brake for repeated heavy OpenFOAM failures. |
| **Root Cause (5 Why)** | **Why1**: LAVIE disappeared from Tailscale and worker probes timed out. **Why2**: The node was running repeated heavy `resin_fill_cad` trials with 1320s TIMEOUTs. **Why3**: The continuous loop only changed dry-run behavior after fail streaks and did not stop assigning heavy categories early. **Why4**: The router checked worker reachability but not monitor-agent CPU/RAM/temperature guardrails before dispatch. **Why5**: Fleet allocation treated online reachability as sufficient capacity evidence, so high load and repeated TIMEOUTs were not converted into an automatic cooldown. |
| **Fix** | Added satellite metrics gating in `scripts/cae_workload_router.py` using each node's monitor agent (`/metrics`) with CPU/RAM/temperature thresholds. Added LAVIE workload cooldown logic in `scripts/k10_lavie_continuous_te_loop.py`: repeated heavy-category failures or unsafe metrics activate a 180-minute guard and remove heavy OpenFOAM categories from that cycle. Added explicit thresholds to `data/workspace/cae_workload_router.yaml`. |
| **Verification** | Static compile checks passed for both Python files. A once-run while LAVIE is offline still exits with `probe_fail`, preserving existing behavior without dispatching new work to an unreachable node. |
| **Lessons Learned** | Online probes are not enough for fleet scheduling. Heavy CAE assignment must require both liveness and capacity health, and repeated TIMEOUTs must demote the workload before the node becomes unstable. |
| **Prevention** | Keep monitor-agent metrics available on all satellite nodes. Treat heavy-category TIMEOUT streaks as a scheduling signal, not only a solver result. Extend dashboard display later to show active `workload_guards` so guarded nodes are visible to the operator. |

## INC-099: Red LAVIE was underused while K10 was thermally constrained

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User noted that Red LAVIE is a Core i7 node with low CPU usage, about 17% RAM usage, and about 62C temperature, while K10 was often close to full CPU use and thermally throttled. Existing routing already probed `red_lavie` before `lavie`, but heavy categories still returned `k10` unconditionally. |
| **Impact** | K10 could continue receiving heavy CAE-style categories even when it was hot, memory pressured, or busy, leaving Red LAVIE available but underused. This increased K10 thermal throttling risk and reduced fleet throughput. |
| **Root Cause (5 Why)** | **Why1**: Red LAVIE did not receive enough work.<br>**Why2**: The router only prioritized Red LAVIE within the satellite probe order, not in heavy-category routing.<br>**Why3**: `category in heavy` returned K10 before considering K10 CPU/RAM/busy state.<br>**Why4**: Dashboard wording still described Red LAVIE as auxiliary, so operator intent and router behavior were not aligned.<br>**Why5**: Fleet policy had not been updated after Red LAVIE metrics showed medium-heavy headroom. |
| **Fix** | Updated `scripts/cae_workload_router.py` so heavy categories route to `red_lavie` when Red LAVIE is reachable and K10 is busy, RAM is above the preferred threshold, or CPU is high. Updated `data/workspace/apps/growth_dashboard/index.html` to show Red LAVIE as `ACTIVE / MEDIUM-HEAVY READY` and to dynamically recommend `MEDIUM-HEAVY READY` when CPU/RAM/temperature headroom is stable. |
| **Files** | `scripts/cae_workload_router.py`, `data/workspace/apps/growth_dashboard/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts/cae_workload_router.py` passed. A mocked `press_drawing` dry-run with Red LAVIE reachable and K10 at CPU 82% / RAM 83% selected `host=red_lavie`. Dashboard inline JavaScript compiled with Node `new Function`. `http://127.0.0.1:8088/apps/growth_dashboard/index.html` returned HTTP 200 and contained `MEDIUM-HEAVY READY` plus the 75C guard text. Live Red LAVIE monitor metrics at `:8111` returned HTTP 200, but `:5682/healthz` and `:5679/webhook/exec_bridge` timed out, so actual dispatch will remain on K10/LAVIE until Red LAVIE job worker or bridge is restored. |
| **Lessons Learned** | Candidate priority is not the same as routing policy. When K10 is thermally constrained, heavy and medium work must consider available satellite headroom before defaulting to K10. |
| **Prevention** | Keep Red LAVIE as the preferred K10 offload target for guarded medium-heavy work while it remains under 75C with CPU/RAM headroom. Avoid unconditional K10 routing for heavy categories when a healthier node is online. |

## INC-098: Fleet workload allocation lacked CPU hardware fields and user-work-PC guardrails

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User requested a dashboard summary showing each connected PC's CPU frequency, core count, thread count, RAM capacity, CPU usage, RAM usage, and whether the assigned work was appropriate. Existing `monitor_agent :8111/metrics` exposed CPU/RAM usage and temperature, but not CPU model, clock, physical cores, or logical threads. The growth dashboard also showed node health separately from workload suitability. |
| **Impact** | Heavy jobs could be assigned based only on online/offline status, without enough visibility into hardware capacity, thermal throttling, RAM pressure, or whether `mhn15` is being used by the user during daytime business hours. |
| **Root Cause (5 Why)** | **Why1**: Dashboard could not explain whether assignment was appropriate.<br>**Why2**: Metrics lacked CPU hardware fields and workload policy output.<br>**Why3**: Fleet monitoring originally focused on liveness/temperature, not allocation decisions.<br>**Why4**: Human usage context such as `mhn15` daytime business use was not encoded as a routing guardrail.<br>**Why5**: There was no hardware-aware allocation table tied to live monitor data. |
| **Fix** | Added CPU model, physical core count, logical thread count, max clock MHz, and current clock MHz to `scripts/monitor_agent.py` metrics. Added a live `Fleet Workload Allocation` table to `data/workspace/apps/growth_dashboard/index.html`, including thermal/RAM/CPU checks and a hard daytime light-only rule for `mhn15` from 08:00 to 19:00. |
| **Files** | `scripts/monitor_agent.py`, `data/workspace/apps/growth_dashboard/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts/monitor_agent.py` passed. Local import of the updated agent on K10 returned `13th Gen Intel(R) Core(TM) i9-13900HK`, `14C / 20T`, and clock fields. Dashboard inline JavaScript passed syntax validation by extracting script blocks and compiling with Node `new Function`. |
| **Lessons Learned** | Fleet assignment must distinguish "online" from "suitable for work." User-facing PCs need explicit human-use windows, not just resource thresholds. |
| **Prevention** | Keep workload allocation based on CPU/RAM/thermal/user-context gates. Do not assign heavy CAE/video/LLM batch jobs to `mhn15` during daytime even if metrics look idle. |

## INC-097: setup_monitor_node.ps1 reported success while monitor_agent was not started or registered

| Field | Detail |
|---|---|
| **Date** | 2026-06-08 JST |
| **Detection** | User ran the satellite setup command on `DESKTOP-UOVCG4T`. Output reached `=== Setup Complete ===`, but showed `[WARN] Process may have exited. Checking port...` and `-> Startup VBS:` with no path. Local inspection of `scripts/setup_monitor_node.ps1` showed the `Start-Process` assignment and `$vbsPath` assignment were accidentally embedded after mojibake comment text on the same commented lines. |
| **Impact** | Fleet node bootstrap could falsely report completion while no new `monitor_agent.py` process was launched and no startup VBS was registered. This could leave satellite machines absent from `:8111/metrics`, break fleet thermal visibility, and cause repeated manual setup attempts. |
| **Root Cause (5 Why)** | **Why1**: Setup showed warning and blank Startup VBS path.<br>**Why2**: `$proc` and `$vbsPath` were never assigned.<br>**Why3**: The executable statements were placed on lines that began with `#`, so PowerShell treated them as comments.<br>**Why4**: Earlier Japanese comments were mojibake-corrupted and lost clear line boundaries around code.<br>**Why5**: There was no syntax/behavior smoke test for `setup_monitor_node.ps1`, and the script printed `Setup Complete` without requiring `/metrics` success. |
| **Fix** | Rewrote `scripts/setup_monitor_node.ps1` as ASCII-only PowerShell. Restored actual `Start-Process`, added bounded `/metrics` verification, restored `$vbsPath` assignment, creates the Startup directory if missing, writes a correctly quoted ASCII VBS, and rejects WindowsApps Python aliases for startup reliability. |
| **Files** | `scripts/setup_monitor_node.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | K10 source `http://100.119.18.40:8123/monitor_agent.py` returned HTTP 200 and 41620 bytes before the fix. Code inspection after the fix confirms `Start-Process` and `$vbsPath` are executable statements, not comments. Full satellite verification requires rerunning the setup command on `DESKTOP-UOVCG4T` and confirming `/metrics` returns HTTP 200. |
| **Lessons Learned** | Setup scripts for old Windows hosts must stay ASCII-only. A final success banner must not imply service readiness unless the readiness probe succeeded. Avoid WindowsApps `pythonw.exe` aliases for background/startup registration. |
| **Prevention** | Keep fleet bootstrap scripts ASCII. Add/maintain a smoke check that rejects commented-out critical statements and requires `Metrics OK` for success. For future bootstrap changes, test on a real PowerShell host and inspect output for non-empty Startup VBS path. |

## INC-096: K10 monitor_agent reported false CPU temperature (27.9C fallback) due to LHM web server off and JSON parser mismatch

| Field | Detail |
|---|---|
| **Date** | 2026-06-07 JST |
| **Detection** | After integrating LibreHardwareMonitor (LHM) HTTP into `monitor_agent.py`, K10 `/metrics` showed `cpu_temp_celsius: 27.9`, `temp_source: fallback`, empty `cpu_package_c` / `core_max_c`. Manual LHM GUI read showed **CPU Package 84C / Core Max 86C** on NUCBOX_K10 (i9-13900HK). User restarted `monitor_agent` twice; first LHM `:8085` unreachable, then `lhm_error: no_cpu_temperatures_in_json`. Third attempt after parser fix: **HTTP 200 (76376 bytes), `temp_source: lhm_http`, CPU Package 84C, Core Max 85C**. |
| **Impact** | Thermal watchdog could not throttle correctly (85C WARNING / 95C CRITICAL thresholds useless). Dashboard and fleet monitors displayed **misleading idle-like 27.9C** while real silicon was **84-86C**. NVMe disk-full warning (`KIOXIA 99.2%`) also missing until LHM path worked. Risk of silent thermal damage during CAE/OpenRadioss if operators trust fallback. |
| **Root Cause (5 Why)** | **Why1**: `/metrics` showed 27.9C instead of 84C.<br>**Why2**: `get_cpu_temp()` used WMI/ACPI fallback because LHM HTTP path failed.<br>**Why3a** (phase 1): LHM Remote Web Server on `:8085` was **not running** when `monitor_agent` started (`Invoke-WebRequest` -> connection refused).<br>**Why3b** (phase 2): After LHM HTTP returned 200, parser returned `no_cpu_temperatures_in_json` because code expected **`SensorType` + numeric `Value`**, but LHM web JSON uses **`Type: "Temperature"`** and **`Value: "86.0 °C"`** (formatted string).<br>**Why4**: Integration assumed same field names as WMI/CIM samples; no contract test against live `data.json`.<br>**Why5**: No `lhm_ok` / `lhm_error` visibility in first deploy; fallback silently accepted as truth (Root Cause). |
| **Fix** | (1) **`scripts/monitor_agent.py`**: Added `get_lhm_metrics()` reading `http://127.0.0.1:8085/data.json` (env `LHM_HTTP_URL`). Parser handles `Type`, `SensorId`, string `Value`/`RawValue` (`"86.0 °C"`, `"99.2 %"`). Exposes `cpu_package_c`, `core_max_c`, `core_avg_c`, `nvme_temps`, `disk_warnings`, `lhm_ok`, `lhm_error`, `temp_source`. (2) Operational order documented: **LHM GUI + Options -> Remote Web Server -> Run (8085) BEFORE monitor_agent restart**. (3) Verify gate: `8085/data.json` HTTP 200 then `/metrics` must show `lhm_ok: True`. |
| **Files** | `scripts/monitor_agent.py`, `docs/INCIDENT_LOG.md`, `data/workspace/memory/trouble_history.md` **[T029]**, `docs/troubleshooting/k10_lhm_monitor_agent_20260607.md` |
| **Verification** | K10 PowerShell (2026-06-07): `8085/data.json` StatusCode 200, 76376 bytes. `/metrics`: `cpu_temp_celsius=84.0`, `cpu_package_c=84.0`, `core_max_c=85.0`, `core_avg_c=77.9`, `temp_source=lhm_http`, `lhm_ok=True`, `disk_warnings` includes KIOXIA 99.2% used. |
| **Lessons Learned** | (1) **Never treat ACPI/WMI fallback as CPU temperature on consumer mini-PCs** -- 27.9C was thermal-zone noise, not i9 load. (2) LHM web JSON schema != C# property names in docs (`Type` not `SensorType`; values often strings). (3) Liveness of `monitor_agent :8111` does not imply LHM `:8085` is up. (4) Parallel alert: KIOXIA E: drive 99.2% full surfaced only via LHM path. |
| **Prevention** | (1) Startup SOP: LHM + Remote Web Server Run -> verify 8085 -> start monitor_agent. (2) Alert if `lhm_ok=False` for >2 cycles or `temp_source=fallback` while CAE jobs active. (3) Add parser unit test with string-formatted LHM JSON sample. (4) Consider Windows Task Scheduler: LHM minimized at logon + Remote Web Server enabled. (5) Do not throttle or report fleet CPU temp without `temp_source=lhm_http`. (6) **Satellites (G3/LAVIE):** never use local repo paths; deploy from K10 `:8123` only. See `docs/troubleshooting/fleet_lhm_monitor_agent_runbook.md`. |

## INC-095: Distributed Fleet PC node failures left unattended due to simple liveness monitoring and lack of automatic recovery watchdogs

| Field | Detail |
|---|---|
| **Date** | 2026-06-04 JST |
| **Detection** | Multiple node failures (K10 C-drive full, Dynabook power off/sleep, LAVIE WSL/Docker container freezes, 41-script batch queue stall) were visible in logs/ports but left unresolved for days. |
| **Impact** | Entire distributed computational runs and automated mecha video pipelines were halted, requiring manual human recovery. |
| **Root Cause (5 Why)** | **Why1**: Issues were left unattended despite being visible.<br>**Why2**: `monitor_agent` only probed port ping status (HTTP 200) without checking system resource state or semantic progress.<br>**Why3**: The system was designed assuming a "happy path" where remote nodes were dedicated stable servers, neglecting consumer-grade PC risks.<br>**Why4**: Implementing remote automatic recovery was delayed due to local security barriers (WinRM TrustedHosts, local account privileges).<br>**Why5**: No systematic FMEA/FTA analysis was performed at the fleet architecture level, prioritizing individual functionality over overall cluster reliability (Root Cause). |
| **Fix** | (1) Registered full FMEA, FTA, Fishbone, Logic Tree, and 5 Whys analysis to `universal_growth.db`'s `growth_records` table (Record ID: 3054).<br>(2) Formulated fleet-wide recurrence prevention rules: mandatory sleep disables on remote nodes, startup trigger execution in Windows Task Scheduler, disk capacity relief guards (`clawstack_janitor.ps1`), and `--allow-offline` mode in deployment workflows (`autonomous_coder.py`). |
| **Files** | `scratch/register_pc_neglect_fmea.py`, `data/workspace/memory/trouble_history.md`, `docs/INCIDENT_LOG.md` |
| **Verification** | SQLite query on `universal_growth.db` confirms record insertion under domain `QUALITY` (ID 3054). |
| **Lessons Learned** | A cluster is only as reliable as its weakest node. Death of a node must trigger active watchdogs and asynchronous queue fallbacks rather than freezing the entire workflow or masking failures behind static ping dashboards. |
| **Prevention** | Mandate meaning gates before executions, enforce periodic disk cleanup, and ensure sleep/suspend states are disabled on all network participants. |

## INC-089: LAVIE moldflow fill video failed silently (missing ffmpeg/pyvista; worker timeout)

| Field | Detail |
|---|---|
| **Date** | 2026-06-02 JST |
| **Detection** | `lavie365-resin_fill_cad-live01` SUCCESS on LAVIE but no Telegram MP4; K10 loop dispatched `moldflow_fill_video_telegram.py` on LAVIE without ffmpeg on PATH; render stopped at 3 frames; job worker connect timeouts blocked zip/upload. |
| **Impact** | User saw FEM success but no 3D fill video; false sense that pipeline was complete; duplicate local render attempts on LAVIE. |
| **Root Cause (5 Why)** | **Why1**: No MP4 sent after SUCCESS.<br>**Why2**: LAVIE lacked ffmpeg; pyvista install intermittent.<br>**Why3**: Orchestrator assumed LAVIE had same toolchain as K10.<br>**Why4**: `maybe_notify` marked notification sent before verifying `telegram sent=True`.<br>**Why5**: No canonical cross-host path documented or enforced. |
| **Fix** | (1) `scripts/lavie_cae_video_support.py`: worker probe, optional LAVIE local fast path, default **K10 pull** (zip PUT :5689 -> pyvista+ffmpeg on K10 -> Telegram, delete after send).<br>(2) `k10_lavie_continuous_te_loop.py`: dispatch via support module; remember notification only if `ok`.<br>(3) `cae_te_remote_trial.py` + `cae_te_engine.py`: `CAE_FILL_VIDEO_TELEGRAM=0` on `host=lavie`.<br>(4) `lavie_usb_pack.ps1`: bundle `tools/ffmpeg.exe` + bootstrap script; sync runs `lavie_bootstrap_cae_video.ps1`. |
| **Files** | `scripts/lavie_cae_video_support.py`, `scripts/lavie_bootstrap_cae_video.ps1`, `scripts/k10_lavie_continuous_te_loop.py`, `scripts/k10_send_lavie_fill_video.py`, `scripts/cae_te_remote_trial.py`, `scripts/cae_te_engine.py`, `scripts/lavie_usb_pack.ps1`, `scripts/k10_sync_lavie_scripts_to_lavie.py`, `docs/cae_north_star_and_meaning_gate_protocol.md` |
| **Verification** | `python -m py_compile scripts/lavie_cae_video_support.py`; after LAVIE worker healthy: `python scripts/k10_send_lavie_fill_video.py --trial-id lavie365-resin_fill_cad-live01` returns `ok=True`. |
| **Lessons Learned** | Satellite nodes must not mirror K10 media toolchain; orchestration belongs on K10 with explicit worker health gates. |
| **Prevention** | P025/T019: only VOF/OR MP4 to Telegram; never mark notify without send proof; read INC-089 before LAVIE video changes. |

## INC-088: Content 5-Forces Gate container startup failure due to WSL/Hyper-V port conflicts and Docker root-path mismatch

| Field | Detail |
|---|---|
| **Date** | 2026-05-24 JST |
| **Detection** | Docker Compose up failed for `minipc_content_5forces_gate` with `Bind for 0.0.0.0:8765 failed: port is already allocated`. After shifting to port `8766`, the container failed again with uvicorn crash `FileNotFoundError: [Errno 2] No such file or directory: '/configs/scoring_rules.yaml'`. |
| **Impact** | The newly integrated Content 5-Forces Gate API was completely unreachable on startup, preventing the Command Center and Creative Studio dashboard from querying the evaluation service. |
| **Root Cause (5 Why)** | **Why1**: Container failed to startup successfully.<br>**Why2**: Port `8765` was allocated by the host-bound `openclaw-spice-lab` container, and port `8766` had Hyper-V port-range exclusions on standard interfaces. The uvicorn app crashed due to looking for `/configs` folder.<br>**Why3**: Path resolution `ROOT = Path(__file__).resolve().parents[2]` assumed the local nested structure (`backend/app/scorer.py`), which resolved to `/` instead of `/app` inside the simplified container directory structure.<br>**Why4**: No self-healing path resolution logic was present in `scorer.py` to identify running inside a container footprint.<br>**Why5**: Standard compose setups assumed standard single-interface bindings without explicit localhost configurations. |
| **Fix** | (1) Changed port binding to `127.0.0.1:18766:8765` in `docker-compose.content-5forces.yml` to bypass Hyper-V exclusion zones and keep it in the safe Clawstack port range.<br>(2) Added self-healing ROOT path detection in `data/workspace/apps/minipc_content_5forces/backend/app/scorer.py` (L11-14) to fallback to parent directory if `/configs` does not exist.<br>(3) Updated manifest, standalone HTML card, and Creative Studio dashboard scripts to query the correct `18766` port. |
| **Files** | `docker-compose.content-5forces.yml`, `data/workspace/apps/minipc_content_5forces/backend/app/scorer.py`, `data/workspace/apps/minipc_content_5forces/portal-card/portal_card_manifest.json`, `data/workspace/apps/minipc_content_5forces/portal-card/content_5forces_card.html`, `data/workspace/apps/creative_studio/index.html`, `data/workspace/apps/minipc_content_5forces/scripts/run_windows_utf8.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | Verified `docker logs minipc_content_5forces_gate` reports `Uvicorn running on http://0.0.0.0:8765`. Verified `curl.exe http://127.0.0.1:18766/health` returns `{"status":"ok","encoding":"utf-8"}`. Verified Python score request evaluates successfully with a real-world manufacturing VBA idea returning score **`97`**. |
| **Lessons Learned** | (1) Paths inside container environments are flatter than nested local packages; always design self-healing path structures that verify folder existence.<br>(2) Docker on Windows is highly vulnerable to Hyper-V reserved port exclusions; binding explicitly to `127.0.0.1` and avoiding low standard ports provides excellent portability. |
| **Prevention** | Mandate self-healing path patterns in Python microservices, and always specify explicit localhost (`127.0.0.1`) mappings for development sidecars. |

## INC-087: CAD DXF-to-STEP solid generation failure due to missing LWPOLYLINE / POLYLINE support in preprocessors

| Field | Detail |
|---|---|
| **Date** | 2026-05-24 JST |
| **Detection** | CAD statistics block on the portal dashboard remained at `1` despite running trial-and-error generation challenges (`run_cad_trialtry.py`). FreeCAD logs from container executions showed that `Profile`, `OuterWall`, `Cavity`, `Base`, and `Fins` layers in custom DXFs were ignored and produced no STEP solids, only generating output for simple `CIRCLE` holes. |
| **Impact** | Dynamic solid generation and multi-view 3D assembly from polylines were completely blocked, forcing users to rely on mock counts or manual CAD models. |
| **Root Cause (5 Why)** | **Why1**: Only circles and simple lines were converted to 3D.<br>**Why2**: The T-junction boundary resolver `resolve_tjunctions` and bounding box calculation `_get_layer_bbox` in `dxf2step_worker.py` only parsed `LINE`, `ARC`, and `CIRCLE` DXF types.<br>**Why3**: Polylines (`LWPOLYLINE` and `POLYLINE`), which are the default output type of `ezdxf.add_lwpolyline`, were silently dropped.<br>**Why4**: No decomposition or explode logic existed to translate compound polylines into simple line segments during 2D preprocessing.<br>**Why5**: Historical design focused solely on simple point-to-point drawing loops and lacked robust native support for industry-standard compound polyline geometries. |
| **Fix** | (1) Refactored `resolve_tjunctions` in `dxf2step_worker.py` to intercept `LWPOLYLINE` and `POLYLINE` and decompose them into lines using `e.get_points('xy')`.<br>(2) Refactored `_get_layer_bbox` to support `CIRCLE`, `LWPOLYLINE`, and `POLYLINE` vertex boundaries.<br>(3) Prepended Windows stdout CP932 encoding protection block (P023 standard) to prevent character encoding issues. |
| **Files** | `data/workspace/apps/dxf2step/dxf2step_worker.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | Ran `python scratch/run_cad_trialtry.py` locally. All 3 challenges completed with **100% success** (`3/3 jobs successfully generated 3D STEP formats`), executing full multi-view 3D reconstruction and updating the live dashboard stats. Real-world CAD counts updated successfully to **`4`** on the growth dashboard page. |
| **Lessons Learned** | Never assume standard geometries like polylines or circles are processed correctly without active type checking. All custom preprocessors and geometry-cleansing pipelines should explicitly decompose complex curves/polylines into standard primitives first. |
| **Prevention** | Use standard polyline decomposition and bbox boundaries, and ensure Windows encoding standards (P023) are adhered to in all processing microservices. |

## INC-086: Image generator container stopped after server restart causing img2img pipeline freeze

| Field | Detail |
|---|---|
| **Date** | 2026-05-23 JST |
| **Detection** | OpenVINO img2img connector reported API connection error to Port 8101. Render diagnostics showed only 1.8KB empty placeholder files for daylight renders. |
| **Impact** | The v40 Extreme daytime photorealism pipeline was completely halted, blocking the visual verification of mecha grounding and Shadow Catcher integration. |
| **Root Cause (5 Why)** | **Why1**: The local img2img script failed to generate photorealistic assets.<br>**Why2**: The backend image generator service `ai_image_gen` on Port 8101 was unresponsive.<br>**Why3**: The Docker container `ai_image_gen-1` was not running.<br>**Why4**: A server restart stopped all containers, and `ai_image_gen` was not configured as a standard auto-start service in the production stack.<br>**Why5**: It is located in a dedicated subdirectory `services/ai_image_gen` and required manual compose-up instantiation after system restaging. |
| **Fix** | (1) Navigated to `services/ai_image_gen` and executed `docker compose up -d --build` to rebuild and launch the CPU OpenVINO container.<br>(2) Executed `comfy_multi_controlnet_connector.py` to process the 3 target views across strengths 0.38 and 0.45.<br>(3) Dispatched all 6 newly stitched comparison sheets to Telegram via `send_comparisons_to_telegram.py`. |
| **Files** | `services/ai_image_gen/docker-compose.yml`, `projects/AtsugiMechaCity/diagnostics/ue5_local_render/comfy_multi_controlnet_connector.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | Verified `docker ps` shows `ai_image_gen-ai_image_gen-1` running healthily. Verified 6/6 high-res daylight comparison sheets are fully generated and successfully dispatched to Telegram (100% success). |
| **Lessons Learned** | Dedicated local helper services that exist outside the main compose stack must have clear recovery procedures documented, and startup routines should gracefully verify container health before executing downstream render integrations. |
| **Prevention** | Ensure the local image generator container is validated and started dynamically during system restaging scripts. |

## INC-085: CityCharacterPipeline walking video know-how was scattered and not reproducible by small local LLMs

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | User reported that the RickDias walking movie finally reached an acceptable shape and asked to convert the lessons into reusable know-how for Byterover, Beads, incident log, QC process chart/PMP, FMEA, FTA, 5Why, and fishbone analysis. |
| **Impact** | Without a consolidated playbook, a future local 8GB LLM could repeat the same failures: untextured FBX, apparent burial, stale-frame MP4 duration errors, overly slow static-looking motion, and unsafe over-refactoring. |
| **Root Cause (5 Why)** | **Why1**: The successful movie required several separate fixes. **Why2**: The fixes were distributed across code, render logs, Telegram sends, and user feedback. **Why3**: QC/FMEA logs existed but did not yet state the final known-good movie baseline in a clean reproducible form. **Why4**: The process lacked explicit acceptance gates for texture preservation, stale frame cleanup, corridor occlusion, and visible motion. **Why5**: Small local LLMs need a compact deterministic checklist, otherwise they may change too many variables or rebuild the wrong layer. |
| **Fix** | Added `docs/knowledge/city_character_pipeline_video_generation_playbook_20260520.md` with golden baseline, commands, acceptance gates, QC/PMP, FMEA, FTA, 5Why, fishbone, local LLM 8GB operating rules, no-go conditions, and final checklist. Appended the same baseline references to `projects/CityCharacterPipeline/knowledge/qc_process_chart.md`, `projects/CityCharacterPipeline/knowledge/fmea_log.md`, and `projects/CityCharacterPipeline/knowledge/lessons.md`. Created Beads issue `iatf_system-ckb` for traceability. |
| **Verification** | Verified Beads issue creation and moved it to `in_progress`. Verified the playbook and existing knowledge files contain the required headings and references using `rg`. ByteRover query timed out at 45 seconds before editing; ByteRover curate was attempted after documentation and timed out at 60 seconds, so the confirmed durable records are the Markdown files and Beads issue. |
| **Lessons Learned** | For video generation, "the code works" is not enough. The reproducible unit must include visual acceptance criteria: texture, feet visibility, motion readability, exact frame count, MP4 duration, and delivery artifact identity. |
| **Prevention** | Future CityCharacterPipeline movie work should begin from the playbook, use `iatf_system-ckb` or a successor Beads issue for task tracking, preserve the 90-frame baseline unless intentionally changed, and update incident/knowledge records whenever a new failure mode is found. |
| **Beads** | `iatf_system-ckb` |

---

## INC-108: LAVIE disconnected and was found stopped at BIOS screen

| Field | Detail |
|---|---|
| **Date** | 2026-06-09 JST |
| **Detection** | User physically checked NEC LAVIE and found it at the BIOS screen after K10 lost connection. K10 also showed LAVIE worker/n8n offline and Tailscale unavailable. |
| **Impact** | LAVIE could not run monitor_agent, Tailscale, n8n, or job worker. Fleet workload routing lost one Windows satellite node and any LAVIE CAE jobs became unavailable. |
| **Root Cause (5 Why)** | **Why1**: K10 could not reach LAVIE because Windows services were not running. **Why2**: Windows services were not running because the physical machine was at BIOS. **Why3**: BIOS state implies abnormal reboot, boot interruption, firmware prompt, or boot-device issue rather than a simple dashboard/network false positive. **Why4**: Immediately before loss, LAVIE had repeated heavy `resin_fill_cad` CAE timeouts and probe failures, increasing thermal/power/driver stress risk. **Why5**: The workload guard did not hard-quarantine normal LAVIE after combined heavy timeout streak plus probe failure. |
| **Evidence** | `data/workspace/lavie_continuous_te_status.json`: probe warning at 2026-06-09 02:58:36 JST and final `resin_fill_cad` `TIMEOUT` at 2026-06-09 03:30:41 JST. `data/workspace/satellite_cae_log.jsonl`: trial `lavie365-resin_fill_cad-4302dca7` timed out after 1320 seconds. `data/workspace/fleet_operations_status.json`: LAVIE job worker and n8n offline. `tailscale status`: `desktop-tfdripe-lavie` offline from K10. |
| **Fix / Current Action** | Created RCA report `quality_incident_report_20260609_lavie_bios_disconnect.md`. Recommended holding normal LAVIE from heavy CAE until Windows boots and local Event Viewer logs are collected. |
| **Verification** | K10-side evidence confirms the sequence: heavy job timeout -> probe timeout -> worker/n8n offline -> Tailscale offline. Exact BIOS trigger remains unverified until LAVIE local Windows event logs and BIOS boot/SSD state are checked. |
| **Lessons Learned** | BIOS screen is a different class of outage from agent/network failure. K10 can detect loss of OS-level services, but the final firmware-level reason needs local event logs after reboot. |
| **Prevention** | Add or enforce a node quarantine rule: repeated heavy-job timeouts plus monitor probe failures must place the node in a recovery hold before more heavy assignments. Resume only after boot confirmation and event-log review. |

---

## INC-084: CityCharacterPipeline walking render lower-body burial caused by OSM occluders and grounding blind spots

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | User reported that the RickDias walking animation still looked buried even after `pre_min_z=-0.080m` produced `const_z_lift=0.130m`. Render diagnostics showed `real_foot_min_z=0.5673m` at frame 1 and `0.3125m` at frame 11, so the mesh itself was above z=0 while the image still looked buried. |
| **Impact** | The generated `Shibuya_Zaku_walk.mp4` made the character's lower body appear hidden by the scene, blocking reliable use of the animation output for review or presentation. |
| **Root Cause (5 Why)** | **Why1**: The lower body looked buried in the rendered video. **Why2**: The feet were not actually below the ground plane; foreground OSM building/roof geometry was occluding the lower body from the camera. **Why3**: The previous guard only skipped buildings around the initial origin and did not clear the camera sight corridor or the full walking corridor. **Why4**: The grounding check only compared character foot Z against z=0 and did not include per-frame surface/occluder diagnostics. **Why5**: Blender 5.1 uses Layered Action data, and the previous attempt to sanitize object transform curves assumed the old `Action.fcurves` API, which failed before rendering. |
| **Fix** | Added evaluated mesh BBox helpers and per-frame walking surface clearance checks in `projects/CityCharacterPipeline/pipeline/scene_builder.py:145`. Added walk-corridor OSM building hiding at `scene_builder.py:166`, camera-corridor OSM building hiding at `scene_builder.py:197`, and Blender 5.1 Layered Action transform-curve cleanup at `scene_builder.py:245` and `scene_builder.py:1011`. Added per-frame grounding summary logs at `scene_builder.py:1153`. Also added Windows UTF-8 stdout setup at `scene_builder.py:11` and generated Blender script setup at `scene_builder.py:26`. |
| **Verification** | Ran `python -m py_compile projects/CityCharacterPipeline/pipeline/scene_builder.py`. Ran `python run_pipeline.py --config configs/shibuya_zaku.yaml --animate --skip-qa` successfully. Blender rendered all 90 frames and ffmpeg rebuilt `Shibuya_Zaku_walk.mp4`. Key log values: `motion corridor: hidden 1 OSM buildings`, `camera corridor: hidden 1 OSM buildings`, `min_foot_z=0.0500`, `min_clearance=0.0500`, `max_extra_lift=0.0000`, frame 1 `real_foot_min_z=0.5673m`, frame 11 `real_foot_min_z=0.3125m`. Manual frame check of `render_frame_0011.png` confirmed the lower body is visible instead of hidden behind the foreground roof/ground-like surface. |
| **Lessons Learned** | A positive foot Z does not prove visual grounding is correct when city geometry can sit between camera and character. Character animation diagnostics must check both physical clearance and camera-visible occluders. Blender 5.x action code should support Layered Action `channelbags` instead of assuming old direct `Action.fcurves`. |
| **Prevention** | Keep walk/camera corridor occluder removal enabled for OSM animation shots, retain per-frame clearance summary logs, and use Blender-version-compatible action curve access when modifying imported FBX animation data. |

---

## INC-083: Missing Email Safety Policy and Unconfigured Maintenance Exclusions

| Field | Detail |
|---|---|
| **Date** | 2026-05-18 |
| **Detection** | Patrol script `continuous_system_improvement.py` reported high-severity weakness `Email safety policy is missing or unsafe` due to missing `email_ops_policy.json`. It also reported high-severity Paperless warnings even though Paperless is intentionally stopped in Mini PC "apply-lite" mode. |
| **Impact** | Operational patrol dashboard remained in a high-severity alert state, causing alert fatigue and masking real runtime anomalies. Auto-repair loop could potentially waste cycles attempting to restart disabled Paperless services. |
| **Root Cause (5 Why)** | **Why1**: The email safety policy weakness and Paperless status weakness persisted.<br>**Why2**: `email_ops_policy.json` and `maintenance_mode.json` were physically missing from the `data/workspace` directory.<br>**Why3**: These configuration files were not pre-initialized during standard environment staging or repository setup.<br>**Why4**: The system improvement and auto-repair check routines assumed these configuration files would exist to govern exclusions and safety policies.<br>**Why5**: No prior execution step had created or generated them to represent the lightweight Mini PC profile. |
| **Fix** | (1) Created `data/workspace/email_ops_policy.json` with strict safety configuration (`draft_only=true`, `auto_send=false`).<br>(2) Created `data/workspace/maintenance_mode.json` to exclude Paperless-related watchdogs (`paperless_rag_watchdog`, `paperless_review_artifacts`, `paperless_ingest_audit`, `paperless_ingest_auth`, `paperless_rag`, `paperless_token`) from both the patrol report and auto-repair check routines. |
| **Files** | `data/workspace/email_ops_policy.json`, `data/workspace/maintenance_mode.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Ran `continuous_system_improvement.py --once` and `auto_repair_allowed.py` directly. Verified that:<br>- The email safety policy is now reported as a **Strength**.<br>- All Paperless weaknesses are cleanly categorized as **MAINTENANCE (Scheduled)**.<br>- Auto-repair reports `planned_maintenance (via maintenance_mode.json)` for `paperless_rag` and `paperless_token`. |
| **Lessons Learned** | Watchdogs and reporting patrols must be designed to natively understand the host's lightweight profile (e.g. `minipc_optimizer`). Crucial safety configuration defaults should be explicitly declared or created on staging, and exclusions must be formalized via maintenance mode configurations to prevent alert fatigue. |
| **Prevention** | Formalized `maintenance_mode.json` exclusions to align the system dashboard with the running container subset on lightweight resource footprints. |

---

## INC-082: cp932 UnicodeEncodeError in replay_pending_queue misidentified as DB connection failure

| Field | Detail |
|---|---|
| **Date** | 2026-05-18 |
| **Detection** | `replay_pending_queue()` in `db_self_healer.py` was catching UnicodeEncodeError as if it were a DB connection error, causing the pending queue replay to silently fail and enter the LLM diagnosis loop. |
| **Impact** | DB pending queue was never replayed on startup. All buffered records remained unwritten to `city_render_trials`. The false diagnosis also triggered unnecessary Telegram alerts and wasted diagnostic cycles. |
| **Root Cause (5 Why)** | **Why1**: `replay_pending_queue()` failed on every run. **Why2**: The `except Exception as e` block around `_pg_connect()` was catching a non-DB error. **Why3**: `print("[DBHealer] DB接続 OK -- リプレイ開始")` raised `UnicodeEncodeError: 'cp932' codec can't encode character '—' at position 19`. **Why4**: The string contained U+2014 (em dash `--`) which cp932 cannot encode. **Why5**: On Japanese Windows, `sys.stdout.encoding = cp932` by default; no `sys.stdout.reconfigure(utf-8)` was set at module initialization. |
| **Fix** | (1) Added `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at module init in `db_self_healer.py` and `knowledge_recorder.py`. (2) Replaced all `--` (U+2014) with `--` (ASCII) in print statements across both files. |
| **Files** | `projects/CityCharacterPipeline/pipeline/db_self_healer.py`, `projects/CityCharacterPipeline/pipeline/knowledge_recorder.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | Ran `replay_pending_queue()` directly — returned 1 (queued record successfully replayed and queue cleared). `[DBHealer] DB接続 OK -- リプレイ開始` printed without error. |
| **Lessons Learned** | On Japanese Windows (cp932), any `print()` containing Unicode symbols (U+2014 `--`, U+2192 `->`, etc.) raises `UnicodeEncodeError`. When this occurs inside a `try/except Exception` block around DB code, it is silently misidentified as a DB failure. Always set `sys.stdout.reconfigure(utf-8)` at module top. |
| **Prevention** | Rule added: all Python modules in this project must call `sys.stdout.reconfigure(encoding="utf-8", errors="replace")` at module initialization. Print statements must use ASCII-safe characters only (`--` not `--`, `->` not `--`). |
| **Beads** | iatf_system-4r4 |
| **DB id** | city_render_trials id=44 (project_tag=infrastructure) |

---

## INC-075: OpenRadioss DOE calculation failure due to extreme Nodal Velocity (Flying Nodes)
| Field | Detail |
|---|---|
| **Date** | 2026-05-05 |
| **Detection** | OpenRadioss run failed at ~17-19ms. The output `4mmx4mm_ASSY_20260105_0001.out` showed `WARNING: NODAL VELOCITY MAY BE TOO HIGH FOR INTERFACE`. Node 5792 reached velocity of 434.9 m/s. |
| **Impact** | The OpenRadioss DOE simulation crashed before completion, causing the AI engineering loop to halt without generating valid results for this DOE run. |
| **Root Cause (5 Why)** | **Why1**: The simulation diverged due to a flying node (node 5792). **Why2**: Elements associated with this node failed and became extremely distorted during the punch fine blanking process. **Why3**: The failed elements were not deleted from the contact interface. **Why4**: Contact interfaces `/INTER/TYPE25/1`, `2`, and `3` had `Idel=1` or `Idel=0`. **Why5**: The parameter `Idel=2` (delete element and segment from interface when failed) was missing, which is strictly required for shearing/cutting simulations with `/FAIL` definitions. |
| **Fix** | Updated `4mmx4mm_ASSY_20260105_0000.rad` to set `Idel = 2` for all `/INTER/TYPE25` interfaces. |
| **Files** | `data/work/4mmx4mm_ASSY_20260105_0000.rad`, `docs/INCIDENT_LOG.md` |
| **Verification** | Prepared the updated `.rad` file. Simulation must be restarted and verified manually to ensure it runs past the 19ms mark without instability. |
| **Lessons Learned** | For any metal cutting or fine blanking simulation in OpenRadioss using solid elements and `/FAIL`, the contact interfaces must have `Idel=2` to prevent failed elements from causing "Nodal velocity too high" crashes. |
| **Prevention** | Formalized this check for future OpenRadioss DOE preparations. Before starting any shearing calculation, ensure `/INTER` cards properly handle element deletion. |

---

## INC-074: GitHub Actions workflow failure due to Permission Denied (actionlint/gitleaks)
| Field | Detail |
|---|---|
| **Date** | 2026-05-05 10:55 JST |
| **Detection** | User reported CI failure in "GitHub Actions Workflow 検査" after a backup push. |
| **Impact** | CI pipeline was blocked, preventing automated verification of code quality and security for the latest production sync. |
| **Root Cause (5 Why)** | **Why1**: `actionlint` installation failed. **Why2**: Attempted to write to `/usr/local/bin` without sufficient privileges. **Why3**: The `ubuntu-latest` runner executes as a non-root user. **Why4**: The workflow command `bash -s -- -b /usr/local/bin` was missing the `sudo` prefix. **Why5**: Historical success or environment drift led to the assumption that standard user permissions were enough for this path. |
| **Fix** | Updated `.github/workflows/ci-fast.yml` and `nightly-health-check.yml` to include `sudo` in `curl | bash` and `tar` installation pipes for `/usr/local/bin`. |
| **Files** | `.github/workflows/ci-fast.yml`, `.github/workflows/nightly-health-check.yml`, `docs/INCIDENT_LOG.md` |
| **Verification** | Re-pushed the corrected workflows. CI job "GitHub Actions Workflow 検査" passed successfully. |
| **Lessons Learned** | Always use `sudo` for system-wide tool installations on GitHub runners. Never assume a push is successful until the CI status is explicitly verified as Green. |
| **Prevention** | Formalized Rule 15 in `AGENTS.md` (GitHub Backup & CI Integrity Protocol), mandating CI status check and self-healing for all future backups. |



## INC-019: Local self-growth and scout loops were incomplete and inconsistent
| Item | Details |
|---|---|
| **Date** | 2026-04-12 |
| **Detected By** | Follow-up audit of self-growth, scout freshness, and Qdrant hygiene |
| **Impact** | The system had partial self-improvement parts, but they were not fully aligned: local scout refresh depended on brittle n8n patching, approved RL skills were syncing to `universal_knowledge` instead of `agent_self_growth_memory`, and startup retrieval verification was not recorded. |
| **Root Cause (5 Why)** | **Why1**: The project had design intent for self-growth and memory hygiene, but not a complete local-only operational loop. **Why2**: AI Scout safe-source patching still depended on an n8n API path that could fail independently of the actual local collection logic. **Why3**: RLAnything skill sync used a generic knowledge collection instead of the dedicated self-growth collection named in governance. **Why4**: No pre-tool or start-of-session verification existed to prove that stored self-growth memory was being queried on future sessions. **Why5**: Memory hygiene thresholds were documented, but no active archive guard was enforcing them on the actual collection. |
| **Fix Summary** | Added a local no-API-cost scout runner and freshness watchdog, added a self-growth memory hygiene guard for `agent_self_growth_memory`, redirected RL skill sync to `agent_self_growth_memory`, and added a `PreToolUse` hook to record first-use retrieval attempts per session. |
| **Files Changed** | `data/workspace/run_ai_strategy_scout_local.py`, `data/workspace/ai_strategy_scout_watchdog.py`, `scripts/start_ai_strategy_scout_watchdog.ps1`, `data/workspace/agent_self_growth_memory_hygiene.py`, `scripts/start_agent_self_growth_memory_hygiene.ps1`, `data/workspace/rl_anything/hook_pre_tool_use.py`, `data/workspace/rl_anything/qdrant_sync.py`, `.claude/settings.json`, `docs/INCIDENT_LOG.md` |
| **Validation** | Local scout refresh can run without n8n API writes, self-growth Qdrant sync now targets `agent_self_growth_memory`, hygiene status can report thresholds without deleting healthy data, and startup retrieval verification writes per-session status with top hits or errors. |
| **Lessons Learned** | For self-improving systems, 窶徇emory exists窶・is not enough. The store, retrieval path, and hygiene path must target the same collection, and there should be an explicit log proving that startup retrieval was attempted. |
| **Recurrence Prevention** | Keep AI Scout on local/no-cost collection paths where possible, enforce a dedicated hygiene script on the actual self-growth collection, and keep first-use retrieval verification enabled through repo-local hook config. |
 
---
 
## INC-053: n8n API authentication failure (401) and patrol weakness persistence
| Field | Detail |
|---|---|
| **Date** | 2026-04-25 11:50 JST |
| **Detection** | `continuous_system_improvement.py` reported high-severity weakness: `n8n API authentication failed (401)`. System health summary showed persistent failure even after credentials were updated in `.env`. |
| **Impact** | Automated n8n maintenance tasks (scheduled report sync, workflow healer, etc.) could fail silently due to auth drift. Patrol summaries stayed "dirty" with high-risk alerts, masking other potential issues. |
| **Root Cause (5 Why)** | **Why1**: n8n v2.6.4 (containerized) requires API keys to be explicitly generated in the UI; environment-variable keys are ignored if not in the DB. **Why2**: The user's `.env` password `Foxconnjpn75` was correct, but the patrol script used `admin@clawstack.local` as a default email for the fallback login, which was incorrect. **Why3**: The fallback login process in the patrol script did not correctly manage sessions/cookies, causing the subsequent `/rest/workflows` check to fail with 401 even after a successful login. **Why4**: The patrol script had redundant reporting: it both probed n8n auth explicitly and included it in a generic host-api-inventory loop, causing double-reporting of weaknesses. **Why5**: The patrol logic lacked a robust multi-strategy auth resolver (API Key -> Cookie Session -> User/PW fallback) that accounted for specific n8n backend behavior. |
| **Fix** | Updated `data/workspace/continuous_system_improvement.py` to: (1) Use `requests.Session` for cookie-based fallback. (2) Explicitly pass the `n8n-auth` cookie in subsequent requests. (3) Prioritize the correct user email `y.suzuki.hk@gmail.com`. (4) Exclude `n8n_auth` from the generic reporting loop to avoid double-alerts. Updated `scheduled_report_search.py` to improve error logging and follow the same auth fallback logic. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/scheduled_report_search.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python data/workspace/continuous_system_improvement.py --once` now reports `n8n API authentication is valid: url=http://127.0.0.1:5679/rest/workflows status=200`. Weakness count dropped from 3 to 1. `scheduled_report_search.py` manual run confirmed sync capability. |
| **Lessons Learned** | For n8n on this machine, API Keys are unreliable. Always implement a robust Cookie-based session fallback using the user's primary email. Patrol reporting must be de-duplicated when a component has both a dedicated probe and a generic inventory check. |
| **Prevention** | Standardize n8n auth helpers across all maintenance scripts. Ensure the patrol summary uses a single canonical source for each component's health status. |

---

## INC-001: C 繝峨Λ繧､繝門ｮｹ驥乗椡貂・ｼ・ost_gmail_incremental_* 荳譎ゅヵ繧ｩ繝ｫ繝譛ｪ蜑企勁・・
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-05 |
| **逋ｺ隕区婿豕・* | Docker 繧ｨ繝ｳ繧ｸ繝ｳ縺後ヵ繝ｪ繝ｼ繧ｺ縺励∝・繧ｳ繝ｳ繝・リ縺悟●豁｢縲・ 繝峨Λ繧､繝匁ｮ句ｮｹ驥上′縺ｻ縺ｼ 0 繝舌う繝医・|
| **蠖ｱ髻ｿ遽・峇** | Docker Desktop 蜈ｨ菴難ｼ・ATF System, QA Dashboard, Gateway 遲峨☆縺ｹ縺ｦ縺ｮ繧ｳ繝ｳ繝・リ・榎
| **譬ｹ譛ｬ蜴溷屏** | `data/workspace/host_gmail_incremental_sync.py` 縺ｮ 110 陦檎岼縺ｧ `tempfile.mkdtemp(prefix="host_gmail_incremental_")` 縺ｫ繧医ｊ荳譎ゅョ繧｣繝ｬ繧ｯ繝医Μ繧剃ｽ懈・縺吶ｋ縺後～finally` 繝悶Ο繝・け縺ｫ `shutil.rmtree()` 縺檎┌縺上∝・逅・ｮ御ｺ・ｾ後ｂ繝輔か繝ｫ繝縺梧ｮ句ｭ倥よｯ主・邏・370MB ﾃ・1 蛟九・繝壹・繧ｹ縺ｧ闢・ｩ阪＠縲∵焚譎る俣縺ｧ謨ｰ蜊√懈焚逋ｾ GB 縺ｫ蛻ｰ驕斐・|
| **菫ｮ豁｣蜀・ｮｹ** | `finally` 繝悶Ο繝・け縺ｫ `shutil.rmtree(tempdir, ignore_errors=True)` 繧定ｿｽ蜉�縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [host_gmail_incremental_sync.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/host_gmail_incremental_sync.py) L221-228 |
| **讀懆ｨｼ邨先棡** | 菫ｮ豁｣蠕・4 蛻・俣逶｣隕・竊・譁ｰ隕上ざ繝溘ヵ繧ｩ繝ｫ繝 0 蛟九・8.12 GB 繧貞叉譎りｧ｣謾ｾ縲・|
| **霑ｽ蜉�蟇ｾ遲・* | (1) 謇句虚貂・祉繧ｹ繧ｯ繝ｪ繝励ヨ `scripts/clawstack_janitor.ps1` 繧帝・蛯吶・2) QA Dashboard 縺ｫ縲粂ost Maintenance縲阪き繝ｼ繝峨ｒ霑ｽ蜉�縲・|
| **讀懆ｨｼ邨先棡** | 菫ｮ豁｣蠕・4 蛻・俣逶｣隕・竊・譁ｰ隕上ざ繝溘ヵ繧ｩ繝ｫ繝€ 0 蛟九€・8.12 GB 繧貞叉譎りｧ｣謾ｾ縲・|
| **霑ｽ蜉蟇ｾ遲・* | (1) 謇句虚貂・祉繧ｹ繧ｯ繝ｪ繝励ヨ `scripts/clawstack_janitor.ps1` 繧帝・蛯吶€・2) QA Dashboard 縺ｫ粂ost Maintenance縲阪き繝ｼ繝峨ｒ霑ｽ蜉・縲・|
| **蜀咲匱髦ｲ豁｢** | 譛ｬ繧､繝ｳ繧ｷ繝・Φ繝医ｒ螂第ｩ溘↓ AGENTS.md 縺ｫ縲御ｿｮ豁｣蠕後・險倬鹸鄒ｩ蜍吶€阪Ν繝ｼ繝ｫ繧定ｿｽ蜉・縲・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **`tempfile.mkdtemp()` 繧剃ｽｿ縺・ｴ蜷医・縲∝ｿ・★ `try...finally` 縺ｧ `shutil.rmtree()` 繧貞・繧後ｋ縺薙→縲・* Python 縺ｮ `tempfile.TemporaryDirectory()` 繧ｳ繝ｳ繝・く繧ｹ繝医・繝阪・繧ｸ繝｣繧剃ｽｿ縺医・閾ｪ蜍募炎髯､縺輔ｌ繧九€・2. **螳壽悄螳溯｡鯉ｼ・ron / daemon・峨せ繧ｯ繝ｪ繝励ヨ縺ｯ 1 蝗槭≠縺溘ｊ縺ｮ繝・ぅ繧ｹ繧ｯ菴ｿ逕ｨ驥上′蟆上＆縺上※繧ゅ€∬塘遨阪☆繧九→閾ｴ蜻ｽ逧・↓縺ｪ繧九€・* 譁ｰ縺励＞螳壽悄螳溯｡後せ繧ｯ繝ｪ繝励ヨ繧呈嶌縺城圀縺ｯ縲∝ｿ・★縲悟ｾ檎援莉倥￠縲阪さ繝ｼ繝峨・譛臥┌繧偵Ξ繝薙Η繝ｼ縺吶ｋ縺薙→縲・3. **繝・ぅ繧ｹ繧ｯ譫ｯ貂・・騾｣骼夜囿螳ｳ繧貞ｼ輔″襍ｷ縺薙☆縲・* Docker 繧ｨ繝ｳ繧ｸ繝ｳ縲￣ostgreSQL縲ヽedis縲ヽails 縺吶∋縺ｦ縺悟ｷｻ縺肴ｷｻ縺医〒蛛懈ｭ｢縺吶ｋ縲よ掠譛滓､懃衍縺ｮ莉慕ｵ・∩・・ptime Kuma 縺ｮ繝・ぅ繧ｹ繧ｯ逶｣隕也ｭ会ｼ峨ｒ讀懆ｨ弱☆繧九€・

## INC-073: Email Blacklist Hub config disappearance and API freeze
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-02 21:00 JST |
| **Detection** | User reported Email Blacklist Hub card missing from Portal and "PURCHASE ORDER" not being filtered. API investigation showed `email_rag_sender_filters.json` was empty (0 bytes) and the API process was frozen. |
| **Impact** | Email filtering logic was lost, allowing blacklisted senders to bypass RAG filters. The Portal UI for blacklist management was inaccessible. |
| **Root Cause (5 Why)** | **Why1**: Config files became empty. **Why2**: Non-atomic `write_text` was used during system-wide I/O stress. **Why3**: If a write was interrupted by a crash or lock, the file was left truncated. **Why4**: The API also froze because it lacked a timeout when connecting to `email_search.db`, which was locked by a background backfill process. **Why5**: There was no unified "atomic persistence" utility in the workspace to handle sensitive JSON configuration safely. |
| **Fix** | Created `data/workspace/file_utils.py` implementing `atomic_write_json` (tempfile + os.replace) and `safe_load_json` (with .bak fallback). Refactored `email_blacklist_hub_api.py` to use these utilities and added `timeout=10` to SQLite connections. Restored `PURCHASE ORDER` to the blacklist and restarted the API. |
| **Files** | `data/workspace/file_utils.py`, `data/workspace/email_blacklist_hub_api.py`, `data/workspace/email_rag_sender_filters.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Verified `email_blacklist_hub_status.json` reports success via atomic write. `curl` against `/api/email-blacklist/config` returned HTTP 200 with the full blacklist content including "purchase order". |
| **Lessons Learned** | Never use direct `write_text` for mission-critical configuration in high-stress environments. Always implement DB timeouts to prevent cascading process freezes during maintenance locks. |
| **Prevention** | Mandatory use of `file_utils.py` for all workspace JSON persistence. Added DB connection timeout as a standard for all engineering APIs. |

---

## INC-002: IATF Rails 繧｢繝励Μ 500 繧ｨ繝ｩ繝ｼ・・B_PORT 荳堺ｸ€閾ｴ・・
| 鬆・岼 | 蜀・ｮｹ |
| --- | --- |
| **逋ｺ逕滓律** | 2026-04-05 |
| **逋ｺ隕区婿豕・* | `http://127.0.0.1:3003/users/sign_in` 縺ｫ繧｢繧ｯ繧ｻ繧ｹ縺吶ｋ縺ｨ HTTP 500 縺瑚ｿ斐ｋ縲ゅΘ繝ｼ繧ｶ繝ｼ縺九ｉ縺ｮ蝣ｱ蜻翫€・|
| **蠖ｱ髻ｿ遽・峇** | IATF16949 蜩∬ｳｪ邂｡逅・す繧ｹ繝・Β・・ails 繧｢繝励Μ・牙・讖溯・縺悟茜逕ｨ荳榊庄縲・|
| **逋ｺ逕溽ｵ檎ｷｯ** | INC-001・・ 繝峨Λ繧､繝匁椡貂・ｼ峨↓繧医ｊ Docker Desktop 縺悟●豁｢縲ょｾｩ譌ｧ縺ｮ縺溘ａ Docker 繧貞・襍ｷ蜍輔＠縲～docker-compose.production.yml` 縺ｧ IATF 繧ｹ繧ｿ繝・け繧貞・讒区・縲ゅさ繝ｳ繝・リ閾ｪ菴薙・襍ｷ蜍輔＠縺溘′縲ヽails 縺・DB 縺ｫ謗･邯壹〒縺阪★ 500 繧ｨ繝ｩ繝ｼ縺ｨ縺ｪ縺｣縺溘・|
| **譬ｹ譛ｬ蜴溷屏・・Why・・* | **Why1**: Rails 縺・DB 縺ｫ謗･邯壹〒縺阪↑縺・竊・**Why2**: `host.docker.internal:5432` 縺ｫ謗･邯壹＠繧医≧縺ｨ縺励※縺・ｋ 竊・**Why3**: `database.yml` 縺・`DB_PORT` 迺ｰ蠅・､画焚・医ョ繝輔か繝ｫ繝・5432・峨ｒ菴ｿ逕ｨ 竊・**Why4**: `docker-compose.production.yml` 縺ｮ `web` 繧ｵ繝ｼ繝薙せ縺ｫ `DB_PORT` 縺梧悴螳夂ｾｩ 竊・**Why5**: DB 繧ｳ繝ｳ繝・リ縺ｮ繝昴・繝医・繝・ヴ繝ｳ繧ｰ縺・`5436:5432`・医・繧ｹ繝亥・ 5436・峨↑縺ｮ縺ｫ縲ヽails 縺ｯ繝・ヵ繧ｩ繝ｫ繝医・ 5432 縺ｧ謗･邯壹ｒ隧ｦ陦後・*繝昴・繝医・繝・ヴ繝ｳ繧ｰ縺ｨ迺ｰ蠅・､画焚縺ｮ荳肴紛蜷医・* |
| **菫ｮ豁｣蜀・ｮｹ** | `docker-compose.production.yml` 縺ｮ `web` 縺翫ｈ縺ｳ `sidekiq` 繧ｵ繝ｼ繝薙せ縺ｮ `environment` 縺ｫ `DB_PORT=5436` 繧定ｿｽ蜉�縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [docker-compose.production.yml](file:///d:/Clawdbot_Docker_20260125/iatf_system/docker-compose.production.yml) L66, L99 |
| **讀懆ｨｼ邨先棡** | 菫ｮ豁｣蠕・`curl` 縺ｧ HTTP 200 繧堤｢ｺ隱阪ゅヶ繝ｩ繧ｦ繧ｶ縺ｧ繝ｭ繧ｰ繧､繝ｳ繝壹・繧ｸ縺梧ｭ｣蟶ｸ陦ｨ遉ｺ・医梧磁邯壹ユ繧ｹ繝・ 騾夂衍繧ｷ繧ｹ繝・Β縺梧ｭ｣蟶ｸ縺ｫ蜍穂ｽ懊＠縺ｦ縺・∪縺吶阪・邱代ヰ繝翫・陦ｨ遉ｺ・峨・|
| **蜀咲匱髦ｲ豁｢** | 荳玖ｨ倥梧蕗險薙榊盾辣ｧ縲・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **`docker-compose.yml` 縺ｧ繝帙せ繝育ｵ檎罰・・host.docker.internal`・峨・DB謗･邯壹ｒ菴ｿ縺・�ｴ蜷医√・繝ｼ繝医・繝・ヴ繝ｳ繧ｰ・・5436:5432`・峨・繝帙せ繝亥・繝昴・繝医ｒ `DB_PORT` 迺ｰ蠅・､画焚縺ｫ譏守､ｺ縺吶ｋ縺薙→縲・* 繝・ヵ繧ｩ繝ｫ繝亥､・・432・峨・繧ｳ繝ｳ繝・リ蜀・Κ縺ｮ繝昴・繝医〒縺ゅｊ縲√・繧ｹ繝育ｵ檎罰縺ｧ縺ｯ荳閾ｴ縺励↑縺・・2. **Docker 蜀崎ｵｷ蜍募ｾ後・縲√さ繝ｳ繝・リ縺ｮ襍ｷ蜍暮�・ｺ上↓豕ｨ諢上☆繧九・* DB 縺ｮ縲罫eady to accept connections縲阪Ο繧ｰ繧堤｢ｺ隱阪＠縺ｦ縺九ｉ Web 繧定ｵｷ蜍輔＠縺ｪ縺・→縲ヽails 縺・DB 襍ｷ蜍穂ｸｭ・・database system is starting up"・峨↓謗･邯壹ｒ隧ｦ縺ｿ縲√◎縺ｮ縺ｾ縺ｾ謗･邯壹・繝ｼ繝ｫ縺悟｣翫ｌ縺溽憾諷九〒蜍輔″邯壹￠繧九・3. **蠕ｩ譌ｧ菴懈･ｭ譎ゅ・ `docker compose logs --tail N <service>` 縺ｧ繧ｨ繝ｩ繝ｼ縺ｮ蜈ｨ譁・ｒ遒ｺ隱阪☆繧九％縺ｨ縲・* 莉雁屓縺ｯ縲継ort 5432縲阪∈縺ｮ謗･邯壼､ｱ謨励Ο繧ｰ縺悟・縺ｦ縺・◆縺後√ち繝ｼ繝溘リ繝ｫ縺ｮ蜃ｺ蜉帙ヨ繝ｩ繝ｳ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ縺ｧ隕玖誠縺ｨ縺励′逋ｺ逕溘＠縺溘・
---

## INC-003: Gateway 繝輔Μ繝ｼ繧ｺ縲＾bsidian 騾｣謳ｺ繧ｿ繧､繝�繧｢繧ｦ繝・
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-10 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 繝励Λ繧ｰ繧､繝ｳ縺ｫ縺ｦ `Request timeout: initialize (120000ms)` 繧ｨ繝ｩ繝ｼ縲・|
| **蠖ｱ髻ｿ遽・峇** | OpenClaw Gateway 蜈ｨ菴難ｼ・I, API, MCP 騾｣謳ｺ荳榊庄・・|
| **逋ｺ逕溽ｵ檎ｷｯ** | 蜑肴律・・4-09・峨・繝ｭ繧ｰ繧呈怙蠕後↓ gateway 縺ｮ譖ｴ譁ｰ縺悟●豁｢縲Ａcurl` 縺ｫ繧医ｋ繝倥Ν繧ｹ繝√ぉ繝・け繧ょｿ懃ｭ斐＠縺ｪ縺上↑縺｣縺溘・|
| **譬ｹ譛ｬ蜴溷屏・域耳貂ｬ・・* | 蟄舌・繝ｭ繧ｻ繧ｹ・・ummary cache builder・峨′ defunct 縺ｨ縺ｪ繧翫√Γ繧､繝ｳ縺ｮ gateway 繝励Ο繧ｻ繧ｹ縺ｮ繧､繝吶Φ繝医Ν繝ｼ繝励′繝・ャ繝峨Ο繝・け縺ｾ縺溘・繝悶Ο繝・く繝ｳ繧ｰ迥ｶ諷九↓髯･縺｣縺溷庄閭ｽ諤ｧ縲ゅΜ繧ｽ繝ｼ繧ｹ・・PU/MEM/DISK・峨・騾ｼ霑ｫ縺ｯ隕九ｉ繧後↑縺・・|
| **菫ｮ豁｣蜀・ｮｹ** | `docker restart clawstack-unified-clawdbot-gateway-1` 縺ｫ繧医ｋ蠑ｷ蛻ｶ蜀崎ｵｷ蜍輔・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | N/A (驕狗畑謫堺ｽ懊↓繧医ｋ蠕ｩ譌ｧ) |
| **讀懆ｨｼ邨先棡** | 蜀崎ｵｷ蜍募ｾ後√Ο繧ｰ縺・`2026-04-10.log` 縺ｫ豁｣蟶ｸ逕滓・縺輔ｌ縲～ws://0.0.0.0:18789` 縺ｧ縺ｮ蠕・女繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢** | (1) Gateway 縺ｮ繝倥Ν繧ｹ繝√ぉ繝・け・・iveness Probe・峨ｒ Docker Compose 蛛ｴ縺ｾ縺溘・逶｣隕悶せ繧ｯ繝ｪ繝励ヨ縺ｫ讀懆ｨ弱・2) defunct 繝励Ο繧ｻ繧ｹ縺ｮ逋ｺ逕溘ｒ髦ｲ縺舌◆繧√∝ｭ舌・繝ｭ繧ｻ繧ｹ縺ｮ繝上Φ繝峨Μ繝ｳ繧ｰ蜃ｦ逅・ｒ隕狗峩縺吶・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **繧ｳ繝ｳ繝・リ縺・`Up` 縺ｧ繧ゅい繝励Μ繧ｱ繝ｼ繧ｷ繝ｧ繝ｳ螻､縺後ヵ繝ｪ繝ｼ繧ｺ縺励※縺・ｋ蝣ｴ蜷医′縺ゅｋ縲・* `docker ps` 縺�縺代〒縺ｯ荳榊香蛻・〒縲√Ο繧ｰ縺ｮ譖ｴ譁ｰ譌･譎ゅｄ API 縺ｮ蠢懃ｭ皮｢ｺ隱阪′蠢・ｦ√・2. **defunct 繝励Ο繧ｻ繧ｹ・医だ繝ｳ繝難ｼ峨・逋ｺ逕溘・逡ｰ蟶ｸ縺ｮ蜈・吶・* 蟄舌・繝ｭ繧ｻ繧ｹ繧・fork 縺吶ｋ險ｭ險医・蝣ｴ蜷医√す繧ｰ繝翫Ν繝上Φ繝峨Μ繝ｳ繧ｰ繧・waitpid 遲峨・驕ｩ蛻・↑蠕悟・逅・′谺�縺代ｋ縺ｨ繧ｾ繝ｳ繝薙′闢・ｩ阪＠縲∬ｦｪ繝励Ο繧ｻ繧ｹ縺ｫ蠖ｱ髻ｿ繧貞所縺ｼ縺吶％縺ｨ縺後≠繧九・3. **縲景nitialize縲阪ち繧､繝�繧｢繧ｦ繝医・ MCP/LSP 繝上Φ繝峨す繧ｧ繧､繧ｯ螟ｱ謨励ｒ遉ｺ縺吶・* 繧ｯ繝ｩ繧､繧｢繝ｳ繝亥・・・bsidian・峨・繧ｨ繝ｩ繝ｼ繝｡繝・そ繝ｼ繧ｸ縺九ｉ縲√←縺ｮ繝励Ο繝医さ繝ｫ縺ｮ縺ｩ縺ｮ谿ｵ髫弱〒豁｢縺ｾ縺｣縺ｦ縺・ｋ縺九ｒ謗ｨ貂ｬ縺ｧ縺阪ｋ縲・
---

## INC-004: 繧ｾ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ闢・ｩ阪→ Paperless 逡ｰ蟶ｸ縺ｫ繧医ｋ Gateway 騾｣邯壼●豁｢

| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-10 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 蜀榊ｺｦ縺ｮ `Request timeout: initialize`縲ょ・襍ｷ蜍輔°繧・譎る俣蠕後↓蜀咲匱縲・|
| **蠖ｱ髻ｿ遽・峇** | Gateway, LiteLLM, Paperless 騾｣謳ｺ蜈ｨ菴・|
| **逋ｺ逕溽ｵ檎ｷｯ** | INC-003 縺ｧ縺ｮ蜊倥↑繧・`docker restart` 縺ｧ縺ｯ譬ｹ譛ｬ蜴溷屏縺瑚ｧ｣豸医＆繧後★縲∵焚譎る俣蠕後↓蜀咲匱縲・ateway 蛛ｴ縺ｧ縺ｮ繧ｾ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ闢・ｩ阪√♀繧医・螟夜Κ E: 繝峨Λ繧､繝紋ｸ翫・ Paperless 繝・ぅ繝ｬ繧ｯ繝医Μ豸亥､ｱ縺ｫ繧医ｋ Liveness Probe 螟ｱ謨励′驥阪↑繧翫√す繧ｹ繝・Β縺後ワ繝ｳ繧ｰ縺励◆縲・|
| **譬ｹ譛ｬ蜴溷屏** | (1) `docker-compose.yml` 縺ｧ `init: true` 縺梧悴險ｭ螳壹・縺溘ａ縲∝ｭ､遶九＠縺溷ｭ舌・繝ｭ繧ｻ繧ｹ縺・PID 1 (OpenClaw) 縺ｫ蝗槫庶縺輔ｌ縺壽ｻ樒蕗縲・2) Paperless 縺ｮ繝槭え繝ｳ繝亥・・・: 繝峨Λ繧､繝・Junction・峨↓繝・ぅ繝ｬ繧ｯ繝医Μ縺悟ｭ伜惠縺帙★縲￣aperless 縺瑚ｵｷ蜍輔お繝ｩ繝ｼ・・ileExistsError・峨〒蛛懈ｭ｢縲・3) `ingest_watchdog.py` 縺檎焚蟶ｸ迥ｶ諷九・ Paperless 縺ｫ蟇ｾ縺励Μ繝医Λ繧､繧堤ｹｰ繧願ｿ斐＠縲√Μ繧ｽ繝ｼ繧ｹ縺ｾ縺溘・繝励Ο繧ｻ繧ｹ蛻ｶ蠕｡縺ｫ蠖ｱ髻ｿ縲・|
| **菫ｮ豁｣蜀・ｮｹ** | (1) `docker-compose.yml` 縺ｫ `init: true` 繧定ｿｽ蜉�縲・2) E: 繝峨Λ繧､繝紋ｸ翫・ Paperless 讒矩�繧貞ｾｩ譌ｧ縲・3) `ingest_watchdog.py` 縺ｫ謖・焚繝舌ャ繧ｯ繧ｪ繝包ｼ・xponential Backoff・峨ｒ螳溯｣・・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | [docker-compose.yml](file:///d:/Clawdbot_Docker_20260125/docker-compose.yml), [ingest_watchdog.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/ingest_watchdog.py) |
| **讀懆ｨｼ邨先棡** | Gateway 縺ｮ PID 1 縺・`docker-init` 縺ｫ縺ｪ縺｣縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱阪１aperless 縺ｮ Healthy 蛻ｰ驕斐♀繧医・ Watchdog 縺ｮ豁｣蟶ｸ繝昴・繝ｪ繝ｳ繧ｰ繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢** | (1) 蜈ｨ縺ｦ縺ｮ髟ｷ譛溷ｮ溯｡後さ繝ｳ繝・リ縺ｧ `init: true` 縺ｾ縺溘・ `tini` 縺ｮ菴ｿ逕ｨ繧呈､懆ｨ弱・2) 繝帙せ繝亥・縺ｮ Junction 蜈茨ｼ亥､紋ｻ倥￠繝峨Λ繧､繝厄ｼ峨・豁ｻ豢ｻ逶｣隕悶∪縺溘・襍ｷ蜍募燕繝√ぉ繝・け繧貞ｼｷ蛹悶・|

### 謨呵ｨ難ｼ・essons Learned・・
1. **PID 1 蝠城｡後・驥崎ｦ∵ｧ**・哢ode.js 遲峨・繝ｩ繝ｳ繧ｿ繧､繝�繧堤峩謗･ PID 1 縺ｧ蜍輔°縺吶→縲√だ繝ｳ繝薙・繝ｭ繧ｻ繧ｹ縺ｮ蝗槫庶縺後お繝ｳ繧ｸ繝ｳ縺ｮ螳溯｣・↓萓晏ｭ倥＠縲∵э蝗ｳ縺励↑縺・ワ繝ｳ繧ｰ繧呈魚縺上Ａinit: true` 縺ｮ蛻ｩ逕ｨ縺碁延蜑・・2. **螟夜Κ繝峨Λ繧､繝夜｣謳ｺ縺ｮ繝ｪ繧ｹ繧ｯ**・哽unction 繧剃ｽｿ逕ｨ縺励◆螟夜Κ繝槭え繝ｳ繝医・縲√ラ繝ｩ繧､繝悶・蛻・妙繧・ｧ矩�螟画峩縺ｫ蠑ｱ縺・りｵｷ蜍墓凾縺ｫ繝・ぅ繝ｬ繧ｯ繝医Μ縺ｮ蟄伜惠繝√ぉ繝・け繧定｡後≧遲峨・亟蠕｡逧・ｮ溯｣・′蠢・ｦ√・3. **繝舌ャ繧ｯ繧ｪ繝輔・谺�螯ゅ↓繧医ｋ莠梧ｬ｡陲ｫ螳ｳ**・壻ｾ晏ｭ倥し繝ｼ繝薙せ縺梧ｭｻ繧薙〒縺・ｋ髫帙↓縲√・繝ｼ繝ｪ繝ｳ繧ｰ蛛ｴ縺悟・蜉帙〒繝ｪ繝医Λ繧､繧堤ｶ壹￠繧九→縲∵ｭ｣蟶ｸ縺ｪ繧ｳ繝ｳ繝・リ縺ｾ縺ｧ雋�闕ｷ繧・Ο繧ｰ縺ｮ蠅怜､ｧ縺ｧ驕馴｣繧後↓縺ｪ繧句庄閭ｽ諤ｧ縺後≠繧九・
---

*谺｡縺ｮ繧､繝ｳ繧ｷ繝・Φ繝医・ INC-005 縺ｨ縺励※霑ｽ險倥＠縺ｦ縺上□縺輔＞縲・

---

## INC-005: Claudian Codex 襍ｷ蜍募､ｱ謨励→ initialize 繧ｿ繝ｼ繧ｲ繝・ヨ荳堺ｸ閾ｴ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Obsidian Claudian 縺ｧ `Request timeout: initialize (120000ms)` 縺ｮ蠕後～Codex target mismatch` 縺碁｣骼悶・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex 騾｣謳ｺ縲７ault 蜀・°繧・Codex 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蛻晄悄蛹悶′螟ｱ謨励・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Codex 繝励Ο繧ｻ繧ｹ縺瑚ｵｷ蜍輔○縺・initialize 縺・120 遘偵〒繧ｿ繧､繝�繧｢繧ｦ繝医＠縺溘・**Why2**: Windows 閾ｪ蜍戊ｧ｣豎ｺ縺・`codex.cmd` / `codex.bat` 繧呈爾邏｢蟇ｾ雎｡縺ｫ蜷ｫ繧√※縺・↑縺九▲縺溘・**Why3**: Vault 繝励Λ繧ｰ繧､繝ｳ驟堺ｸ九↓縺ｯ `codex.cmd` 繝ｩ繝・ヱ繝ｼ縺後≠繧翫￣ATH 縺ｫ縺ｯ蟄伜惠縺励※縺・◆縺瑚ｧ｣豎ｺ縺ｧ縺阪↑縺九▲縺溘・**Why4**: 縺溘→縺・`.cmd` 繧定ｦ九▽縺代※繧ゅ仝indows 縺ｧ縺ｯ `spawn(..., { shell: false })` 縺ｮ縺ｾ縺ｾ縺ｧ縺ｯ襍ｷ蜍穂ｺ呈鋤諤ｧ縺悟ｼｱ縺・・**Why5**: 襍ｷ蜍募ｾ後ｂ `codex_bridge.js` 縺ｮ initialize 蠢懃ｭ斐↓ `platformOs` / `platformFamily` 縺後↑縺上√ち繝ｼ繧ｲ繝・ヨ讀懆ｨｼ縺ｧ蛻･繧ｨ繝ｩ繝ｼ縺ｫ縺ｪ縺｣縺ｦ縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | Windows 縺ｮ CLI 謗｢邏｢縺ｫ `codex.cmd` / `codex.bat` 繧定ｿｽ蜉�縺励～.cmd` / `.bat` 縺瑚ｧ｣豎ｺ縺輔ｌ縺溷�ｴ蜷医・ sibling 縺ｮ `codex_bridge.js` 繧・`node` 縺ｧ逶ｴ謗･襍ｷ蜍輔☆繧九ｈ縺・ｿｮ豁｣縲ゅ＆繧峨↓ bridge initialize 蠢懃ｭ斐∈ `platformOs=windows` 縺ｨ `platformFamily=windows` 繧定ｿｽ蜉�縺励√Ο繧ｰ繝・ぅ繝ｬ繧ｯ繝医Μ繧定・蜍穂ｽ懈・縺吶ｋ繧医≧菫ｮ豁｣縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60884`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60905`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61858`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:11`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js:37` |
| **讀懆ｨｼ邨先棡** | 繧ｽ繝ｼ繧ｹ遒ｺ隱阪〒 Windows 謗｢邏｢蟇ｾ雎｡縺ｫ `.cmd` / `.bat` 縺瑚ｿｽ蜉�縺輔ｌ縺溘％縺ｨ縲～.cmd` 隗｣豎ｺ譎ゅ↓ `node + codex_bridge.js` 縺ｮ逶ｴ謗･襍ｷ蜍輔∈蛻・ｊ譖ｿ繧上ｋ縺薙→縲｜ridge initialize 蠢懃ｭ斐↓ target 諠・�ｱ縺瑚ｼ峨ｋ縺薙→繧堤｢ｺ隱阪ょ刈縺医※ `codex_bridge.js` 蜊倅ｽ薙・ initialize 蠢懃ｭ斐ユ繧ｹ繝医〒 `platformOs` / `platformFamily` 繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 蝗ｺ譛峨・螳溯｡悟ｽ｢蠑・(`.cmd` / `.bat`) 繧・CLI 閾ｪ蜍戊ｧ｣豎ｺ縺九ｉ螟悶＆縺ｪ縺・Ｊnitialize 蠢懃ｭ斐・蠢・�医ヵ繧｣繝ｼ繝ｫ繝峨ｒ谺�縺九＆縺ｪ縺・ｈ縺・｜ridge 螟画峩譎ゅ・襍ｷ蜍募燕縺ｮ JSON-RPC 繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ邯ｭ謖√☆繧九・|

### Lessons Learned
1. Windows 邵ｺ・ｧ邵ｺ・ｯ邵ｲ險鄭TH 邵ｺ・ｫ邵ｺ繧・ｽ狗ｸｲ髦ｪ笆｡邵ｺ莉｣縲堤ｸｺ・ｯ闕ｳ讎企ｦ呵崕繝ｻ縲堤ｸｲ・枹pawn` 邵ｺ・ｮ陞ｳ貅ｯ・｡謔滂ｽｽ・｢陟台ｸ橸ｽｷ・ｮ邵ｺ・ｾ邵ｺ・ｧ髫穂ｹ晢ｽ玖�｢繝ｻ・ｦ竏壺ｲ邵ｺ繧・ｽ狗ｸｲ繝ｻ2. `initialize` 邵ｺ・ｯ郢ｧ・ｿ郢ｧ・､郢晢｣ｰ郢ｧ・｢郢ｧ・ｦ郢晏現笆｡邵ｺ莉｣縲堤ｸｺ・ｪ邵ｺ荳環竏晢ｽｿ諛・ｽｭ譁舌○郢ｧ・ｭ郢晢ｽｼ郢晄ｨ費ｽｸ讎奇ｽ咏ｸｺ・ｧ郢ｧ繧・ｽｺ譴ｧ・ｮ・ｵ騾ｶ・ｮ邵ｺ・ｮ鬮ｫ諛ｷ・ｮ・ｳ郢ｧ螳夲ｽｵ・ｷ邵ｺ阮吮・邵ｺ貅假ｽ∫ｸｲ竏ｬ・ｵ・ｷ陷崎ｼ披・陟｢諛・ｽｭ譁舌・闕ｳ・｡隴・ｽｹ郢ｧ雋樣・隴弱ｅ竊楢ｮ諛・ｽｨ・ｼ邵ｺ蜷ｶ・狗ｸｲ繝ｻ3. 隴鯉ｽ｢陝・･ﾎ帷ｹ昴・繝ｱ郢晢ｽｼ (`codex.cmd`) 郢ｧ蜻茨ｽｴ・ｻ邵ｺ荵昶・隲｡・｡陟托ｽｵ邵ｺ・ｮ隴・ｽｹ邵ｺ蠕個竏晄肩驍会ｽｻ驍ｨ・ｱ邵ｺ・ｮ隘搾ｽｷ陷肴・・ｵ迹夲ｽｷ・ｯ郢ｧ雋橸ｽ｢蜉ｱ・・ｸｺ蜷ｶ・育ｹｧ髮・ｽｮ迚吶・邵ｺ・ｫ陝・ｸｻ繝ｻ邵ｺ・ｧ邵ｺ髦ｪ・狗ｸｲ繝ｻ

## INC-017: `email_search.db` 遐ｴ謳肴凾縺ｮ閾ｪ蜍穂ｿｮ蠕ｩ邨瑚ｷｯ繧定ｿｽ蜉�
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | `email_continuous_watchdog_status.json` 縺ｨ `email_continuous_ingest_status.json` 縺ｧ `temp integrity_check failed` / `database disk image is malformed` 繧堤｢ｺ隱・|
| **蠖ｱ髻ｿ遽・峇** | Gmail incremental ingest 縺悟､ｱ謨励Ν繝ｼ繝励↓蜈･繧翫『atchdog 縺・daemon 繧貞・襍ｷ蜍輔＠縺ｦ繧ょ屓蠕ｩ縺励↑縺・憾諷・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `email_search.db` 縺ｫ freelist 荳肴紛蜷医′蜈･繧・`PRAGMA integrity_check` 縺悟､ｱ謨励＠縺溘・**Why2**: `host_gmail_incremental_sync.py` 縺ｯ temp DB 縺ｮ讀懈渊縺ｧ逡ｰ蟶ｸ繧呈､懃衍縺励※繧ゅ‥aemon 蛛ｴ縺ｫ菫ｮ蠕ｩ蛻・ｲ舌′縺ｪ縺九▲縺溘・**Why3**: `continuous_email_ingest_daemon.py` 縺ｯ螟ｱ謨玲凾縺ｫ `error` 繧呈嶌縺・※蠕・ｩ溘☆繧九□縺代〒縲∫�ｴ謳阪す繧ｰ繝翫Ν縺ｨ荳闊ｬ繧ｨ繝ｩ繝ｼ繧貞玄蛻･縺励※縺・↑縺九▲縺溘・**Why4**: 譌｢蟄倥・ `repair_email_search_db.py` 縺ｯ縺ゅ▲縺溘′縲‥aemon 蜀・°繧牙ｮ牙・縺ｫ蜻ｼ縺ｶ驟咲ｷ壹′縺ｪ縺九▲縺溘・**Why5**: watchdog 繧・`db repair` 繧帝壼ｸｸ繧ｨ繝ｩ繝ｼ縺ｨ蛹ｺ蛻･縺励↑縺・燕謠舌〒縲∽ｿｮ蠕ｩ荳ｭ縺ｮ菫晁ｭｷ縺御ｸ崎ｶｳ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/continuous_email_ingest_daemon.py` 縺ｫ DB 遐ｴ謳阪す繧ｰ繝翫Ν讀懃衍縲∽ｿｮ蠕ｩ蜻ｼ縺ｳ蜃ｺ縺励〉epair cooldown縲〉epair 迥ｶ諷倶ｿ晏ｭ倥ｒ霑ｽ蜉�縲・`data/workspace/repair_email_search_db.py` 縺ｫ `--skip-stop-processes` 繧定ｿｽ蜉�縺励‥aemon 縺九ｉ螳牙・縺ｫ inline 螳溯｡後〒縺阪ｋ繧医≧縺ｫ縺励◆縲・`data/workspace/email_continuous_watchdog.py` 縺ｧ `stage == "db_repair"` 繧貞▼蜈ｨ謇ｱ縺・↓縺励※縲∽ｿｮ蠕ｩ荳ｭ縺ｮ辟｡鬧・↑蜀崎ｵｷ蜍輔ｒ髦ｲ豁｢縲・縺昴・蠕・`python data/workspace/repair_email_search_db.py --restart-watchdog` 繧貞ｮ溯｡後＠縺ｦ螳・DB 繧剃ｿｮ蠕ｩ縲・|
| **讀懆ｨｼ邨先棡** | 菫ｮ蠕ｩ邨先棡 `email_search_db_repair_status.json` 縺ｯ `stage=completed`縲・蠕ｩ譌ｧ蠕後・ DB 縺ｯ `integrity_check=ok`, `quick_check=ok`, `emails=22688`, `tasks=9065` 繧堤｢ｺ隱阪・watchdog 縺ｯ PID `10428`縲‥aemon 縺ｯ PID `11748` 縺ｧ蜀崎ｵｷ蜍墓ｸ医∩縲・|
| **Lessons Learned** | 菫ｮ蠕ｩ繧ｹ繧ｯ繝ｪ繝励ヨ縺悟ｭ伜惠縺励※縺・※繧ゅ∫焚蟶ｸ蛻・｡槭→蜻ｼ縺ｳ蜃ｺ縺礼ｵ瑚ｷｯ縺檎┌縺代ｌ縺ｰ迴ｾ蝣ｴ縺ｧ縺ｯ蝗槫ｾｩ縺励↑縺・・遐ｴ謳咲ｳｻ縺ｯ荳闊ｬ螟ｱ謨励→蛻・￠縲《tatus JSON 縺ｨ watchdog 縺ｮ荳｡譁ｹ縺ｧ蟆ら畑迥ｶ諷九ｒ謖√▽縺ｹ縺阪・|
| **蜀咲匱髦ｲ豁｢遲・* | daemon 蛛ｴ縺ｧ DB 遐ｴ謳阪ｒ讀懃衍縺励◆繧芽・蜍穂ｿｮ蠕ｩ縺ｸ蛻・ｲ舌☆繧九・watchdog 縺ｯ `db_repair` 繧貞・襍ｷ蜍募ｯｾ雎｡縺九ｉ螟悶☆縲・莉･蠕後・ DB 遐ｴ謳阪・ backup 縺ｨ repair status 繧呈ｮ九＠縺ｪ縺後ｉ蝗槫ｾｩ繧定ｩｦ縺ｿ繧九・|

## INC-018: mini PC 蟶ｸ鬧舌ワ繝ｼ繝阪せ縺ｮ譛ｪ謗･邯壹→隱､隴ｦ蝣ｱ繧呈紛逅・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | system hardening 轤ｹ讀懊〒縲～docker_desktop_ui_watchdog` 縺・observe-only縲～claudian_watchdog` 縺梧悴蟶ｸ鬧舌～minipc_optimizer` 縺ｫ閾ｪ蜍募・蜿｣縺檎┌縺・～n8n` API 繧ｭ繝ｼ縺後せ繧ｯ繝ｪ繝励ヨ縺ｸ逶ｴ譖ｸ縺阪～continuous_system_improvement` 縺御ｸ驛ｨ繧定ｪ､縺｣縺ｦ high risk 謇ｱ縺・＠縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱・|
| **蠖ｱ髻ｿ遽・峇** | Docker UI 荳崎ｪｿ譎ゅ↓閾ｪ蜍募屓蠕ｩ縺励↑縺・，laudian/mini PC 霆ｽ驥丞喧縺ｮ逶｣隕悶′蛻・ｌ縺ｦ繧よｰ励▼縺阪↓縺上＞縲《ystem summary 縺悟ｮ滄圀繧医ｊ蜊ｱ髯ｺ縺ｫ隕九∴繧九∫ｧ伜ｯ・ュ蝣ｱ縺ｮ繝ｭ繝ｼ繝・・繧ｷ繝ｧ繝ｳ縺碁屮縺励＞ |
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: watchdog 繧・optimizer 閾ｪ菴薙・蟄伜惠縺励※繧ゅ∝ｸｸ鬧占ｵｷ蜍輔ｄ逶ｸ莠定｣懷ｮ後・驟咲ｷ壹′荳崎ｶｳ縺励※縺・◆縲・**Why2**: Docker UI watchdog 縺ｯ `allowUiReset=false` 縺ｮ縺ｾ縺ｾ髟ｷ譎る俣 failure 繧堤ｩ阪ｓ縺ｧ縺・◆縲・**Why3**: Claudian watchdog 縺ｯ蜿､縺・Ο繧ｰ繧呈怙霑代・螟ｱ謨励→縺励※隗｣驥医＠縲・撕豁｢迥ｶ諷九〒繧・error 縺ｫ縺ｪ繧雁ｾ励◆縲・**Why4**: mini PC optimizer 縺ｯ謇句虚 CLI 縺ｮ縺ｿ縺ｧ縲∝ｸｸ鬧舌・逶｣隕門ｽｹ縺悟ｭ伜惠縺励↑縺九▲縺溘・**Why5**: n8n API 繧ｭ繝ｼ縺後せ繧ｯ繝ｪ繝励ヨ蜀・↓蝓九ａ霎ｼ縺ｾ繧後∬ｨｭ螳壼､画峩繧・・蛻ｩ逕ｨ譎ゅ↓繧ｳ繝ｼ繝臥ｷｨ髮・′蠢・ｦ√□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/docker_desktop_ui_watchdog.py` 縺ｫ髟ｷ譛・failure 譎ゅ・蠑ｷ蛻ｶ reset 蛻・ｲ舌ｒ霑ｽ蜉�縺励～docker_desktop_ui_watchdog_config.json` 繧・`quietMode=true`, `allowUiReset=true`, `consecutiveFailuresForReset=12` 縺ｸ譖ｴ譁ｰ縲・`data/workspace/claudian_watchdog.py` 繧偵〉ecent activity 縺檎┌縺・商縺・bridge/spawn 繝ｭ繧ｰ縺ｧ縺ｯ error 繧貞・縺輔↑縺・ｈ縺・｣懷ｼｷ縲・`data/workspace/minipc_optimizer_watchdog.py` 縺ｨ `scripts/start_minipc_optimizer_watchdog.ps1` 繧定ｿｽ蜉�縺励∽ｽ弱Γ繝｢繝ｪ譎ゅ□縺・`apply-lite` 繧貞ｮ溯｡後☆繧玖ｻｽ驥・watchdog 繧呈眠險ｭ縲・`data/workspace/continuous_system_improvement.py` 縺ｨ `data/workspace/auto_repair_allowed.py` 繧呈峩譁ｰ縺励．ocker UI / Claudian / mini PC watchdog 縺ｮ蟶ｸ鬧千｢ｺ隱阪→蜀崎ｵｷ蜍輔ｒ霑ｽ蜉�縲・`data/workspace/add_ai_scout_safe_sources.py` 縺ｨ `scripts/setup_n8n_changedetection_flow.ps1` 縺ｯ `N8N_API_KEY` 繧・`.env` / 迺ｰ蠅・､画焚縺九ｉ隱ｭ繧譁ｹ蠑上∈螟画峩縲・|
| **讀懆ｨｼ邨先棡** | `docker_desktop_ui_watchdog.py`, `claudian_watchdog.py`, `minipc_optimizer_watchdog.py` 縺ｯ縺吶∋縺ｦ `py_compile` 謌仙粥縲・螳溘・繝ｭ繧ｻ繧ｹ縺ｨ縺励※ 3 譛ｬ縺ｮ watchdog 襍ｷ蜍輔ｒ遒ｺ隱阪・`claudian_watchdog.py --once` 縺ｯ `stage=healthy`縲・`minipc_optimizer_watchdog_status.json` 縺ｧ縺ｯ free memory `35.14GB`, `freePercent=73.6`, `stage=healthy` 繧堤｢ｺ隱阪・Docker UI watchdog 縺ｯ `lastAction=reset_frontend_cache` 縺ｾ縺ｧ騾ｲ縺ｿ縲∽ｻ･蠕後・ status 縺ｧ reset 縺梧怏蜉ｹ蛹悶＆繧後◆縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | 逶｣隕悶Ο繧ｸ繝・け縺ｯ縲悟ｭ伜惠縺吶ｋ縺薙→縲阪ｈ繧翫悟ｸｸ鬧舌＠邯壹￠繧九％縺ｨ縲阪→縲悟商縺・､ｱ謨励ｒ迴ｾ蝨ｨ縺ｮ髫懷ｮｳ縺ｨ縺励※謇ｱ繧上↑縺・％縺ｨ縲阪′驥崎ｦ√・菴手ｲ�闕ｷ遶ｯ譛ｫ縺ｧ縺ｯ縲∝ｸｸ鬧舌ヤ繝ｼ繝ｫ繧貞｢励ｄ縺吶ｈ繧翫ｂ霆ｽ驥・watchdog 縺ｧ谿ｵ髫主宛蠕｡縺吶ｋ譁ｹ縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | system summary 縺ｨ auto repair 縺ｫ watchdog 蟶ｸ鬧舌メ繧ｧ繝・け繧呈ｮ九☆縲・Docker UI 縺ｯ observe-only 縺ｫ謌ｻ縺輔★谿ｵ髫・reset 繧堤ｶ咏ｶ壹☆繧九・遘伜ｯ・ュ蝣ｱ縺ｯ `.env` / 迺ｰ蠅・､画焚縺ｸ蟇・○縲√せ繧ｯ繝ｪ繝励ヨ逶ｴ譖ｸ縺阪ｒ蠅励ｄ縺輔↑縺・・|

---

## INC-013: Antigravity `Notify file events failed` 騾｣謇薙↓繧医ｋ IDE 繝輔Μ繝ｼ繧ｺ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Mini PC 縺悟壕蠕後°繧画妙邯夂噪縺ｫ繝輔Μ繝ｼ繧ｺ縺励ヽemote Desktop 荳翫〒 Antigravity 縺ｮ `Notify file events failed.` 縺梧焚遘偵＃縺ｨ縺ｫ蜃ｺ邯壹￠繧九％縺ｨ繧堤｢ｺ隱阪・|
| **蠖ｱ髻ｿ遽・峇** | Antigravity 邱ｨ髮・判髱｢縺ｮ謫堺ｽ懈ｧ菴惹ｸ九，PU 菴ｿ逕ｨ邇・ｸ頑・縲√Ο繧ｰ閧･螟ｧ蛹悶３emote Desktop 閾ｪ菴薙・謗･邯夂ｶｭ謖√＆繧後ｋ縺後！DE 縺ｮ蠢懃ｭ疲ｧ縺梧が蛹悶・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Antigravity 諡｡蠑ｵ繝帙せ繝医〒 `Notify file events failed.` 縺碁｣邯夂匱逕溘＠縺ｦ縺・◆縲・**Why2**: 蜷後§繝ｭ繧ｰ逶ｴ蜑阪↓ `Client is not running` 縺檎ｹｰ繧願ｿ斐＠蜃ｺ縺ｦ縺翫ｊ縲∬ｨ隱槭し繝ｼ繝舌・蜀崎ｵｷ蜍募ｾ後ｂ繝輔ぃ繧､繝ｫ逶｣隕夜夂衍縺�縺代′谿狗蕗縺励※縺・◆縲・**Why3**: 縺薙・繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｯ `data/workspace` 驟堺ｸ九↓ `node_modules`縲∬､・焚縺ｮ `venv`縲＾bsidian Vault縲∫函謌千黄縲√Ο繧ｰ縲》mp 繧貞､ｧ驥上↓謚ｱ縺医※縺翫ｊ縲∫屮隕門ｯｾ雎｡縺碁℃螟ｧ縺�縺｣縺溘・**Why4**: `.vscode/settings.json` 縺ｫ watcher 髯､螟悶ｄ讀懃ｴ｢髯､螟悶′縺ｪ縺上！DE 縺悟ｷｨ螟ｧ繝・ぅ繝ｬ繧ｯ繝医Μ鄒､繧偵◎縺ｮ縺ｾ縺ｾ逶｣隕悶＠縺ｦ縺・◆縲・**Why5**: 逶｣隕冶ｲ�闕ｷ縺ｮ鬮倥＞逕滓・迚ｩ縺ｨ螳滄圀縺ｫ邱ｨ髮・☆繧九さ繝ｼ繝蛾�伜沺縺ｮ蛻・屬繝昴Μ繧ｷ繝ｼ縺梧悴險ｭ螳壹〒縲∝・襍ｷ蜍墓凾縺ｫ蜷後§逶｣隕冶ｲ�闕ｷ縺悟・迴ｾ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `.vscode/settings.json` 縺ｫ `files.watcherExclude`縲～search.exclude`縲～python.analysis.exclude` 繧定ｿｽ蜉�縺励～node_modules`縲∽ｻｮ諠ｳ迺ｰ蠅・＾bsidian Vault縲∫函謌千黄縲》mp縲√Ο繧ｰ邉ｻ繝・ぅ繝ｬ繧ｯ繝医Μ繧堤屮隕悶・讀懃ｴ｢蟇ｾ雎｡縺九ｉ髯､螟悶＠縺溘・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | Antigravity 繝ｭ繧ｰ縺ｧ `Notify file events failed.` 縺・`Client is not running` 逶ｴ蠕後°繧臥ｶ咏ｶ夂匱逕溘＠縺ｦ縺・ｋ縺薙→縲，PU 荳贋ｽ阪↓ Antigravity 譛ｬ菴薙→ `remoting_host` 縺御ｸｦ繧薙〒縺・ｋ縺薙→縲∫屮隕門ｯｾ雎｡縺ｫ蟾ｨ螟ｧ繝・ぅ繝ｬ繧ｯ繝医Μ縺悟性縺ｾ繧後※縺・ｋ縺薙→繧堤｢ｺ隱阪＠縺溘りｨｭ螳壼渚譏�蠕後・ Antigravity 縺ｮ `Developer: Reload Window` 縺ｾ縺溘・繧｢繝励Μ蜀崎ｵｷ蜍輔〒譁ｰ縺励＞ watcher 險ｭ螳壹′譛牙柑蛹悶＆繧後ｋ迥ｶ諷九↓縺励◆縲・|
| **Lessons Learned** | Remote Desktop 繧呈ｭ｢繧√ｉ繧後↑縺・憾豕√〒縺ｯ縲√∪縺・IDE 縺ｮ watcher 雋�闕ｷ繧貞・繧企屬縺呎婿縺悟ｮ牙・縺ｧ蜉ｹ譫懊′鬮倥＞縲ょｷｨ螟ｧ縺ｪ逕滓・迚ｩ繧・Vault 繧貞酔荳繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｧ髢九￥蝣ｴ蜷医∵､懃ｴ｢髯､螟悶□縺代〒縺ｪ縺・watcher 髯､螟悶ｂ譛蛻昴°繧牙・繧後※縺翫￥蠢・ｦ√′縺ゅｋ縲・|
| **蜀咲匱髦ｲ豁｢遲・* | 譁ｰ縺励＞螟ｧ螳ｹ驥上ョ繧｣繝ｬ繧ｯ繝医Μ繧偵％縺ｮ repo 驟堺ｸ九∈霑ｽ蜉�縺吶ｋ髫帙・縲～.vscode/settings.json` 縺ｮ watcher 髯､螟悶↓蜷梧凾霑ｽ蜉�縺吶ｋ縲・DE 繝輔Μ繝ｼ繧ｺ邉ｻ縺ｮ髫懷ｮｳ縺ｧ縺ｯ縲～logs/.../7-antigravity.log` 縺ｮ `Client is not running` 縺ｨ `Notify file events failed.` 縺ｮ邨・∩蜷医ｏ縺帙ｒ蛻晏虚遒ｺ隱埼�・岼縺ｫ縺吶ｋ縲・|

## INC-014: Antigravity 縺ｮ R 諡｡蠑ｵ縺・`cmd.exe` 繝昴ャ繝励い繝・・繧帝｣邯夊ｵｷ蜍・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | Antigravity 蠕ｩ譌ｧ蠕後ｂ `CMD` 繧ｦ繧｣繝ｳ繝峨え縺梧焚遘偵＃縺ｨ縺ｫ髢九＞縺ｦ髢峨§繧九％縺ｨ繧堤｢ｺ隱阪ょｮ溯｡御ｸｭ繝励Ο繧ｻ繧ｹ縺ｮ隕ｪ蟄宣未菫ゅ→繧ｳ繝槭Φ繝峨Λ繧､繝ｳ繧定ｪｿ譟ｻ縺励◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Mini PC 謫堺ｽ懈ｧ菴惹ｸ九∫判髱｢縺ｮ縺｡繧峨▽縺阪、ntigravity 蛻ｩ逕ｨ荳ｭ縺ｮ髮・ｸｭ髦ｻ螳ｳ縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `cmd.exe` 縺悟捉譛溽噪縺ｫ襍ｷ蜍輔＠縺ｦ縺・◆縲・**Why2**: 繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺ｯ `cmd.exe /c ... Rterm.exe ... helpServer.R` 縺ｨ `languageServer.R` 縺ｧ縲、ntigravity 縺ｮ R 諡｡蠑ｵ縺瑚ｵｷ轤ｹ縺�縺｣縺溘・**Why3**: 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜀・・ R 髢｢騾｣繝輔ぃ繧､繝ｫ讀懃衍縺ｧ R 諡｡蠑ｵ縺・activation 縺輔ｌ縲∬ｨ隱槭し繝ｼ繝舌→ help server 繧定・蜍戊ｵｷ蜍輔＠縺ｦ縺・◆縲・**Why4**: 縺薙・ repo 縺ｧ縺ｯ R 繧剃ｸｻ隕∫畑騾斐→縺励※菴ｿ縺｣縺ｦ縺・↑縺・ｸ譁ｹ縲～.vscode/settings.json` 縺ｫ縺ｯ `r.rpath.windows` 縺ｮ縺ｿ縺後≠繧翫∬・蜍戊ｵｷ蜍輔ｒ謚代∴繧玖ｨｭ螳壹′縺ｪ縺九▲縺溘・**Why5**: 髱樔ｽｿ逕ｨ諡｡蠑ｵ縺ｮ閾ｪ蜍墓ｩ溯・繧偵Ρ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜊倅ｽ阪〒邨槭ｋ驕狗畑縺梧悴謨ｴ蛯吶〒縲∽ｸ崎ｦ√↑陬懷勧繝励Ο繧ｻ繧ｹ縺悟ｸｸ譎りｵｷ蜍輔＠縺ｦ縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `.vscode/settings.json` 縺ｫ `r.lsp.enabled=false`縲～r.sessionWatcher=false`縲～r.helpPanel.previewLocalPackages=[]`縲～r.session.viewers.viewColumn.*=Disable`縲～r.alwaysUseActiveTerminal=true` 繧定ｿｽ蜉�縺励ヽ 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｨ隱槭し繝ｼ繝舌・Help/Plot 繝薙Η繝ｼ繧｢襍ｷ蜍輔ｒ蛛懈ｭ｢縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `.vscode/settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | 螳溯｡御ｸｭ `cmd.exe` 縺ｮ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺・Antigravity 驟堺ｸ九・ `reditorsupport.r-2.8.8-universal` 繧呈欠縺励※縺・ｋ縺薙→縲∵怙譁ｰ繝ｭ繧ｰ縺ｫ `R Language Server ... started` 縺悟・縺ｦ縺・ｋ縺薙→繧堤｢ｺ隱阪＠縺溘りｨｭ螳壼渚譏�蠕後・ Antigravity 縺ｮ繧ｦ繧｣繝ｳ繝峨え蜀崎ｪｭ縺ｿ霎ｼ縺ｿ縺ｾ縺溘・蜀崎ｵｷ蜍輔〒譁ｰ險ｭ螳壹′譛牙柑縺ｫ縺ｪ繧九・|
| **Lessons Learned** | IDE 繝輔Μ繝ｼ繧ｺ隱ｿ譟ｻ縺ｧ縺ｯ縲√ヵ繧｡繧､繝ｫ watcher 縺�縺代〒縺ｪ縺乗僑蠑ｵ縺瑚｣上〒遶九■荳翫￡繧玖｣懷勧繝励Ο繧ｻ繧ｹ縺ｾ縺ｧ隕九ｋ縺ｨ蜴溷屏縺ｫ譌ｩ縺丞ｱ翫￥縲ゆｽｿ縺｣縺ｦ縺・↑縺・ｨ隱樊僑蠑ｵ縺ｯ縲∫┌蜉ｹ蛹悶〒縺阪↑縺・�ｴ蜷医〒繧ゅΡ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壹〒閾ｪ蜍墓ｩ溯・繧呈ｭ｢繧√ｋ縺�縺代〒螳牙ｮ壽ｧ縺御ｸ翫′繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | 譁ｰ縺励＞ IDE 諡｡蠑ｵ繧貞ｸｸ逕ｨ縺吶ｋ蜑阪↓縲∬・蜍戊ｵｷ蜍輔☆繧玖ｨ隱槭し繝ｼ繝舌”elp server縲『atcher 縺ｮ譛臥┌繧堤｢ｺ隱阪☆繧九ゆｻ雁屓縺ｮ繧医≧縺ｪ `cmd.exe` 轤ｹ貊・′蜃ｺ縺溷�ｴ蜷医・縲√∪縺夊ｦｪ繝励Ο繧ｻ繧ｹ縺ｨ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ縺九ｉ諡｡蠑ｵ蜷阪ｒ迚ｹ螳壹＠縺ｦ繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壹〒謚大宛縺吶ｋ縲・|

## INC-015: R 諡｡蠑ｵ險ｭ螳壹□縺代〒縺ｯ `cmd.exe` 轤ｹ貊・ｒ豁｢繧√″繧後★縲∵僑蠑ｵ譛ｬ菴薙ｒ辟｡蜉ｹ蛹・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | INC-014 縺ｮ險ｭ螳壼､画峩蠕後↓ Antigravity 繧貞・襍ｷ蜍輔＠縺ｦ繧・`cmd.exe` 繝昴ャ繝励い繝・・縺檎ｶ咏ｶ壹よ怙譁ｰ繝ｭ繧ｰ `20260412T000423` 縺ｨ `cmd.exe` 縺ｮ繧ｳ繝槭Φ繝峨Λ繧､繝ｳ繧貞・遒ｺ隱阪＠縺溘・|
| **蠖ｱ髻ｿ遽・峇** | 繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ險ｭ螳壼､画峩縺�縺代〒縺ｯ R 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｵｷ蜍輔′谿九ｊ縲∫判髱｢轤ｹ貊・→謫堺ｽ憺仆螳ｳ縺檎ｶ咏ｶ壹＠縺溘・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `r.lsp.enabled=false` 縺ｨ `r.sessionWatcher=false` 繧貞・繧後※繧・`cmd.exe /c ... Rterm.exe ... helpServer.R` 縺悟・逋ｺ縺励◆縲・**Why2**: R 諡｡蠑ｵ縺ｯ `workspaceContains` 縺ｫ繧医ｊ activation 縺輔ｌ縲∬ｨｭ螳夂┌蜉ｹ蛹門ｾ後ｂ Help server 蛛ｴ縺ｮ襍ｷ蜍慕ｵ瑚ｷｯ縺梧ｮ九▲縺ｦ縺・◆縲・**Why3**: 縺薙・繝ｯ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ縺ｫ縺ｯ R 髢｢騾｣繝輔ぃ繧､繝ｫ讀懃衍譚｡莉ｶ縺後≠繧翫∵僑蠑ｵ閾ｪ菴薙・隱ｭ縺ｿ霎ｼ縺ｿ繧帝∩縺代ｉ繧後↑縺九▲縺溘・**Why4**: Antigravity 蛛ｴ縺ｧ縺薙・諡｡蠑ｵ繧偵Ρ繝ｼ繧ｯ繧ｹ繝壹・繧ｹ蜊倅ｽ阪↓邁｡蜊倥↓ disable 縺ｧ縺阪★縲∬ｨｭ螳壹□縺代〒縺ｯ螳悟・蛛懈ｭ｢縺ｫ螻翫°縺ｪ縺九▲縺溘・**Why5**: 髱樔ｽｿ逕ｨ險隱樊僑蠑ｵ縺ｫ蟇ｾ縺吶ｋ譛邨よ焔谿ｵ縺ｨ縺励※縲悟庄騾・↑諡｡蠑ｵ騾驕ｿ縲阪ｒ驕狗畑謇矩�・↓謖√▲縺ｦ縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | Antigravity 繧貞●豁｢縺励◆荳翫〒 `C:\\Users\\yasu\\.antigravity\\extensions\\reditorsupport.r-2.8.8-universal` 繧・`...universal.disabled` 縺ｸ繝ｪ繝阪・繝�縺励ヽ 諡｡蠑ｵ譛ｬ菴薙ｒ蜿ｯ騾・↓辟｡蜉ｹ蛹悶＠縺溘・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | 辟｡蜉ｹ蛹門ｾ後∵僑蠑ｵ荳隕ｧ荳翫・ `reditorsupport.r-2.8.8-universal.disabled` 縺ｨ縺励※騾驕ｿ縺輔ｌ縲、ntigravity 蜀崎ｵｷ蜍墓凾縺ｫ蠖楢ｩｲ諡｡蠑ｵ縺後Ο繝ｼ繝牙ｯｾ雎｡縺九ｉ螟悶ｌ繧狗憾諷九↓縺励◆縲・|
| **Lessons Learned** | IDE 諡｡蠑ｵ縺ｮ閾ｪ蜍戊ｵｷ蜍輔・縲∬ｨｭ螳壼､繧医ｊ繧・activation event 縺悟・縺ｫ蜉ｹ縺丞�ｴ蜷医′縺ゅｋ縲ゆｸ崎ｦ∵僑蠑ｵ縺悟ｮ牙ｮ壽ｧ繧貞ｴｩ縺吶→縺阪・縲∝庄騾・↑繝輔か繝ｫ繝騾驕ｿ縺梧怙繧る溘￥螳牙・縺ｪ豁｢陦遲悶↓縺ｪ繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | 髱樔ｽｿ逕ｨ諡｡蠑ｵ縺瑚｣懷勧繝励Ο繧ｻ繧ｹ繧・watcher 繧貞享謇九↓襍ｷ蜍輔☆繧句�ｴ蜷医・) 險ｭ螳壹〒謚大宛縲・) 縺�繧√↑繧画僑蠑ｵ譛ｬ菴薙ｒ騾驕ｿ縲√・鬆・〒蟇ｾ蜃ｦ縺吶ｋ縲ょｾｩ蟶ｰ縺悟ｿ・ｦ√↓縺ｪ縺｣縺溷�ｴ蜷医・ `.disabled` 繧貞・蜷阪↓謌ｻ縺励※蜀崎ｵｷ蜍輔☆繧九・|

## INC-016: `continuous_email_ingest_daemon.py` 縺悟ｭ・Python 繧偵さ繝ｳ繧ｽ繝ｼ繝ｫ莉倥″縺ｧ襍ｷ蜍・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-12 |
| **逋ｺ隕区婿豕・* | R 諡｡蠑ｵ繧堤┌蜉ｹ蛹悶＠縺溷ｾ後ｂ譁ｰ縺励＞ `CMD` 縺悟・逋ｺ縲よ怙譁ｰ `conhost.exe` 縺ｮ隕ｪ蟄宣未菫ゅｒ霑ｽ縺｣縺溘→縺薙ｍ縲～python.exe -> host_gmail_incremental_sync.py` 縺ｫ蛻ｰ驕斐＠縺溘・|
| **蠖ｱ髻ｿ遽・峇** | 謨ｰ蛻・＃縺ｨ縺ｫ `CMD` 繧ｦ繧｣繝ｳ繝峨え縺・1 縺､髢九″縲√Θ繝ｼ繧ｶ繝ｼ謫堺ｽ懊ｒ螯ｨ縺偵◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: 譁ｰ縺励＞ `conhost.exe` 縺檎函謌舌＆繧後※縺・◆縲・**Why2**: 隕ｪ縺ｯ `python.exe` 縺ｧ縲～host_gmail_incremental_sync.py` 繧貞ｮ溯｡後＠縺ｦ縺・◆縲・**Why3**: 縺昴・隕ｪ縺ｯ `continuous_email_ingest_daemon.py` 縺ｧ縲～subprocess.Popen()` 縺ｫ繧医ｊ蟄・Python 繧定ｵｷ蜍輔＠縺ｦ縺・◆縲・**Why4**: Windows 蜷代￠縺ｮ `CREATE_NO_WINDOW` 謖・ｮ壹′縺ｪ縺上∵里螳壹〒繧ｳ繝ｳ繧ｽ繝ｼ繝ｫ莉倥″襍ｷ蜍輔↓縺ｪ縺｣縺ｦ縺・◆縲・**Why5**: 蟶ｸ鬧舌ワ繝ｼ繝阪せ縺九ｉ蟄舌・繝ｭ繧ｻ繧ｹ繧定ｵｷ蜍輔☆繧矩圀縺ｮ縲碁撼陦ｨ遉ｺ襍ｷ蜍輔阪Ν繝ｼ繝ｫ縺後さ繝ｼ繝峨↓邨・∩霎ｼ縺ｾ繧後※縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/continuous_email_ingest_daemon.py` 縺ｮ `subprocess.Popen()` 縺ｫ Windows 縺ｧ縺ｯ `creationflags=subprocess.CREATE_NO_WINDOW` 繧呈ｸ｡縺吶ｈ縺・ｿｮ豁｣縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/workspace/continuous_email_ingest_daemon.py`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `conhost.exe PID 13652` 縺ｮ隕ｪ縺・`python.exe PID 6160`縲√◎縺ｮ隕ｪ縺・`continuous_email_ingest_daemon.py` 縺ｧ縺ゅｋ縺薙→繧堤｢ｺ隱阪よ里蟄倥・ `python.exe` / `conhost.exe` 縺ｯ蛛懈ｭ｢貂医∩縺ｧ縲∵ｬ｡蝗櫁ｵｷ蜍輔°繧峨・髱櫁｡ｨ遉ｺ繝輔Λ繧ｰ莉倥″縺ｧ蟄舌・繝ｭ繧ｻ繧ｹ縺瑚ｵｷ蜍輔☆繧区ｧ区・縺ｫ縺励◆縲・|
| **Lessons Learned** | Windows 蟶ｸ鬧舌せ繧ｯ繝ｪ繝励ヨ縺悟挨縺ｮ Python 繧定ｵｷ蜍輔☆繧句�ｴ蜷医∬｡ｨ遉ｺ譛臥┌縺ｯ譏守､ｺ縺励↑縺・→譌｢螳壽嫌蜍輔↓蠑輔″縺壹ｉ繧後ｋ縲６I 繧呈戟縺溘↑縺・｣懷勧繝励Ο繧ｻ繧ｹ縺ｯ縲∝ｸｸ縺ｫ髱櫁｡ｨ遉ｺ襍ｷ蜍輔ｒ繝・ヵ繧ｩ繝ｫ繝医↓縺吶ｋ譁ｹ縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 縺ｧ `subprocess.Popen()` / `run()` 繧剃ｽｿ縺・ｸｸ鬧千ｳｻ繧ｹ繧ｯ繝ｪ繝励ヨ縺ｯ縲√さ繝ｳ繧ｽ繝ｼ繝ｫ荳崎ｦ√↑繧・`CREATE_NO_WINDOW` 繧呈ｨ呎ｺ門喧縺吶ｋ縲よ眠縺励＞ `conhost.exe` 縺悟・縺溷�ｴ蜷医・隕ｪ蟄宣未菫ゅｒ縺溘←繧翫√∪縺・daemon 縺九ｉ縺ｮ蟄占ｵｷ蜍輔°繧堤｢ｺ隱阪☆繧九・|

---

## INC-010: Claudian 蜷檎ｨｮ髫懷ｮｳ縺ｮ閾ｪ蜍墓､懃衍谺�螯・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺九ｉ縲悟酔遞ｮ髫懷ｮｳ繧定・蜍墓､懃衍縺吶ｋ繝√ぉ繝・け鬆・岼縺ｾ縺ｧ霑ｽ蜉�縲阪→隕∵悍縲よ里蟄倥・蠕ｩ譌ｧ蠕後ｂ縲～claudian-spawn.log` 縺ｨ `claudian-bridge.log` 繧呈焔蜍輔〒隱ｭ繧驕狗畑縺ｫ萓晏ｭ倥＠縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Claudian 縺ｮ Windows 襍ｷ蜍輔｜ridge response shape縲＾llama 逶ｴ邨占ｨｭ螳壹∬ｿ皮ｭ泌ｾ・■驕・ｻｶ縺ｮ蜀咲匱繧貞叉譎ゅ↓讀懃衍縺ｧ縺阪★縲∝・縺ｳ縲檎┌蜿榊ｿ懊阪↓隕九∴繧九Μ繧ｹ繧ｯ縺梧ｮ九▲縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: 蠕ｩ譌ｧ繧ｳ繝ｼ繝峨・蜈･縺｣縺ｦ縺・◆縺後∝・逋ｺ蜈・吶ｒ邯咏ｶ夂屮隕悶☆繧・watchdog 縺後↑縺九▲縺溘・**Why2**: `spawn EINVAL`縲～undefined.id`縲～model not found`縲∫ｩｺ霑皮ｭ斐｝ending turn 縺悟挨繝ｭ繧ｰ縺ｫ謨｣蝨ｨ縺励※縺・◆縲・**Why3**: 蜿､縺・､ｱ謨励Ο繧ｰ縺梧ｮ九ｋ縺溘ａ縲∝腰邏・grep 縺ｧ縺ｯ隱､讀懃衍縺励ｄ縺吶￥縲梧怙蠕後・謌仙粥縺梧怙蠕後・螟ｱ謨励ｒ荳雁屓縺｣縺溘°縲阪・蛻､螳壹′蠢・ｦ√□縺｣縺溘・**Why4**: 荳谺｡蠕ｩ譌ｧ繧貞━蜈医＠縺溽ｵ先棡縲・°逕ｨ observability 縺ｮ螳溯｣・′蠕悟屓縺励↓縺ｪ縺｣縺ｦ縺・◆縲・**Why5**: Claudian 蟆ら畑縺ｮ `status.json` / `harness_status.json` 繧貞・縺吝､紋ｻ倥￠繝上・繝阪せ縺梧悴謨ｴ蛯吶□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `data/workspace/claudian_watchdog.py` 繧定ｿｽ蜉�縺励・1) `.claudian/claudian-settings.json` 縺ｨ plugin `data.json` 縺ｮ險ｭ螳壽紛蜷域ｧ縲・2) spawn log 縺ｮ `spawn EINVAL` 蜀咲匱譛臥┌縺ｨ configured path 蝗槫ｾｩ縲・3) bridge log 縺ｮ `undefined.id` / `model 'openai/qwen3:8b' not found` / 遨ｺ霑皮ｭ・/ pending turn / 鬮倬≦蟒ｶ縲・4) Ollama `/api/tags` 縺ｫ繧医ｋ `qwen3:8b` 蟄伜惠遒ｺ隱阪ｒ閾ｪ蜍募愛螳壹☆繧九ｈ縺・↓縺励◆縲ゅ≠繧上○縺ｦ `scripts/start_claudian_watchdog.ps1` 繧定ｿｽ蜉�縺励∝､紋ｻ倥￠蟶ｸ鬧占ｵｷ蜍輔ｒ蜿ｯ閭ｽ縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/workspace/claudian_watchdog.py`, `scripts/start_claudian_watchdog.ps1`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `python data/workspace/claudian_watchdog.py --once` 縺ｧ status JSON 繧堤函謌舌＠縲・縺､縺ｮ繝√ぉ繝・け縺悟・蜉帙＆繧後ｋ縺薙→繧堤｢ｺ隱阪☆繧九Ａspawn EINVAL` 縺ｯ縲悟ｱ･豁ｴ縺ゅｊ縺�縺悟屓蠕ｩ貂医∩縲阪｜ridge 縺ｯ recent completed turn 縺ｨ latency縲＾llama 縺ｯ `qwen3:8b` 縺ｮ蟄伜惠繧貞愛螳壹〒縺阪ｋ讒区・縲・|
| **Lessons Learned** | 蠕ｩ譌ｧ縺�縺代〒邨ゅ∴繧九→縲∝・逋ｺ譎ゅ・蛻晏虚縺後∪縺滓焔蜍輔Ο繧ｰ隱ｿ譟ｻ縺ｫ謌ｻ繧九８indows wrapper 繧・bridge contract 縺ｮ繧医≧縺ｪ蠅・阜髫懷ｮｳ縺ｯ縲∽ｿｮ豁｣縺ｨ蜷梧凾縺ｫ watchdog / status JSON 縺ｾ縺ｧ蜈･繧後※蛻昴ａ縺ｦ驕狗畑蜩∬ｳｪ縺ｫ縺ｪ繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | `claudian_watchdog.py` 繧貞ｮ壽悄螳溯｡後∪縺溘・蟶ｸ鬧舌＆縺帙～data/workspace/claudian_watchdog_status.json` 縺ｮ `stage` / `findings` 繧堤屮隕門ｯｾ雎｡縺ｫ縺吶ｋ縲ゆｻ雁ｾ・Claudian 髢｢騾｣菫ｮ豁｣繧貞・繧後ｋ縺溘・縺ｫ縲√％縺ｮ watchdog 縺ｸ譁ｰ縺励＞ failure signature 繧定ｿｽ蜉�縺吶ｋ縲・|

---

## INC-012: Claudian Codex 繝｢繝・Ν驕ｸ謚櫁い縺悟ｰ代↑縺剰ｻｽ驥上Δ繝・Ν縺ｸ蛻・ｊ譖ｿ縺医↓縺上＞
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ蝣ｱ蜻翫・laudian 縺ｮ Codex 繝｢繝・Ν繝峨Ο繝・・繝繧ｦ繝ｳ縺ｫ `GPT-5.4` 縺ｨ `qwen3:8b` 縺ｪ縺ｩ荳驛ｨ縺励°蜃ｺ縺壹√ｈ繧願ｻｽ縺・Δ繝・Ν縺ｸ蛻・ｊ譖ｿ縺医↓縺上°縺｣縺溘・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex UI縲る∈謚櫁い荳崎ｶｳ縺ｫ繧医ｊ縲・溷ｺｦ驥崎ｦ悶・蛻・ｊ譖ｿ縺医ｄ霑ｽ蜉�繝｢繝・Ν縺ｮ髴ｲ蜃ｺ縺碁°逕ｨ萓晏ｭ倥↓縺ｪ縺｣縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Codex 繝｢繝・Ν荳隕ｧ縺・`main.js` 蜀・・髱咏噪驟榊・縺ｫ縺ｻ縺ｼ蝗ｺ螳壹＆繧後※縺・◆縲・**Why2**: 譌｢蟄伜ｮ溯｣・・ `OPENAI_MODEL` 1莉ｶ縺�縺代ｒ迚ｹ蛻･謇ｱ縺・＠縲∬､・焚繝｢繝・Ν縺ｮ蛻玲嫌繧貞女縺大叙繧後↑縺九▲縺溘・**Why3**: 繝ｭ繝ｼ繧ｫ繝ｫ/霑ｽ蜉�繝｢繝・Ν繧貞・縺励◆縺・�ｴ蜷医〒繧ゅゞI 縺ｫ貂｡縺帙ｋ迺ｰ蠅・､画焚縺悟腰荳繝｢繝・Ν蜑肴署縺�縺｣縺溘・**Why4**: 縺昴・縺溘ａ霆ｽ驥上Δ繝・Ν繧・ｰ・擂霑ｽ蜉�繝｢繝・Ν繧貞・縺吶◆縺ｳ縺ｫ繧ｳ繝ｼ繝牙､画峩縺悟ｿ・ｦ√□縺｣縺溘・**Why5**: 縲梧里螳壹Δ繝・Ν縲阪→縲檎腸蠅・罰譚･縺ｮ霑ｽ蜉�繝｢繝・Ν縲阪ｒ繝槭・繧ｸ縺吶ｋ蜈ｱ騾壼・逅・′ Codex 蛛ｴ縺ｫ譛ｪ螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `main.js` 縺ｮ Codex 繝｢繝・Ν螳夂ｾｩ縺ｫ `gpt-5.3-codex` 縺ｨ `gpt-5.2` 繧定ｿｽ蜉�縺励√＆繧峨↓ `OPENAI_AVAILABLE_MODELS` / `CODEX_AVAILABLE_MODELS` 縺九ｉ隍・焚繝｢繝・Ν繧定ｪｭ縺ｿ霎ｼ繧薙〒繝峨Ο繝・・繝繧ｦ繝ｳ縺ｸ邨ｱ蜷医☆繧九ｈ縺・ｿｮ豁｣縺励◆縲ゅ≠繧上○縺ｦ `.claudian/claudian-settings.json` 縺ｨ plugin `data.json` 縺ｫ `OPENAI_AVAILABLE_MODELS` 繧定ｿｽ蜉�縺励∬ｻｽ驥丞ｯ・ｊ縺ｮ蛟呵｣懊ｒ蜊ｳ譎る∈謚槫庄閭ｽ縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` 縺ｧ讒区枚繧ｨ繝ｩ繝ｼ縺ｪ縺励ｒ遒ｺ隱阪ＡOPENAI_AVAILABLE_MODELS` 縺ｫ蛻玲嫌縺励◆繝｢繝・Ν縺瑚ｨｭ螳壹ヵ繧｡繧､繝ｫ荳翫〒菫晄戟縺輔ｌ縲∵里螳壹Δ繝・Ν縺ｨ驥崎､・勁蜴ｻ縺励▽縺､ UI 縺ｫ貂｡繧区ｧ区・縺ｫ縺ｪ縺｣縺溘・|
| **Lessons Learned** | 繝｢繝・Ν驕ｸ謚・UI 縺ｯ蝗ｺ螳壼・謖吶↓蟇・○縺吶℃繧九→驕狗畑騾溷ｺｦ縺瑚誠縺｡繧九りｿｽ蜉�鬆ｻ蠎ｦ縺碁ｫ倥＞蛟､縺ｯ縲∵里螳壼､繧呈戟縺｡縺､縺､迺ｰ蠅・､画焚縺九ｉ諡｡蠑ｵ縺ｧ縺阪ｋ蠖｢縺ｫ縺励※縺翫￥縺ｨ菫晏ｮ医＠繧・☆縺・・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ Codex 繝｢繝・Ν霑ｽ蜉�譎ゅ・ `OPENAI_AVAILABLE_MODELS` 繧貞━蜈育噪縺ｫ譖ｴ譁ｰ縺励√さ繝ｼ繝牙､画峩縺ｯ譌｢螳壼呵｣懊ｄ繝槭・繧ｸ繝ｭ繧ｸ繝・け縺ｮ謾ｹ蝟・凾縺ｫ髯仙ｮ壹☆繧九ゆｻ雁ｾ梧眠繝｢繝・Ν繧定ｶｳ縺咎圀繧ょ腰荳 `OPENAI_MODEL` 縺�縺代↓萓晏ｭ倥＠縺ｪ縺・％縺ｨ繧偵Ξ繝薙Η繝ｼ鬆・岼縺ｫ蜉�縺医ｋ縲・|

---

## INC-011: Claudian 蛻晏屓蠢懃ｭ斐・菴捺─驕・ｻｶ
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺・`Hello` 蠕後・霑皮ｭ泌ｾ・■縺碁聞縺吶℃繧九→蝣ｱ蜻翫Ｃridge log 縺ｧ縺ｯ 2026-04-11 13:10:40 JST 縺ｮ騾∽ｿ｡縺九ｉ 13:13:37 JST 縺ｮ霑皮ｭ泌ｮ御ｺ・∪縺ｧ邏・77遘偵°縺九▲縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Claudian 縺ｮ霆ｽ縺・ｼ夊ｩｱ縺ｧ繧ゅ檎┌蜿榊ｿ懊阪↓隕九∴繧・☆縺上∝茜逕ｨ邯咏ｶ壽ｧ繧剃ｸ九￡縺ｦ縺・◆縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: `Hello` 縺ｮ繧医≧縺ｪ霆ｽ縺・・蜉帙〒繧ゅΟ繝ｼ繧ｫ繝ｫ `qwen3:8b` 縺ｮ蠢懃ｭ泌ｮ御ｺ・∪縺ｧ蠕・▲縺ｦ縺九ｉ UI 縺ｫ蜈ｨ譁・ｒ霑斐＠縺ｦ縺・◆縲・**Why2**: bridge 縺ｯ `stream:false` 縺ｧ completion 螳御ｺ・ｾ後↓ 1 蝗槭□縺・`delta` 繧帝√▲縺ｦ縺・◆縲・**Why3**: 蛻晏屓繝｡繝・そ繝ｼ繧ｸ騾∽ｿ｡譎ゅ↓縺ｯ蛻･繧ｹ繝ｬ繝・ラ縺ｧ莨夊ｩｱ繧ｿ繧､繝医Ν逕滓・繧ょ酔譎ゅ↓襍ｰ縺｣縺ｦ縺・◆縲・**Why4**: 繧ｿ繧､繝医Ν逕滓・繧よ悽菴薙→蜷後§繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν繧剃ｽｿ縺・◆繧√；PU/CPU 雉・ｺ舌→蠕・■譎る俣繧剃ｽ呵ｨ医↓豸郁ｲｻ縺励※縺・◆縲・**Why5**: 菴捺─騾溷ｺｦ謾ｹ蝟・・縺溘ａ縺ｮ縲悟・縺ｫ譁・ｭ励ｒ蜃ｺ縺吶阪瑚｣懷勧蜃ｦ逅・ｒ繝ｭ繝ｼ繧ｫ繝ｫ蜊ｳ譎ょ喧縺吶ｋ縲阪→縺・≧譛驕ｩ蛹悶′ bridge 縺ｫ譛ｪ螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧呈峩譁ｰ縺励・1) 騾壼ｸｸ蠢懃ｭ斐・ Ollama OpenAI 莠呈鋤 API 繧・`stream:true` 縺ｧ蜻ｼ縺ｳ蜃ｺ縺励※ `item/agentMessage/delta` 繧帝先ｬ｡騾√ｋ縲・2) `max_tokens: 160` 縺ｨ `temperature: 0.2` 縺ｧ遏ｭ繧√・螳牙ｮ壼ｯ・ｊ縺ｫ縺吶ｋ縲・3) 繧ｿ繧､繝医Ν逕滓・繝ｪ繧ｯ繧ｨ繧ｹ繝医・繝｢繝・Ν繧貞他縺ｰ縺・bridge 蜀・〒蜊ｳ譎ら函謌舌☆繧九√ｈ縺・↓縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check` 縺ｧ讒区枚遒ｺ隱肴ｸ医∩縲ゅΟ繝ｼ繧ｫ繝ｫ蜀咲樟縺ｧ繧ｿ繧､繝医Ν逕滓・繝ｪ繧ｯ繧ｨ繧ｹ繝医・蜊ｳ蠎ｧ縺ｫ `Greet the assistant` 繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪る壼ｸｸ莨夊ｩｱ縺ｯ `item/agentMessage/start` 縺悟叉譎ゅ↓蜃ｺ繧九％縺ｨ繧堤｢ｺ隱阪＠縺溘・|
| **Lessons Learned** | 繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν縺ｧ縺ｯ縲梧怙邨ょｮ御ｺ・凾髢薙阪□縺代〒縺ｪ縺上梧怙蛻昴・蜿ｯ隕匁枚蟄励∪縺ｧ縺ｮ譎る俣縲阪ｒ譛驕ｩ蛹悶＠縺ｪ縺・→縲√Θ繝ｼ繧ｶ繝ｼ菴捺─縺ｯ螟ｧ縺阪￥謔ｪ蛹悶☆繧九り｣懷勧繧ｿ繧ｹ繧ｯ縺・deterministic 縺ｫ蜃ｦ逅・〒縺阪ｋ縺ｪ繧峨Δ繝・Ν縺ｫ謚輔￡縺ｪ縺・婿縺悟ｮ牙ｮ壹☆繧九・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ latency 謾ｹ蝟・〒縺ｯ縲√Δ繝・Ν螟画峩蜑阪↓ `streaming`縲～token cap`縲～title-generation bypass` 縺ｮ繧医≧縺ｪ transport 蛛ｴ蟇ｾ遲悶ｒ蜈医↓讀懆ｨ弱☆繧九Ｘatchdog 縺ｮ latency 繝√ぉ繝・け繧堤ｶ咏ｶ壹＠縲∝・蠎ｦ 2 蛻・ｶ・・螻･豁ｴ縺悟｢励∴繧句�ｴ蜷医・霆ｽ驥上Δ繝・Ν霑ｽ蜉�繧呈､懆ｨ弱☆繧九・|

---

## INC-007: Claudian `spawn EINVAL` 蜀阪・匱・・onfigured `cliPath` 縺・PATH 閾ｪ蜍戊ｧ｣豎ｺ縺ｫ雋�縺代ｋ・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ蝣ｱ蜻・`Error: spawn EINVAL`縲ＡC:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` 繧堤｢ｺ隱阪☆繧九→縲～data.json` 縺ｧ縺ｯ plugin 蜷梧｢ｱ `codex.cmd` 繧呈欠螳壹＠縺ｦ縺・ｋ縺ｮ縺ｫ縲∝ｮ溯｡梧凾縺ｯ `C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` 縺碁∈縺ｰ繧後※縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | `data/state/Obsidian Vault/.obsidian/plugins/claudian` 驟堺ｸ九・ Codex 騾｣謳ｺ縲８indows 迺ｰ蠅・〒 Codex provider 蛻晄悄蛹悶′螟ｱ謨励＠縲＾bsidian 縺九ｉ Codex 繧ｻ繝・す繝ｧ繝ｳ繧帝幕蟋九〒縺阪↑縺・・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺・global npm 驟堺ｸ九・ `codex.cmd` 繧堤峩謗･ spawn 縺励～spawn EINVAL` 縺ｫ縺ｪ縺｣縺溘・**Why2**: `codex_bridge.js` 縺ｸ蛻・ｊ譖ｿ縺医ｋ蜑肴ｮｵ縺ｮ CLI 隗｣豎ｺ縺ｧ縲∬ｨｭ螳壽ｸ医∩ `cliPath` 繧医ｊ PATH 閾ｪ蜍墓爾邏｢邨先棡縺悟━蜈医＆繧後※縺・◆縲・**Why3**: `data.json` 縺ｫ縺ｯ plugin 蜷梧｢ｱ `codex.cmd` 縺御ｿ晏ｭ倥＆繧後※縺・◆縺後～resolveCodexCliPath` 縺・Windows 縺ｧ `findCodexBinaryPath(customEnv.PATH)` 繧貞・縺ｫ霑斐＠縺ｦ縺・◆縲・**Why4**: 縺昴・邨先棡縲《ibling bridge 謗｢邏｢繧・global npm 驟堺ｸ九ｒ蝓ｺ貅悶↓縺励∝ｭ伜惠縺励↑縺・`codex_bridge.js` 繧定ｦ九◆蠕後↓蜊ｱ髯ｺ縺ｪ `.cmd` 逶ｴ spawn 縺ｸ谿狗蕗縺励◆縲・**Why5**: 縲後Θ繝ｼ繧ｶ繝ｼ縺梧・遉ｺ險ｭ螳壹＠縺・CLI path 繧呈怙蜆ｪ蜈医☆繧九阪→縺・≧蝓ｺ譛ｬ繝ｫ繝ｼ繝ｫ縺・resolver 縺ｫ蜿肴丐縺輔ｌ縺ｦ縺・↑縺九▲縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `resolveCodexCliPath` 縺ｮ蜆ｪ蜈磯�・ｽ阪ｒ菫ｮ豁｣縺励～cliPathsByHost` / `cliPath` 縺ｮ螳溷惠繝輔ぃ繧､繝ｫ繧・PATH 閾ｪ蜍戊ｧ｣豎ｺ繧医ｊ蜈医↓謗｡逕ｨ縺吶ｋ繧医≧螟画峩縲りｨｭ螳・path 繧剃ｽｿ縺｣縺溷�ｴ蜷医ｂ spawn 繝ｭ繧ｰ縺ｸ谿九☆繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `data.json` 縺ｮ `cliPath` 縺・plugin 蜷梧｢ｱ `codex.cmd` 繧呈欠縺励※縺・ｋ縺薙→繧堤｢ｺ隱阪ゆｿｮ豁｣蠕後た繝ｼ繧ｹ縺ｧ縺ｯ configured path 繧貞・縺ｫ霑斐☆縺薙→繧堤｢ｺ隱阪Ａnode --check "data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js"` 繧貞ｮ溯｡後＠縲∵ｧ区枚繧ｨ繝ｩ繝ｼ縺ｪ縺励ｒ遒ｺ隱阪・|
| **Lessons Learned** | Windows 縺ｮ wrapper 蝗樣∩縺�縺代〒縺ｪ縺上√後←縺ｮ wrapper 繧帝∈縺ｶ縺九阪・蜆ｪ蜈磯�・ｽ阪ｂ蜷後§縺上ｉ縺・㍾隕√り・蜍墓爾邏｢縺ｯ萓ｿ蛻ｩ縺ｧ繧ゅ∵・遉ｺ險ｭ螳壹ｒ荳頑嶌縺阪☆繧九→蜀咲匱隕∝屏縺ｫ縺ｪ繧翫ｄ縺吶＞縲ゅΟ繧ｰ縺ｫ縺ｯ縲御ｽ輔ｒ隕九▽縺代◆縺九阪□縺代〒縺ｪ縺上御ｽ輔ｒ謗｡逕ｨ縺励◆縺九阪ｒ谿九☆譁ｹ縺瑚ｿｽ霍｡縺励ｄ縺吶＞縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows resolver 縺ｮ蝗槫ｸｰ遒ｺ隱阪〒縺ｯ縲～configured path exists` / `PATH has different codex.cmd` 縺ｮ遶ｶ蜷医こ繝ｼ繧ｹ繧貞ｿ・★蜷ｫ繧√ｋ縲Ｔpawn 繝ｭ繧ｰ縺ｯ謗｡逕ｨ CLI path 繧呈ｮ九＠縲～.cmd` 逶ｴ spawn 縺瑚ｵｷ縺阪◆繧牙叉蠎ｧ縺ｫ逡ｰ蟶ｸ蛻､螳壹〒縺阪ｋ繧医≧縺ｫ縺吶ｋ縲・|

---

## INC-008: Claudian `Cannot read properties of undefined (reading 'id')`
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | `spawn EINVAL` 隗｣豸亥ｾ後，laudian 蛛ｴ縺ｧ `Cannot read properties of undefined (reading 'id')` 縺檎匱逕溘Ｃridge log 縺ｧ縺ｯ `thread/start` 縺悟ｱ翫＞縺ｦ縺・◆縺後∝ｯｾ蠢懊☆繧区ｧ矩�蛹門ｿ懃ｭ斐′荳崎ｶｳ縺励※縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縲・odex provider 蛻晄悄蛹門ｾ後↓ thread 菴懈・繧・turn 髢句ｧ九〒 UI 縺檎ｶ咏ｶ壻ｸ崎・縺ｫ縺ｪ繧九・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺・`result.thread.id` 縺ｾ縺溘・ `result.turn.id` 繧定ｪｭ縺ｿ蜿悶ｍ縺・→縺励※ `undefined.id` 縺ｫ縺ｪ縺｣縺溘・**Why2**: `codex_bridge.js` 縺ｯ `initialize` 莉･螟悶・螟ｧ蜊翫・繝｡繧ｽ繝・ラ縺ｫ蟇ｾ縺励※ `{}` 繧定ｿ斐☆縺�縺代〒縲，odex app-server 莠呈鋤縺ｮ蠢懃ｭ泌ｽ｢繧定ｿ斐＠縺ｦ縺・↑縺九▲縺溘・**Why3**: `thread/start` 縺ｮ謌ｻ繧雁､縺ｫ `thread.id` / `thread.path` 縺後↑縺上～turn/start` 縺ｫ繧・`turn.id` 縺後↑縺九▲縺溘・**Why4**: 騾夂衍邉ｻ繧よ悴螳溯｣・〒縲》urn 螳御ｺ・ｒ蠕・▽蛛ｴ縺梧悄蠕・☆繧・`turn/completed` 繧・agent message 繧､繝吶Φ繝医′譚･縺ｪ縺九▲縺溘・**Why5**: 襍ｷ蜍慕｢ｺ隱阪ｒ `initialize` 謌仙粥縺ｾ縺ｧ縺ｧ豁｢繧√※縺翫ｊ縲∝ｮ滄圀縺ｮ turn 髢句ｧ九ヵ繝ｭ繝ｼ縺ｾ縺ｧ縺ｮ莠呈鋤諤ｧ讀懆ｨｼ縺御ｸ崎ｶｳ縺励※縺・◆縲・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧呈怙蟆城剞縺ｮ Codex app-server 莠呈鋤 bridge 縺ｫ諡｡蠑ｵ縲Ａthread/start` / `thread/resume` / `turn/start` / `turn/interrupt` / `thread/compact/start` 縺ｮ蠢懃ｭ斐ｒ霑ｽ蜉�縺励～thread.id` / `thread.path` / `turn.id` 繧定ｿ斐☆繧医≧菫ｮ豁｣縲ゅ＆繧峨↓ `item/agentMessage/*` 縺ｨ `turn/completed` 騾夂衍繧帝√ｋ繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | `node --check` 縺ｧ bridge 縺ｮ讒区枚遒ｺ隱阪ｒ螳滓命縲ゅΟ繝ｼ繧ｫ繝ｫ蜀咲樟縺ｧ縺ｯ `initialize` 蠕後・ `thread/start` 縺・`thread.id` 縺ｨ `path` 繧定ｿ斐＠縲～turn/start` 縺・`turn.id` 縺ｨ `turn/completed` 騾夂衍繧定ｿ斐☆縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | transport 謗･邯壽・蜉溘→ app-server 莠呈鋤縺ｯ蛻･蝠城｡後・CP/JSON-RPC 縺ｮ縲後▽縺ｪ縺後ｋ縲阪□縺代〒縺ｯ荳榊香蛻・〒縲ゞI 縺瑚ｪｭ繧蜈ｷ菴鍋噪縺ｪ繝ｬ繧ｹ繝昴Φ繧ｹ shape 縺ｾ縺ｧ蜷医ｏ縺帙ｋ蠢・ｦ√′縺ゅｋ縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian bridge 縺ｮ蝗槫ｸｰ遒ｺ隱阪↓ `initialize -> thread/start -> turn/start` 縺ｮ荳騾｣縺ｮ繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ霑ｽ蜉�縺励～thread.id` / `turn.id` / `turn/completed` 縺ｮ蟄伜惠繧貞ｿ・�医メ繧ｧ繝・け縺ｫ縺吶ｋ縲・|

---

## INC-009: Claudian 騾∽ｿ｡辟｡蜿榊ｿ懶ｼ・iteLLM alias 荳肴紛蜷医→ Ollama 逶ｴ邨仙喧・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | 繝ｦ繝ｼ繧ｶ繝ｼ縺・`Hello` 繧帝∽ｿ｡縺励※繧・UI 縺檎┌蜿榊ｿ懊Ａclaudian-bridge.log` 縺ｧ縺ｯ `turn/start` 縺ｾ縺ｧ騾ｲ繧薙〒縺・◆縺後∬ｿ皮ｭ疲悽譁・′遨ｺ縺�縺｣縺溘・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縲る∽ｿ｡閾ｪ菴薙・騾壹ｋ縺後∬ｿ皮ｭ斐′陦ｨ遉ｺ縺輔ｌ縺壻ｼ夊ｩｱ蛻ｩ逕ｨ縺悟ｮ溯ｳｪ荳崎・縲・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Claudian 縺ｧ縺ｯ `turn/start` 縺悟ｮ御ｺ・＠縺ｦ縺・◆縺ｮ縺ｫ蠢懃ｭ疲悽譁・′霑斐ｉ縺ｪ縺九▲縺溘・**Why2**: bridge 縺・LiteLLM 縺ｮ 404 繧ｨ繝ｩ繝ｼ繧堤ｩｺ霑皮ｭ斐→縺励※謇ｱ縺｣縺ｦ縺・◆縲・**Why3**: LiteLLM proxy 縺ｮ alias `claude` / `codex` 縺ｯ蜀・Κ縺ｧ `openai/qwen3:8b` 繧貞盾辣ｧ縺礼ｶ壹￠縲＾llama 蛛ｴ縺ｧ `model not found` 縺ｫ縺ｪ縺｣縺ｦ縺・◆縲・**Why4**: config 菫ｮ豁｣縺�縺代〒縺ｯ proxy 蜀・Κ縺ｮ provider 隗｣驥亥ｷｮ繧貞ｮ悟・縺ｫ貎ｰ縺帙★縲，laudian 縺ｮ蟇ｾ隧ｱ邨瑚ｷｯ縺御ｸ榊ｮ牙ｮ壹↑縺ｾ縺ｾ縺�縺｣縺溘・**Why5**: Claudian 縺梧悽蠖薙↓蠢・ｦ√→縺励※縺・◆縺ｮ縺ｯ LiteLLM 蝗ｺ譛画ｩ溯・縺ｧ縺ｯ縺ｪ縺上√Ο繝ｼ繧ｫ繝ｫ Ollama 縺ｸ縺ｮ螳牙ｮ壹＠縺・chat completion 邨瑚ｷｯ縺�縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | `codex_bridge.js` 繧堤腸蠅・､画焚繝吶・繧ｹ縺ｫ縺励～OPENAI_BASE_URL` / `OPENAI_MODEL` / `OPENAI_API_KEY` 縺九ｉ逶ｴ謗･謗･邯壼・繧定ｧ｣豎ｺ縺吶ｋ繧医≧螟画峩縲・laudiian 險ｭ螳壹ｒ `http://127.0.0.1:11434/v1` + `qwen3:8b` 縺ｫ譖ｴ譁ｰ縺励´iteLLM 繧堤ｵ檎罰縺帙★ Ollama 縺ｸ逶ｴ邨舌☆繧狗ｵ瑚ｷｯ縺ｸ蛻・ｊ譖ｿ縺医◆縲ゆｽｵ縺帙※ `data/state/litellm_config.yaml` 縺ｮ繝ｭ繝ｼ繧ｫ繝ｫ繝｢繝・Ν螳夂ｾｩ繧・LiteLLM 莠呈鋤蠖｢蠑上∈譏ｯ豁｣縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/codex_bridge.js`, `data/state/Obsidian Vault/.claudian/claudian-settings.json`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/data.json`, `data/state/litellm_config.yaml`, `docs/INCIDENT_LOG.md` |
| **讀懆ｨｼ邨先棡** | bridge 蜊倅ｽ灘・迴ｾ縺ｧ `initialize -> thread/start -> turn/start` 繧貞ｮ溯｡後＠縲～Hello! How can I assist you today?` 縺・`item/agentMessage/delta` 縺ｨ `completed` 縺ｧ霑斐ｋ縺薙→繧堤｢ｺ隱阪・|
| **Lessons Learned** | proxy 繧帝俣縺ｫ謖溘・險ｭ險医・譟碑ｻ溘□縺後∝次蝗�蛻・ｊ蛻・￠荳ｭ縺ｯ萓晏ｭ倡せ縺悟｢励∴繧九ゅΟ繝ｼ繧ｫ繝ｫ蜊倅ｸ霍ｯ邱壹〒蜊∝・縺ｪ讖溯・縺ｯ縲√∪縺壽怙遏ｭ邨瑚ｷｯ縺ｧ螳牙ｮ夂ｨｼ蜒阪＆縺帙※縺九ｉ謚ｽ雎｡蛹悶ｒ雜ｳ縺呎婿縺悟ｮ牙・縲・|
| **蜀咲匱髦ｲ豁｢遲・* | Claudian 縺ｮ逍朱夂｢ｺ隱阪〒縺ｯ縲ゞI 陦ｨ遉ｺ縺�縺代〒縺ｪ縺・bridge 蜊倅ｽ薙・ `Hello` 繧ｹ繝｢繝ｼ繧ｯ繝・せ繝医ｒ邯ｭ謖√☆繧九・iteLLM alias 繧剃ｽｿ縺・�ｴ蜷医ｂ縲√Ο繝ｼ繧ｫ繝ｫ Ollama 逶ｴ邨舌・莉｣譖ｿ邨瑚ｷｯ繧呈ｮ九＠縺ｦ縺翫￥縲・|

---

## INC-006: Claudian `spawn EINVAL` 蜀咲匱・・lobal `codex.cmd` 縺ｨ bundled bridge 縺ｮ蛻・屬・・| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-11 |
| **逋ｺ隕区婿豕・* | Claudian 襍ｷ蜍墓凾縺ｫ `spawn EINVAL`縲ＡC:\\Users\\yasu\\.claude\\debug\\claudian-spawn.log` 繧堤｢ｺ隱阪☆繧九→縲～C:\\Users\\yasu\\AppData\\Roaming\\npm\\codex.cmd` 繧堤峩謗･ spawn 縺励※螟ｱ謨励＠縺ｦ縺・◆縲・|
| **蠖ｱ髻ｿ遽・峇** | Obsidian Vault 縺ｮ Claudian 繝励Λ繧ｰ繧､繝ｳ縺九ｉ Codex app-server 繧定ｵｷ蜍輔〒縺阪★縲∝・譛溷喧縺ｫ螟ｱ謨励・|
| **譬ｹ譛ｬ蜴溷屏 (5 Why)** | **Why1**: Windows 縺ｧ `codex.cmd` 繧・`spawn(..., { shell: false })` 縺励～spawn EINVAL` 縺悟・逋ｺ縺励◆縲・**Why2**: `.cmd` 繧堤峩謗･襍ｷ蜍輔＠縺ｪ縺・◆繧√・蝗樣∩縺ｯ蜈･縺｣縺ｦ縺・◆縺後～codex_bridge.js` 縺ｮ謗｢邏｢縺・global npm 驟堺ｸ九・ sibling 繧貞燕謠舌↓縺励※縺・◆縲・**Why3**: 螳滄圀縺ｮ迺ｰ蠅・〒縺ｯ `codex.cmd` 縺ｯ `C:\\Users\\yasu\\AppData\\Roaming\\npm` 縺ｫ縺ゅｊ縲～codex_bridge.js` 縺ｯ `data/state/Obsidian Vault/.obsidian/plugins/claudian/` 縺ｫ蜷梧｢ｱ縺輔ｌ縺ｦ縺・※蜷後§蝣ｴ謇縺ｫ辟｡縺九▲縺溘・**Why4**: bridge 縺瑚ｦ九▽縺九ｉ縺ｪ縺・◆繧・`node + codex_bridge.js` 縺ｮ逶ｴ襍ｷ蜍輔∈蛻・ｊ譖ｿ繧上ｉ縺壹∵里蟄倥・蜊ｱ髯ｺ縺ｪ `.cmd` spawn 邨瑚ｷｯ縺ｫ谿狗蕗縺励◆縲・**Why5**: global CLI 縺ｨ plugin bundled asset 縺悟・髮｢縺輔ｌ縺滄・鄂ｮ繧呈Φ螳壹＠縺滓怙蠕後・繝輔か繝ｼ繝ｫ繝舌ャ繧ｯ縺梧悴螳溯｣・□縺｣縺溘・|
| **菫ｮ豁｣蜀・ｮｹ** | Windows wrapper 讀懷・譎ゅ・ bridge 隗｣豎ｺ鬆・ｒ `preferred PATH bridge` -> `codex.cmd sibling bridge` -> `plugin bundled codex_bridge.js` 縺ｫ螟画峩縲Ｔpawn 螟ｱ謨玲凾縺ｮ retry 邨瑚ｷｯ繧ょ酔縺倬�・ｺ上↓邨ｱ荳縺励“lobal npm 驟堺ｸ九↓ bridge 縺檎┌縺上※繧・bundled bridge 繧・`node.exe` 縺ｧ襍ｷ蜍輔〒縺阪ｋ繧医≧縺ｫ縺励◆縲・|
| **菫ｮ豁｣繝輔ぃ繧､繝ｫ** | `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:60983`, `data/state/Obsidian Vault/.obsidian/plugins/claudian/main.js:61007` |
| **讀懆ｨｼ邨先棡** | 繧ｽ繝ｼ繧ｹ遒ｺ隱阪〒 bridge 隗｣豎ｺ鬆・↓ bundled fallback 縺瑚ｿｽ蜉�縺輔ｌ縺溘％縺ｨ繧堤｢ｺ隱阪Ａmain.js` 縺ｯ `node` 縺ｧ讒区枚繝√ぉ繝・け貂医∩縲Ａcodex_bridge.js` 蛛ｴ縺ｮ initialize 蠢懃ｭ斐・ `platformOs=windows`, `platformFamily=windows` 繧定ｿ斐☆縺薙→繧貞・遒ｺ隱阪ゅΟ繧ｰ荳翫・螟ｱ謨礼ｵ瑚ｷｯ (`codex.cmd` 逶ｴ spawn) 縺ｯ莉雁屓縺ｮ蛻・ｲ舌〒蝗樣∩縺輔ｌ繧九・|
| **Lessons Learned** | Windows 縺ｮ `.cmd` 蝗樣∩縺ｯ縲恵ridge 縺瑚ｦ九▽縺九ｋ蜑肴署縲阪□縺代〒縺ｯ荳榊香蛻・・LI 縺ｨ bridge 縺悟挨驟咲ｽｮ縺ｫ縺ｪ繧・npm/plugin 豺ｷ蝨ｨ迺ｰ蠅・ｒ蜑肴署縺ｫ縲∵怙蠕後↓ bundled asset 縺ｸ謌ｻ繧後ｋ險ｭ險医′蠢・ｦ√・|
| **蜀咲匱髦ｲ豁｢遲・* | Windows 襍ｷ蜍輔さ繝ｼ繝峨〒縺ｯ wrapper 螳滉ｽ薙→ bridge 螳滉ｽ薙・驟咲ｽｮ蛻・屬繧貞ｸｸ縺ｫ諠ｳ螳壹☆繧九Ｃridge 隗｣豎ｺ鬆・ｒ繝ｭ繧ｰ縺ｸ谿九＠縲～.cmd` 繧堤峩謗･ spawn 縺吶ｋ邨瑚ｷｯ繧貞屓蟶ｰ遒ｺ隱榊ｯｾ雎｡縺ｫ縺吶ｋ縲・|
1. Windows 縺ｧ縺ｯ縲訓ATH 縺ｫ縺ゅｋ縲阪□縺代〒縺ｯ荳榊香蛻・〒縲～spawn` 縺ｮ螳溯｡悟ｽ｢蠑丞ｷｮ縺ｾ縺ｧ隕九ｋ蠢・ｦ√′縺ゅｋ縲・2. `initialize` 縺ｯ繧ｿ繧､繝�繧｢繧ｦ繝医□縺代〒縺ｪ縺上∝ｿ懃ｭ斐せ繧ｭ繝ｼ繝樔ｸ榊ｙ縺ｧ繧ゆｺ梧ｮｵ逶ｮ縺ｮ髫懷ｮｳ繧定ｵｷ縺薙☆縺溘ａ縲∬ｵｷ蜍輔→蠢懃ｭ斐・荳｡譁ｹ繧貞酔譎ゅ↓讀懆ｨｼ縺吶ｋ縲・3. 譌｢蟄倥Λ繝・ヱ繝ｼ (`codex.cmd`) 繧呈ｴｻ縺九☆諡｡蠑ｵ縺ｮ譁ｹ縺後∝挨邉ｻ邨ｱ縺ｮ襍ｷ蜍慕ｵ瑚ｷｯ繧貞｢励ｄ縺吶ｈ繧雁ｮ牙・縺ｫ蟆主・縺ｧ縺阪ｋ縲・## INC-020: Gmail priority backfill container path was unstable on the mini PC
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | A manual priority backfill run for `2026-01-01` onward failed first with `returncode 137` even after reducing the month scope, while host-side Gmail incremental sync for the same query completed successfully. |
| **Impact** | Historical Gmail ingestion was not progressing beyond recent incremental sync, so older mail from January 2026 onward was not being backfilled continuously. |
| **Root Cause (5 Why)** | **Why1**: `run_priority_gmail_backfill.py` executed Gmail indexing inside the gateway container via `docker exec`. **Why2**: On this mini PC, that container backfill path was unstable and the process was killed with exit `137` before completing a month-sized chunk. **Why3**: The daemon had been restarted with `--skip-full-backfill`, so the unstable full-backfill path stayed bypassed and historical ingestion never resumed. **Why4**: The original backfill implementation used a heavier execution path than the already-stable host-side temp-DB promotion flow used by `host_gmail_incremental_sync.py`. **Why5**: The system lacked a bounded, host-side historical backfill path that reused the proven safe SQLite promotion pattern. |
| **Fix** | Switched `data/workspace/run_priority_gmail_backfill.py` from container execution to the host-side temp-DB promotion pattern, added bounded CLI args (`--start-date`, `--end-date`, `--max-messages-per-chunk`), reduced the default monthly backfill chunk to `500`, and removed `--skip-full-backfill` from `data/workspace/email_continuous_watchdog.py` so restarted daemons can resume historical backfill. |
| **Files** | `data/workspace/run_priority_gmail_backfill.py`, `data/workspace/email_continuous_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python data/workspace/run_priority_gmail_backfill.py --start-date 2026-01-01 --end-date 2026-01-31 --max-messages-per-chunk 500` completed with `returncode 0`; January chunk result was `candidates=500`, `indexed=160`, `skipped=340`, `errors=0`. Direct host sync for the same query also succeeded earlier with `indexed=411`, `skipped=89`, `errors=0`. |
| **Lessons Learned** | For long-running Gmail backfills on this mini PC, reuse the host-side temp SQLite promotion path that already proved stable. Prefer bounded month or date windows before re-enabling unattended historical catch-up. |
| **Prevention** | Keep full backfill chunk sizes bounded, preserve lock-based serialization with `EmailDbLock`, and validate backfill changes with a single-month run before allowing unattended daemon recovery to trigger them. |
## INC-021: Blacklisted Gmail messages were still stored in `emails`
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | Review of the Gmail ingest flow showed that blacklist and newsletter filters only affected task extraction and did not prevent blacklisted messages from being written into `emails` and SQLite FTS. |
| **Impact** | Newsletter and blocked notification mail still consumed SQLite rows, FTS space, and downstream processing time even when they were excluded from `tasks`. |
| **Root Cause (5 Why)** | **Why1**: `index_gmail()` fetched and parsed Gmail messages, then always called `upsert_record()`. **Why2**: The sender filter file was only consulted inside `looks_like_task()`. **Why3**: `looks_like_task()` runs after the email row is already inserted, during task extraction. **Why4**: The system optimized task quality but not storage hygiene. **Why5**: There was no pre-storage Gmail filter step that reused the existing blacklist, newsletter, and whitelist logic. |
| **Fix** | Added a Gmail pre-storage filter in `data/workspace/email_search_index.py` so blacklisted and newsletter messages are skipped before insertion into `emails`, and exposed `skipped_by_filter` in the Gmail ingest summary. Added `email ingest watchdog restart` to `data/workspace/email_rag_sender_filters.json` so watchdog restart notifications are dropped before DB insertion. |
| **Files** | `data/workspace/email_search_index.py`, `data/workspace/email_rag_sender_filters.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Static validation via `python -m py_compile data/workspace/email_search_index.py`. Runtime Gmail summaries now include `skipped_by_filter`, enabling direct observation of pre-storage blacklist filtering in future sync cycles. |
| **Lessons Learned** | On this mini PC, blacklist and newsletter rules should be applied as early as possible to reduce DB growth and FTS churn, not only at task extraction time. |
| **Prevention** | Keep sender and content filters shared between task classification and pre-storage gating, and include skip counters in operational status so filter effectiveness is visible without inspecting the DB manually. |
## INC-022: Continuous patrol missed local API outages and user-intent drift
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that local APIs such as `email_blacklist_hub` often fell unnoticed, and earlier Gmail ingest drift had shown that patrols were checking heartbeat files without fully validating whether user-requested behavior was still being achieved. |
| **Impact** | Local tools could be down while dashboards still looked broadly healthy, and user-requested behaviors such as January 2026 onward Gmail backfill or blacklist effectiveness observability could drift without prompt correction. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` focused on watchdog freshness and status JSONs, but not on direct local API reachability. **Why2**: `email_blacklist_hub` had a start script, yet neither `continuous_system_improvement.py` nor `auto_repair_allowed.py` monitored or restarted it. **Why3**: Patrol logic did not audit contract-level expectations such as 窶廨mail daemon must not run with `--skip-full-backfill`窶・or 窶彷ilter telemetry must remain visible.窶・**Why4**: `data/workspace` resolves through the `E:` workspace path on this machine, so repo-root discovery based only on `__file__.resolve()` could point start actions at non-existent `E:\scripts\...` paths. **Why5**: The patrol layer had grown around component heartbeat checks, but not around user-intent contracts and mixed-drive path reality on this mini PC. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` to probe `email_blacklist_hub` API endpoints directly, verify Gmail backfill drift and filter telemetry, and expose those checks in summary/status output. Extended `data/workspace/auto_repair_allowed.py` to restart `email_blacklist_hub` when stale or missing. Added repo-root fallback resolution in both scripts so start actions use the actual repo `scripts/` directory even when `data/workspace` resolves through `E:`. Restarted `email_blacklist_hub` and re-ran the patrol until summary showed the API reachable and `skipped_by_filter` visible. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py` passed. `http://127.0.0.1:8791/api/email-blacklist/config` returned live JSON again. `python data/workspace/host_gmail_incremental_sync.py --gmail-max-messages 5 --gmail-fallback-days 1` completed with `skipped_by_filter=2`. `data/workspace/continuous_system_improvement_status.json` at `2026-04-12 07:12:58 JST` showed `Email blacklist hub API is reachable`, `Historical Gmail backfill still targets January 2026 onward`, and `Gmail filter telemetry is visible in ingest summaries`. |
| **Lessons Learned** | Heartbeat files are necessary but not sufficient. On this environment, patrols must verify API endpoints and a small set of explicit user-intent contracts, not just whether a process exists. |
| **Prevention** | Keep critical local APIs in the patrol catalog, keep at least one observable metric for each user-facing optimization (such as `skipped_by_filter`), and resolve repo-root paths defensively whenever workspace files may be mirrored onto another drive. |
## INC-023: Email Search API was not supervised and degraded the portal experience
| Field | Detail |
|---|---|
| **Date** | 2026-04-12 |
| **Detection** | User reported that `http://localhost:8088/apps/email_search/` looked down during a broader mini PC slowdown check. Investigation showed the portal page itself was reachable, but its backend API on `127.0.0.1:8792` was not running. |
| **Impact** | The Email Search UI loaded from the portal but could not return stats or search results, so it appeared broken. The system also lacked automatic restart for that API, making the failure recur silently after process loss. |
| **Root Cause (5 Why)** | **Why1**: `apps/email_search/index.html` depends on `email_search_api.py` at `127.0.0.1:8792`. **Why2**: The API had no dedicated Windows start script or watchdog integration. **Why3**: `continuous_system_improvement.py` and `auto_repair_allowed.py` originally monitored other local APIs but not Email Search. **Why4**: The mini PC slowdown symptoms prompted a check of background activity, revealing that watchdog cadence was moderate while the heavier pressure came from `Memory Compression`, `vmmemWSL`, Docker/WSL workloads, and VS Code processes. **Why5**: Service supervision coverage had focused on Gmail, Docker UI, and Blacklist Hub first, leaving Email Search outside the local API patrol catalog. |
| **Fix** | Added `scripts/start_email_search_api.ps1` to start and health-check `data/workspace/email_search_api.py`. Extended `data/workspace/continuous_system_improvement.py` to probe `http://127.0.0.1:8792/api/stats` and surface Email Search health in patrol summaries. Extended `data/workspace/auto_repair_allowed.py` to restart Email Search API when the process is missing or the API probe fails. Started the API and confirmed the portal backend was serving again. |
| **Files** | `scripts/start_email_search_api.ps1`, `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/email_search_api.py` passed. `http://127.0.0.1:8792/api/stats` returned JSON with `total_emails=23212` and `total_tasks=9172`. `data/workspace/continuous_system_improvement_status.json` showed `Email search API is reachable`. |
| **Lessons Learned** | For portal apps backed by local host APIs, supervising only the static UI path is not enough. The host API must be in the patrol catalog with a concrete health probe. |
| **Prevention** | Keep each portal app窶冱 host API paired with a start script and patrol probe, and treat UI reachability and backend reachability as separate checks. |

## INC-024: `minipc_optimizer` 縺・mini PC 縺ｮ螳溽腸蠅・〒 Lite 蛛懈ｭ｢縺ｫ螟ｱ謨励＠縺ｦ縺・◆

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 07:32 JST |
| **Detection** | User approved stopping safe background services to lighten the mini PC. `python data/workspace/minipc_optimizer.py apply-lite` first failed with `open E:\\clawstack_v2\\docker-compose.yml` and then `no such service: infinity`, even though candidate containers were visibly running. |
| **Impact** | The lightweight-mode harness could report heavy candidates but could not actually stop them on this machine, so memory-heavy optional services stayed online and the user-facing slowdown would persist longer than necessary. |
| **Root Cause (5 Why)** | **Why1**: `minipc_optimizer.py` derived `ROOT` from `Path(__file__).resolve()`, which can resolve through the `E:` workspace mirror on this mini PC. **Why2**: That made the compose path point to a non-existent `E:\\clawstack_v2\\docker-compose.yml` instead of the real repo on `D:`. **Why3**: After fixing the root, the harness still used `docker compose stop <service>`, assuming guessed service names exactly matched compose service ids. **Why4**: At least one running container (`clawstack-unified-infinity-1`) did not map cleanly enough for compose-stop by guessed service name, causing `no such service`. **Why5**: The optimizer had been designed around compose topology, but this mini PC now has mixed-drive path reality and practical container-name truth that are more reliable for emergency lightweight actions. |
| **Fix** | Updated `data/workspace/minipc_optimizer.py` to resolve the repo root by searching for the actual repo containing `clawstack_v2/docker-compose.yml` and `data/workspace`, falling back only if needed. Reworked Lite stopping to target currently running container names via `docker stop` instead of `docker compose stop`, so optional services can be stopped even when compose service ids drift from guessed names. |
| **Files** | `data/workspace/minipc_optimizer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. `python data/workspace/minipc_optimizer.py apply-lite` returned `changed=true` and stopped 21 optional containers including `infinity`, `clickhouse`, `paperless`, `docling`, `metabase`, `stirling_pdf`, `portainer`, and `uptime-kuma`. A follow-up `python data/workspace/minipc_optimizer.py status` reported `heavyRunningCandidates=[]`, and `docker ps` no longer listed those optional services as running. |
| **Lessons Learned** | On this machine, host-side harnesses should prefer runtime-truth checks over inferred compose metadata when doing safe operational reductions. Mixed-drive path resolution and partial compose drift are normal enough that emergency controls should degrade gracefully. |
| **Prevention** | Reuse repo-root fallback logic in every host harness that launches or stops services, and prefer container-name based safe-stop flows for Lite mode unless a strong reason exists to require compose service ids. |

## INC-025: Gateway memory bloat was caused by duplicate `ingest_watchdog.py` processes and the harness lacked a full live inventory

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 21:12 JST |
| **Detection** | During mini PC slowdown analysis, `docker stats` showed `clawstack-unified-clawdbot-gateway-1` consuming about `4.8 GiB` RSS. Inspecting processes inside the container revealed hundreds of duplicate `python3 /home/node/clawd/ingest_watchdog.py` instances. At the same time, the AI Engineering Harness page did not yet expose a complete host API and major Docker service inventory, which made the drift harder to see quickly. |
| **Impact** | The gateway container consumed several GiB of memory, increasing overall pressure on `vmmemWSL` and host memory compression, and the existing dashboard did not clearly show which APIs or services were up, down, or intentionally stopped. |
| **Root Cause (5 Why)** | **Why1**: `paperless_rag_watchdog.py` only treated 窶從o ingest process窶・as unhealthy and did not detect duplicate `ingest_watchdog.py` processes. **Why2**: Its restart flow mainly relied on a single pidfile-oriented path, so stale or multiplied watchdog processes could survive while new ones were launched. **Why3**: Repeated repair attempts over time allowed duplicate `ingest_watchdog.py` processes to accumulate inside the gateway container. **Why4**: `continuous_system_improvement.py` summarized many patrol signals but did not yet collect a single inventory of host APIs, key Docker services, and gateway ingest watchdog counts. **Why5**: Operational observability had evolved around individual status files rather than a compact live inventory tied to the user-facing Harness card. |
| **Fix** | Updated `data/workspace/paperless_rag_watchdog.py` to count running `ingest_watchdog.py` processes, mark duplicate counts as unhealthy, and restart by killing all matching ingest watchdog processes before relaunching a single one. Updated `data/workspace/continuous_system_improvement.py` to collect `hostApiInventory`, `serviceInventory`, and `gatewayIngestWatchdogCount`, and to schedule `run_paperless_rag_watchdog` when duplicate gateway ingest processes are detected. Expanded `data/workspace/apps/ai_engineering_harness_status/index.html` to show the gateway ingest watchdog count, a full Host APIs panel, and a Major Docker Services panel. Restarted both the Windows `paperless_rag_watchdog.py` and `continuous_system_improvement.py` background patrols so the new logic is active. Manually collapsed duplicate gateway ingest watchdog processes back to a single running process. |
| **Files** | `data/workspace/paperless_rag_watchdog.py`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/paperless_rag_watchdog.py data/workspace/continuous_system_improvement.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'ps -ef | grep ingest_watchdog.py | grep -v grep | wc -l'` returned `1` after cleanup. `docker stats` dropped gateway memory from about `4.8 GiB` to about `580 MiB`. `python data/workspace/continuous_system_improvement.py --once` produced `continuous_system_improvement_status.json` with `context.hostApiInventory`, `context.serviceInventory`, and `context.gatewayIngestWatchdogCount`, and the status summary now reports `Gateway ingest watchdog process count is healthy` with `processes=1`. |
| **Lessons Learned** | For long-running gateway sidecars, 窶徘rocess exists窶・is not a sufficient health test. The harness must detect multiplicity, not just absence. Operational cards are much more useful when they display both health summaries and the current live inventory that explains those summaries. |
| **Prevention** | Keep duplicate-process counts as first-class patrol signals, restart Windows patrol daemons after harness code changes, and expose the up/down state of major APIs and services on the Harness page so silent drift is visible before memory bloat becomes user-visible. |

## INC-026: Paperless ingest stopped because Paperless was offline and the gateway used a stale direct token path

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:02 JST |
| **Detection** | User requested Paperless ingest recovery after investigation showed repeated `401 Unauthorized` in `/home/node/clawd/ingest_watchdog.log`, stale `paperless_rag_watchdog` warnings, and `clawstack-unified-paperless-1` stopped with `Exited (137)`. |
| **Impact** | Paperless document ingestion into `universal_knowledge` was no longer progressing, watchdogs kept trying to revive the ingest loop, and the mini PC carried extra background churn without actually indexing new Paperless documents. |
| **Root Cause (5 Why)** | **Why1**: The Paperless container itself was not running, so the ingest path was intermittently unreachable. **Why2**: Even when Paperless was available again, `data/workspace/ingest_watchdog.py` still used a hard-coded legacy API token and direct `http://paperless:8000` target. **Why3**: That legacy token was no longer valid for the current Paperless API, causing repeated `401 Unauthorized`. **Why4**: On this mini PC, the gateway could successfully authenticate through `http://host.docker.internal:8000`, while the direct container alias path returned `Invalid token`, so the old fixed endpoint was no longer the reliable route. **Why5**: Paperless ingest credentials and route selection had been embedded in scripts instead of being kept in one host-editable operational config. |
| **Fix** | Restarted `clawstack-unified-paperless-1`, verified the Paperless API on `127.0.0.1:8000`, generated a fresh API token via `/api/token/`, and moved Paperless ingest settings into `data/workspace/paperless_ingest_config.json`. Updated `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, and `data/workspace/audit_paperless_ingest_alignment.py` to consume that config instead of a hard-coded token. Switched the gateway ingest route to `http://host.docker.internal:8000`, updated `paperless_rag_watchdog.py` to count only real Python ingest processes, and reran the Paperless audit using host-side fallbacks. |
| **Files** | `data/workspace/paperless_ingest_config.json`, `data/workspace/ingest_watchdog.py`, `data/workspace/requeue_recent_paperless_docs.py`, `data/workspace/audit_paperless_ingest_alignment.py`, `data/workspace/paperless_rag_watchdog.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `docker start clawstack-unified-paperless-1` brought Paperless back to `Up ... (healthy)`. `POST http://127.0.0.1:8000/api/token/` with `admin/admin` returned a fresh token. From inside the gateway, `requests.get('http://host.docker.internal:8000/api/documents/?page_size=1', headers={'Authorization': 'Token ...'})` returned `200`, and importing `ingest_watchdog.py` inside the gateway showed `PAPERLESS_URL=http://host.docker.internal:8000`. `paperless_rag_watchdog_status.json` then reported `stage=healthy`, `ingestAlive=true`, `ingestProcessCount=1`. `python data/workspace/audit_paperless_ingest_alignment.py --recent-limit 10` completed with `status=healthy` and no missing recent documents. |
| **Lessons Learned** | For Paperless on this mini PC, the stable path is not just 窶彡ontainer-to-container by service name窶・ Authentication and reachability can diverge between the direct container alias and the host-exposed route, so the operational config needs an explicit chosen endpoint. |
| **Prevention** | Keep Paperless ingest token and base URL in a dedicated workspace config file, avoid hard-coded long-lived tokens in scripts, and validate both 窶廣PI auth works窶・and 窶彗udit sees recent docs窶・after any Paperless restart or Lite-mode service reduction. |

## INC-027: Patrols needed to treat `401/403` as outage-equivalent and semi-automate Paperless token renewal

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:14 JST |
| **Detection** | User requested that `401/403` responses be treated as patrol failures rather than mere 窶廣PI responded窶・signals, and asked for Paperless-style token reissue to be semi-automated. Existing API inventory cards could show up/down, but auth drift still required manual digging. |
| **Impact** | An API could be effectively unusable while still appearing reachable, and token-backed integrations like Paperless ingest could silently degrade until a human manually reissued credentials and updated config. |
| **Root Cause (5 Why)** | **Why1**: `continuous_system_improvement.py` treated successful TCP/HTTP response handling and authentication validity as the same concept. **Why2**: `401/403` were not being elevated into explicit auth-failure patrol weaknesses. **Why3**: Paperless ingest token refresh existed only as a manual recovery pattern from the previous incident, not as a reusable harness action. **Why4**: `auto_repair_allowed.py` did not have a direct rule for 窶彗uth is stale but service is otherwise reachable窶・ **Why5**: Operational hardening had focused first on process recovery and freshness, leaving auth-contract drift as a separate manual concern. |
| **Fix** | Extended `data/workspace/continuous_system_improvement.py` so HTTP probes classify `401/403` as `authFailure`, expose that on `hostApiInventory`, and raise explicit weaknesses such as `paperless_ingest_auth`. Added `refresh_paperless_ingest_token.py` to mint a fresh Paperless API token from the running Paperless container credentials and update `paperless_ingest_config.json`. Integrated that refresh action into both `continuous_system_improvement.py` and `auto_repair_allowed.py`. Updated `data/workspace/apps/ai_engineering_harness_status/index.html` so host API rows show `AUTH 401/403` instead of looking like generic connectivity failures. Also aligned gateway ingest-process counting in `continuous_system_improvement.py` with `pgrep` so the dashboard does not overcount wrapper shells. |
| **Files** | `data/workspace/continuous_system_improvement.py`, `data/workspace/auto_repair_allowed.py`, `data/workspace/refresh_paperless_ingest_token.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/continuous_system_improvement.py data/workspace/auto_repair_allowed.py data/workspace/refresh_paperless_ingest_token.py` passed. `python data/workspace/refresh_paperless_ingest_token.py` completed and wrote `paperless_token_refresh_status.json`. A fresh `continuous_system_improvement.py --once` run showed `Paperless ingest API authentication is valid` and included `paperless_ingest_auth` in `hostApiInventory`. `auto_repair_allowed.py` completed with `paperless_token` rule evaluating `healthy`, confirming the new semi-automatic path is wired in. |
| **Lessons Learned** | For operations patrols, `reachable` is not enough. Authentication validity is part of availability when a user-facing workflow depends on it. |
| **Prevention** | Keep auth-backed probes separate from plain liveness checks, surface them on the portal card, and maintain one dedicated token-refresh harness per long-lived local integration that depends on renewable credentials. |

## INC-028: Auto-repair had stale target assumptions for scheduled reports and missed dead Paperless watchdogs

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 22:49 JST |
| **Detection** | A weakness review of the current mini PC patrol stack showed two avoidable blind spots: `auto_repair_allowed.py` still tried to run scheduled report sync through a non-existent `clawstack-unified-learning_engine-1` container, and it could mark `paperless_rag` healthy even when `paperless_rag_watchdog.py` itself was no longer running. |
| **Impact** | Scheduled-report repair attempts produced misleading `No such container` failures instead of the real underlying cause, and Paperless ingest supervision could silently degrade if the Windows watchdog died while the ingest heartbeat remained fresh for a while. |
| **Root Cause (5 Why)** | **Why1**: `auto_repair_allowed.py` had an old hard-coded `docker exec clawstack-unified-learning_engine-1 ...` command. **Why2**: The environment had moved to `wsl_native` and no longer guaranteed that container name or a container-based execution path for this task. **Why3**: The same script evaluated `paperless_rag` only from JSON freshness, not from the Windows watchdog process itself. **Why4**: That allowed a dead watchdog to be masked by still-fresh ingest heartbeat files. **Why5**: Repair logic had evolved around status files first, and some operational assumptions were not updated when the runtime topology changed. |
| **Fix** | Updated `data/workspace/auto_repair_allowed.py` so scheduled-report repair now executes the host-side `scheduled_report_search.py` directly instead of targeting the removed container name. Added an explicit process-presence check for `paperless_rag_watchdog.py` before declaring Paperless RAG healthy, so auto-repair can restart the watchdog when the Windows process is missing. |
| **Files** | `data/workspace/auto_repair_allowed.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/auto_repair_allowed.py` passed. A fresh `python data/workspace/auto_repair_allowed.py` run restarted `paperless_rag_watchdog.py` successfully and showed `scheduled_reports_sync` invoking the host-side script path instead of the removed container. The scheduled report sync still failed, but now with the true cause: upstream `n8n` API timeout, not a fake container-name mismatch. |
| **Lessons Learned** | Repair harnesses should point at the smallest stable execution surface available on the host, and liveness of a watchdog process must be checked separately from freshness of the child service it supervises. |
| **Prevention** | Prefer host-side script entry points over fragile container-name assumptions for maintenance jobs, and always combine `status freshness` with `process existence` when supervising watchdog-style services. |

## INC-029: Scheduled-report sync used the wrong n8n auth path and gateway ingest had multiple owners

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-12 23:25 JST |
| **Detection** | User requested root-cause investigation for `n8n timeout` and `gateway duplicate ingest`. The scheduled report repair path had stopped failing with a fake container-name error, but still timed out while probing `host.docker.internal:5679`. Separately, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "ps -o pid,ppid,lstart,cmd -C python3 | grep ingest_watchdog.py"` showed a new `ingest_watchdog.py` process every ~5 minutes with `PPID 1`, confirming duplicate ownership. |
| **Impact** | Scheduled report sync could not read workflow executions reliably, so `scheduled_reports` stayed stale. Gateway memory and CPU were wasted by many duplicate `ingest_watchdog.py` processes, worsening mini PC responsiveness and risking repeated Paperless ingest churn. |
| **Root Cause (5 Why)** | **Why1**: `scheduled_report_search.py` only tried n8n public API-key routes and kept `host.docker.internal` in the host-side candidate set. **Why2**: On this machine, host access to `127.0.0.1:5679/rest/login` succeeds, but API-key access to `/api/v1` and `/rest` returns `401`, and `host.docker.internal:5679` can time out from the Windows host. **Why3**: The script had no login-cookie fallback even though other repo utilities already used `n8n-auth` cookies successfully. **Why4**: Gateway ingest was started by more than one control plane: container boot plus the active n8n workflow `Ingest Watchdog Supervisor`. **Why5**: Lifecycle ownership for `ingest_watchdog.py` was never reduced to one authoritative watchdog, so overlapping restart paths kept multiplying the process. |
| **Fix** | Updated `data/workspace/scheduled_report_search.py` to load `N8N_API_KEY` from env/`.env`, prefer localhost routes, and fall back to `POST /rest/login` with cached `n8n-auth` cookies when API-key auth returns `401/403`. Applied the same login fallback pattern to `data/workspace/create_scheduled_report_sync_workflow.py`. Updated `data/workspace/recreate_workflows.py` so the `Ingest Watchdog Supervisor` workflow is preserved but explicitly deactivated, with future re-runs keeping it inactive instead of re-enabling duplicate restarts. Clarified `data/state/entrypoint.sh` so host-side `paperless_rag_watchdog` is the intended restart owner. Then deactivated n8n workflow `VBQMPFGWSVtwy2Vy`, killed all real `ingest_watchdog.py` processes in the live gateway container, and relaunched a single instance. |
| **Files** | `data/workspace/scheduled_report_search.py`, `data/workspace/create_scheduled_report_sync_workflow.py`, `data/workspace/recreate_workflows.py`, `data/state/entrypoint.sh`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/scheduled_report_search.py data/workspace/create_scheduled_report_sync_workflow.py data/workspace/recreate_workflows.py` passed. Direct host login to `http://127.0.0.1:5679/rest/login` returned `200` and an `n8n-auth` cookie. `python data/workspace/scheduled_report_search.py sync --limit-executions 20` now completes successfully instead of timing out. `python data/workspace/recreate_workflows.py` reported `Ingest Watchdog Supervisor ... active=False`. After cleanup, `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "sleep 330; pgrep -fc '^python3 /home/node/clawd/ingest_watchdog.py$'"` returned `1`, proving the 5-minute duplicate loop stopped. |
| **Lessons Learned** | For n8n on this mini PC, host-maintenance scripts must prefer the same login-cookie path that already works for other local admin tools; API-key-only assumptions are brittle. For long-running sidecars, one process owner is a design rule, not just an implementation detail. |
| **Prevention** | Keep host-side n8n maintenance utilities on localhost-first login fallback, and keep only one authoritative restart path for gateway sidecars. When a workflow is retained only for historical reference, explicitly keep it deactivated in the workflow recreation script so future maintenance runs do not resurrect duplicate process loops. |

## INC-030: Outbound notifications relied on policy text more than code-level allowlist enforcement

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 06:12 JST |
| **Detection** | User requested a hard-force guard so no information could ever be sent outside their own Telegram and `y.suzuki.hk@gmail.com`. Review found that policy files already restricted outbound delivery, but multiple runtime send paths still relied on local constants or environment values instead of one fail-closed allowlist check. |
| **Impact** | A drifted environment variable, reused helper, or future sender script could have delivered notifications to an unintended Telegram chat or Gmail recipient even though the written policy prohibited it. |
| **Root Cause (5 Why)** | **Why1**: Outbound safety was documented in `data/workspace/AGENTS.md` and `email_ops_policy.json`, but not centralized in a shared runtime guard. **Why2**: Several scripts (`email_continuous_watchdog.py`, `run_email_rag_ingest_report.py`, `risk_notification.py`, `workflow_healer.py`, `inbox_watcher.py`, `scheduled_notify.py`, and Telegram bridge code) each constructed their own send calls. **Why3**: Most of those senders trusted embedded constants or env-derived values rather than validating the destination at send time. **Why4**: The AI Engineering Harness had no dedicated visibility card for outbound-delivery policy enforcement. **Why5**: Safety hardening had focused first on `draft_only` policy and specific Gmail helper scripts, but not on one shared fail-closed outbound guard across all active notification paths. |
| **Fix** | Added `data/workspace/outbound_delivery_guard.py` as a shared fail-closed allowlist module that only permits Gmail delivery to `y.suzuki.hk@gmail.com` and Telegram delivery to chat `8173025084`, while recording policy status in `outbound_delivery_guard_status.json`. Wired the guard into `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, and `data/workspace/scripts/scheduled_notify.py`. Hardened `scripts/telegram_fast_bridge.js` to block non-allowlisted Telegram chat IDs at send/edit time. Extended `data/workspace/continuous_system_improvement.py` and `data/workspace/apps/ai_engineering_harness_status/index.html` so the Harness now shows an `Outbound Guard` card and raises a weakness if the enforced Gmail or Telegram targets drift. |
| **Files** | `data/workspace/outbound_delivery_guard.py`, `data/workspace/email_continuous_watchdog.py`, `data/workspace/run_email_rag_ingest_report.py`, `data/workspace/risk_notification.py`, `data/workspace/workflow_healer.py`, `data/workspace/inbox_watcher.py`, `data/workspace/scripts/scheduled_notify.py`, `scripts/telegram_fast_bridge.js`, `data/workspace/continuous_system_improvement.py`, `data/workspace/apps/ai_engineering_harness_status/index.html`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for all changed Python files, and `node --check scripts/telegram_fast_bridge.js` passed. `outbound_delivery_guard_status.json` now shows `policyActive=true`, `allowedGmailRecipient=y.suzuki.hk@gmail.com`, and `allowedTelegramChatId=8173025084`. A fresh `continuous_system_improvement_status.json` run now includes the strength `Outbound delivery allowlist guard is enforced`, and the Harness page can render the new `Outbound Guard` card. |
| **Lessons Learned** | Written safety policy is not enough for outbound channels. Telegram and Gmail delivery must both be guarded by one runtime allowlist that fails closed. |
| **Prevention** | Require every future outbound sender to import the shared guard before network delivery, keep the Harness card visible so drift is obvious, and treat any non-allowlisted destination as a hard error instead of a warning. |

## INC-031: Telegram bridge stopped replying because runtime ownership drifted away from the supervised implementation

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-13 |
| **Detection** | User reported that Telegram messages no longer received replies after a mini PC freeze/slowdown period. Investigation found the last successful Telegram reply recorded at `2026-04-13 08:10:26 JST`, while runtime status later pointed to a live `powershell.exe -File scripts\\telegram_fast_bridge_v3.ps1` process instead of the monitored `node scripts\\telegram_fast_bridge.js` bridge. |
| **Impact** | Telegram could silently stop behaving as expected while the repo still contained a newer hardened bridge implementation. Recovery was unreliable because the watchdog, startup task, and active runtime were not aligned on one canonical process owner. |
| **Root Cause (5 Why)** | **Why1**: Multiple Telegram bridge implementations (`telegram_fast_bridge.js`, `telegram_fast_bridge.ps1`, `telegram_fast_bridge_v2.ps1`, `telegram_fast_bridge_v3.ps1`) coexisted. **Why2**: The active runtime had drifted to `telegram_fast_bridge_v3.ps1`, while the startup script and recent hardening targeted `telegram_fast_bridge.js`. **Why3**: The watchdog only checked pid/status freshness and did not verify that the running process actually matched the canonical implementation. **Why4**: The Windows Startup folder and scheduled-task setup did not enforce one authoritative owner end to end, so an older/manual PowerShell bridge could survive outside the intended recovery path. **Why5**: Operational supervision focused on liveness files first, but not on implementation drift between legacy and canonical Telegram bridge entrypoints. |
| **Fix** | Updated `scripts/start_telegram_fast_bridge.ps1` to stop all repo-local Telegram bridge variants before starting the canonical `node scripts/telegram_fast_bridge.js` process, and to log startup actions in `data/state/telegram_fast/startup.log`. Updated `scripts/watchdog_telegram_bridge.ps1` to detect legacy PowerShell bridge variants, duplicate bridge processes, and status-pid mismatch, then restart only the canonical JS bridge. Updated `scripts/check_telegram_fast_bridge.ps1` so diagnostics now show the actual bridge command line and implementation type. Updated `scripts/install_telegram_fast_bridge_startup.ps1` so watchdog installation and login-time startup are handled together, with Windows Startup-folder fallback if scheduled-task creation is denied. |
| **Files** | `scripts/start_telegram_fast_bridge.ps1`, `scripts/watchdog_telegram_bridge.ps1`, `scripts/check_telegram_fast_bridge.ps1`, `scripts/install_telegram_fast_bridge_startup.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `powershell -ExecutionPolicy Bypass -File scripts/install_telegram_fast_bridge_startup.ps1` ensured watchdog installation and login-start fallback. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` stopped the drifted PowerShell bridge and launched the canonical Node bridge. `powershell -ExecutionPolicy Bypass -File scripts/check_telegram_fast_bridge.ps1` now reports the live `telegram_fast_bridge.js` command line. `node --check scripts/telegram_fast_bridge.js` passed, and `watchdog_telegram_bridge.ps1` now restarts when a legacy PowerShell implementation is detected. |
| **Lessons Learned** | For long-poll bots, "a process exists" is not enough. The harness must verify that the supervised implementation is the one actually consuming updates. |
| **Prevention** | Keep one canonical Telegram bridge owner, make watchdogs validate command-line identity in addition to pid freshness, and reinstall startup/watchdog tasks together whenever the Telegram runtime path changes. |

## INC-032: Workflow Healer crashed after n8n execution-list API shape drift and always returned a failure exit code

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:04 JST |
| **Detection** | User reported that `Workflow Healer` had crashed. Investigation of `/home/node/clawd/workflow_healer.log` showed repeated `FATAL: 0` every 15 minutes from `2026-04-13 21:15 JST` onward. A traced manual run inside `clawstack-unified-clawdbot-gateway-1` reproduced `KeyError: 0` at `latest_status = execs[0].get("status", "")`. |
| **Impact** | The `P017 Workflow Self-Healer` n8n job was running on schedule but failing before it could inspect or repair any workflow. Because the script also unconditionally ended with `sys.exit(1)`, even healthy runs would still be marked as failed by n8n. |
| **Root Cause (5 Why)** | **Why1**: `workflow_healer.py` assumed `/rest/executions` returned a plain list under `data`, and indexed `execs[0]`. **Why2**: The current n8n API shape returns execution rows under `data.results`, so `get_recent_executions()` handed back a dict instead of a list. **Why3**: The script had no response-normalization helper for API shape drift across n8n versions. **Why4**: Runtime logging only recorded `FATAL: 0`, because the raised `KeyError(0)` was stringified without a traceback. **Why5**: The CLI epilogue had also been left with an unconditional `sys.exit(1)`, so successful runs were not clearly distinguishable from real crashes in scheduler results. |
| **Fix** | Updated `data/workspace/workflow_healer.py` to normalize n8n list payloads via `extract_n8n_items()`, covering both legacy `data: [...]` and current `data.results: [...]` execution responses. Wired that normalization into `get_active_workflows()`, `get_recent_executions()`, and `get_execution_error()`. Also added traceback logging on fatal errors and corrected the CLI exit path so `--dry-run` and healthy runtime executions return exit code `0`, while true exceptions return `1`. |
| **Files** | `data/workspace/workflow_healer.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/workflow_healer.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py --dry-run'` reported `Active workflows: 5` with all monitored workflows healthy. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc 'cd /home/node/clawd && python3 workflow_healer.py; code=$?; echo EXIT=$code'` completed with `=== Workflow Healer done ===` and `EXIT=0`. The live log no longer ends in `FATAL: 0` after the fix. |
| **Lessons Learned** | n8n maintenance scripts need one local normalization layer for REST payloads instead of baking in a single response shape. Exit codes matter as much as business logic in scheduled jobs, because a scheduler can only distinguish healthy from broken through process termination status. |
| **Prevention** | Reuse response-normalization helpers for other n8n maintenance scripts, log tracebacks for unexpected exceptions instead of only exception strings, and treat `exit 0 on healthy / exit 1 on fault` as a required check whenever a script is run under n8n `Execute Command`. |

## INC-033: Telegram bridge treated DB-search requests as generic email chat instead of explicit local DB lookup

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:32 JST |
| **Detection** | User reported that a Telegram request to search the mini PC's DB did not work. Review of `data/state/telegram_fast/harness_status.json` showed the latest request had been routed as `email`, and the bridge replied with a generic Gmail capability explanation instead of returning local DB search results. |
| **Impact** | Telegram users could ask for a DB search and receive a misleading explanatory reply rather than actual results from the local indexed stores, making the mini PC appear unable to search its own data even though the underlying SQLite search backend was healthy. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` had no dedicated `db` route. **Why2**: Messages containing words like `gmail` or `mail` were classified directly as `email`, even when the user's intent was "search the DB". **Why3**: The `email` path used a general prompt-building flow that can answer conversationally, not a fail-closed structured DB response. **Why4**: Telegram routing relied mainly on broad intent regexes rather than an explicit "local DB lookup" override. **Why5**: The bridge design had evolved around email/task/report assistants, but not around a user-facing "DB讀懃ｴ｢縺励※" command family. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` to recognize explicit DB-search wording via `isDatabaseIntent()`, prioritize a new `db` route in `classifyRoute()`, and answer through `generateDatabaseReply()` that queries local task, report, and email contexts directly and returns structured DB-hit summaries. Restarted the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1` so the new routing logic is live. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db context 'gmail 隱ｭ縺ｿ蜿悶ｋ 縺ｧ縺阪∪縺吶°' --limit 3` returned valid JSON results from the live SQLite DB inside `clawstack-unified-clawdbot-gateway-1`, confirming the backend was healthy. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical Node bridge at `2026-04-14 07:31:57 JST`. End-to-end Telegram confirmation still requires one fresh user message after this routing fix. |
| **Lessons Learned** | For chat-driven ops tools, "search-capable backend exists" is not enough. The conversational router needs an explicit intent for "search the local DB now" so capability explanations do not mask successful search backends. |
| **Prevention** | Keep explicit operational intents such as `DB讀懃ｴ｢`, `螻･豁ｴ讀懃ｴ｢`, and `繝｡繝ｼ繝ｫDB讀懃ｴ｢` ahead of softer conversational email intents, and prefer structured fail-closed summaries for search requests instead of letting them fall through to open-ended model prompting. |

## INC-034: Relative due-date parsing missed `譚･騾ｱ` / `譚･騾ｱ譛ｫ` and fell back to free-text task search

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:43 JST |
| **Detection** | User reported that asking Telegram for tasks due by next week returned obviously stale items from 2019-2020. Log review showed the Telegram bridge correctly routed `譚･騾ｱ譛ｫ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※縺上□縺輔＞` to `task`, but `email_search_query.py` returned `due_on=null`, `due_from=null`, and `due_to=null`, causing a plain text-match search instead of a due-date range filter. |
| **Impact** | Relative-date task queries such as `譚･騾ｱ縺ｾ縺ｧ`, `譚･騾ｱ譛ｫ縺ｾ縺ｧ`, and similar deadline requests could return unrelated historical tasks, making Telegram task-search answers unreliable for near-term planning. |
| **Root Cause (5 Why)** | **Why1**: `scripts/telegram_fast_bridge.js` successfully routed the user message to task search. **Why2**: `data/workspace/email_search_query.py` only recognized `莉頑律`, `譏取律`, `莉企ｱ`, and `莉頑怦` for due-date resolution. **Why3**: `譚･騾ｱ` and `譚･騾ｱ譛ｫ` were not mapped into a date window in `resolve_due_range()`. **Why4**: When no date window was found, task search fell back to term-based SQL matching. **Why5**: Relative-date coverage had grown incrementally around current-day and current-week use cases, but the next-week planning phrases used from Telegram had not been added to the parser. |
| **Fix** | Updated `data/workspace/email_search_query.py` so `RELATIVE_TERMS` includes `譚･騾ｱ`, `莉企ｱ譛ｫ`, and `譚･騾ｱ譛ｫ`, and `resolve_due_range()` now maps `莉企ｱ譛ｫ` to the current week window and `譚･騾ｱ` / `譚･騾ｱ譛ｫ` to the next week window. Synced the updated script into `clawstack-unified-clawdbot-gateway-1` at `/home/node/clawd/email_search_query.py`. |
| **Files** | `data/workspace/email_search_query.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "cd /home/node/clawd && python3 email_search_query.py --db /home/node/clawd/email_search.db tasks-context '譚･騾ｱ譛ｫ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※縺上□縺輔＞' --limit 5"` now returns `due_from=2026-04-20` and `due_to=2026-04-26`, with current 2026-dated items instead of 2019-2020 records. |
| **Lessons Learned** | Chat routing and DB health are only half the path. Relative-date parsers need explicit coverage for the phrases users actually use in operations, especially planning ranges like next week and next weekend. |
| **Prevention** | Extend relative-date parsing with a maintained set of operational Japanese phrases and add smoke checks for `莉頑律`, `莉企ｱ`, `莉企ｱ譛ｫ`, `譚･騾ｱ`, and `譚･騾ｱ譛ｫ` whenever task-search date logic changes. |

## INC-035: Telegram DB count requests fell through to generic RAG advice instead of returning a numeric count

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 07:49 JST |
| **Detection** | User reported another disappointing Telegram reply after sending `DB縺九ｉIATF髢｢騾｣縺ｮ雉・侭謨ｰ繧呈焚縺医※`. The latest bridge log showed `route=general`, `tier=rag`, and the reply was generic guidance about searching for `IATF`, rather than a counted result from the local DB. |
| **Impact** | Telegram could answer count-style DB requests with advice text instead of an actual number, making DB-backed operational questions feel unreliable even though the underlying SQLite store was healthy and queryable. |
| **Root Cause (5 Why)** | **Why1**: The bridge recognized some DB-search wording, but not the specific combination of `DB縺九ｉ ... 雉・侭謨ｰ繧呈焚縺医※`. **Why2**: That message therefore fell through to general classification, where `IATF` triggered the RAG path. **Why3**: The RAG path can summarize retrieved snippets, but it has no notion of total matching-document count. **Why4**: `email_search_query.py` had context and search commands, but no dedicated count command for Telegram to call. **Why5**: DB-search support had been expanded around retrieval and due-date queries first, while aggregate/count requests were still unimplemented. |
| **Fix** | Added `search-count` to `data/workspace/email_search_query.py`, backed by `count_search_rows()` using FTS count with LIKE fallback. Added `fetchEmailCount()` to `data/state/email_context_helper.js`. Updated `scripts/telegram_fast_bridge.js` so DB + IATF/material/count wording is forced onto the `db` route, and `generateDatabaseReply()` now returns a numeric count for count-style requests. Restarted the canonical Telegram bridge and synced the updated Python script into `clawstack-unified-clawdbot-gateway-1`. |
| **Files** | `data/workspace/email_search_query.py`, `data/state/email_context_helper.js`, `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/email_search_query.py` passed. `node --check scripts/telegram_fast_bridge.js` passed. `docker exec clawstack-unified-clawdbot-gateway-1 sh -lc "python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 髢｢騾｣ 雉・侭'"` returned `result_count=1117`. `powershell -ExecutionPolicy Bypass -File scripts/start_telegram_fast_bridge.ps1` restarted the canonical bridge so the new route is live. |
| **Lessons Learned** | For chat ops, retrieval and aggregation are different capabilities. If users can ask "how many?", the bridge needs a dedicated count path instead of hoping a retrieval-oriented model route will infer aggregation correctly. |
| **Prevention** | Keep explicit patterns for `莉ｶ謨ｰ`, `菴穂ｻｶ`, `謨ｰ繧呈焚縺医※`, and similar aggregate queries ahead of generic RAG routing, and maintain one script-level count command so Telegram, CLI, and future dashboards can all reuse the same DB-count implementation. |

## INC-036: Telegram answered IATF document counts from model inference instead of DB truth and lost follow-up title context

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 08:12 JST |
| **Detection** | User reported that Telegram answered `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔 with `12莉ｶ`, and then answered `雉・侭蜷阪・菴輔〒縺吶°・歔 with only one fabricated-looking title. Log review showed the first message routed to `general` and `tier=rag`, not `db`, and the follow-up also routed to `general/simple`. |
| **Impact** | Telegram gave materially wrong inventory information for IATF-related materials, undercounting a large local corpus and failing to list representative titles from the real DB. This undermined trust in Telegram-based retrieval for local knowledge counts. |
| **Root Cause (5 Why)** | **Why1**: The bridge only forced `db` routing when the message explicitly contained DB-like wording. **Why2**: `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔 lacked `DB` but still semantically asked for a local count, so it fell through to general classification. **Why3**: General classification sent `IATF` questions into the RAG path, which is retrieval-oriented rather than count-oriented. **Why4**: The count response path did not persist the returned title list for the next follow-up turn. **Why5**: Telegram DB support had been implemented as one-shot answers first, without a lightweight local context memory for follow-up questions like `雉・侭蜷阪・・歔. |
| **Fix** | Updated `scripts/telegram_fast_bridge.js` so `IATF/ISO/QMS + 莉ｶ謨ｰ/雉・侭/謨ｰ` questions route directly to `db` even without the literal `DB` keyword. Extended `generateDatabaseReply()` to call the real `search-count` backend, include representative titles from `fetchEmailContext()`, and save those titles into `data/state/telegram_fast/last_db_context.json` for immediate follow-up questions such as `雉・侭蜷阪・菴輔〒縺吶°・歔. Restarted the canonical Telegram bridge after the change. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. The live DB backend reports `result_count=1118` for `IATF 髢｢騾｣ 雉・侭` via `python3 /home/node/clawd/email_search_query.py --db /home/node/clawd/email_search.db search-count 'IATF 髢｢騾｣ 雉・侭'`. Representative titles returned from the same DB search include `Re: 雉ｼ雋ｷ繝励Ο繧ｻ繧ｹ KPI縺ｫ縺､縺・※`, `繧ｰ繝ｫ繝ｼ繝励い繧ｫ繧ｦ繝ｳ繝・ IATF蜀・Κ逶｣譟ｻ蜩｡ "譖ｴ譁ｰ縺ｮ縺顔衍繧峨○`, and `Re: VDA縺ｫ縺､縺・※`, confirming that the local store contains far more than 12 items and multiple distinct titles. |
| **Lessons Learned** | For local-knowledge chat tools, "domain question" and "DB truth query" are not the same. Count and listing requests need to bypass generative shortcuts, and follow-up questions need lightweight state so users can ask naturally without repeating the full query every turn. |
| **Prevention** | Route `菴穂ｻｶ` / `莉ｶ謨ｰ` / `雉・侭蜷港 follow-ups to the DB layer by default when a recent DB context exists, and keep a short-lived local result cache for follow-up listing questions in Telegram. |

## INC-037: Telegram intent handling needed canonical normalization for varied Japanese expressions
| 鬆・岼 | 蜀・ｮｹ |
|---|---|
| **逋ｺ逕滓律** | 2026-04-14 |
| **逋ｺ隕区婿豕・* | User reported that Telegram replies still missed intent when the same request was phrased as `IATF髢｢騾｣縺ｮ雉・侭縺ｯ菴穂ｻｶ縺ゅｊ縺ｾ縺吶°・歔, `雉・侭蜷阪・菴輔〒縺吶°・歔, `譚･騾ｱ縺ｾ縺ｧ縺檎ｴ肴悄縺ｮ讌ｭ蜍呎蕗縺医※`, or `繝｡繝ｼ繝ｫDB縺ｧ蜿嶺ｿ｡縺励◆IATF縺ｮ雉・侭繧呈爾縺励※`. |
| **蠖ｱ髻ｿ遽・峇** | Telegram routing for local DB search, task search, and follow-up questions. Users could receive model-style replies or ambiguous fallbacks instead of the intended local search behavior. |
| **Root Cause (5 Why)** | **Why1**: Route selection depended on ad hoc regex branches added case by case. **Why2**: The same user intent could appear as count, list, follow-up, or search wording, but those variants were not normalized into a canonical intent bucket. **Why3**: Follow-up questions relied on a single cached title list, but the cache was only useful after some branches and not consistently preserved across all DB responses. **Why4**: The search layer was already capable, but the bridge did not enforce a stable `db_count` / `db_list` / `db_followup` / `task_due` style classification. **Why5**: The system had been optimized for individual fixes first, rather than a reusable intent normalization layer. |
| **Fix** | Reworked `scripts/telegram_fast_bridge.js` so user text is normalized with NFKC and compacted before routing. Added canonical intent helpers for DB count/list/follow-up, task due-date phrasing, report, email, and complaint intents. Updated `generateDatabaseReply()` to store and reuse recent titles for follow-up questions, and to keep DB count replies grounded in the local search backend. |
| **Files** | `scripts/telegram_fast_bridge.js`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed after the change. The updated bridge now classifies the representative inputs above into the intended intent buckets in code review, and the previous `12莉ｶ` style inference path is no longer the DB count path for IATF material questions. |
| **Lessons Learned** | User phrasing must be treated as noisy input, not as a specification. The bridge needs a small number of canonical intents and short-lived context, rather than one-off regexes for each new wording. |
| **Prevention** | Keep expanding canonical intent buckets and shared normalization instead of adding isolated phrasing rules. When a new wording appears more than once, map it to an existing intent bucket first and only add a new bucket when the behavior is genuinely new. |

## INC-038: 2025 process monitoring measurement refresh failed because PDF directory check blocked Excel-only regeneration

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:34 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` showed too many blank cells and did not reflect the Excel content. Investigation found `year_2025` in `db/process_monitoring_measurement.json` was still an array with only five monthly PDF items, even though `db/documents/繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls` already existed. |
| **Impact** | The 2025 process-monitoring page displayed incomplete or mostly empty content, so users could not rely on it as a faithful view of the registered Excel source. |
| **Root Cause (5 Why)** | **Why1**: `ProcessMonitoringMeasurementRefreshService.call` returned `PDF source directory was not found.` before doing any work if `/paperless_consume` was absent. **Why2**: That guard lived at the top of `call`, even though `refresh_year` could already rebuild 2025 from the local Excel file alone. **Why3**: As a result, Excel-only regeneration was impossible unless a PDF source directory happened to exist. **Why4**: The current JSON had never been switched from the older `year_2025` array format into the Excel-backed grid format. **Why5**: The refresh flow had been optimized around PDF fallback first, and the Excel-primary case was not allowed to complete without an unrelated PDF directory. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so the top-level `call` no longer fails early when the PDF source directory is missing. The PDF directory check now happens only inside the PDF fallback branch of `refresh_year`, after Excel has been checked first. Then regenerated 2025 from `db/documents/繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls`, which rewrote `db/process_monitoring_measurement.json` with the full grid data. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` now returns `success=>true` and `updated_years=>[2025]`. The refreshed JSON now stores `year_2025` as a hash with `rows=96`, `nonblank_cells=1365`, and `source_file=繝励Ο繧ｻ繧ｹ縺ｮ逶｣隕悶・貂ｬ螳夊ｨ倬鹸_2025蟷ｴ.xls`. `http://localhost:3004/products/process_monitoring_measurement?year=2025` returns `200` after the refresh. |
| **Lessons Learned** | A fallback path should not block the primary path. If a year can be rebuilt from local Excel, the refresh flow must not require an unrelated PDF source directory first. |
| **Prevention** | Keep Excel regeneration independent from PDF availability, and prefer source-specific checks inside each branch instead of at the top of the whole refresh flow. Add a smoke check for 2025 refresh whenever this service changes. |

## INC-039: 2025 process monitoring measurement header layout broke because the refresh path lacked template widths and header rows

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 10:57 JST |
| **Detection** | User reported that `http://localhost:3004/products/process_monitoring_measurement?year=2025` still had a broken header after the 2025 data regeneration. A visual browser check with Playwright confirmed that the page was rendering, but the 2025 table header was compressed and misaligned compared with 2024. |
| **Impact** | The 2025 process-monitoring page was readable in the body but the top header region looked malformed, which made the page feel unreliable even though the data rows were present. |
| **Root Cause (5 Why)** | **Why1**: The 2025 refresh path wrote Excel-derived rows into `db/process_monitoring_measurement.json` without `column_widths`. **Why2**: The view uses `active_year[:column_widths]` to size the table, so a missing array falls back to browser auto-sizing. **Why3**: The Excel-only regeneration path also preserved the workbook's raw top rows, which did not visually match the stable 2024 template header. **Why4**: The earlier fix focused on getting the 2025 data and counts back, but not on preserving the 2024 visual baseline. **Why5**: The refresh service did not have a template-normalization step for the header region, so structurally valid data could still render with a broken-looking table top. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel-backed refreshes now copy `column_widths` from the 2024 template and replace the first eight rows with the 2024 header rows before saving the 2025 payload. Re-ran `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` and verified the rendered page with Playwright screenshot after the fix. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true` and rewrote the JSON with the normalized 2025 payload. Playwright screenshot review of the authenticated `2025` page showed the header aligned to the 2024 visual baseline and the table no longer compressed at the top. `http://localhost:3004/products/process_monitoring_measurement?year=2025` continued to return `200`. |
| **Lessons Learned** | A structurally correct table can still look broken if the visual template is not preserved. Header rows and column widths are part of the contract, not just the data cells. |
| **Prevention** | Keep a template-normalization step for year-specific refreshes, and compare the rendered 2025 page against the 2024 visual baseline whenever the refresh pipeline changes. |

## INC-040: 2025 process monitoring measurement body rows were over-wrapped by long decimal values

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:05 JST |
| **Detection** | After visually comparing authenticated `2024` and `2025` screenshots, the 2025 body still looked denser than 2024 even though the header was aligned. The first metric block and some score cells were wrapping long floating-point strings such as `0.8571428571428571`, making the body feel compressed. |
| **Impact** | The 2025 page was technically correct but harder to read than 2024 because long numeric strings expanded several rows and reduced the visual similarity between the two years. |
| **Root Cause (5 Why)** | **Why1**: Excel-derived floats were serialized with full precision via `Float#to_s`. **Why2**: Some cells contained formula results with many decimal places. **Why3**: Those long strings wrapped inside fixed-width table cells. **Why4**: The 2025 rendering path did not apply the same compact numeric presentation as the 2024 template. **Why5**: The refresh pipeline focused on data completeness first and visual normalization second, so the body row density drifted from the 2024 baseline. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so float values are formatted with `%.4f` and trimmed before being written to `db/process_monitoring_measurement.json`. Re-ran the 2025 refresh and rechecked both `2024` and `2025` screenshots in Playwright. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/db/process_monitoring_measurement.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | The refreshed `year_2025` payload now renders compact values such as `0.8571` instead of long full-precision decimals, and the authenticated 2025 screenshot no longer shows the same degree of body-row over-wrapping. Both `2024` and `2025` pages still return `200`. |
| **Lessons Learned** | Visual parity is not just about structure; numeric formatting materially affects row height and readability. |
| **Prevention** | Keep a compact formatting rule for all Excel-derived floats in this report, and compare rendered screenshots after refreshes that introduce or regenerate formula-driven numbers. |
## INC-041: 2025 process monitoring measurement body rows misrendered because refresh stored a raw grid instead of template-backed year items

| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 11:19 JST |
| **Detection** | User pointed out that the `2025` page still had a misaligned `累積 / 実績 / 計画` region even after the header was fixed. Visual comparison showed the page was rendering a different structure than `2024`, especially in the effectiveness section. |
| **Impact** | The 2025 process-monitoring table looked structurally different from 2024, making the cumulative rows appear shifted and reducing trust in the report. |
| **Root Cause (5 Why)** | **Why1**: The refresh service was saving 2025 as an Excel-derived grid hash. **Why2**: The view expected 2025 data to be replayed through the 2024 template so row spans and block structure would remain stable. **Why3**: Excel layout and template layout diverged in the effectiveness section, especially around cumulative/actual/plan rows. **Why4**: A raw grid preserves workbook layout details instead of the canonical contract used by the page. **Why5**: The refresh flow had drifted from the `template + year items` design that the renderer already supports. |
| **Fix** | Updated `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb` so Excel refreshes now save 2025 as month-based year items instead of a raw grid. Added `extract_excel_year_entries` to read the workbook into `{process, metric, target, actual}` items, and updated `ProcessMonitoringMeasurementService#split_actual_values` to accept `当月 / 累計` as well as the legacy labels. The view now rebuilds 2025 through the 2024 template path again. |
| **Files** | `iatf_system/app/services/process_monitoring_measurement_refresh_service.rb`, `iatf_system/app/services/process_monitoring_measurement_service.rb`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ProcessMonitoringMeasurementRefreshService.call(year: 2025)` returned `success=>true`. `bundle exec ruby -c` passed for both modified service files. Playwright screenshots of authenticated `2024` and `2025` pages showed the 2025 table returning to the 2024 template shape, with the cumulative region no longer visibly shifted. |
| **Lessons Learned** | The page contract is the template, not the source workbook. Even when raw Excel looks valid, saving it as a final render format can break the visual invariants users rely on. |
| **Prevention** | Keep 2025 and later stored as normalized year items, not workbook-shaped grids. Compare the rendered result against the 2024 template whenever the refresh path changes. |
## INC-042: Mini PC slowdown required a split between always-on core services and on-demand heavy services
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-14 23:17 JST |
| **Detection** | User reported that the PC still felt slow while wanting `clawstack-unified` to remain basically always on, and specifically asked for a setup where Telegram stays usable without bringing the whole heavy stack up all the time. |
| **Impact** | The previous all-or-nothing mental model encouraged keeping many heavy services resident together, which made the mini PC feel sluggish even when only Telegram and the core gateway path were needed. |
| **Root Cause (5 Why)** | **Why1**: The unified Docker stack had been treated as one monolith. **Why2**: Heavy services such as Open WebUI, n8n, monitoring, and media tools tended to ride along with the always-on path. **Why3**: Telegram only needs the gateway and a small local model/runtime surface, not the full optional stack. **Why4**: There was no explicit host-side `core` startup entrypoint to separate “always-on but light” from “start only when needed.” **Why5**: Operational convenience had been prioritized over load separation, so the slow mini PC had no first-class lightweight startup mode. |
| **Fix** | Added `scripts/start_clawstack_core.ps1` to start a lightweight always-on set of Docker services (`clawdbot-gateway`, `postgres`, `redis`, `ollama`, `qdrant`, `litellm`, `searxng`, `minio`, `portal_server`) and then launch the canonical Telegram bridge via `scripts/start_telegram_fast_bridge.ps1`. This keeps Telegram usable while leaving the heavy stack on demand through `scripts/start_docker_addons.ps1`. |
| **Files** | `scripts/start_clawstack_core.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/minipc_optimizer.py` passed. The new core-start script was added without touching `docker-compose.yml`, and the operational plan now separates the always-on Telegram/core path from the heavy addon path. |
| **Lessons Learned** | “Always on” should mean “always on at the lightest viable layer,” not “all services at once.” A small host-side launcher is enough to make the split explicit and safe. |
| **Prevention** | Use the new core launcher for normal work, reserve `start_docker_addons.ps1` for heavy workloads, and keep Telegram bridge startup tied to the lightweight core path so user messages remain responsive. |
## INC-043: Mini PC load needed a staged startup plan instead of simultaneous service activation
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-15 |
| **Detection** | User requested a plan that keeps all apps available but reduces slowdown as much as possible. Current runtime showed a mix of always-on Docker services, email watchdogs, learning memory, and portal tooling, which can create a startup spike if launched together. |
| **Impact** | Simultaneous startup of Docker services and host-side watchdogs increases CPU, memory, and disk pressure during boot or recovery, especially on the mini PC. That makes the system feel slower even if each app is useful on its own. |
| **Root Cause (5 Why)** | **Why1**: Startup paths were spread across several scripts without a single coordinated sequence. **Why2**: Some services were safe individually but still expensive when launched at the same time. **Why3**: Dependency-aware waiting was only partially present in a few scripts. **Why4**: There was no host-side balanced launcher to serialize startup and gate the next step on readiness. **Why5**: The runtime had evolved toward feature coverage first, while load-shedding and startup pacing had not been formalized. |
| **Fix** | Added `scripts/start_minipc_balanced_stack.ps1` as a host-side launcher that starts services in a controlled sequence with per-step health probes and cooldowns. It writes status to `data/state/minipc_balanced_stack/startup_status.json` and supports `-DryRun` plus `-Mode balanced|full`. Also added readiness waits to `scripts/start_email_blacklist_hub_api.ps1` and `scripts/start_email_continuous_watchdog.ps1` so dependent services do not pile up immediately. |
| **Files** | `scripts/start_minipc_balanced_stack.ps1`, `scripts/start_email_blacklist_hub_api.ps1`, `scripts/start_email_continuous_watchdog.ps1`, `data/state/minipc_balanced_stack/startup_status.json`, `data/state/minipc_balanced_stack/startup.log`, `docs/INCIDENT_LOG.md` |
| **Verification** | PowerShell syntax check passed for all edited scripts. `scripts/start_minipc_balanced_stack.ps1 -DryRun` completed successfully and wrote the planned balanced startup sequence: postgres, redis, qdrant, ollama, gateway, portal_server, litellm, n8n, learning_engine, email_search_api, email_blacklist_hub, email_continuous_watchdog, telegram_fast_bridge. |
| **Lessons Learned** | Keeping all apps available does not require starting all of them at once. A staged launcher with health gates gives most of the responsiveness benefit without turning off useful services. |
| **Prevention** | Use the balanced launcher for normal boot and recovery scenarios. Keep heavy extras in `full` mode only, and continue adding readiness checks instead of adding more simultaneous startup paths. |

## INC-044: Postgres WAL corruption caused crash loop and system freeze
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-17 14:35 JST |
| **Detection** | User reported system freeze. docker ps showed postgres in a Restarting state. Container logs confirmed PANIC: could not locate a valid checkpoint record. |
| **Impact** | Entire stack (n8n, Gateway, Paperless, etc.) unable to connect to DB, leading to resource-intensive reconnection loops and system sluggishness/freeze. |
| **Root Cause (5 Why)** | **Why1**: Postgres failed to start. **Why2**: WAL files were corrupted. **Why3**: Likely an improper shutdown or system freeze during heavy I/O. **Why4**: The system was under heavy load due to many simultaneous services (INC-043). **Why5**: Hard reset was performed during a freeze, leading to disk state inconsistency. |
| **Fix** | Stopped postgres container. Ran pg_resetwal -f via a temporary container to reset the Write Ahead Logs. Fixed lightrag health check which was contributing to noise. |
| **Files** | docs/INCIDENT_LOG.md, docker-compose.lightrag.yml |
| **Verification** | postgres status returned to Up and logs showed ready to accept connections. System responsiveness restored. |
| **Lessons Learned** | Database corruption is a high risk during system freezes. Priority should be given to DB health in recovery playbooks. |
| **Prevention** | Ensure staged startup and load balancing (INC-043) are enforced to prevent freezes that lead to hard restarts. |

## INC-045: Rails app access failure (502 Bad Gateway) due to port mismatch
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 15:40 JST |
| **Detection** | User reported "Rails繧｢繝励Μ縺ｮ襍ｷ蜍輔↓螟ｱ謨励＠縺ｦ縺�∪縺�". Browser check confirmed 502 Bad Gateway at port 80 (Nginx). |
| **Impact** | Application inaccessible via Nginx reverse proxy (Port 80), though backend container was Up on Port 3004. |
| **Root Cause** | Port mismatch in Nginx configuration. iatf_system/nginx/conf.d/default.conf was pointing to web:3003 while the Rails production server was configured to listen on port **3004** in both docker-compose.production.yml and .env.production. |
| **Fix** | Updated iatf_system/nginx/conf.d/default.conf to use port **3004** for the upstream 
ails_app and restarted the Nginx container. |
| **Files** | [default.conf](file:///d:/Clawdbot_Docker_20260125/iatf_system/nginx/conf.d/default.conf), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed http://localhost (Port 80) successfully rendering the Rails login page. |
| **Lessons Learned** | When moving Rails ports or updating environment variables, reverse proxy configurations (Nginx) must be synchronized. |
| **Prevention** | Ensure port consistency across .env.production, docker-compose.production.yml, and 
ginx configurations. Consider using shared environment variables for ports where possible. |

## INC-046: Rails products index (500 Internal Server Error) due to view syntax error
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 15:55 JST |
| **Detection** | User reported "We're sorry, but something went wrong" at http://localhost:3004/products. Rails logs confirmed syntax error, unexpected rescue modifier, expecting ')' in pp/views/products/index.html.erb. |
| **Impact** | The main products index page was completely inaccessible, preventing users from viewing item progress. |
| **Root Cause (5 Why)** | **Why1**: ERB compilation failed. **Why2**: Syntax error at line 256. **Why3**: A 
escue modifier was placed inside method call parentheses without proper grouping (I18n.l(val, format: :long rescue val)). **Why4**: This is invalid Ruby syntax for keyword arguments. **Why5**: The template had been modified previously to add localization, and the syntax check was not exhaustive. |
| **Fix** | Corrected the syntax in pp/views/products/index.html.erb by properly grouping the localized call: <%= (I18n.l(@publish_dates[idx], format: :long) rescue @publish_dates[idx]) %>. |
| **Files** | [index.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index.html.erb), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed /products successfully redirects to /users/sign_in and renders the login page without the "something went wrong" error. |
| **Lessons Learned** | ERB views should be checked for syntax correctness, especially when using inline 
escue modifiers. |
| **Prevention** | Ensure any changes to localization or view logic are tested by rendering the actual page. Consider a CI step that runs erblint or similar. |

## INC-047: Rails home page (500 Error) due to missing 'index_tasseido' route/action
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 16:20 JST |
| **Detection** | After fixing INC-046, the home page still returned a 500 error. Logs confirmed undefined local variable or method 'index_tasseido_path' at pp/views/products/index.html.erb:48. |
| **Impact** | The Products index page could not be rendered for logged-in users, as the "Attainment Level" (驕疲�蠎ｦ) feature was missing its backend infrastructure. |
| **Root Cause (5 Why)** | **Why1**: The home page failed to render. **Why2**: An undefined path helper index_tasseido_path was called. **Why3**: A new UI component for "Attainment Level" had been added to the template without implementing the route or controller. **Why4**: Changes were made in production mode, and one error (syntax) was masking another (missing route). **Why5**: Development and production environments lacked synchronization on new features. |
| **Fix** | (1) Added index_tasseido route to config/routes.rb. (2) Implemented index_tasseido action in ProductsController. (3) Created pp/views/products/index_tasseido.html.erb to render the existing chart partial. (4) Restarted Docker containers to clear the Rails production route/code cache. |
| **Files** | [routes.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/config/routes.rb), [products_controller.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/controllers/products_controller.rb), [index_tasseido.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index_tasseido.html.erb), docs/INCIDENT_LOG.md |
| **Verification** | Browser subagent confirmed the home page loads correctly and clicking '驕疲�蠎ｦ (蝗ｳ逡ｪ蛻･)' renders a valid bar chart for specific part numbers. |
| **Lessons Learned** | Adding UI components requires updating the full stack (Route -> Controller -> View). In production, a container restart is mandatory to apply these changes. |
| **Prevention** | Use automated smoke tests to ensure that all navigation items and form targets on the main dashboard are reachable. |

## INC-048: TOP page layout "destruction" after incomplete UI modernization
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-18 16:40 JST |
| **Detection** | User reported that the TOP page format was "completely destroyed" after the recent fixes. |
| **Impact** | The Products index page had a broken sidebar layout, missing tab styles, and incorrect summary logic (showing flat list instead of grouped summary). |
| **Root Cause (5 Why)** | **Why1**: The layout appeared broken. **Why2**: Essential CSS for the dashboard tabs was missing from the template. **Why3**: An experimental Tailwind sidebar layout had been introduced during a "repair" phase that was incompatible with the existing view structure. **Why4**: The summary partial (_form) differed from the expected dashboard partial (_form3). **Why5**: Changes in production were not immediately visible due to Puma's template caching, masking errors until a restart. |
| **Fix** | (1) Reconstructed index.html.erb using the classic centered 1200px layout from index3. (2) Restored the radio-button tab system with its original CSS. (3) Switched Phase dashboard to use orm3 (grouped summary). (4) Integrated the new 'Tasseido' feature as a functional 8th tab. (5) Restarted the Docker container to apply view changes. |
| **Files** | [index.html.erb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/views/products/index.html.erb), [products_controller.rb](file:///d:/Clawdbot_Docker_20260125/iatf_system/app/controllers/products_controller.rb) |
| **Verification** | Browser subagent verified the restoration of the classic look, the removal of the sidebar, and the functionality of all 8 tabs. |
| **Lessons Learned** | When "repairing" templates, strictly adhere to existing project design patterns (like radio-button tabs) unless a full redesign is requested. Always restart the production server when updating view templates to clear memory caches. |

### INC-049: Layout Mismatch during IATF Restoration
- **発生日**: 2026-04-18
- **発見方法**: ユーザーからの「デザイン変更」および「崩壊」の指摘
- **影響範囲**: /products ページのUI不一致
- **根本原因**: 「GitHubから入手」という指示に対し、リポジトリの履歴にある旧サイドバー形式を復元したが、その際のCSS/HTMLの整合性不足およびユーザーの期待する『最新のGitHub状態』への理解不足。
- **修正内容**: origin/main から厳密にサイドバー＋青テーブル形式をロールバックし、文字化けのみを技術的に修正。
- **検証結果**: ブラウザ検証によりサイドバー・青テーブル・正確な日本語表示を確認済み。
- **教訓**: 『オリジナル』の定義が文脈により異なるため（Git上のコードか、直近の稼働状態か）、大規模な差し戻し前には必ず構造のプレビューを行うこと。

## INC-050: Email continuous ingest daemon restarted due to stale heartbeat
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-20 05:39 JST |
| **Detection** | Email continuous ingest watchdog restarted the daemon, logging "Reason: daemon heartbeat stale" with "Known stage: full_backfill". |
| **Impact** | The email ingestion process was interrupted during long-running tasks, causing uncompleted syncs and unnecessary service churn. |
| **Root Cause (5 Why)** | **Why1**: Heartbeat (updatedAt) became stale during the full_backfill phase. **Why2**: The full backfill took longer than the watchdog threshold. **Why3**: The script continuous_email_ingest_daemon.py calls 
un_command which blocks completely until the subprocess (
un_priority_gmail_backfill.py) finishes. **Why4**: 
un_command has no mechanism to update the heartbeat file (email_continuous_ingest_status.json) while waiting. **Why5**: Heartbeats were only updated between tasks, failing to account for tasks like ull_backfill (max 5400s) and sync_learning (max 1800s) that run for a long time. |
| **Fix** | Replaced 
un_command in 
un_full_backfill and 
un_learning_sync with a new 
un_command_with_heartbeat wrapper that utilizes subprocess.Popen to update the heartbeat every 30 seconds while waiting. |
| **Files** | data/workspace/continuous_email_ingest_daemon.py |
| **Verification** | Verified code explicitly emits updatedAt and currentTaskHeartbeatAt during long subprocess operations without changing underlying business logic. |
| **Lessons Learned** | Long-running subprocesses required by a constantly monitored daemon must include an internal heartbeat loop. |
| **Prevention** | Ensure any new task invoking a subprocess with a timeout greater than the watchdog's threshold (e.g., > 60 seconds) wraps it with periodic heartbeat updates. |

## INC-051: Learning Engine & Watchdog Failure (Process Conflict)
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-23 02:30 JST |
| **Detection** | Risk notification flagged Learning Engine as offline. Auto-repair failed with exit code 4294770688. |
| **Impact** | Temporary unavailability of learning features and email search/blacklist APIs. |
| **Root Cause (5 Why)** | **Why1**: Learning Engine and Email APIs were reporting as offline or unstable. **Why2**: Duplicate background processes for email_search_api.py and email_blacklist_hub_api.py were running (one via Microsoft Store Python, one via Venv), causing port contention and resource waste. **Why3**: The auto-repair script failed to restart them because it resolved the repo ROOT to C:\Windows\System32. **Why4**: resolve_repo_root() fell back to Path.cwd() when running as a system task, and its traversal logic was insufficient for the host environment. **Why5**: mcp-bridge was also looping because it was configured with a stdio-only MCP server command in a container. |
| **Fix** | (1) Terminated all duplicate host processes. (2) Restored services cleanly using Venv-based launchers. (3) Patched auto_repair_allowed.py with resilient path resolution (traversing up from __file__ and adding explicit fallbacks). (4) Reconfigured mcp-bridge to use clawstack_mcp_server.py (Python/FastMCP) listening on 0.0.0.0:3333. |
| **Files** | [auto_repair_allowed.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/auto_repair_allowed.py), [docker-compose.yml](file:///d:/Clawdbot_Docker_20260125/docker-compose.yml), [clawstack_mcp_server.py](file:///d:/Clawdbot_Docker_20260125/data/workspace/clawstack_mcp_server.py), docs/INCIDENT_LOG.md |
| **Verification** | Verified all endpoints (8110, 8791, 8792, 3333) are reachable from the host. Auto-repair script confirmed correct ROOT resolution (D:\Clawdbot_Docker_20260125). |
| **Lessons Learned** | Background processes must be managed via a single canonical launcher to avoid duplicates. Auto-repair scripts must be path-agnostic or have robust discovery for the host repository root. |
| **Prevention** | Audit the startup sequence in start_minipc_balanced_stack.ps1 to ensure no duplicate spawns occur. Add a check in individual API scripts to exit if another instance is already bound to the port. |

## INC-052: AI Strategy Scout watchdog stopped due to omission from balanced startup
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-25 06:21 JST |
| **Detection** | User reported that AI tool info was not being updated. `ai_strategy_scout_watchdog_status.json` showed updatedAt from 12 days ago. |
| **Impact** | Automated technology research and architectural recommendations were stale. |
| **Root Cause (5 Why)** | **Why1**: Watchdog process was not running. **Why2**: System was recovered multiple times recently (INC-051, etc.). **Why3**: Recoveries used `start_minipc_balanced_stack.ps1`. **Why4**: The balanced startup script did not include the scout watchdog step. **Why5**: The scout was initially treated as a non-core "extra" but is actually part of daily governance. |
| **Fix** | (1) Triggered manual scout to refresh data. (2) Modified `scripts/start_minipc_balanced_stack.ps1` to include `ai_strategy_scout_watchdog` in the default balanced sequence. (3) Restarted the watchdog process. |
| **Files** | `scripts/start_minipc_balanced_stack.ps1`, `docs/INCIDENT_LOG.md`, `ACT.md` |
| **Verification** | Verified `ai_strategy_scout_local_digest.md` contains current date (2026-04-25). Watchdog process confirmed active. |
| **Lessons Learned** | Governance and research tasks (Scout) are as critical as connectivity tasks (Telegram Bridge) for long-term agent autonomy. |
| **Prevention** | Audit the balanced startup script whenever a new critical governance or watchdog service is introduced. |
## INC-053: Telegram OpenClaw conversation and scheduled notification degradation
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 21:40 JST |
| **Detection** | User reported abnormal Telegram conversation and asked whether Gmail due-date notifications, AI Strategy Scout, and self-growth were still alive. Local checks showed Telegram replies in mojibake, repeated model timeouts, current n8n API listing only 4 workflows, missing AI Scout/P016 workflows from the active API surface, and duplicate AI Scout watchdog processes. |
| **Impact** | Telegram conversation quality was degraded; Gmail due-date information was not reliably sent to Telegram; AI Scout n8n workflow was absent from the active n8n API; self-growth hygiene was running but had not written a fresh status until manually checked. |
| **Root Cause (5 Why)** | **Why1**: Telegram replies were abnormal. **Why2**: The bridge routed simple messages into a slow local model path and retained stale mojibake status from prior replies. **Why3**: The default bridge model path could exceed the interaction timeout under current host load. **Why4**: Scheduled notification workflows were assumed present from old SQLite/backups, but the active n8n API surface had lost them after prior restore/import churn. **Why5**: Startup/watchdog ownership was split between n8n workflows and host watchdogs, allowing duplicate host processes and missing active n8n workflows to coexist without a single health assertion. |
| **Fix** | (1) Changed `scripts/start_telegram_fast_bridge.ps1` default Telegram model to `qwen3-nothink:latest` and shortened timeout to 20s. (2) Added deterministic fast replies for greetings and weather-unavailable cases in `scripts/telegram_fast_bridge.js`, and added a safe Japanese timeout fallback. (3) Confirmed `data/state/email_context_helper.js` routes Gmail/due-date/report intents with readable Japanese patterns. (4) Added Telegram sending to `data/workspace/ai_strategy_scout_watchdog.py` after successful local scout refresh. (5) Added and ran `data/workspace/repair_telegram_n8n_schedules_20260429.py` to restore P016 and AI Scout workflows from backups, patch P016 to send Gmail due-date summaries to Telegram, and set schedules. (6) Activated restored n8n workflows and restarted canonical Telegram, AI Scout, and self-growth watchdog processes. |
| **Files** | `scripts/start_telegram_fast_bridge.ps1`, `scripts/telegram_fast_bridge.js`, `data/state/email_context_helper.js`, `data/workspace/ai_strategy_scout_watchdog.py`, `data/workspace/repair_telegram_n8n_schedules_20260429.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | `node --check scripts/telegram_fast_bridge.js` passed. `python -m py_compile` passed for the modified Python scripts. `email_search_query.py tasks-context "納期 今週 未回答"` returned 1 open Gmail due-date item for 2026-04-29. Active n8n workflows verified: P016 restored as `OpnCRJquLkBjXOyw` active=true; AI Scout restored as `Mc3U5YAJrQxydJ96` active=true. Self-growth hygiene status is healthy with 4 points and estimated 0.023 MB. One canonical process each is running for Telegram bridge, AI Scout watchdog, and self-growth hygiene. |
| **Lessons Learned** | n8n database snapshots/backups are not proof that workflows are active in the current API surface. Telegram chat bridges need deterministic fast paths for common interactions when the local model stack is busy. |
| **Prevention** | Keep a single canonical launcher for each host watchdog, verify active n8n workflows through the REST API after restore, and treat Telegram response timeout/error rate as a health signal rather than only process liveness. |

## INC-054: ByteRover curate failures and local memory fallback
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:20 JST |
| **Detection** | User reported frequent ByteRover failures and asked whether prior experience had been lost. `brv query` worked from `.brv/context-tree`, but `brv curate` returned HTTP 401 with the built-in ByteRover provider. |
| **Impact** | Existing project memories remained readable, but new experiences could fail to persist through normal `brv curate`, creating a risk that repair knowledge would be lost between sessions. |
| **Root Cause (5 Why)** | **Why1**: ByteRover saves failed. **Why2**: `brv curate` returned HTTP 401 while `brv query` still worked. **Why3**: The built-in ByteRover provider path treated curate as unauthorized even though the provider was connected. **Why4**: The installed CLI was old (`2.1.3`) and local provider fallback with Ollama avoided 401 but was too slow for curate. **Why5**: There was no project-local timeout/fallback wrapper to preserve memory when the official curator path failed. |
| **Fix** | Upgraded global `byterover-cli` from `2.1.3` to `3.10.0`, verified query still works, tested built-in and local provider curate paths, and added `scripts/brv_safe_curate.ps1` as an external harness that writes a local Markdown fallback when `brv curate` fails or times out. |
| **Files** | `scripts/brv_safe_curate.ps1`, `docs/INCIDENT_LOG.md` |
| **Verification** | `brv --version` reports `byterover-cli/3.10.0`. `brv query` completes successfully. Built-in `curate` still returns HTTP 401, confirming the residual upstream/auth issue. Local Ollama provider `query` works, while curate timed out after 180s. `scripts/brv_safe_curate.ps1` was verified with a forced 1s timeout and wrote `.brv/context-tree/infrastructure/byterover_repair/safe_curate_fallback.md`. |
| **Lessons Learned** | ByteRover read health and write health are separate. A working `query` does not prove `curate` can persist new operational lessons. |
| **Prevention** | Use `scripts/brv_safe_curate.ps1` for important post-fix memories until official `brv curate` is healthy. Include `brv status`, provider, CLI version, query, and curate checks in future memory-health triage. |

## INC-055: Missing critical n8n workflows restored from backups
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:30 JST |
| **Detection** | User asked whether all n8n workflows had been restored. n8n REST API showed only six workflows, and critical scheduled workflows for Daily Promises, Daily System Health Check, Email RAG Ingest, and Daily Trend Opportunity Report were missing from the active API surface while backups existed under `backups/n8n/`. |
| **Impact** | Several scheduled governance and reporting tasks would not run at their expected times, even though older backup files made the workflows appear recoverable. |
| **Root Cause (5 Why)** | **Why1**: Scheduled n8n tasks were missing. **Why2**: The active n8n API surface had fewer workflows than the historical critical set. **Why3**: Prior recovery focused on P016 and AI Scout, leaving other critical workflows in backups only. **Why4**: The integrity manifest was not present on the host, so missing critical workflows were not automatically asserted after n8n restore/import churn. **Why5**: Workflow existence had been inferred from backup files instead of verified through the current REST API. |
| **Fix** | Added and ran `data/workspace/restore_missing_critical_n8n_workflows_20260429.py`. The script backed up the current n8n API list, selected the latest active backup per critical workflow, imported each workflow inactive, validated expected cron expressions, then activated only workflows with no validation problems. |
| **Files** | `data/workspace/restore_missing_critical_n8n_workflows_20260429.py`, `data/workspace/restore_missing_critical_n8n_workflows_20260429_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | Restored workflows: `Daily Promises Report` as `4X9B3RqBOtcMvpZh` cron `0 23 * * *`, `Daily System Health Check` as `E1ATfn6J7i7aZrMr` cron `0 9 * * *`, `Email RAG Ingest` as `SKarchfEc4Oy9lMr` cron `0 2 * * *`, and `Daily Trend Opportunity Report` as `nGPAoWhJXVxCF899` cron `30 20 * * *`. Re-checked six critical workflows including P016 and AI Scout; all were `active=true` with expected cron expressions. |
| **Lessons Learned** | Backups prove recoverability, not active service. After any n8n repair, the active REST API surface must be compared against the critical workflow set. |
| **Prevention** | Keep `restore_missing_critical_n8n_workflows_20260429_status.json` as the current restoration evidence and recreate a host-visible critical workflow manifest/check if n8n import churn happens again. |

## INC-056: OpenCode GO LiteLLM config contained direct API key
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:38 JST |
| **Detection** | User asked whether OpenCode GO was rule-based and running under the optimal environment. Inspection of `data/state/litellm_config.yaml` showed OpenCode GO aliases were registered, but the OpenCode GO API credential was directly embedded in alias definitions instead of using environment-variable references. |
| **Impact** | The OpenCode GO routing policy existed and aliases were visible through LiteLLM, but the config did not fully comply with the external AI confidentiality policy and increased credential exposure risk. |
| **Root Cause (5 Why)** | **Why1**: A credential appeared in a runtime config. **Why2**: OpenCode GO model aliases had been added directly to `data/state/litellm_config.yaml`. **Why3**: The template/notes required environment-variable based configuration, but the merged runtime config used literal values. **Why4**: Registration was checked by model-list visibility rather than by policy compliance. **Why5**: There was no post-merge lint/check for secret literals in LiteLLM routing files. |
| **Fix** | Replaced OpenCode GO `api_base` and `api_key` literals in `data/state/litellm_config.yaml` with `${OPENCODE_GO_API_BASE}` and `${OPENCODE_GO_API_KEY}` for `opencode-go-research`, `opencode-go/kimi-k2.6`, `opencode-go/glm-5.1`, `opencode-go/deepseek-v4-flash`, and `opencode-go/deepseek-v4-pro`. |
| **Files** | `data/state/litellm_config.yaml`, `docs/INCIDENT_LOG.md` |
| **Verification** | LiteLLM `/v1/models` still lists the OpenCode GO aliases. `Select-String` confirms OpenCode GO aliases now use environment-variable references rather than direct literals. No external OpenCode GO inference call was executed because that would send data to a cloud API and may incur cost. |
| **Lessons Learned** | Model alias visibility is not the same as policy-compliant operation. External-provider routes must be checked for both runtime availability and secret-handling hygiene. |
| **Prevention** | Add secret-literal checks for `data/state/litellm_config*.yaml` before future external model merges, and require explicit consent before cloud inference smoke tests. |

## INC-057: IATF教材生成がOpenCode GOからGeminiへ早期フォールバック
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-29 22:50 JST |
| **Detection** | User noted that IATF教材生成 should be using OpenCode GO models. `data/iatf_videos/generation.log` showed recent successful scripts as `google/gemini-2.5-flash` or `direct/gemini-2.5-flash` even though `SCRIPT_MODELS` listed `opencode-go/kimi-k2.6` first. Minimal public smoke tests through LiteLLM confirmed OpenCode GO aliases were reachable. |
| **Impact** | IATF script generation could use the more expensive Gemini fallback even when OpenCode GO was available under the intended routing policy. Failures were also hard to diagnose because empty model responses and timeout details were only printed, not written to a durable status file. |
| **Root Cause (5 Why)** | **Why1**: Gemini was used for recent IATF scripts. **Why2**: The script generator tried only `opencode-go/kimi-k2.6` before Gemini in the LiteLLM route. **Why3**: Kimi/OpenCode calls can take longer than the previous 30s client timeout or occasionally return empty content, causing immediate fallback. **Why4**: Other OpenCode GO aliases (`deepseek-v4-flash` and `deepseek-v4-pro`) were registered but not included in the script-generation priority list. **Why5**: There was no preflight harness to prove OpenCode GO returned non-empty content before a long IATF generation run. |
| **Fix** | Updated `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py` to load root `.env` when used standalone, add `opencode-go/deepseek-v4-flash` and `opencode-go/deepseek-v4-pro` before Gemini, extend OpenCode GO LiteLLM client timeout to 180s, treat empty content as an explicit route failure, and write the latest route status to `data/workspace/iatf_opencode_go_routing_status.json`. Added `data/workspace/iatf_opencode_go_preflight.py` as a host-side read-only preflight that tests OpenCode GO aliases with a public non-sensitive prompt and writes `data/workspace/iatf_opencode_go_preflight_status.json`. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py`, `data/workspace/iatf_opencode_go_preflight.py`, `data/workspace/iatf_opencode_go_preflight_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py data/workspace/iatf_opencode_go_preflight.py` passed. `python data/workspace/iatf_opencode_go_preflight.py --timeout 60` succeeded for `opencode-go/kimi-k2.6` in 28.30s, `opencode-go/deepseek-v4-flash` in 24.33s, and `opencode-go/deepseek-v4-pro` in 26.83s, all returning non-empty JSON content through LiteLLM. |
| **Lessons Learned** | A model being first in a priority list is not enough; the client timeout and empty-response handling must match the provider's real latency and response behavior. |
| **Prevention** | Run `data/workspace/iatf_opencode_go_preflight.py` before long IATF generation batches and inspect the generated status JSON. Keep multiple OpenCode GO aliases before paid fallbacks so one OpenCode model failure does not immediately route to Gemini. |

## INC-058: OpenRadioss run35 estimated multi-week runtime
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 06:50 JST |
| **Detection** | User asked to make OpenRadioss finish in about 10 hours. Inspection of `/work/engine_run35.log` showed the engine was still around `T=0.00124 s` after about `50,200 s` elapsed, while the deck end time was `0.08 s` with `DT=5.0e-8 s`, giving a multi-week remaining estimate. |
| **Impact** | The OpenRadioss job was consuming CPU but was not practical as an engineering feedback run. It also competed with other local generation work for host resources. |
| **Root Cause (5 Why)** | **Why1**: The calculation was projected to take far longer than expected. **Why2**: The engine deck requested `0.08 s` of simulation time at a very small timestep. **Why3**: That implies roughly `1,600,000` cycles before contact/cost effects. **Why4**: The job was being used as a feedback/screening calculation rather than a final high-fidelity validation, but the run controls were closer to a long validation deck. **Why5**: There was no host-side tuning harness that preserved the original deck, records the intended runtime budget, and restarts a shortened screening run with traceable settings. |
| **Fix** | Added `data/workspace/openradioss_10h_tune_run35.py` to back up current `/work` inputs/logs, patch the engine deck, stop only the active OpenRadioss engine process, and restart as `run37`. Tuned settings: end time `0.0014 s`, minimum nodal timestep `8.0e-8 s`, animation interval `0.00035 s`, and reduced animation output to EPSP/VONM/DISP. Added `data/workspace/openradioss_10h_tuning_report.md` with the analysis and remaining engineering notes. |
| **Files** | `data/workspace/openradioss_10h_tune_run35.py`, `data/workspace/openradioss_10h_tuning_report.md`, `data/workspace/openradioss_10h_tuning_status.json`, `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/openradioss_10h_tune_run35.py` passed. `run37` started in `clawstack-unified-openradioss-1` with PID recorded in `/work/engine.pid`. Initial line showed `DT=8.0000E-08` and `DM/M=1.9495E+01`. After about 90 seconds, `/work/engine_run37.log` reported `NC=100`, `T=8.0000E-06`, `DM/M=1.9526E+01`, and `REMAINING TIME=13122.24 s`, which is within the requested 10-hour class. |
| **Lessons Learned** | Runtime budget must be encoded directly into the engine deck for screening runs. Leaving a validation-style end time in place can make a job appear healthy while being operationally unusable. |
| **Prevention** | Keep a separate screening profile for OpenRadioss jobs, preserve original validation decks before tuning, and check estimated cycles plus early `REMAINING TIME` before leaving a long CAE run unattended. |

## INC-059: Rails app unavailable through nginx and LAN address
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 08:20 JST |
| **Detection** | User reported that `http://192.168.5.172/` did not display the Rails app. Host-side `curl` showed `http://127.0.0.1/` initially returned 502 through nginx, while the Rails container itself returned a login redirect on port 3004. |
| **Impact** | The Rails app was not reachable through the intended nginx entrypoint, and LAN access through the host IP remained unavailable even after the application proxy was repaired. |
| **Root Cause (5 Why)** | **Why1**: nginx returned 502. **Why2**: nginx tried to proxy to `web:3003`. **Why3**: the Rails/Puma container was listening on `0.0.0.0:3004`, so upstream port 3003 refused the connection. **Why4**: the nginx config had drifted from the active Rails container port. **Why5**: there was no startup health check that validated nginx upstream reachability and LAN binding together. Residual LAN timeout is separate: Docker reported `0.0.0.0:80->80`, but Windows did not show a host listener on physical port 80 and adding a `netsh portproxy` entry requires administrator rights. |
| **Fix** | Changed `iatf_system/nginx/conf.d/default.conf` upstream from `web:3003` to `web:3004`, validated the config with `nginx -t`, reloaded nginx, and restarted `iatf_system-nginx-1` to refresh the port binding. After user approved the Docker binding fix, tested direct Docker LAN binding, then moved the active production compose nginx mapping to `127.0.0.1:18090:80` after direct `192.168.5.172:80:80` still failed before reaching nginx. This leaves host port 80 free for an administrator-level Windows `0.0.0.0:80 -> 127.0.0.1:18090` portproxy. Recreated only `iatf_system-nginx-1`. No protected Rails view/layout/route/application files were changed. |
| **Files** | `iatf_system/nginx/conf.d/default.conf`, `iatf_system/docker-compose.production.yml`, `docs/INCIDENT_LOG.md` |
| **Verification** | `docker exec iatf_system-nginx-1 nginx -t` passed. `curl.exe -I --max-time 8 http://127.0.0.1/` returned `HTTP/1.1 302 Found` with `Location: http://127.0.0.1/users/sign_in`, proving nginx-to-Rails proxying is repaired. Direct Docker LAN binding showed `127.0.0.1:80->80/tcp, 192.168.5.172:80->80/tcp` but `http://192.168.5.172/` still timed out and nginx logs showed the request never reached nginx. Final tested Docker mapping is `127.0.0.1:18090->80/tcp`; Windows `portproxy` is `0.0.0.0:80 -> 127.0.0.1:18090`. `curl.exe -I --max-time 8 http://127.0.0.1:18090/` and `curl.exe -I --max-time 8 http://192.168.5.172/` both return `HTTP/1.1 302 Found`; the LAN response redirects to `http://192.168.5.172/users/sign_in`. nginx access logs show both requests reaching `iatf_system-nginx-1`. |
| **Lessons Learned** | Local container health, nginx upstream health, and LAN reachability are separate checks. A Docker port mapping line is not sufficient evidence that Windows is listening on the physical LAN address. |
| **Prevention** | Add a lightweight host-side health check that asserts all three paths: Rails container port 3004, nginx via `127.0.0.1:80`, and LAN address `192.168.5.172:80`. Keep nginx upstream port synchronized with the Rails/Puma runtime port in future compose/config changes. |

## INC-060: Rails production Tailwind/assets missing after LAN recovery
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:10 JST |
| **Detection** | User reported that the Rails design/layout decoration disappeared and Tailwind CSS appeared dead after LAN access was restored. `curl` against the sign-in page showed stylesheet links to `/assets/tailwind-...css`, `/assets/inter-font-...css`, and JS assets, but direct requests for those asset URLs returned 404. |
| **Impact** | Rails pages loaded, but production styling, layout decoration, images, and JavaScript assets were missing or degraded. The app looked unstyled even though the route itself was reachable. |
| **Root Cause (5 Why)** | **Why1**: The browser loaded the HTML but not the CSS. **Why2**: `/assets/...` URLs returned 404. **Why3**: `public/assets` inside `iatf_system-web-1` was empty after the production container/volume state changed. **Why4**: The production startup command only ran `npm run build:css`, which creates the non-digested Tailwind build but does not populate Rails' digested `public/assets` manifest. **Why5**: There was no post-restart health check that requested the actual digest CSS/JS URLs referenced by the rendered HTML. |
| **Fix** | Ran `RAILS_ENV=production bundle exec rails assets:precompile` inside `iatf_system-web-1`, then restarted the web container so Rails reloaded the new asset manifest. Updated `iatf_system/docker-compose.production.yml` so the production web command runs `bundle exec rails assets:precompile` before starting Puma, preventing empty `public/assets` after future container recreation. |
| **Files** | `iatf_system/docker-compose.production.yml`, `iatf_system/app/assets/stylesheets/tailwind.css`, `docs/INCIDENT_LOG.md` |
| **Verification** | After precompile and web recreation, `curl -L http://192.168.5.172/users/sign_in` references `/assets/tailwind-e9c087ad77e1b3d918d43a7664907da844ab9e7b.css`, `/assets/inter-font-1b0c468edea01b74041b0c74f0ae84d34c09f89f.css`, and `/assets/application-e249ed276a5680c3eca8b1b2c3b5d81ea26353d9.js`. Direct `curl -I` checks for those three URLs through `http://192.168.5.172/` all returned `HTTP/1.1 200 OK`. `public/assets` contains 74 files after precompile. |
| **Lessons Learned** | A successful Rails route check is not enough after production container changes. Asset health must be verified by fetching the exact digest URLs emitted in the rendered HTML. |
| **Prevention** | Keep production startup responsible for `rails assets:precompile` before Puma starts, and add digest CSS/JS URL checks to future Rails availability triage. |

## INC-061: Amada press IoT charts did not receive numeric data
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:27 JST |
| **Detection** | User reported that graphs from the Amada press machine were not reflected on `http://192.168.5.172/products/iot?commit=IOTデータ`. Local checks found today's Amada CSV files under `/myapp/db/record/iot`, but `IotDataService.call` returned series like `["0", nil]` because the parser expected two CSV columns. |
| **Impact** | The IoT page loaded, but Amada80t3 line charts had empty/nil values for most series, so current press data was not visualized even though Node-RED/Raspberry Pi CSV files were present. |
| **Root Cause (5 Why)** | **Why1**: Amada charts did not show current values. **Why2**: Chartkick received nil values for the y-axis. **Why3**: `IotDataService` used `CSV.foreach(..., headers: true)` and emitted `[row[0], row[1]]`. **Why4**: Current Amada CSV files are one-value-per-line time series without headers, so the first value was treated as a header and there was no second column. **Why5**: The page also used historical snake_case instance variable names for several Amada/Dobby charts while the service generated mixed-case names, so some series could remain nil even after CSV loading. |
| **Fix** | Updated `IotDataService#load_csv` to parse headerless CSV, support both one-column and two-column formats, synthesize the x-axis from row index for one-column files, and cast numeric values. Updated `ProductsController#iot` to provide backward-compatible instance variable aliases used by the existing IoT view. Restarted `iatf_system-web-1` to load the production code. |
| **Files** | `iatf_system/app/services/iot_data_service.rb`, `iatf_system/app/controllers/products_controller.rb`, `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c` passed for `iot_data_service.rb` and `products_controller.rb`. `RAILS_ENV=production rails runner` confirmed Amada series contain numeric values: `StampingJYOTAIAmada80t3` 54 points ending `["53", 1]`, `StampingchokoteiAmada80t3` 54 points ending `["53", 25]`, `SPMAmada80t3` 54 points ending `["53", 130]`, and `ShotAmada80t3` 54 points ending `["53", 13130]`. After restart, Puma listened on `0.0.0.0:3004` and `http://192.168.5.172/` returned `HTTP/1.1 302 Found`. |
| **Lessons Learned** | Field CSV contracts can change independently from Rails assumptions. IoT graph health must validate non-nil y-values, not just file existence. |
| **Prevention** | Keep `IotDataService` tolerant of one-column and two-column CSVs, and add future health checks that report row count plus first/last non-nil values for each machine series. |

## INC-062: Node-RED IoT CSV lacked timestamp column for chart x-axis
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 09:39 JST |
| **Detection** | User clarified that the IoT chart x-axis should be date/time and that Node-RED should write the sensor acquisition time into column A when generating CSV files. Inspection showed the active `Shiftr Receiver` flow in `iatf_system-nodered-1` wrote raw MQTT payload values directly to CSV, producing one-value-per-line files. |
| **Impact** | Rails could graph current values after INC-061, but the x-axis used fallback row indexes for one-column legacy rows rather than actual acquisition timestamps. This reduced traceability of Amada press data. |
| **Root Cause (5 Why)** | **Why1**: The chart x-axis was not date/time. **Why2**: CSV rows did not contain acquisition timestamps. **Why3**: Docker-side Node-RED receiver functions set only `msg.filename` and passed raw `msg.payload` to the file node. **Why4**: The Shiftr receiver was introduced as a transport bridge and did not preserve the timestamp behavior used in some Raspberry Pi local CSV flows. **Why5**: The data contract between Node-RED CSV output and Rails Chartkick input was not documented or verified with a two-column sample. |
| **Fix** | Updated `Node_Red_JSON_20260429/docker/docker_nodered_shiftr_receiver.json` so all ten `Prep *` function nodes write `YYYY/MM/DD HH:mm:ss,value` to `msg.payload` before the file node appends the row. Backed up active Node-RED flows to `backups/nodered/iot_timestamp_20260430/iatf_system_nodered_flows_before_timestamp_patch.json` and patched the live `iatf_system-nodered-1` `Shiftr Receiver` flow through the Node-RED `/flows` API. After discovering the Node-RED container clock is UTC, changed the timestamp generation to explicitly output JST by adding 9 hours and formatting UTC fields from the adjusted timestamp. Backed up live IoT CSVs to `backups/iot_csv_timezone_20260430_095031/iot` and corrected already-written `2026/04/30 00:xx` timestamp rows to `2026/04/30 09:xx`; legacy one-column rows were left unchanged because they do not contain recoverable acquisition timestamps. |
| **Files** | `Node_Red_JSON_20260429/docker/docker_nodered_shiftr_receiver.json`, `backups/nodered/iot_timestamp_20260430/iatf_system_nodered_flows_before_timestamp_patch.json`, `backups/iot_csv_timezone_20260430_095031/iot`, `docs/INCIDENT_LOG.md` |
| **Verification** | JSON validation passed for `docker_nodered_shiftr_receiver.json`; all 10 `Prep *` nodes contain `msg.payload = timestamp + ',' + csvValue(msg.payload)`. The active Node-RED `/flows` API also shows the same timestamp payload logic in the `docker_receiver_tab`, including the JST correction `Date.now() + 9 * 60 * 60 * 1000`. Rails parsing was verified with a two-column sample: `[["2026/04/30 09:31:00", 123], ["2026/04/30 09:32:00", 124.5]]`. Host time and Rails `Time.current` both showed `2026/04/30 09:45-09:46 +09:00` during verification. After CSV correction, `2026_04_30*Amada80t3.csv` contained `utc00=0` and `jst09=111`; each Amada CSV tail ended at `2026/04/30 09:51:36,...` during verification. |
| **Lessons Learned** | Transport bridge flows must preserve the data contract, not only move MQTT topics. Chart traceability requires timestamped CSV rows at the data acquisition/write boundary. |
| **Prevention** | Treat IoT CSV as `timestamp,value`. Keep Rails tolerant of legacy one-column files, but require new Node-RED receiver flows to emit timestamped two-column rows and validate this before import. |

## INC-063: IoT monthly press utilization summary was missing
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:05 JST |
| **Detection** | User requested a monthly page that lists each monitored press machine's operating time, operating rate, shot count, SPM, and chokotei count, with browser-adjustable planned working hours such as 7.0 or 7.5 hours per day. |
| **Impact** | The real-time IoT graph showed current series, but users could not quickly review monthly equipment performance or compare multiple machines as the monitored press count grows. |
| **Root Cause (5 Why)** | **Why1**: Monthly utilization was not visible. **Why2**: Existing Rails IoT logic only loaded today's CSV series for charts. **Why3**: There was no service that scanned monthly IoT CSV files and grouped data by machine and metric. **Why4**: The original implementation assumed fixed known series instead of using the filename contract to discover machines. **Why5**: Operating rate rules had not yet been encoded as a reusable calculation with user-adjustable working-hour assumptions. |
| **Fix** | Added `IotMonthlySummaryService` to scan `/myapp/db/record/iot/YYYY_MM_*.csv`, detect equipment from `Shot*`, `SPM*`, `Stampingchokotei*`, and `StampingJYOTAI*` filenames, and calculate monthly active days, operating hours, operating rate, shot delta, average non-zero SPM, chokotei delta, and latest timestamp. Added `ProductsController#iot_monthly`, the `/products/iot_monthly` route, and a simple self-contained monthly summary view with month and planned-hours controls. Added a link from the real-time IoT page to the monthly summary. |
| **Files** | `iatf_system/app/services/iot_monthly_summary_service.rb` lines 7, 127, 145, 168; `iatf_system/app/controllers/products_controller.rb` lines 199-203; `iatf_system/config/routes.rb` line 72; `iatf_system/app/views/products/iot_monthly.html.erb` lines 262, 271, 313, 352; `iatf_system/app/views/products/iot.html.erb`; `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c app/services/iot_monthly_summary_service.rb` and `ruby -c app/controllers/products_controller.rb` passed in `iatf_system-web-1`. `RAILS_ENV=production rails runner` for `month=2026-04` and `work_hours_per_day=8` detected `Amada80t3` with `active_days=2`, `available_hours=16.0`, `operating_hours=3.78`, `operating_rate=23.6`, `shot_count=28259`, `average_spm=125.7`, `chokotei_count=51`, and a latest timestamp in JST. Renderer verification for the monthly template returned HTML containing `iotm-title`, `Amada80t3`, and the adjustable `7.5` value. After restarting only `iatf_system-web-1`, `curl -I http://127.0.0.1:18090/products/iot_monthly?month=2026-04&work_hours_per_day=7.5` reached `ProductsController#iot_monthly` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | IoT dashboards need both current graph views and period summaries. Filename-based machine discovery is safer for expansion than hard-coding every future press machine in the controller. |
| **Prevention** | Keep the monthly summary service tied to the `timestamp,value` CSV contract and add future equipment by following the metric filename prefixes instead of changing Rails code for each new machine. |

## INC-064: IoT daily equipment matrix was missing
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:31 JST |
| **Detection** | User requested another IoT page where the user selects year and month, the horizontal axis is day, the vertical axis is equipment, and tabs switch between chokotei count, shot count, and SPM statistics including MAX, AVE, MIN, and AVE±3σ. |
| **Impact** | Users could see current graphs and monthly totals, but could not compare daily machine performance across the whole month in a scan-friendly matrix. This would become harder as the number of monitored presses increases. |
| **Root Cause (5 Why)** | **Why1**: Daily cross-machine comparison was unavailable. **Why2**: Existing Rails IoT pages were chart/current-series and monthly-total oriented. **Why3**: There was no daily matrix service that grouped CSV files by date, equipment, and metric. **Why4**: SPM statistics had not been encoded as daily max/average/min/control-band values. **Why5**: The expansion path for more equipment required a filename-driven discovery service rather than another hard-coded controller/view list. |
| **Fix** | Added `IotDailyMatrixService` to scan `/myapp/db/record/iot/YYYY_MM_DD*.csv`, detect equipment from `Shot*`, `SPM*`, and `Stampingchokotei*` filenames, build all dates in the selected month, and calculate daily chokotei delta, daily shot delta, and SPM max/average/min/average±3 sigma from non-zero SPM samples. Added `ProductsController#iot_daily_matrix`, `/products/iot_daily_matrix`, a self-contained daily matrix view with year/month selectors and CSS-only tabs, a reusable numeric matrix partial, and navigation links from the real-time and monthly IoT pages. |
| **Files** | `iatf_system/app/services/iot_daily_matrix_service.rb` lines 7, 10, 26, 117, 124; `iatf_system/app/controllers/products_controller.rb` lines 206-210; `iatf_system/config/routes.rb` line 73; `iatf_system/app/views/products/iot_daily_matrix.html.erb` lines 254, 264, 280, 298, 321, 340; `iatf_system/app/views/products/_iot_daily_matrix_number_table.html.erb`; `iatf_system/app/views/products/iot.html.erb`; `iatf_system/app/views/products/iot_monthly.html.erb`; `docs/INCIDENT_LOG.md` |
| **Verification** | `ruby -c app/services/iot_daily_matrix_service.rb` and `ruby -c app/controllers/products_controller.rb` passed in `iatf_system-web-1`. `RAILS_ENV=production rails runner` for `year=2026, month=4` detected `["Amada80t3"]`, 30 date columns, 2026-04-30 shot count `19426`, chokotei count `30`, and SPM stats `{max: 248.0, average: 125.6, min: 63.0, plus_3sigma: 160.2, minus_3sigma: 91.1}`. Renderer verification confirmed the page includes `iotd-title`, tab IDs, `Amada80t3`, and `MAX`. After restarting only `iatf_system-web-1`, `curl -I http://127.0.0.1:18090/products/iot_daily_matrix?year=2026&month=4` reached `ProductsController#iot_daily_matrix` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | Period dashboards should support both aggregate totals and daily matrix views. Statistical SPM summaries are more useful when presented in the same equipment/date matrix as counts. |
| **Prevention** | Keep daily IoT analysis filename-driven, preserve the `timestamp,value` CSV contract, and add future metrics as new service-level metric patterns before changing controller/view code. |

## INC-065: IoT real-time graph page needed business-friendly visual modernization
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 12:59 JST |
| **Detection** | User requested `http://192.168.5.172/products/iot` to be made more modern while staying simple, understated, and business-oriented, with rollback available. |
| **Impact** | The existing IoT page showed the graphs but used very wide fixed layouts, old tab styling, mojibake labels, and sparse navigation. It was harder to scan in daily business use even though the data path was functioning. |
| **Root Cause (5 Why)** | **Why1**: The page looked dated and difficult to read. **Why2**: It used a fixed `2200px` tab layout and minimal visual hierarchy. **Why3**: It had grown from an early graph test page rather than a maintained production dashboard. **Why4**: Later monthly and daily summary pages were added with clearer navigation, but the real-time graph page had not been brought up to the same standard. **Why5**: The page relied on old inline structure instead of a self-contained, rollback-friendly view refresh. |
| **Fix** | Backed up the current state to `backup/pre-iot-page-modernize-20260430`, `backups/git_worktree/pre_iot_page_modernize_20260430.diff`, and `backups/git_worktree/iot_html_erb_pre_modernize_20260430.bak`. Replaced only `iatf_system/app/views/products/iot.html.erb` with a self-contained business-style layout: restrained slate/white palette, compact header, navigation buttons to monthly and daily pages, summary tiles, CSS-only equipment tabs, and chart sections using `width: 100%`. Existing controller, services, routes, CSV logic, layout, shared partials, assets, and Docker settings were not changed for this UI refresh. |
| **Files** | `iatf_system/app/views/products/iot.html.erb` lines 213, 217-218, 251, 261-361; `docs/INCIDENT_LOG.md`; rollback backups under `backups/git_worktree/` |
| **Verification** | `RAILS_ENV=production rails runner` rendered `products/iot` with Chartkick output and produced a 64,819 character HTML fragment. File checks confirmed the new title, monthly/daily links, Amada tab, and all `line_chart` calls are present. Restarted only `iatf_system-web-1`; after startup asset processing completed, `curl -I http://127.0.0.1:18090/products/iot` reached `ProductsController#iot` and returned the expected login redirect for an unauthenticated request. |
| **Lessons Learned** | Operational dashboards need periodic UI maintenance even when data pipelines are healthy. Keeping the refresh self-contained in the view made rollback straightforward and avoided Tailwind build fragility. |
| **Prevention** | For future IoT UI changes, keep the chart data path separate from visual refreshes, preserve a per-view backup before replacing dashboards, and verify both renderer output and route reachability after restart. |

## INC-066: IATF video rendered invalid close-up frames without visual QA
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 15:50 JST |
| **Detection** | User reported that the generated IATF video showed the same grayscale close-up frame from start to finish and was unusable as training material. A sampled contact sheet confirmed six sampled frames were visually identical close-ups. |
| **Impact** | The produced MP4 was falsely treated as a completed training video although the visual content was invalid. This damaged trust and could waste review time if delivered as a finished IATF teaching asset. |
| **Root Cause (5 Why)** | **Why1**: The final video showed the same unusable image throughout. **Why2**: The Blender renderer imported GLB character assets and rendered frames even when the camera/scale produced an extreme close-up. **Why3**: The pipeline only checked that enough PNG frames existed and then composed MP4; it did not visually inspect sample frames. **Why4**: Existing-frame resume logic skipped rerendering when frame count was sufficient, so bad frames could be reused repeatedly. **Why5**: There was no mandatory AI/human visual gate between render and final MP4 composition. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py`, which samples rendered frames, writes a contact sheet, checks frame dimension consistency, visual detail, contrast, and near-identical sampled frames, and fails closed before MP4 composition. Updated `run_host.py` to call Visual QA after Blender render or existing-frame skip and before FFmpeg compose, and initialized `model = "unknown"` so final status updates do not fail on resume/error edge cases. Stopped an orphaned old `blender.exe` process. Built a replacement slide-based MP4 from the existing valid Japanese timeline/audio using `data/workspace/rebuild_iatf_video_as_slides_20260430.py` so the current deliverable is at least readable business training content instead of the invalid character close-up render. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py`; `clawstack_v2/apps/iatf_video_factory/run_host.py`; `data/workspace/rebuild_iatf_video_as_slides_20260430.py`; `data/workspace/iatf_video_visual_qa/contact_sheet_current_bad_video.jpg`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_rebuild.mp4`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for `visual_qa.py`, `run_host.py`, and `rebuild_iatf_video_as_slides_20260430.py`. Running Visual QA on the bad existing frames returned `ok=False` with `inconsistent_frame_dimensions`, `low_visual_detail`, and `sample_frames_are_nearly_identical`, proving the new gate catches this failure before MP4 composition. The slide rebuild generated 56 slides and `IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_rebuild.mp4`; `ffprobe` reported 1280x720, duration `833.2s`, and size about `9.6MB`. Preview frames at 5s, 6m, and 12m were extracted and visually inspected; the 12m frame was regenerated after fixing Japanese text wrapping so long text stays inside the card. |
| **Lessons Learned** | File existence and render completion are not quality checks. Long-running media generation must include visual inspection gates before finalization, especially when 3D camera/model assets are involved. |
| **Prevention** | Treat `visual_qa_report.json` and `contact_sheet.jpg` as mandatory artifacts for every IATF video render. Do not mark a video done unless Visual QA passes; when it fails, preserve the contact sheet and stop before FFmpeg composition. Prefer business slide rendering for IATF teaching assets unless character animation has passed a short preview QA first. |

## INC-067: IATF video generation lacked slide-first AI review gate
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 16:20 JST |
| **Detection** | After the invalid close-up video incident, user required that slides be generated first, visually checked by a capable AI model against the script, and only then allowed to proceed to video generation. |
| **Impact** | The previous pipeline could generate audio, render frames, and compose video without proving the instructional slides/storyboard were readable or script-aligned. This allowed expensive downstream work to start before the most reviewable artifact existed. |
| **Root Cause (5 Why)** | **Why1**: Video generation started before a reviewable slide/storyboard gate. **Why2**: The pipeline treated script/timeline JSON as enough structure to proceed to rendering. **Why3**: The first visual artifact was the Blender frame set, which is expensive and can fail in camera/model placement. **Why4**: There was no pre-video AI review contract requiring approval of a contact sheet and manifest. **Why5**: Cloud AI cost/data safety concerns had prevented ad hoc visual-model calls, but no fail-closed local review handoff existed. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py`, which renders a slide deck from the timeline, writes `slide_preflight/contact_sheet.jpg`, `slide_manifest.json`, and `ai_review_request.json`, verifies slide count, file existence, 1280x720 size, nonblank script text, and text SHA-256 alignment with the timeline. Updated `run_host.py` to call `slide_preflight_gate` immediately after script/timeline creation or resume and before lip sync, Blender rendering, Visual QA, or FFmpeg composition. The default mode is fail-closed: if `IATF_VIDEO_AI_REVIEW_CMD` is not configured, video generation stops before rendering. A `local_only` mode exists only for deterministic local verification and does not represent AI visual approval. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py` lines 28, 194, 215, 244; `clawstack_v2/apps/iatf_video_factory/run_host.py` lines 160, 287-288; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py clawstack_v2/apps/iatf_video_factory/run_host.py` passed. With `IATF_VIDEO_SLIDE_REVIEW_MODE=local_only`, the module generated 56 slide previews, `slide_manifest.json`, `ai_review_request.json`, and `contact_sheet.jpg`; the contact sheet was visually inspected and showed readable Japanese business slides across the sequence. With default settings and no AI reviewer command, the module failed closed with `ai_review_required_but_IATF_VIDEO_AI_REVIEW_CMD_not_set`, proving video generation will not proceed without explicit AI review approval. |
| **Lessons Learned** | The cheapest useful visual artifact should be reviewed first. A slide contact sheet is easier to inspect than a finished MP4 and catches storyboard, readability, and content-order problems before rendering. |
| **Prevention** | Keep slide preflight mandatory before every IATF video run. Do not configure cloud visual-review commands without user consent on model, data sent, and cost. Preserve `slide_preflight_result.json` as the audit evidence for each generated training video. |

## INC-068: IATF video rebuild continued with approved slide-video path
| Field | Detail |
| --- | --- |
| **Date** | 2026-04-30 16:21 JST |
| **Detection** | User reported that Claude had stopped at usage limit after being instructed to rebuild the IATF training video by generating slides first, checking them with a capable AI model, and only then starting video generation with periodic content checks. |
| **Impact** | The rebuild could have remained half-finished, and the unsafe Blender-first path could still be used in future runs after slide approval. |
| **Root Cause (5 Why)** | **Why1**: The rebuild stopped before completion. **Why2**: The previous continuation depended on an interactive agent session reaching the end. **Why3**: The video factory had a slide preflight gate but no dedicated approved-slide video composer with periodic MP4 spot checks. **Why4**: `run_host.py` still defaulted to the Blender render path after slide approval. **Why5**: There was no resumable host-side build harness that records AI slide approval, composes a slide video, and verifies sampled MP4 frames against expected slides. |
| **Fix** | Added `clawstack_v2/apps/iatf_video_factory/pipeline/slide_video_builder.py`. The builder consumes `slide_preflight/slide_manifest.json`, `timeline.json`, and `master_audio.wav`, records `ai_review_approval.json`, composes an H.264 1280x720 slide video at 30fps, and extracts 12 checkpoint frames across the finished MP4 to compare each against the expected slide hash. Updated `run_host.py` so the default render mode is now `IATF_VIDEO_RENDER_MODE=slides`; Blender only runs when explicitly requested with `IATF_VIDEO_RENDER_MODE=blender`. Fixed a Windows console logging crash by replacing an unsupported dash character in the psutil fallback log. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/pipeline/slide_video_builder.py`; `clawstack_v2/apps/iatf_video_factory/run_host.py`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ_slide_reviewed.mp4`; `data/iatf_videos/IATF 16949 内部監査資料_ 箇条10.2.4ポカヨケ/slide_preflight/video_build/slide_video_build_result.json`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile` passed for `slide_video_builder.py`, `slide_preflight.py`, `visual_qa.py`, and `run_host.py`. The reviewed slide video was generated successfully at `1280x720`, duration `849.652s`, size `16,031,789 bytes`, with video stream duration `849.633s` and `25,489` frames. The periodic MP4 spot check sampled slides 1, 6, 11, 16, 21, 26, 31, 36, 41, 46, 51, and 56; all 12 had hash distance `0` from the expected slide. The spot-check contact sheet was visually inspected and showed readable Japanese slides through the beginning, middle, and end. A full `run_host.py --pdf ...` integration run with `IATF_VIDEO_SLIDE_REVIEW_MODE=local_only` and `IATF_VIDEO_RENDER_MODE=slides` completed without Blender and logged `Slide video OK` plus `Spot check OK`. |
| **Lessons Learned** | A reliable training-video pipeline should review the storyboard artifact first, then verify the final MP4 at multiple timestamps. For static teaching material, slide-video composition is safer and cheaper than 3D character rendering until the 3D path has its own short-preview approval loop. |
| **Prevention** | Keep `IATF_VIDEO_RENDER_MODE=slides` as the default. Require explicit opt-in for Blender. Preserve `ai_review_approval.json`, `slide_video_build_result.json`, and `video_spot_check_contact_sheet.jpg` with every rebuilt IATF video. |

## INC-069: IATF video factory did not pick up normal Japanese training PDFs
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-01 11:00 JST |
| **Detection** | User clarified that slide videos are not useful for this training flow and pointed to `iatf_system/db/documents` plus `iatf_system/db/record/attachedfile.csv` as the canonical source for PDFs whose filenames start with `IATF 16949 内部監査資料`. A `run_host.py --limit 0` check had previously reported zero pending PDFs despite many matching files in `documents`. |
| **Impact** | The IATF video factory could not resume batch generation from the intended PDF source. It also defaulted toward the slide-video path added during the previous recovery, contrary to the desired non-slide training-video flow. |
| **Root Cause (5 Why)** | **Why1**: The pending queue was empty. **Why2**: `list_pending` searched for a mojibake filename prefix instead of the normal Japanese prefix. **Why3**: The pipeline did not use `attachedfile.csv`, even though it is the seed/list source for files in `documents`. **Why4**: The previous incident response optimized for a slide fallback after bad Blender frames. **Why5**: There was no smoke check comparing pending detection against `attachedfile.csv` and the host `documents` directory after the recovery change. |
| **Fix** | Updated `clawstack_v2/apps/iatf_video_factory/run_host.py` to read `attachedfile.csv` as UTF-8, select PDF rows whose normalized filename starts with `IATF 16949 内部監査資料`, resolve them against `iatf_system/db/documents`, and fall back to a normalized directory scan if the CSV is unavailable. Changed the default render mode back to `blender`, so slide preflight/video composition only runs when explicitly requested with `IATF_VIDEO_RENDER_MODE=slides`. Added quarantine-and-rerender behavior when existing rendered frames fail Visual QA, preventing bad close-up frames from being reused. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/run_host.py` lines 16, 99, 185, 335, 384; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/run_host.py clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py` passed. Import-level smoke check reported `pending_count 43` from `attachedfile.csv`/`documents`, with the first items including `IATF 16949 内部監査資料_箇条8.5.4_箇条8.5.4.1梱包工程.pdf` and `IATF 16949 内部監査資料_箇条10.2.4_ポカヨケ.pdf`. `python clawstack_v2/apps/iatf_video_factory/run_host.py --limit 0` returned `未処理PDF: 0本`, confirming limit-zero remains a non-processing safety check. |
| **Lessons Learned** | Recovery defaults must be revisited when the user rejects the fallback path. Queue detection should follow the project’s seed source (`attachedfile.csv`) rather than hard-coded filename fragments. |
| **Prevention** | Keep a lightweight pending-detection smoke check for the IATF video factory that compares `attachedfile.csv` against `iatf_system/db/documents` before long-running video generation. Use `IATF_VIDEO_RENDER_MODE=slides` only as an explicit opt-in. |

## INC-070: IATF check-slide gate was accidentally tied to slide-video mode
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-01 12:00 JST |
| **Detection** | User clarified that although slide videos are not desired as the deliverable, check slides are still required before video generation. The previous `run_host.py` adjustment made slide preflight run only when `IATF_VIDEO_RENDER_MODE=slides`, which would allow the default Blender path to skip the front/middle/end script-alignment review gate. |
| **Impact** | The pipeline could again enter expensive Blender rendering without first generating reviewable check slides and confirming they are visually readable and aligned with the script. This weakened the guard added after the invalid close-up video incident. |
| **Root Cause (5 Why)** | **Why1**: Check-slide generation was disabled for the default Blender path. **Why2**: The phrase "slides are not useful" was interpreted as rejecting both slide-video delivery and pre-render slide checking. **Why3**: `run_host.py` placed `slide_preflight_gate` inside the `render_mode == "slides"` branch. **Why4**: The distinction between "check slides" and "slide video output" was not encoded as separate steps. **Why5**: The immediate verification focused on queue detection and render mode default, not on preserving the pre-render AI review rule from INC-067. |
| **Fix** | Moved `slide_preflight_gate(script, timeline, video_dir, stem)` so it always runs after script/timeline creation or resume and before either slide-video composition or Blender rendering. Kept `IATF_VIDEO_RENDER_MODE=blender` as the default deliverable path, while `IATF_VIDEO_RENDER_MODE=slides` remains only an explicit slide-video output option. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/run_host.py` lines 335-340; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile clawstack_v2/apps/iatf_video_factory/run_host.py clawstack_v2/apps/iatf_video_factory/pipeline/slide_preflight.py clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py` passed. Static inspection confirmed the log line `Slide preflight: generate check slides + AI visual review gate...` appears before `render_mode` branching, so both Blender and slide-video modes require the check-slide gate. |
| **Lessons Learned** | Check artifacts and delivery artifacts must be named separately. Rejecting slide-video output does not imply rejecting storyboard/check-slide review. |
| **Prevention** | Preserve INC-067 as the canonical rule: generate check slides first, review them against the script, then proceed to whichever delivery renderer is selected. |

## INC-071: OpenCodeGo LiteLLM route returned 500 and direct API returned 403/401
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-02 15:45 JST |
| **Detection** | User asked why IATF video OpenCodeGo usage showed `LiteLLM/OpenCodeGo 未接続/500` and zero successful calls. Re-running the preflight showed host `localhost:4001` refused connections, Docker LiteLLM returned 500, and direct OpenCodeGo calls returned `403 error code: 1010`. |
| **Impact** | OpenCodeGo could not act as the primary IATF video generation/self-check model. CUT007-CUT009 PDCA continued locally, increasing Codex visual-check involvement and preventing OpenCodeGo usage/cost accounting from recording successful calls. |
| **Root Cause (5 Why)** | **Why1**: OpenCodeGo calls through LiteLLM failed with 500. **Why2**: The active LiteLLM container is not published to host port 4001, while the existing preflight default still points to `http://localhost:4001/v1`. **Why3**: Inside Docker, the mounted LiteLLM config used values this older LiteLLM path did not expand consistently, producing `missing protocol` and later authentication failures. **Why4**: The `env_variables` section then overwrote the real process `OPENCODE_GO_API_KEY` with the literal string `os.environ/OPENCODE_GO_API_KEY`, so Docker-level env inspection looked correct while the LiteLLM process used an invalid key. **Why5**: OpenCodeGo also rejects the default Python User-Agent and does not accept LiteLLM's `openai/` model prefix or internal `-ModelID-` suffix, so the route needed provider-specific normalization. |
| **Fix** | Updated OpenCodeGo entries in `data/state/litellm_config.yaml` to use explicit OpenCodeGo base URLs and provider-prefixed LiteLLM model IDs, then removed the OpenCodeGo `env_variables` overrides that corrupted the process key. Updated `data/state/litellm_entrypoint.sh` so OpenCodeGo requests bypass the old LiteLLM router client cache, resolve the key from real environment variables, send `User-Agent: OpenCode/1.0`, strip LiteLLM-only model prefixes/suffixes, and remove proxy-only request fields before posting upstream. Recreated only `clawstack-unified-litellm-1`; other Docker services were not restarted. |
| **Files** | `data/state/litellm_config.yaml`; `data/state/litellm_entrypoint.sh`; `docker-compose.yml` (OpenCodeGo env passthrough added earlier in this incident); `.env` (OpenCodeGo alias variables added earlier in this incident); `docs/INCIDENT_LOG.md` |
| **Verification** | Docker LiteLLM was force-recreated so `.env` was re-read. Hash-only checks confirmed the container-level OpenCodeGo env values were present without exposing the secret. Direct OpenCodeGo chat completion from inside the container returned HTTP 200. Final LiteLLM proxy request to `model=opencode-go/deepseek-v4-flash` also returned HTTP 200 with `model=deepseek-v4-flash`, `content=OK`, and usage `prompt_tokens=87`, `completion_tokens=27`, `total_tokens=114`. |
| **Lessons Learned** | Preflight checks must validate both the currently active endpoint and the provider upstream. A historical successful status file is not enough when LiteLLM port exposure, mounted config, or provider credentials drift. |
| **Prevention** | Update IATF OpenCodeGo preflight to prefer the live Docker-internal LiteLLM endpoint when host port 4001 is unavailable, report local routing errors separately from provider-side denials, and never count failed/blocked calls as successful usage cost. |

## INC-072: IATF video generation lacked a mandatory live OpenCodeGo preflight gate
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-02 22:44 JST |
| **Detection** | User asked whether IATF video generation success rate would improve and requested the proposed OpenCodeGo preflight guard be added. |
| **Impact** | The IATF video flow could start PDF/script/slide/video work even when OpenCodeGo routing was stale, unavailable, or silently falling back. This increased the chance of wasted render cycles and manual Codex review. |
| **Root Cause (5 Why)** | **Why1**: The main IATF video runner did not call a live OpenCodeGo connectivity check before generation. **Why2**: Existing OpenCodeGo status files were observational and not a blocking gate. **Why3**: The existing preflight script checked several routes but was not wired into `run_host.py`. **Why4**: Host-side LiteLLM ports can be unavailable even when Docker-internal LiteLLM works, so a host runner also needs direct OpenCodeGo validation. **Why5**: Direct OpenCodeGo checks require the provider-compatible `User-Agent`, which was missing from the script generator direct fallback. |
| **Fix** | Added `opencode_go_preflight_gate()` to `clawstack_v2/apps/iatf_video_factory/run_host.py` and call it at `[0/6]` before PDF extraction, script generation, slide preflight, Blender, or MP4 composition. Strengthened `data/workspace/iatf_opencode_go_preflight.py` with direct-only mode, provider User-Agent, reasoning-content acceptance, compact one-model default, and JSON status output. Added the same OpenCodeGo User-Agent to `pipeline/script_generator.py` direct fallback. |
| **Files** | `clawstack_v2/apps/iatf_video_factory/run_host.py`; `clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py`; `data/workspace/iatf_opencode_go_preflight.py`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/iatf_opencode_go_preflight.py clawstack_v2/apps/iatf_video_factory/run_host.py clawstack_v2/apps/iatf_video_factory/pipeline/script_generator.py` passed. `python data/workspace/iatf_opencode_go_preflight.py --direct-only --timeout 45` returned `ok=true` with `usable_routes=["direct:deepseek-v4-flash"]`. Direct invocation of `run_host.opencode_go_preflight_gate()` returned `ok True` and wrote `opencode_go_preflight_status.json` before any video rendering. |
| **Lessons Learned** | A generation pipeline should gate on the exact route available to that runner, not only on a Docker-internal success or historical status file. Fast one-model checks are enough for a blocking gate; broader multi-model checks should be optional. |
| **Prevention** | Keep `IATF_VIDEO_OPENCODE_PREFLIGHT=1` as the default. Use `IATF_VIDEO_OPENCODE_REQUIRE_LITELLM=1` only when the host LiteLLM port is intentionally published and must be validated. |

## INC-073: Email Blacklist Hub config deletion and API freeze due to DB lock and atomic write failure
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-03 06:40 JST |
| **Detection** | User reported missing Blacklist card on Portal and failure to add "PURCHASE ORDER" pattern. Investigation found `email_rag_sender_filters.json` was 0 bytes or missing, and API was unresponsive. |
| **Impact** | Email filtering was non-functional; sensitive internal or noise patterns were not being filtered. API calls to update or read the blacklist hung indefinitely. |
| **Root Cause (5 Why)** | **Why1**: Configuration files were overwritten directly via `Path.write_text()`. **Why2**: System stress or process termination during I/O caused 0-byte file corruption. **Why3**: The API lacked SQLite connection timeouts. **Why4**: Long-running background DB tasks (backfill) held exclusive locks. **Why5**: The API process entered an unrecoverable deadlock waiting for the DB and reading a corrupted config. |
| **Fix** | Created `file_utils.py` for atomic JSON writes using `tempfile` + `os.replace`. Refactored `email_blacklist_hub_api.py` to use safe loading with backup fallbacks and implemented `sqlite3` connection timeouts (10s). Terminated frozen processes and restarted with PID cleanup. |
| **Files** | `data/workspace/file_utils.py` [NEW]; `data/workspace/email_blacklist_hub_api.py`; `docs/INCIDENT_LOG.md` |
| **Verification** | Verified `email_rag_sender_filters.json` contains "PURCHASE ORDER". Confirmed API endpoint `http://127.0.0.1:8791` returns 200 OK with correct config. Status file `email_blacklist_hub_status.json` is updating correctly. |
| **Lessons Learned** | Critical configuration must always use atomic write patterns to prevent truncation. Database-backed APIs must have explicit lock timeouts to avoid service deadlocks during maintenance. |
| **Prevention** | Standardize `file_utils.py` for all JSON persistence in the workspace. Monitor API status files for staleness. |

## INC-074: Turso Cloud backup failure and Nightly Report error due to path mismatch and script disappearance
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-03 07:10 JST |
| **Detection** | User asked if Turso backup was successful. Investigation of `email_rag_ingest_runtime_status.json` showed Phase 4 (Backfill) timeout and Phase 6 (Turso) error. |
| **Impact** | Nightly knowledge accumulation in Turso Cloud was skipped. Gmail Todo reports failed to send because the Node.js mailer script was missing. |
| **Root Cause (5 Why)** | **Why1**: `MULTICAD_PYTHON` was hardcoded to a Windows path (`Scripts/python.exe`), causing failure in Linux Docker. **Why2**: `run_priority_gmail_backfill.py` defaulted to 2019-01-01, attempting 7 years of history and exceeding the 1.5h timeout. **Why3**: `scripts/send_allowed_gmail_from_b64.js` was missing from the workspace. **Why4**: Recent structural reorganization or maintenance cleanup (Janitor) may have accidentally removed the `scripts` folder. |
| **Fix** | Updated `run_email_rag_ingest_report.py` with OS-aware venv path detection and explicit `--start-date 2026-01-01` for the backfill command. Recreated `data/workspace/scripts/send_allowed_gmail_from_b64.js` with a robust, standalone OAuth2 Gmail implementation. |
| **Files** | `data/workspace/run_email_rag_ingest_report.py`; `data/workspace/scripts/send_allowed_gmail_from_b64.js` [NEW]; `docs/INCIDENT_LOG.md` |
| **Verification** | `python get_turso_metrics.py` (via multicad venv) confirmed cloud records are still at 2026-05-01. Manual run of the report script path logic verified correct Linux/Windows path resolution. The recreated Node.js script correctly decodes Base64 inputs. |
| **Lessons Learned** | Shared scripts running in mixed environments (Host/Docker) must be OS-aware. Critical external script dependencies should be protected from "janitor" cleanup or structured for auto-regeneration. |
| **Prevention** | Add `scripts` folder to the protected list in janitor/maintenance protocols. Use explicit start dates for all nightly batch tasks. |

## INC-075: Integration of Instagram Honki (Manus Connector) for automated SNS strategy
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-03 07:45 JST |
| **Detection** | User provided `OpenClaw_Manus_Instagram_Honki_V1.zip` for Instagram strategy and integration. |
| **Impact** | Enhances Clawstack with a dedicated Instagram monetization and quality assurance pipeline. Provides structured competitor analysis and content validation. |
| **Root Cause (Adoption)** | The package provides high-value prompts and scripts for manufacturing-focused AI content on Instagram. Adoption was requested to formalize SNS presence. |
| **Fix** | Performed full file scan and script audit (Brawn/Codex). Confirmed no destructive commands or port conflicts. Executed `ADOPT_PARTIAL` decision: deployed strategy, prompts, and validators to `apps/manus_instagram_connector/`. Created `final_decision_report_20260503.md`. |
| **Files** | `data/workspace/apps/manus_instagram_connector/` [NEW]; `docs/INCIDENT_LOG.md` |
| **Verification** | `safe_run_checklist.py` returned OK. `audit_clawstack_readonly.ps1` logic verified as non-destructive. Portal card proposed for future UI integration. |
| **Lessons Learned** | High-value external packages should undergo a formal adoption review (Adoption Assessment) before integration. "Partial Adopt" is a safe bridge for beta-stage tools. |
| **Prevention** | Maintain the mandatory ZIP audit protocol for all external system extensions. Use "proposal_only" status for UI cards until full validation. |

## INC-076: Adoption of AI IE CostDown Complete Kit (Spaghetti Analysis)
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-03 09:47 JST |
| **Detection** | User provided `ai_ie_costdown_complete_kit_v4_spaghetti.zip` for movement and waste analysis. |
| **Impact** | Expands Clawstack with Spaghetti diagram generation, zone dwell time analysis, and automated waste pattern detection (A-B-A travel). Complements existing motion study tools. |
| **Root Cause (Adoption)** | High-quality Industrial Engineering (IE) toolset identified as a missing capability for macro-motion analysis. "Merge Adapter" design allowed for safe, non-destructive integration. |
| **Fix** | Performed full file scan and script audit (Brawn/Codex). Confirmed non-destructive data processing and Streamlit-based GUI compatibility. Executed `ADOPT_FULL` decision: deployed all modules to `apps/ie_costdown_spaghetti/`. Created `final_decision_report_ie_costdown_20260503.md`. |
| **Files** | `data/workspace/apps/ie_costdown_spaghetti/` [NEW]; `docs/INCIDENT_LOG.md` |
| **Verification** | `safe_run_checklist.py` (Instagram kit version adapted) logic verified safety. Internal `read_only_detect_spaghetti.py` confirmed environment compatibility. |
| **Lessons Learned** | "Merge Adapter" design is the gold standard for adding heavy analytical capabilities without risking core system stability. |
| **Prevention** | Continue prioritizing packages that follow the non-destructive integration pattern. Maintain separation between macro-motion (Spaghetti) and micro-motion (Therblig) data flows. |

## INC-077: Turso Cloud sync failure and Nightly Ingest skip recovery
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-04 09:20 JST |
| **Detection** | User asked about Turso backup. Investigation showed `email_rag_ingest_runtime_status.json` had not updated since May 3rd, and Turso record count remained at 1 despite 15 local records. |
| **Impact** | Nightly knowledge accumulation in Turso Cloud was partially broken (CAD growth didn't sync) and the main RAG report was skipped. |
| **Root Cause (5 Why)** | **Why1**: `cad_self_growth_daemon.py` was running with system Python instead of the multicad venv, missing `libsql_client` or correct environment variables. **Why2**: `run_email_rag_ingest_report.py` had a `NameError` due to incomplete path resolution logic for host-side execution. **Why3**: The n8n trigger for the nightly report may have failed or was inactive in the current configuration. |
| **Fix** | Fixed `run_email_rag_ingest_report.py` path resolution logic. Restarted `cad_self_growth_daemon.py` using the correct virtual environment. Manually triggered the ingest report for backfill. |
| **Files** | `data/workspace/run_email_rag_ingest_report.py`; `docs/INCIDENT_LOG.md` |
| **Verification** | `test_turso_sync.py` confirmed "Turso Cloud DB updated successfully" when using venv. `get_turso_metrics.py` showed record count increase from 1 to 2. |
| **Lessons Learned** | Background daemons must be explicitly tied to their required virtual environments. Path resolution logic in shared scripts must be robustly tested for both Host and Container contexts. |
| **Prevention** | Add a check to `cad_self_growth_daemon.py` to verify it's running in the expected venv. Include self-test phases in nightly scripts to report environment mismatches early. |

## INC-078: Atsugi terrain buildings appeared floating after initial grounding render
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-16 JST |
| **Detection** | User visually reviewed the generated Atsugi terrain images and reported that buildings were floating above the ground. A follow-up manual visual check of `Atsugi_Terrain_Grounded_Subset_Wide.png` and `Atsugi_Terrain_Grounded_Subset_Close.png` confirmed that center-point building grounding was insufficient on sloped terrain. |
| **Impact** | The diagnostic render could mislead future 3D map work by appearing numerically aligned while still failing visually. If reused for another map, the same center-point grounding method would likely produce floating buildings on slopes or large footprints. |
| **Root Cause (5 Why)** | **Why1**: Some buildings appeared to float. **Why2**: Each building was aligned using only one terrain height around its center. **Why3**: Sloped terrain and large footprints can have several meters of Z variation between corners. **Why4**: The acceptance check relied too much on raycast metrics and not enough on visual contact review from multiple camera angles. **Why5**: The pipeline did not yet encode a reusable terrain/building FMEA gate for "center-point pass but footprint/corner visual fail." |
| **Fix** | Updated `projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` to sample each building footprint on a 5 x 5 terrain grid. The first correction used dark foundation pads, but user follow-up visual review showed remaining floating/台座感. The current correction sets building bottom Z from the lowest sampled terrain point minus `BUILDING_EMBED_DEPTH = 0.75`, disables dark foundations, and creates thin terrain-colored contact pads under each building footprint to remove visible air gaps without making a dark raised pedestal. Regenerated `Atsugi_Terrain_Grounded_Subset_Close.png`, `Atsugi_Terrain_Grounded_Subset_Wide.png`, and `atsugi_terrain_grounding_subset_report.json`. Updated `3D_PIPELINE_CURRENT_STATUS_20260515.md` with the floating correction. |
| **Files** | `projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` lines 30-38, 359-435, 895-933, 1042-1044; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/Atsugi_Terrain_Grounded_Subset_Close.png`; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/Atsugi_Terrain_Grounded_Subset_Wide.png`; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/atsugi_terrain_grounding_subset_report.json`; `3D_PIPELINE_CURRENT_STATUS_20260515.md` |
| **Verification** | `python -m py_compile projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` passed. Blender 5.1 background render completed successfully. The regenerated JSON reported `building_adjusted_count = 394`, `building_embed_depth = 0.75`, `building_foundation_enabled = false`, `building_contact_pad_enabled = true`, `raycast_hit_candidate_count = 394`, and terrain offset `[-3912.98053, -619.917969]`. Manual visual review was performed on both regenerated close and wide PNGs. Corrected images from the earlier correction were sent to Telegram as message IDs `4616` and `4617`; the latest contact-pad images were reviewed locally before backup. Commit `e0e2a09` and later corrective commits were pushed to `backup/atsugi-terrain-grounding-subset-20260516`; GitHub reported no CI status or workflow run for these commits. |
| **Lessons Learned** | For 3D terrain/building placement, a single center raycast is not an acceptance criterion. The minimum acceptable diagnostic should include footprint sampling, terrain range reporting, foundation/embedding behavior for slopes, and manual or automated screenshot review from at least close and wide angles. |
| **Prevention** | Promote the Atsugi correction into a generic 3D map intake gate: detect axis mapping, avoid naive bbox scaling, score terrain/building overlap, sample all building footprints, flag high terrain range footprints, generate foundations or require terrain pads, and block "good" status until screenshots are visually reviewed. Store the FMEA/FTA/5Why pattern in `docs/knowledge/atsugi_terrain_grounding_generic_quality_playbook_20260516.md` and ByteRover. |

## INC-079: Atsugi road layer visually intersected large right-side building
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-16 JST |
| **Detection** | User visually reviewed the road-layer render and reported that the large right-side building was not parallel with the road network and appeared to sit on top of a road. Manual review of `Atsugi_Terrain_Grounded_Subset_Wide.png` confirmed the road layer was too close to, and visually intersecting, some building footprints. |
| **Impact** | The diagnostic render could imply impossible geometry: roads drawn under or through buildings. This reduces trust in the 3D map intake pipeline and could hide source alignment differences between PLATEAU road data and imported building geometry. |
| **Root Cause (5 Why)** | **Why1**: Roads appeared under or too close to buildings. **Why2**: The first road layer rendered all selected PLATEAU `tran` polygons directly over terrain. **Why3**: The renderer did not clip road triangles against building footprints. **Why4**: Building, terrain, and road layers were validated mainly for coordinate overlap, not for inter-layer occupancy conflicts. **Why5**: The generic 3D map quality gate did not yet include road-building intersection checks. |
| **Fix** | Updated `projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` to create building XY exclusion boxes and suppress road triangles when their centroid or any vertex falls inside the exclusion box. Added `ROAD_BUILDING_CLEARANCE = 3.0` and recorded `skipped_by_building`, `building_clearance`, and top building exclusion hits in the JSON report. Regenerated close/wide PNGs and JSON. |
| **Files** | `projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` lines 58, 218-235, 357-405, 421-443; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/Atsugi_Terrain_Grounded_Subset_Close.png`; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/Atsugi_Terrain_Grounded_Subset_Wide.png`; `projects/AtsugiMechaCity/diagnostics/atsugi_terrain_grounding/atsugi_terrain_grounding_subset_report.json`; `3D_PIPELINE_CURRENT_STATUS_20260515.md` |
| **Verification** | `python -m py_compile projects/AtsugiMechaCity/place_mecha_on_atsugi_terrain.py` passed. Blender 5.1 background render completed successfully. Latest road report: `selected_polygons = 243`, `vertices = 3850`, `faces = 2986`, `skipped_by_building = 378`, `building_clearance = 3.0`, `Bldg.282 = 92` skipped triangles, `skipped_no_terrain = 0`. Manual visual review was performed on regenerated close and wide PNGs. |
| **Lessons Learned** | Adding a new map layer needs occupancy validation against already accepted layers. Coordinate conversion success is not enough; visual conflicts such as road-through-building must be part of the acceptance gate. |
| **Prevention** | Extend the Atsugi generic quality playbook with road-building intersection checks, per-layer conflict counters, and a focused diagnostic camera for the worst overlap building before treating a new PLATEAU map as first-pass acceptable. |

## INC-080: Hon-Atsugi station mecha render initially used an unposed/static model
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-16 JST |
| **Detection** | User visually reviewed the Hon-Atsugi station render and reported that the 3D model remained in a T-pose/static placement. Follow-up visual review confirmed that the model needed a real posed Mixamo-rigged source rather than the default in-scene armature pose. |
| **Impact** | The scene looked technically placed but not production-ready. A T-pose or axis-broken model undermines the intended station-scale composition and can hide pose/import regressions in future map renders. |
| **Root Cause (5 Why)** | **Why1**: The model appeared unposed. **Why2**: The station render reused the default in-scene model placement path. **Why3**: Directly importing the Mixamo preview FBX produced an unusable horizontal/axis orientation. **Why4**: Appending the full Mixamo preview blend also brought in unrelated reference armature/mesh objects, corrupting bounds and placement. **Why5**: The station render lacked a dedicated acceptance gate for pose visibility, source-object selection, and post-import axis sanity. |
| **Fix** | Updated `projects/AtsugiMechaCity/render_hon_atsugi_station_from_plateau.py` to append only the confirmed visible Mixamo preview objects (`tmpsvjdp8mbobj` and `Armature`) from `DOM_Mixamo_Walk_Preview.blend`, evaluate pose frame 34, freeze the posed evaluated mesh, and place it on the Hon-Atsugi terrain. Increased clearance and diagnostic scale so the posed model is visible among buildings. |
| **Files** | `projects/AtsugiMechaCity/render_hon_atsugi_station_from_plateau.py`; `projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/Hon_Atsugi_Station_Plateau_Mecha_Close.png`; `projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/Hon_Atsugi_Station_Plateau_Mecha_Wide.png`; `projects/AtsugiMechaCity/diagnostics/hon_atsugi_station/hon_atsugi_station_plateau_mecha_report.json`; `3D_PIPELINE_CURRENT_STATUS_20260515.md` |
| **Verification** | `python -m py_compile projects/AtsugiMechaCity/render_hon_atsugi_station_from_plateau.py` passed. Blender 5.1 background render completed successfully. The report shows `rig_type = Mixamo-rigged model frozen to posed static mesh`, `pose_frame = 34`, terrain placement Z `18.056`, and bounds max Z `70.055954`. Manual visual review confirmed the close render shows a standing, non-T-pose model. |
| **Lessons Learned** | A successful rigged import is not enough; pose, axis orientation, object filtering, and final screenshot visibility must all be checked. For static hero renders, freezing the evaluated pose can be safer than carrying animation curves into a larger map scene. |
| **Prevention** | Add a pose-visibility gate to future 3D map renders: reject T-pose silhouettes, reject horizontal/axis-broken bounds, record selected rig objects, and require close/wide screenshots where the posed model is visibly present. |

## INC-081: Atsugi realistic 3D render failures were recorded across multiple places but not yet consolidated
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-16 JST |
| **Detection** | User asked whether all failures from the recent Atsugi / Hon-Atsugi 3D render work had been recorded. Review found formal incident entries for floating buildings, road/building intersection, and T-pose issues, but the station-front realism failures, Stable Diffusion usage limits, asset licensing rules, ByteRover daily-limit failure, and quality-gate scores were scattered across reports and project notes. |
| **Impact** | Future 3D map work could repeat expensive visual iterations because the full failure pattern was not available as a single reusable playbook. A later agent might see the successful output files without understanding why previous renders were rejected by visual inspection. |
| **Root Cause (5 Why)** | **Why1**: Not all failures were production bugs in one script; some were visual-quality or process failures. **Why2**: Visual failures were recorded in render reports, Telegram messages, and quality JSON rather than one canonical incident. **Why3**: ByteRover could not persist the latest lessons because the free tier daily request limit was reached. **Why4**: The pipeline added quality gates after several iterations, so earlier failures were documented retroactively. **Why5**: The project had incident logging for operational bugs, but no consolidated 3D-render failure ledger covering geometry, realism, licensing, local-AI, and delivery constraints together. |
| **Fix** | Added `docs/knowledge/atsugi_3d_render_failure_lessons_20260516.md` as the consolidated 3D render failure ledger. It links the known incidents, the latest quality report, the licensed asset-search pipeline, and the current prevention rules for future PLATEAU/OSM/Blender/OpenVINO/UE5 work. |
| **Files** | `docs/INCIDENT_LOG.md`; `docs/knowledge/atsugi_3d_render_failure_lessons_20260516.md`; related prior records: `docs/knowledge/atsugi_terrain_grounding_generic_quality_playbook_20260516.md`, `services/ai_image_gen/outputs/hon_atsugi_station_front_quality_report.json`, `projects/AtsugiMechaCity/realistic_city_pipeline/README.md`, `projects/AtsugiMechaCity/asset_search/asset_manifest.json` |
| **Verification** | Confirmed existing incident entries `INC-078`, `INC-079`, and `INC-080` cover the major geometry/pose failures. Confirmed the latest station-front quality gate records `pass_release_gate = false` with `city_density = 3`, `material_realism = 1`, `lighting = 2`, `camera = 2`, and `character_integration = 2`. Confirmed ByteRover returned the daily limit message `50/50`, so local documentation is the current durable source. Follow-up storage check recorded the same lesson to Turso `training_logs` as `Atsugi 3D render failure consolidation 2026-05-16` and to Beads as `iatf_system-a3d`. |
| **Lessons Learned** | Visual quality failures need the same traceability as code bugs. "It rendered" is not equivalent to "it is acceptable"; each rejection reason should become a reusable gate or checklist item. |
| **Prevention** | Keep the consolidated 3D failure ledger updated after each rejected visual render, run the quality gate before sending final images, and use local documentation as fallback whenever ByteRover cannot curate the memory. |

## INC-082: OpenClaw Chat latency resolved by switching primary model to OpenCodeGO DeepSeek-v4-Flash, resolving SSRF block, and fixing .env syntax
| Field | Detail |
| --- | --- |
| **Date** | 2026-05-18 JST |
| **Detection** | User reported that the OpenClaw Chat panel is taking way too long to respond. Subsequently, user requested switching from Google Gemini 2.5 Flash to OpenCodeGO DeepSeek-v4-Flash. However, chat still remained slow after switching to DeepSeek. |
| **Impact** | Chat UI had high latency or fell back to Gemini because outbound requests to `http://litellm:4000/v1` were silently blocked by the gateway's Server-Side Request Forgery (SSRF) protection policy. |
| **Root Cause (5 Why)** | **Why1**: DeepSeek chat requests failed and fell back. **Why2**: OpenClaw gateway threw `SsrFBlockedError: resolves to private/internal/special-use IP address` when hitting LiteLLM. **Why3**: The hostname `"litellm"` was not registered in OpenClaw's `ssrfPolicy.allowedHostnames`. **Why4**: LiteLLM runs as a private container service inside the Docker bridge network. **Why5**: The openclaw.json `ssrfPolicy` restricted outbound connections to a hardcoded whitelist that omitted new local services. |
| **Fix** | 1. Added `"litellm"` to `browser.ssrfPolicy.allowedHostnames` in `openclaw.json`. 2. Added `"apiKey": "local-dev-key"` under `models.providers.openai` to satisfy LiteLLM authorization. 3. Corrected `.env` space-containing key names. 4. Restarted the gateway container. |
| **Files** | `data/state/openclaw.json`, `.env`, `docs/INCIDENT_LOG.md` |
| **Verification** | Verified container startup. Gateway logs confirm the `SsrFBlockedError` has resolved. Direct chat requests to `openai/opencode-go/deepseek-v4-flash` are successfully allowed by the SSRF filter, authorized by LiteLLM, and return reasoning and chat outputs within 1.6 seconds. |
| **Lessons Learned** | When integrating internal services inside a Docker network, ensure their hostnames are whitelisted in the application's SSRF and CORS policies. Silent failover behaviors in chat backends must be monitored via live logs. |
| **Prevention** | Keep `"litellm"` whitelisted under `allowedHostnames`. Maintain the OpenAI provider key. |

## INC-086: P009 cost reports and self-growth freshness were implemented but not continuously scheduled

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | User asked whether P009 and P015 were still on hold and pointed out that `agent_self_growth_memory_hygiene` had not updated since 2026-05-05 and the PDCA scoring loop had no recent evidence. Local checks showed P009 status was active but last generated at 2026-05-17, and no Windows Scheduled Task existed for P009/self-growth refresh. |
| **Impact** | P009 could silently become stale, and self-growth could appear healthy from an old status file while the process was no longer running. This weakened the intended 24-hour improvement loop. |
| **Root Cause (5 Why)** | **Why1**: P009 and self-growth reports stopped updating. **Why2**: They had scripts and status files, but not a durable scheduler/repair loop for the host runtime. **Why3**: `start_minipc_balanced_stack.ps1` could start self-growth hygiene, but the dedicated scheduled tasks were missing. **Why4**: `auto_repair_allowed.py` did not treat stale P009/self-growth/PDCA status as repairable rules. **Why5**: The promise table was updated with implementation notes, but the operational freshness gate was not promoted into the central harness. |
| **Fix** | Added scheduled task installer `scripts/install_p009_self_growth_schedules.ps1` for P009, self-growth hygiene, PDCA refresh, and bounded auto-repair. Added a no-admin fallback watchdog via `data/workspace/p009_self_growth_watchdog.py` and `scripts/start_p009_self_growth_watchdog.ps1`. Added `scripts/run_pdca_feedback_refresh.ps1`. Updated `scripts/run_api_cost_report.ps1` for UTF-8 output and explicit exit propagation. Extended `data/workspace/auto_repair_allowed.py` with P009 stale detection, self-growth hygiene process/status detection, and PDCA refresh detection. The new P009/self-growth/PDCA repair path records diagnosis, countermeasure, command result, and post-repair verification for each attempt instead of blindly rerunning the same command. Added these steps to `scripts/start_minipc_balanced_stack.ps1`. Updated `data/workspace/PROMISES.md` with the 2026-05-20 hardening note. |
| **Verification** | Ran PowerShell/Python syntax checks. Windows Scheduled Task registration returned `Access is denied`, so the fallback watchdog started successfully. Ran one watchdog cycle and verified `p009_self_growth_watchdog_status.json` is healthy, P009 regenerated at 2026-05-20 10:39 JST, PDCA status refreshed at 2026-05-20 10:39 JST, `agent_self_growth_memory_hygiene.py` is running, and `auto_repair_allowed.py` reports P009/self-growth/PDCA rules as healthy. |
| **Lessons Learned** | A status file marked healthy is not proof of a living growth loop. Long-lived promises need both a scheduler and an auto-repair freshness rule. P015 must mean diagnosis -> countermeasure -> verification, not blind repetition. |
| **Prevention** | Prefer Windows Scheduled Tasks when available, but keep `p009_self_growth_watchdog.py` as the no-admin fallback. Include P009/self-growth/PDCA in balanced startup, and keep `auto_repair_allowed.py` as the bounded repair path when freshness checks become stale. |

---

## INC-087: ByteRover memories were not protected against local PC loss

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | User asked whether ByteRover Markdown memories remain in Turso or GitHub and raised concern that a mini-PC crash could lose them. Investigation showed `.brv/` is ignored by Git, ByteRover Space is not connected, and no confirmed Turso mirror exists for `.brv/context-tree/*.md`. |
| **Impact** | Important operational lessons saved only under `.brv/context-tree/` could be lost if the local PC storage fails before a separate backup is made. |
| **Root Cause (5 Why)** | **Why1**: ByteRover memories were local-only. **Why2**: `.brv/` is intentionally ignored by Git to avoid noisy internal state and possible sensitive context. **Why3**: The existing safe fallback wrote to `.brv/context-tree/infrastructure/byterover_repair/safe_curate_fallback.md`, which is also ignored. **Why4**: There was no Git-tracked Markdown mirror for high-value curate contexts. **Why5**: Obsidian/Turso/GitHub roles had not been separated into recovery backup, human reading, and search/index layers. |
| **Fix** | Extended `scripts/brv_safe_curate.ps1` with `-MirrorPath`, defaulting to `docs/knowledge/byterover_memory_backup.md`. The wrapper now writes a Git-tracked Markdown mirror on successful, failed, or timed-out curation attempts while preserving the original `.brv` fallback behavior for failures. |
| **Files** | `scripts/brv_safe_curate.ps1`; `docs/knowledge/byterover_memory_backup.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | Confirmed `docs/knowledge/byterover_memory_backup.md` is not ignored by Git. Ran `scripts/brv_safe_curate.ps1` with a small verification context; `brv curate` completed and the wrapper appended `mirror_written=docs/knowledge/byterover_memory_backup.md` with exit code 0. During verification, the first implementation incorrectly treated a completed stream as failure when the CLI exit code was non-zero; the wrapper was corrected to prefer explicit `"event":"completed"` / `"status":"completed"` before fallback handling. |
| **Lessons Learned** | A local AI memory is not a durable backup unless it lands in a Git-tracked or externally synced location. Successful `curate` streams should be detected from their structured events, not only process exit code. |
| **Prevention** | Use `scripts/brv_safe_curate.ps1` for important memories. Keep GitHub as the primary recovery path, Obsidian as an optional human-readable vault, and Turso/Qdrant as search or scoring indexes rather than the only source of truth. |

---

## INC-088: CI Fast workflow lint failed because the workflow file contained a malformed step and control characters

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | User reported that `CI Fast / GitHub Actions Workflow 検査` failed while Python, YAML, and Markdown checks passed. Local inspection of `.github/workflows/ci-fast.yml` found a malformed `actionlint` step at line 129 where `name` and `run` were collapsed onto one line. Local `actionlint` also reported that the workflow could not be parsed because control characters were present. |
| **Impact** | Every push could show a failed workflow lint job even when unrelated code changes were valid. This made CI look abandoned and weakened trust in the self-healing promise. |
| **Root Cause (5 Why)** | **Why1**: Workflow lint failed. **Why2**: `ci-fast.yml` had an invalid step line and hidden control characters. **Why3**: Mojibake text in comments/job labels introduced C1 control characters such as `U+0080`. **Why4**: The file had been allowed to keep non-ASCII garbled text in a CI control file. **Why5**: The workflow itself was not locally actionlint-verified before push, so CI became the first parser to catch it. |
| **Fix** | Rewrote `.github/workflows/ci-fast.yml` with ASCII-only job names, comments, and log messages while preserving the same Python, YAML, workflow, and Markdown check behavior. Split the malformed `actionlint` step into a valid `name` plus `run` block. |
| **Files** | `.github/workflows/ci-fast.yml`; `docs/INCIDENT_LOG.md` |
| **Verification** | Confirmed zero disallowed control characters in `.github/workflows/ci-fast.yml`. Downloaded `actionlint` v1.7.12 for Windows and ran it against all `.github/workflows/*.yml`; it exited successfully. Ran `git diff --check` for the workflow file successfully. |
| **Lessons Learned** | CI workflow files should be boring ASCII. Garbled labels and comments are not cosmetic when they can introduce parser-level control characters. |
| **Prevention** | Run local actionlint before pushing workflow changes. Keep workflow control files ASCII-only unless there is a strong reason otherwise. Treat any CI failure after push as a P015 self-healing target: fetch logs, diagnose, apply a changed countermeasure, verify, and push a fix. |

---

## INC-089: CityCharacterPipeline preview video rendered frames but initially failed to produce a complete MP4

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | During photoreal/video standardization, the first preview render attempt failed in Blender with `enum "BLENDER_EEVEE_NEXT" not found`. After fixing that, Blender rendered 90 PNG frames but no MP4 file was produced, so the result was not yet a completed video. |
| **Impact** | The pipeline could report a pass while leaving only image frames, which made video delivery manual and fragile. Blender 5.1 also rejected the old `BLENDER_EEVEE_NEXT` engine name, preventing animation renders before self-repair. |
| **Root Cause (5 Why)** | **Why1**: The first animation run failed. **Why2**: `run_pipeline.py` still forced `BLENDER_EEVEE_NEXT` inside the legacy `--animate` branch. **Why3**: New render profiles were applied earlier, but the old animation override ran later and replaced the selected engine. **Why4**: The animation pipeline rendered PNG frames through `scene_builder.py`, but `run_pipeline.py` had no standard ffmpeg assembly step. **Why5**: Previous acceptance focused on Blender frame completion, not final video artifact completion. |
| **Fix** | Added `--render-profile` and `--camera-angle` as standard controls, removed the legacy `BLENDER_EEVEE_NEXT` override, and added `_assemble_animation_video()` to convert `frames/render_frame_%04d.png` into H.264 MP4 with ffmpeg after successful animation renders. Added `configs/photoreal_video.yaml` and the standard operating note `docs/knowledge/city_character_photoreal_standard_20260520.md`. |
| **Files** | `projects/CityCharacterPipeline/run_pipeline.py`; `projects/CityCharacterPipeline/configs/photoreal_video.yaml`; `docs/knowledge/city_character_photoreal_standard_20260520.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile projects/CityCharacterPipeline/run_pipeline.py` passed. YAML load check confirmed `Shibuya_RickDias_Photoreal`, 90 frames, 30 fps. Dry-run passed with `--render-profile preview --camera-angle street_low`. Blender 5.1 rendered 90 frames successfully in 614.6 seconds. `_assemble_animation_video()` produced `Shibuya_RickDias_Photoreal_walk.mp4`; `ffprobe` reported H.264, 854x480, 90 frames, 3.000 seconds, 703721 bytes. |
| **Lessons Learned** | A video pipeline is not complete until the final MP4 is created and probed. Profile logic must be applied after or instead of legacy animation defaults so later overrides do not undo the selected standard. |
| **Prevention** | Keep MP4 existence and `ffprobe` duration/frame checks in the completion criteria. Use `preview` for fast movement verification, `standard` for review, and `photoreal` for final candidates. Treat missing MP4 after frames render as a self-repair target rather than a pass. |

---

## INC-090: Email nightly risk notification was triggered by Turso metrics Python path mismatch

| Field | Detail |
|---|---|
| **Date** | 2026-05-20 JST |
| **Detection** | Risk notification reported `Email nightly reported a failed phase | step=completed currentPhase=phase8_universal_growth failedPhases=phase6_turso_metrics`. `email_rag_ingest_runtime_status.json` showed `phase6_turso_metrics` failed with return code 127: `/workspace/apps/3d_fab_forge/multicad_pipeline/.venv/bin/python: not found`. |
| **Impact** | The nightly email task list itself completed, but the report was marked error because the optional Turso metric phase failed. The growth video phase also used the Windows-only `.venv/Scripts/python.exe` path from inside Linux and could silently skip metric visualization. |
| **Root Cause (5 Why)** | **Why1**: Risk notification was raised. **Why2**: `phase6_turso_metrics` returned 127. **Why3**: The n8n/Linux container could see a Windows-style venv mounted from the host, but it did not have an executable `.venv/bin/python`. **Why4**: The path resolver checked file existence but did not reject Windows `.exe` candidates on Linux. **Why5**: Optional Turso metrics were treated like a hard nightly failure instead of a degraded enrichment when `libsql_client` is unavailable in the container runtime. |
| **Fix** | Updated `run_email_rag_ingest_report.py` to resolve a usable Python by OS and ignore `.exe` candidates on Linux. Updated `generate_growth_video.py` with the same resolver. Updated `get_turso_metrics.py` to return `status=degraded` with exit code 0 when `libsql_client` or Turso credentials are unavailable, preserving the nightly report while clearly showing that Turso metrics were not collected. |
| **Files** | `data/workspace/run_email_rag_ingest_report.py`; `data/workspace/generate_growth_video.py`; `data/workspace/get_turso_metrics.py`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile data/workspace/get_turso_metrics.py data/workspace/run_email_rag_ingest_report.py data/workspace/generate_growth_video.py` passed. In `clawstack-unified-n8n-1`, `python3 /workspace/get_turso_metrics.py` returned degraded JSON with exit code 0, and `python3 /workspace/generate_growth_video.py` skipped video generation cleanly instead of failing on a Windows path. After updating the runtime status to the repaired phase result, `risk_notification.collect_findings()` returned an empty list, so `email_nightly_failed` is cleared. |
| **Lessons Learned** | A bind-mounted Windows venv can look present from Linux while still being unusable. Cross-OS job runners must validate executable compatibility, not just path existence. Optional enrichment phases should degrade without making the core nightly report look failed. |
| **Prevention** | Keep Turso metric collection as best-effort until a Linux-compatible dependency path is provisioned inside the n8n container or the metric job is moved to a host-side scheduled task. Risk notification should continue to flag hard failures, but degraded optional metrics should be visible in the report rather than treated as a failed nightly. |

---

## INC-091: ByteRover fallback memories were preserved locally but not automatically resynced

| Field | Detail |
|---|---|
| **Date** | 2026-05-21 JST |
| **Detection** | User asked whether fallback operation means local storage first and ByteRover re-entry after quota reset, then requested an automatic resync queue to reduce memory loss risk when the free daily ByteRover limit is reached. |
| **Impact** | Failed `brv curate` calls were mirrored to Markdown, but an agent had to manually find and re-submit important entries after quota recovery. This could leave durable lessons outside ByteRover search. |
| **Root Cause (5 Why)** | **Why1**: ByteRover entries could remain local-only. **Why2**: `brv_safe_curate.ps1` wrote fallback and Git mirror records but did not create machine-readable retry work. **Why3**: The fallback Markdown format was optimized for human recovery, not idempotent queue processing. **Why4**: There was no retry script with bounded attempts, timeout control, and backoff. **Why5**: The memory durability fix in INC-087 solved loss prevention, but not automatic reintegration into ByteRover. |
| **Fix** | Extended `scripts/brv_safe_curate.ps1` with `-QueuePath`, defaulting to `docs/knowledge/byterover_curate_queue.jsonl`, and added `scripts/brv_sync_curate_queue.ps1` to retry pending JSONL entries, archive synced entries, and keep failed entries pending with `attempts`, `last_error`, and `next_attempt_after`. |
| **Files** | `scripts/brv_safe_curate.ps1`; `scripts/brv_sync_curate_queue.ps1`; `docs/INCIDENT_LOG.md` |
| **Verification** | PowerShell parsing succeeded for both scripts. A scratch queue test with the current ByteRover daily limit wrote `queue_written=scratch/brv_test_queue.jsonl`; running the sync script processed 1 item, kept it pending, incremented `attempts` to 1, and wrote a future `next_attempt_after` instead of dropping it. |
| **Lessons Learned** | Fallback storage and resync are separate controls. A human-readable mirror prevents data loss, while a JSONL queue makes recovery actionable after quota reset. |
| **Prevention** | Use `scripts/brv_safe_curate.ps1` for important memories and run `scripts/brv_sync_curate_queue.ps1` manually or from a scheduler after ByteRover quota resets. Keep retries bounded per invocation with `-MaxItems` and `-TimeoutSec`. |

---

---

## INC-094: OpenRadioss 連続 T&E デック構文不整合 — 全 trial ~1s FAIL (ERROR 21/402/1051)

| Field | Detail |
|---|---|
| **Date** | 2026-06-03 JST |
| **Detection** | K10 `k10_openradioss_continuous_te_loop.py` が `press_blanking` / `press_bending` / `press_blanking_stripper` を ~1s で FAILED。Starter/Engine ログに ERROR 21 (SHELL NEGATIVE/NULL SURFACE)、402 (PART ID 0)、1051 (BCS)、573/574 (GRNOD/IMPDISP) が連続。 |
| **Impact** | 順送金型 North Star (T019) の OpenRadioss 曲げ/打ち抜き T&E ループが物理計算に到達せず、KPI (せん断域%, スプリングバック) が更新されない。LAVIE OpenFOAM 側は別途復旧済みだが OR 側がボトルネック化。 |
| **Root Cause (5 Why)** | **Why1**: Engine/Starter が ERROR TERMINATION (~1s)。<br>**Why2**: シェル ERROR 21 + PROP 厚み 0/誤解釈 + IMPDISP パース失敗。<br>**Why3**: AI 生成 minimal deck が OpenRadioss 2024 公式 `/PROP/TYPE1` 6行形式・`/IMPDISP` 2行形式・`/SHELL/part_id` 形式に非準拠。<br>**Why4**: 厚みを `/PROP` の `Thick` ではなく `hm`(hourglass) または Y 方向ノードオフセットに入れていた。<br>**Why5**: テンプレート追加時に DBEND_44 参照・starter-only 検証・pregate 未整備。 |
| **Fix** | (1) テンプレート3種を修正: 中面メッシュ X-Z (y=0)、`/SHELL/pid` + 末尾 `0`、`/PROP/SHELL` は `hm/hf/hr` + `N Thick Ashear Ithick Iplas`、`/IMPDISP` 2行 (fct,dir,grnod + Ascale,Tstart,Tstop)、`/DEF_SHELL`、`GRNOD` id>=100。<br>(2) `cae_te_engine.py`: engine block strip、stripper IMPDISP/2 注入、BEGIN 正規化、IMPDISP 注入 regex 更新。<br>(3) `cae_self_growth_gates.py`: starter 内 `/OUTP` `/H3D` `/ANIM/ELOUT` 禁止、GRNOD/ノード id 衝突、厚みジオメトリ化検知。<br>(4) 検証: `inc094e-blank/bend/strip` すべて **NORMAL TERMINATION** (17/230/17 cycles)。 |
| **Files** | `data/cae_te_workspace/experiments/openradioss/press_*_v001/*_0000.rad`; `scripts/cae_te_engine.py`; `scripts/cae_self_growth_gates.py` |
| **Verification** | `press_blanking`: duration 1.24s, returncode 0, NORMAL TERMINATION, 17 cycles, restart `.rst` 生成。`press_bending`: 230 cycles SUCCESS。`press_blanking_stripper`: 17 cycles SUCCESS。Starter-only 単体: 0 ERROR, `press_blanking_0000_0001.rst` 275KB。 |
| **Lessons Learned** | OpenRadioss 2024 では `/PROP/SHELL` の `hm` は hourglass 係数 (0-0.05)、板厚は **`Thick` フィールド (mm)**。シェル中面は平面のみ — 板厚を Y オフセットで表現すると ERROR 21。IMPDISP は Dir=整数 (2=Y)。Engine-only block は `_0001.rad` のみ。 |
| **Prevention** | 新規 OR テンプレートは DBEND_44 形式コピー + `precheck_openradioss_case` + starter-only dry run 必須。チェックリスト: 中面平面 / Thick 行 / IMPDISP 2行 / GRNOD>=100 / エンジンblock不在。bd key `openradioss-continuous-te-inc094`。 |

### FMEA (抜粋)

| Step | Failure Mode | Effect | S | O | D | RPN | Action |
|---|---|---:|---:|---:|---:|---:|---|
| テンプレート作成 | 厚みを hm または Y ノードに設定 | ERROR 21, restart 未生成 | 8 | 6 | 3 | 144 | Thick 行 + 中面 XZ pregate |
| テンプレート作成 | `/SHELL` 旧4列+part 行形式 | ERROR 402 PART 0 | 7 | 5 | 2 | 70 | `/SHELL/pid` + elem n1-n4 |
| テンプレート作成 | `/IMPDISP` 1行混在 | Dir parse fail / punch 未適用 | 6 | 5 | 3 | 90 | 2行形式 + inject regex |
| 連続ループ | ~1s FAIL を SUCCESS 扱い | 無意味 T&E 消費 | 7 | 4 | 4 | 112 | duration_sec + NORMAL TERMINATION gate |
| 運用 | GRNOD id=ノード id | BCS 1051/573 | 6 | 3 | 2 | 36 | id>=100 強制 |

### FTA (頂事象: 連続 T&E 全 FAIL ~1s)

```
連続 T&E 全 FAIL (~1s)
├── Starter 入力エラー
│   ├── /PROP/SHELL 誤形式 (hm=厚み誤認, Istrain 余分) --> 厚み 0 / ERROR 21
│   ├── /IMPDISP 1行形式 --> parse fail (100103)
│   ├── /SHELL 旧形式 --> PART 402
│   └── /BCS 旧 node 行 --> 1051
├── メッシュ設計エラー
│   └── 板厚 Y オフセット --> ERROR 21 null surface
└── 運用ゲート欠如
    └── pregate 未実行 --> 不良 deck が loop に流入
```

### なぜなぜ分析 (6段)

1. **なぜ ~1s FAIL?** Starter/Engine が入力/要素初期化で即 ERROR TERMINATION。
2. **なぜ ERROR 21?** シェル表面積が null/negative と判定。
3. **なぜ null surface?** 板厚 0 (PROP 誤読) + 非平面中面 (Y=0/1.2 二面) の複合。
4. **なぜ PROP 誤読?** `# h` 短縮形式と `hm` 行への 1.2 設定 — 2024 では `Thick` 列が正。
5. **なぜテンプレート誤り?** LLM 慣例の簡略 deck を DBEND 非参照で投入。
6. **なぜ検知遅延?** starter-only 検証・pregate・NORMAL TERMINATION KPI が未整備。

### ロジックツリー (Goal: 順送金型 OR T&E が物理計算到達)

```
Goal: press_* trial --> NORMAL TERMINATION + KPI
├─ OR[デック品質] テンプレート OpenRadioss 2024 準拠
│  ├─ AND 中面メッシュ (単一平面)
│  ├─ AND PROP: N, Thick, Ashear, Ithick, Iplas
│  ├─ AND /SHELL/pid + winding
│  ├─ AND IMPDISP 2行 (dir=2 for Y punch)
│  └─ AND GRNOD id>=100, BCS grnod 形式
├─ OR[ゲート] precheck_openradioss_case PASS
└─ OR[実行] starter --> .rst --> engine --> duration >> 1s
```

---

## INC-093: Unreal Engine 5 Headless Render Target Export Header Mismatch (OpenEXR Payload HTTP 500 Crash)

| Field | Detail |
|---|---|
| **Date** | 2026-05-23 JST |
| **Detection** | Automated execution of `comfy_multi_controlnet_connector.py` triggered a local OpenVINO image generation container payload crash (HTTP 500) when handling imported Color, Depth, and Normal G-Buffer maps exported from UE5, despite all files carrying standard `.png` extensions. |
| **Impact** | The end-to-end photorealistic rendering pipeline failed immediately at the first frame, blocking automatic generation of both the high-res LCM outputs and the comparison sheets. |
| **Root Cause (5 Why)** | **Why1**: The local OpenVINO container returned HTTP 500 when processing image payloads.<br>**Why2**: The input base64 payload represented an invalid or unsupported image format for the image generator's internal parser.<br>**Why3**: The files exported by UE5's `export_render_target` were actually high-dynamic-range 16-bit/32-bit float OpenEXR images, despite their `.png` file names.<br>**Why4**: UE5's render target exporter ignores the file extension in the output path and always saves raw render targets in HDR OpenEXR format to prevent dynamic range truncation.<br>**Why5**: The connector script blindly trusted file extensions and did not inspect binary magic headers or normalize G-Buffer passes before sending them as base64 strings to the inference API. |
| **Fix** | Added binary magic signature validation and automatic in-flight normalization inside the connection pipeline (`comfy_multi_controlnet_connector.py`):<br>(1) Implemented `ensure_png_format()` to check the first 4 bytes of input files for the OpenEXR magic signature (`b'v/1\x01'` or `b'v/1\x02'`).<br>(2) If detected, the script runs a silent subprocess call `ffmpeg -y -i <EXR> <PNG>` to convert the 16-bit float EXR files into standard, LDR 8-bit PNG files in-place before Base64 encoding. |
| **Files** | [comfy_multi_controlnet_connector.py](file:///d:/Clawdbot_Docker_20260125/projects/AtsugiMechaCity/diagnostics/ue5_local_render/comfy_multi_controlnet_connector.py) |
| **Verification** | All G-Buffer files were successfully detected as EXRs and converted to standard PNGs on-the-fly. The pipeline executed successfully across all 3 views (`road`, `sealed`, `overview`) and 2 strengths (`0.38`, `0.45`), generating 6 high-res photorealistic outputs and all 6 comparison sheets perfectly. |
| **Lessons Learned** | Never trust file extensions across engine borders, especially with headless rendering libraries that output HDR buffers (like Unreal Engine). Always verify binary signatures (magic numbers) and implement in-flight conversion safeguards (e.g. FFmpeg) to normalize payloads before pipeline ingress. |
| **Prevention** | Standardize binary header checks (OpenEXR vs PNG/JPEG) in all future image-generation or asset pipeline connections. Ensure all headless rendering scripts convert raw buffers to web-safe standard formats before transmitting to external/local API containers. |


---

## INC-092: 本厚木駅LOD2モデル実写化における押し出しポリゴン症候群とローカルStable Diffusionによるハイブリッド肉付け手法の確立

| Field | Detail |
|---|---|
| **Date** | 2026-05-22 JST |
| **Detection** | ユーザーより本厚木LOD2（押し出し単純ポリゴン）モデルのUE5レンダリング出力が「実写とは程遠い」「CG感の脱却ができていない」との指摘を受けた。調査により、UE5のライティング（Lumen）やマテリアルの極限調整だけでは、現実世界の微細な不規則性（店舗看板、窓枠汚れ、アスファルトの濡れパッチ、電線等）＝「スケールキュー」を再現できないことが判明した（押し出しポリゴン症候群）。 |
| **Impact** | LOD2データのままで都市モデルをフォトリアルに仕上げる手法が不足しており、手作業によるLOD3/4へのアップグレードモデリングは膨大なコストが発生し、プロジェクト進行を圧迫するリスクがあった。 |
| **Root Cause (5 Why)** | **Why1**: レンダリング画像が実写に見えない。<br>**Why2**: モデルが極めて綺麗でシンプルな立方体（LOD2）で構成されており、現実の都市にあるノイズや汚れ、看板の文字などの「スケールキュー」が存在しない。<br>**Why3**: UE5のシェーダー調整だけでは直方体の輪郭を超えて有機的な微細構造を生成できない。<br>**Why4**: ローカルStable Diffusion (img2img OpenVINO LCM) を用いたハイブリッドディテール肉付けを導入したが、形状維持とディテール付与の最適なバランス（Strength）の調整手法が未確立だった。<br>**Why5**: 非同期推論および結果収集スクリプトをWindowsローカル環境で走らせる際、日本語Windowsのデフォルトエンコーディング（cp932）によって文字化けおよびスクリプトクラッシュ（P023基準違反）が発生しやすく、再現実験の効率が極めて悪かった。 |
| **Fix** | (1) UE5のパース・大域照明をベースに、ローカル SD LCM (OpenVINO) img2img を走らせてディテールを上書き合成するハイブリッドレンダリングパイプラインを構築。<br>(2) 構造維持（Strength=0.38）とディテール付与（Strength=0.45）の2つの最適キャリブレーション閾値を確立。<br>(3) `run_img2img.py` 内に P023 エンコーディング強制対策（sys.stdoutのUTF-8再構成）を挿入し、Windows環境での動作を安定化。<br>(4) `ffmpeg` の `hstack` を用いて、Road, Sealed, Overview の3つのカメラアングルを横連結したコンタクトシート（比較シート）を自動作成する処理を追加。<br>(5) 成果物の管理パスを artifacts ディレクトリおよび `radius100_compare/` に整理し、Telegram APIを介した自動通知パイプラインを統合。<br>(6) 構築されたハイブリッドノウハウを `.brv/context-tree/design/atsugi-lod2-photoreal-hybrid-pattern.md` に形式知として保存。 |
| **Files** | `D:\Clawdbot_Docker_20260125\.brv\context-tree\design\atsugi-lod2-photoreal-hybrid-pattern.md`, `C:\Users\yasu\.gemini\antigravity\brain\3d62300e-184c-4bd9-9d38-edb9a284c145\scratch\run_img2img.py`, `docs/INCIDENT_LOG.md` |
| **Verification** | 3アングル×2強度（0.38/0.45）の画像6点、および結合コンタクトシート2点（s38, s45）の生成に完全成功。成果物はすべて artifacts とローカルディレクトリに同期保存された。Telegram API（curl経由）での送信が正常に機能することを確認。ByteRoverノウハウDBへの書き出しを確認。 |
| **Lessons Learned** | 3Dモデル自体の精細度が低い（LOD2等）場合、レンダラーの極限調整だけでは限界がある。正確な3Dパースペクティブと光源環境をUE5で担保し、有機的・微細なテクスチャや看板等のディテールはAI（img2img）でブレンドする「ハイブリッド手法」が最も高い対費用効果と視覚的説得力を持つ。Windows I/Oのエンコーディング保護（P023）は、外部APIや画像連携スクリプトの全モジュールで必須である。 |
| **Prevention** | 今後、押し出しポリゴンモデルからの高速な実写化要請に対しては、このハイブリッド img2img 手法を標準手順として採用する。Strengthは 0.38 を整合性基準、0.45 をテクスチャ肉付け基準とし、検証時は必ず `ffmpeg` でコンタクトシートを作成して並行評価を行う。 |


---
# INC-110: ThinkPad SSH node needed safe 24x7 job allocation instead of manual operation

| Field | Detail |
|---|---|
| **Date** | 2026-06-10 JST |
| **Detection** | User requested that K10 assign recommended work to the Ubuntu ThinkPad and have it work 24 hours a day, 365 days a year. |
| **Impact** | The ThinkPad was reachable over SSH and had metrics collection, but K10 only had one-shot probe dispatch. Without a guarded loop, the node would remain mostly idle or require manual commands. Without guards, a future loop could overheat or assign heavy solver/render work to an unproven laptop. |
| **Root Cause (5 Why)** | **Why1**: ThinkPad had no always-on assignment loop. **Why2**: Existing `k10_thinkpad_ssh_dispatch.py` was intentionally one-shot and probe-only. **Why3**: Safety policy required SSH metrics and thermal history before real heavy jobs. **Why4**: The fleet recently had LAVIE stability incidents after long jobs, so new 24x7 work must start with guarded medium/light workloads. **Why5**: The dashboard/registry distinguished allowed and blocked work, but there was no scheduler enforcing that distinction continuously. |
| **Fix** | Added `scripts/k10_thinkpad_continuous_loop.py`, a K10-side guarded loop that collects ThinkPad SSH metrics, checks CPU/RAM/temperature thresholds from `thinkpad_node_registry.json`, dispatches only allow-listed probe/light jobs, writes status/log JSONL, and backs off after repeated failures. Added `scripts/start_k10_thinkpad_continuous_loop.ps1` to start the loop hidden and register current-user startup. Hardened existing ThinkPad SSH metrics/dispatch scripts by sending `bash -lc` as one shell-quoted remote command. |
| **Files** | `scripts/k10_thinkpad_continuous_loop.py`; `scripts/start_k10_thinkpad_continuous_loop.ps1`; `scripts/k10_thinkpad_ssh_dispatch.py`; `scripts/thinkpad_ssh_metrics.py`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts\k10_thinkpad_continuous_loop.py scripts\k10_thinkpad_ssh_dispatch.py scripts\thinkpad_ssh_metrics.py` passed. Direct `qms_iatf_probe` dispatch completed successfully. A one-cycle guarded dispatch completed and wrote `data/workspace/thinkpad_continuous_loop_status.json`. The PowerShell starter launched the hidden loop and registered `StartThinkPadContinuousLoop.vbs`. |
| **Lessons Learned** | A new always-on node should begin with guarded, observable, reversible work. The correct first production step is not maximum throughput, but an allow-listed loop with explicit thermal and RAM gates. |
| **Prevention** | Keep heavy solvers, video rendering, and unbounded downloads blocked on ThinkPad until sustained temperature history and a real worker payload prove stable. Use the loop status JSON and SSH job log for RCA if the node becomes unstable. |

---
# INC-111: LAVIE dashboard temperature showed 要LHM because the node had an old monitor agent and LHM web server was off

| Field | Detail |
|---|---|
| **Date** | 2026-06-10 JST |
| **Detection** | User reported that the Growth Dashboard showed `Lavie Node` online but `CPU Temp` as `要LHM`. K10 probe to `http://100.87.244.46:8111/metrics` returned only old fields with `cpu_temp_celsius: null`; `/diagnostics` returned 404; `http://100.87.244.46:8085/data.json` timed out. |
| **Impact** | LAVIE load and RAM were visible, but thermal routing and dashboard temperature could not be trusted. Heavy or medium jobs should not use LAVIE temperature gates until LHM HTTP and the latest monitor agent are restored. |
| **Root Cause (5 Why)** | **Why1**: Dashboard showed `要LHM` because `cpu_temp_celsius` was null. **Why2**: LAVIE monitor agent was old and did not expose `lhm_ok`, `temp_source`, or `/diagnostics`. **Why3**: LibreHardwareMonitor Remote Web Server on port 8085 was not reachable. **Why4**: Existing `lhm_setup.ps1` installed/started LHM but still required a manual GUI step to enable Remote Web Server. **Why5**: The fleet setup relied on manual LHM GUI state, which is fragile after reboot or recovery from BIOS/offline incidents. |
| **Fix** | Updated `scripts/lhm_setup.ps1` to write `%APPDATA%\LibreHardwareMonitor\LibreHardwareMonitor.config` with `IsHttpServerEnabled=true`, `MinimizeToTray=true`, and `HttpPort=8085` before restarting LHM. The repair path is to run the updated LHM setup and then rerun `setup_monitor_node.ps1` so LAVIE gets the latest agent with `/diagnostics` and LHM parsing. |
| **Files** | `scripts/lhm_setup.ps1`; `docs/INCIDENT_LOG.md` |
| **Verification** | K10 confirmed both `http://100.119.18.40:8123/lhm_setup.ps1` and `setup_monitor_node.ps1` are served. Local PowerShell parse check passed. Live LAVIE verification still requires running the repair command on the LAVIE desktop because LAVIE exec_bridge and LHM HTTP ports are currently unreachable from K10. |
| **Lessons Learned** | LHM GUI state is a hidden dependency. For fleet nodes, the setup script should write the web server config directly and restart LHM, then monitor_agent should be redeployed from K10. |
| **Prevention** | Treat `lhm_ok=false` or missing `lhm_ok` on Windows satellites as a repair condition. Do not assign thermally sensitive LAVIE jobs until `:8111/metrics` shows `lhm_ok:true` and a real `temp_source`. |

---

# INC-112: Fleet diagnostics were partially blind because old Windows monitor agents kept port 8111

| Field | Detail |
|---|---|
| **Date** | 2026-06-10 JST |
| **Detection** | User reported frequent offline events and asked whether logs were being captured sufficiently. A K10 fleet audit showed Red LAVIE and Dynabook had metrics but old or missing `/diagnostics`; K10 itself had `/diagnostics` returning 404; LAVIE timed out; Vivobook refused `:8111`. |
| **Impact** | Root-cause analysis after node offline events was unreliable on several PCs. Some nodes could show basic CPU/RAM metrics while still lacking the 24-hour node-local diagnostic log needed for power, thermal, startup, and process RCA. |
| **Root Cause (5 Why)** | **Why1**: Offline RCA lacked full node-local logs. **Why2**: Several nodes were still running old monitor_agent processes that did not expose `/diagnostics`. **Why3**: Existing setup verified only `/metrics`, so a metrics-only old agent could be treated as complete. **Why4**: On Windows, multiple Python listeners could bind to port 8111, and some old listeners were access-denied from the current user, so normal refresh could not replace them. **Why5**: The remote refresh script originally sent a long encoded command and later matched its own script name, causing command-line length failures and self-termination before a robust refresh path existed. |
| **Fix** | Added `scripts/k10_fleet_diagnostics_audit.py` to audit `/metrics` plus `/diagnostics` and write `data/workspace/fleet_diagnostics_status.json` plus a Growth Dashboard copy. Added `scripts/refresh_monitor_agent_node.ps1`, fetched from K10 by `scripts/k10_refresh_monitor_agent_via_worker.py`, so remote nodes execute a short update command. Updated `scripts/setup_monitor_node.ps1` to verify downloaded `/diagnostics`. Added fallback metrics and diagnostic port `8112` when an access-denied old `8111` listener cannot be removed. Added a Fleet Diagnostics Monitor section to the Growth Dashboard so restored nodes such as Vivobook are visible. |
| **Files** | `scripts/k10_fleet_diagnostics_audit.py`; `scripts/k10_refresh_monitor_agent_via_worker.py`; `scripts/refresh_monitor_agent_node.ps1`; `scripts/setup_monitor_node.ps1`; `data/workspace/apps/growth_dashboard/index.html`; `data/workspace/apps/growth_dashboard/fleet_diagnostics_status.json`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts\\k10_refresh_monitor_agent_via_worker.py scripts\\k10_fleet_diagnostics_audit.py` passed. PowerShell parse checks passed for `setup_monitor_node.ps1` and `refresh_monitor_agent_node.ps1`. Red LAVIE returned `/diagnostics` 200 on `:8111`. Dynabook could not kill old PID 13816 due access denied, but fallback `http://100.98.133.40:8112/diagnostics` returned 200. K10 fallback `http://127.0.0.1:8112/diagnostics` returned 200. After user reran setup on Vivobook, K10 audit showed `k10`, `red_lavie`, `dynabook`, and `vivobook` diagnostics OK; only `lavie` still needs manual check. Dashboard JS extracted from `index.html` passed `node --check`. |
| **Lessons Learned** | Basic `/metrics` is not enough to prove a node is RCA-ready. For Windows fleet nodes, a stale elevated listener can survive normal user refreshes, so the diagnostic plane needs a verified endpoint and a fallback port instead of assuming 8111 can always be reclaimed. |
| **Prevention** | Treat diagnostics absence as a failed setup even if `/metrics` works. Keep `8112` as a diagnostic fallback for nodes with unkillable old `8111` listeners. Use the fleet audit before assigning long jobs, and require manual power/startup checks for nodes where both metrics and diagnostics are unreachable. |

---

# INC-133: Robot walk thigh mesh was misidentified as knee pads, causing no visible thigh swing

| Field | Detail |
|---|---|
| **Date** | 2026-06-29 JST |
| **Detection** | User reported repeatedly that the thigh did not swing in V19/V20/V21/V23 walk outputs, then supplied `C:\Users\yasu\OneDrive\デスクトップ\太もも.jpg`. Review showed that `robot_0_part34.glb` and `robot_0_part35.glb` had been treated as thighs, but they are knee-pad / knee-cap parts. |
| **Impact** | The animation QA claimed thigh motion even though the visible upper-leg shell was not the animated object. Robot walk versions could pass numeric bone/keypoint checks while failing the user's visual ergonomic requirement: the thigh must swing around the hip joint. |
| **Root Cause (5 Why)** | **Why1**: The visible thigh did not move because the actual upper-leg mesh was not isolated as the thigh control target. **Why2**: Part labels were inferred from position and small candidate renders, so knee pads were mapped as thighs. **Why3**: QA measured skeleton/keypoint/root motion and not per-visible-mesh angular motion of the upper-leg shell. **Why4**: PartPacker output grouped pelvis and both upper-leg shells into `robot_0_part25.glb`, hiding the true thigh mesh inside a combined shell. **Why5**: The rig pipeline lacked a mandatory user-facing part identification gate before rebuilding IK/FK walk animation. |
| **Fix** | Chose the preserve-first option: do not rerun full PartPacker yet. Split existing `robot_0_part25.glb` into three exported GLBs: `Pelvis_Center`, `UpperLeg_L`, and `UpperLeg_R`, using face-center X/Z thresholds and preserving the original source output. Marked `robot_0_part34.glb` and `robot_0_part35.glb` as knee-pad candidates, not thigh candidates. |
| **Files / Artifacts** | `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\part25_split_pelvis_thighs\robot_0_part25_pelvis_center.glb`; `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\part25_split_pelvis_thighs\robot_0_part25_upperleg_l.glb`; `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\part25_split_pelvis_thighs\robot_0_part25_upperleg_r.glb`; `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\part25_split_pelvis_thighs\part25_split_report.json`; `quality_incident_report_20260629_robot_part25_thigh_misidentification_inc133.md` |
| **Verification** | Blender 5.1 export succeeded. Split report shows `Pelvis_Center` with 63,054 faces, `UpperLeg_L` with 26,137 faces, and `UpperLeg_R` with 25,929 faces. Review image `part25_split_pelvis_thighs_review.png` shows three separated objects: left upper leg, pelvis center, and right upper leg. |
| **Lessons Learned** | In segmented robot assets, a small visually leg-adjacent part can be a pad or cover, not the anatomical segment. Motion QA must confirm that the visible mesh named "thigh" rotates around the hip, not just that a nearby joint or child bone moves. |
| **Prevention** | Add a part-identification gate before V24: render isolated pelvis/thigh/shin/foot candidates with labels, require thigh mesh to be the long upper-leg shell from hip to knee, and measure per-frame upper-leg mesh axis swing. Do not call a walk "passed" until the visible thigh part swings around the hip in the rendered video. |

---

# INC-134: Robot walk V49 arm swing separated upper arm, forearm, and hand at elbow/wrist joints

| Field | Detail |
|---|---|
| **Date** | 2026-06-29 JST |
| **Detection** | User reported that when both arms swing, the upper arm separates from the elbow joint, the elbow joint separates from the forearm, and the forearm separates from the wrist/hand. |
| **Impact** | V49 was mechanically unacceptable for humanoid robot motion because arm parts moved without a visible shared hinge/parent-child relationship. |
| **Root Cause (5 Why)** | **Why1**: Upper arm, forearm, and hand were moved as independent mesh groups. **Why2**: The transform aligned abstract segment axes but did not make each child segment start from the parent end joint. **Why3**: V49 did not include a hand segment or shared wrist connector. **Why4**: Existing gates checked forward direction and foot lock, but not arm joint continuity. **Why5**: The rigging rule "anatomy first, armor second; joints require shared pivots or parent-child constraints" was not enforced automatically before delivery. |
| **Fix** | V50 added shared elbow and wrist joint-core objects, added hand source parts as a separate segment, and added `tools/check_v50_arm_chain.py` to verify shared elbow/wrist cores and hand `source_part` objects after generation. |
| **Files** | `tools/check_v50_arm_chain.py`; `docs/quality_incident_report_v49_arm_joint_separation.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | Foot lock PASS: max XY `0.000644`, max Z `0.003509`. Forward direction PASS: direction score `2.100000`. Arm chain core check PASS: elbow/wrist shared cores existed and were animated across frames `1, 36, 72, 108, 144, 180`. MP4 `robot_walk_v50_arm_chain_joint_core.mp4` was sent to Telegram with `status_code=200`, `ok=True`. |
| **Lessons Learned** | For humanoid/mecha limbs, visible armor pads cannot substitute for anatomy. Upper arm -> elbow -> forearm -> wrist -> hand must be represented as a connected chain before arm swing is increased. |
| **Prevention** | Any future humanoid walk MP4 must run a joint-continuity gate for arms as well as legs. Do not deliver if upper arm/forearm/hand are only independently posed without shared pivots, connector cores, or parent-child/bone constraints. |

---

# INC-135: V50 diagnostic motion QA MP4 failed because Blender 5.1 rejected direct FFMPEG image format

| Field | Detail |
|---|---|
| **Date** | 2026-06-30 JST |
| **Detection** | `projects/AtsugiMechaCity/v50_armature_motion_qa.py` failed in Blender 5.1 with `enum "FFMPEG" not found in ('AVIF', 'JPEG', 'OPEN_EXR', 'PNG', ...)` while generating a diagnostic MP4. |
| **Impact** | No source V50, KEEP baseline, or generated rig blend was modified. Only the diagnostic MP4 generation step failed. |
| **Root Cause (5 Why)** | **Why1**: The job failed because Blender rejected `image_settings.file_format = "FFMPEG"`. **Why2**: The script assumed direct movie output was available through that enum. **Why3**: `py_compile` cannot validate Blender runtime enum values. **Why4**: The QA pipeline needed a repeatable movie path but had only been checked with still PNG renders. **Why5**: The render pipeline did not isolate Blender rendering from video encoding. |
| **Fix** | Updated `projects/AtsugiMechaCity/v50_armature_motion_qa.py` to render PNG frames first and then call external `ffmpeg` to create MP4. If encoding fails, the script preserves the PNG frames and writes `ffmpeg_error.txt`. |
| **Files** | `projects/AtsugiMechaCity/v50_armature_motion_qa.py`; `quality_incident_report_20260630_v50_motion_qa_ffmpeg.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile projects\AtsugiMechaCity\v50_armature_motion_qa.py` passed. Blender 5.1 rendered 72 PNG frames and external `ffmpeg` encoded `projects/AtsugiMechaCity/diagnostics/v50_armature_motion_qa_fullbody_norm/v50_fullbody_normalized_motion_qa.mp4` with return code 0. Sample frames 1, 36, and 72 were visually inspected. |
| **Lessons Learned** | For Blender version drift, still-image rendering is the stable boundary. Treat MP4 encoding as a separate step so diagnostic frames survive even if codec settings change. |
| **Prevention** | Use PNG-sequence-first rendering for generated QA videos and verify the external encoder return code before treating a movie as available. |

---

# INC-136: V50 promotion loop lacked mandatory joint attachment gate before Telegram

| Field | Detail |
|---|---|
| **Date** | 2026-07-01 JST |
| **Detection** | User pointed out that robot limbs and hands had repeatedly separated at joints and that past trouble records should have been checked before starting related jobs. Local review found T033/T035 and INC-134 already required joint-continuity or joint-separation gates. |
| **Impact** | A high-score V50 candidate could still be visually invalid if shoulder, elbow, wrist, hip, knee, or ankle attachment failed. The old overnight loop could render and compare candidates without enforcing explicit joint attachment before Telegram delivery. |
| **Root Cause (5 Why)** | **Why1**: The loop promoted on motion score, local render bounds, and original compare. **Why2**: Those checks do not prove rigid limb endpoints stay attached. **Why3**: Known lessons from INC-134/T033/T035 were documented but not mandatory at job start. **Why4**: The gate was not part of the V50 promotion harness. **Why5**: The workflow treated RL improvement and media QA as enough without enforcing anatomy-first mechanical continuity. |
| **Fix** | Added fail-closed `projects/AtsugiMechaCity/v50_joint_attachment_gate.py` and integrated it into `projects/AtsugiMechaCity/rl_integration/v50_overnight_autonomy.py` before original compare and Telegram send. Added Beads task `Clawdbot_Docker_20260125-eaf`, an Obsidian mirror, and this RCA report. |
| **Files** | `projects/AtsugiMechaCity/v50_joint_attachment_gate.py`; `projects/AtsugiMechaCity/rl_integration/v50_overnight_autonomy.py`; `quality_incident_report_20260701_v50_joint_attachment_gate.md`; `data/state/Obsidian Vault/60_PC_Logs/Robot_Walk_INC-136_V50_joint_attachment_gate_20260701.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | `py_compile` passed for the modified autonomy script and gate. Running the new gate on the latest promoted candidate returned `HOLD_JOINT_DETACHMENT`: arms failed at shoulder_L/elbow_L/wrist_L/shoulder_R/elbow_R/wrist_R; legs passed at hip/knee/ankle. Telegram is now blocked unless this gate passes. |
| **Lessons Learned** | Score improvement and broad visual bounds are not physical attachment. Humanoid/mecha jobs must check prior incidents and enforce shoulder/elbow/wrist plus hip/knee/ankle continuity before delivery. |
| **Prevention** | Before any AtsugiMechaCity mecha generation, rigging, RL loop, or media delivery job, run a preflight against Beads, ByteRover, Obsidian `60_PC_Logs`, `data/workspace/memory/trouble_history.md`, and `docs/INCIDENT_LOG.md`. Do not send humanoid/mecha walk MP4s unless the joint attachment gate passes. |

---

# INC-137: Postgres WAL repair restored startup, but Paperless still needed primary-key reindex after recovery

| Field | Detail |
|---|---|
| **Date** | 2026-07-02 JST |
| **Detection** | `clawstack-unified-postgres-1` logged `PANIC: could not find redo location ... referenced by checkpoint record`, and `clawstack-unified-paperless-1` could not connect or later raised `IndexCorrupted` on `documents_paperlesstask_pkey` while starting. |
| **Impact** | Paperless startup was blocked after the WAL repair. The DB came back online, but the consumer/workers hit a corrupted primary-key index until the table was repaired. |
| **Root Cause (5 Why)** | **Why1**: Postgres could not replay a valid WAL chain after the prior crash. **Why2**: The data directory needed `pg_resetwal` to recover to a mountable state. **Why3**: Once the server booted, a corrupted `documents_paperlesstask_pkey` still caused `IndexCorrupted` during Paperless task inserts. **Why4**: The affected table had survived the crash with a damaged index structure even though the cluster itself could start. **Why5**: Crash recovery and logical index health are separate; clearing WAL does not guarantee all table indexes are valid. |
| **Fix** | Backed up `clawstack_v2\data\postgres` to `clawstack_v2\data\postgres_backup_20260702`, ran `pg_resetwal -f` against the mounted data dir, recreated the known-bad secondary indexes, then ran `REINDEX INDEX CONCURRENTLY documents_paperlesstask_pkey;` after stopping Paperless. |
| **Files** | `clawstack_v2/data/postgres`; `clawstack_v2/data/postgres_backup_20260702`; `docs/INCIDENT_LOG.md` |
| **Verification** | `docker exec clawstack-unified-postgres-1 psql -U postgres -d postgres -c \"SELECT now(), pg_is_in_recovery();\"` returned `pg_is_in_recovery = f`. `clawstack-unified-paperless-1` later returned to `healthy`, and `docker ps` showed both `paperless` and `postgres` up. |
| **Lessons Learned** | WAL recovery can resurrect the cluster without fully repairing table indexes. After a crash, expect a second pass for index health, especially on hot task tables. |
| **Prevention** | After any future WAL reset or crash recovery, check application logs for `IndexCorrupted`, then reindex only the damaged relation before re-enabling consumers. Keep the service stopped while doing the final reindex to avoid noisy concurrent inserts. |

---

# INC-138: V50 preview quality regressed because diagnostic joint locks were visible and the candidate preview was shorter than the original

| Field | Detail |
|---|---|
| **Date** | 2026-07-02 JST |
| **Detection** | Local smoke renders showed the preview candidate with visible lock spheres/cylinders in front of the robot, and the original-compare gate for the promoted walk candidate flagged the candidate as much shorter than the original V50 baseline video. |
| **Impact** | The preview looked more broken than the source V50 because diagnostic scaffolding was rendered as part of the candidate video. The compare gate also had a structural disadvantage because the candidate preview used 96 frames while the original baseline video was 180 frames. |
| **Root Cause (5 Why)** | **Why1**: Diagnostic joint locks were always created and rendered. **Why2**: The preview script did not distinguish diagnostic scaffolding from a promotion candidate. **Why3**: The render length was set to a short fixed preview window rather than matching the baseline. **Why4**: The promotion harness treated the candidate as a quick preview instead of a comparison artifact. **Why5**: The pipeline did not encode "no visual scaffolding by default" and "baseline-length parity" as defaults. |
| **Fix** | Default-disabled visible joint locks in `projects/AtsugiMechaCity/v50_final_walk_preview.py` via `--show-joint-locks`, and changed the overnight promotion render to use 180 frames at 24 fps so the candidate matches the original V50 baseline duration more closely. |
| **Files / Artifacts** | `projects/AtsugiMechaCity/v50_final_walk_preview.py`; `projects/AtsugiMechaCity/rl_integration/v50_overnight_autonomy.py`; `docs/INCIDENT_LOG.md`; `data/state/Obsidian Vault/60_PC_Logs/Robot_Walk_INC-138_V50_preview_scaffold_and_duration_20260702.md` |
| **Verification** | Blender smoke runs succeeded after the code change. The preview script rendered frames with joint locks hidden by default, and the armature builder smoke output created a full-body armature with Root, Hips, Chest, Neck, Head, both arm chains, and both leg chains. |
| **Lessons Learned** | Diagnostic scaffolding belongs in an opt-in path. For video comparison, duration parity matters as much as pose quality because short clips can fail promotion even when the motion itself is acceptable. |
| **Prevention** | Keep visible joint locks behind an explicit flag, and keep promotion renders at baseline-like duration unless a shorter diagnostic clip is intentionally requested. Re-run the original-compare gate after any render-length or scaffold change. |

---

# INC-139: V50 shoulder attachment gate failed because the torso had no visible shoulder contact surface

| Field | Detail |
|---|---|
| **Date** | 2026-07-02 JST |
| **Detection** | The updated V50 preview passed duration parity but `v50_joint_attachment_gate.py` still returned `HOLD_JOINT_DETACHMENT` for `shoulder_L` and `shoulder_R`. Visual smoke frames also showed a gap-like read between the torso shell and upper arms. |
| **Impact** | The candidate could not be promoted or sent to Telegram even though elbow, wrist, hip, knee, and ankle checks were already within tolerance. The original V50 baseline was not modified. |
| **Root Cause (5 Why)** | **Why1**: Both shoulder checks failed because the torso-side mesh was too far from the shoulder marker at rest. **Why2**: The armature had shoulder pivots, but the rendered torso mesh lacked a socket/contact surface at those pivots. **Why3**: Earlier fixes focused on bone constraints and visible diagnostic locks rather than final-render attachment surfaces. **Why4**: The left hand had no independent stable mesh, so the gate could confuse hidden proxy remnants with the visible distal forearm/hand surface. **Why5**: The V50 source inventory contains mixed armor/limb parts, so QA must distinguish rig semantics from visible contact surfaces. |
| **Fix** | Added final-render shoulder socket meshes in `projects/AtsugiMechaCity/v50_final_walk_preview.py`, hid unstable left-hand proxy fragments from the final render, excluded hidden meshes from preview camera bounds, and updated `projects/AtsugiMechaCity/v50_joint_attachment_gate.py` so shoulder sockets count as torso contact surfaces and `geometry_0.005` is used only as the visible left wrist contact surface. |
| **Files / Artifacts** | `projects/AtsugiMechaCity/v50_final_walk_preview.py`; `projects/AtsugiMechaCity/v50_joint_attachment_gate.py`; `scratch/v50_preview_shoulder_socket_180/v50_joint_attachment_gate_report.json`; `scratch/v50_preview_shoulder_socket_180/v50_original_compare_gate_report.json` |
| **Verification** | `py_compile` passed for the preview and gate scripts. A 24-frame smoke preview rendered successfully. The 180-frame candidate rendered successfully and `v50_joint_attachment_gate.py` returned `PASS_JOINT_ATTACHMENT` with no failed joints. The original V50 compare gate returned `REVIEW_REQUIRED`, `visual_compare_score=0.887500`, no hard flags, and one soft flag: `candidate_has_more_large_disconnected_components_than_original`. Telegram delivery remained blocked. |
| **Lessons Learned** | Passing rig constraints is not enough when the visible shell lacks a contact surface. Shoulder sockets should be final-render geometry, while diagnostic locks remain opt-in. Mixed forearm/hand meshes should be documented as contact surfaces rather than silently reclassified as full hand bones. |
| **Prevention** | Keep `v50_joint_attachment_gate.py` in the promotion path before Telegram. Do not promote V50 candidates unless both joint attachment and original compare pass, or unless a human explicitly accepts a `REVIEW_REQUIRED` visual comparison. |

---

# INC-140: Moldflow VOF video delivery stopped on system Python because PyVista was only installed in the repo venv

| Field | Detail |
|---|---|
| **Date** | 2026-07-04 JST |
| **Detection** | Running `python scripts/moldflow_fill_video_telegram.py --trial-id tri-lavie-resin_fill_vof-2b7ce003 --run-dir data/cae_te_workspace/runs/tri-lavie-resin_fill_vof-2b7ce003 --fps 6` failed immediately with `ModuleNotFoundError: No module named 'pyvista'`. |
| **Impact** | The OpenFOAM VOF animation could not be built from the default interpreter, so the Moldflow-like calculation report path appeared stopped even though the run data already existed. No source case files were modified. |
| **Root Cause (5 Why)** | **Why1**: The script imported `pyvista` inside the render path and the active Python did not have it installed. **Why2**: The project keeps visualization dependencies in `.venv`, not in the system interpreter. **Why3**: The script assumed operators would remember to launch it with the repo venv. **Why4**: There was no self-healing interpreter fallback. **Why5**: The delivery path was written for a known-good environment, but the current runbook did not guard against the common "wrong Python" case. |
| **Fix** | Updated [`scripts/moldflow_fill_video_telegram.py`](/D:/Clawdbot_Docker_20260125/scripts/moldflow_fill_video_telegram.py) to detect missing `pyvista` and transparently re-run itself under `.\.venv\Scripts\python.exe` when available. |
| **Files** | [`scripts/moldflow_fill_video_telegram.py`](/D:/Clawdbot_Docker_20260125/scripts/moldflow_fill_video_telegram.py); [`docs/INCIDENT_LOG.md`](/D:/Clawdbot_Docker_20260125/docs/INCIDENT_LOG.md); [`quality_incident_report_20260704_moldflow_fill_video_telegram_pyvista_venv.md`](/D:/Clawdbot_Docker_20260125/quality_incident_report_20260704_moldflow_fill_video_telegram_pyvista_venv.md); [`data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-140_PyVista_venv_fallback_20260704.md`](/D:/Clawdbot_Docker_20260125/data/state/Obsidian%20Vault/60_PC_Logs/Moldflow_INC-140_PyVista_venv_fallback_20260704.md) |
| **Verification** | `python scripts/moldflow_fill_video_telegram.py --trial-id tri-lavie-resin_fill_vof-2b7ce003 --run-dir data/cae_te_workspace/runs/tri-lavie-resin_fill_vof-2b7ce003 --fps 6 --no-telegram` completed successfully after the fallback, rendering 3 frames and encoding `tri-lavie-resin_fill_vof-2b7ce003_fill.mp4`. A second run without `--no-telegram` returned `[telegram] sent=True`. One frame was visually inspected and confirmed to show the closed-cavity 3D alpha.polymer fill view. |
| **Lessons Learned** | Visualization and delivery scripts should fail closed, but they should also recover from a missing optional dependency when the repository already ships the correct environment. Interpreter selection is part of operational reliability. |
| **Prevention** | Keep render-and-send utilities self-contained: if they rely on repo-local visualization packages, they should automatically use the repo venv or emit a precise one-line recovery hint. |

---

# INC-141: Moldflow/OpenFOAM automatic reports stopped because LAVIE services were down and the scheduled task had an invalid launch action

| Field | Detail |
|---|---|
| **Date** | 2026-07-05 JST |
| **Detection** | User reported no Telegram reports from the Moldflow/OpenFOAM app. `k10_tri_track_cae_status.json` showed `openfoam_lavie` at `SKIP_OFFLINE`, `fail_streak=45`, with `http://100.87.244.46:8111/metrics -> timed out`. Windows Task Scheduler showed `ClawstackCAETrialEngine` last result `0x80070002`. |
| **Impact** | Automatic OpenFOAM dispatch to LAVIE did not run. Telegram itself was healthy, but no new Moldflow calculation reports could be generated from the normal LAVIE route. |
| **Root Cause (5 Why)** | **Why1**: No Telegram reports arrived because no new OpenFOAM job completed on the normal route. **Why2**: `openfoam_lavie` skipped dispatch because LAVIE `monitor_agent :8111` and `job_worker :5682` timed out. **Why3**: LAVIE Tailscale ping was healthy, so the host was reachable but its CAE service plane was down. **Why4**: K10's fallback scheduled task also failed because it used `python` without a stable working directory or the `cae_te_engine.py` script argument. **Why5**: The reporting chain depended on both a remote service plane and a scheduled local fallback, but only Telegram delivery was being checked directly. |
| **Fix** | Updated [`scripts/install_cae_te_engine_schedule.ps1`](/D:/Clawdbot_Docker_20260125/scripts/install_cae_te_engine_schedule.ps1) to use the repo venv Python, pass [`scripts/cae_te_engine.py`](/D:/Clawdbot_Docker_20260125/scripts/cae_te_engine.py), set the working directory, and log through `cmd.exe /c`. Re-registered `ClawstackCAETrialEngine` as a normal user scheduled task after elevated registration was denied. Sent a Telegram status notice and ran one K10-local `resin_fill_vof` rescue calculation. |
| **Files** | [`scripts/install_cae_te_engine_schedule.ps1`](/D:/Clawdbot_Docker_20260125/scripts/install_cae_te_engine_schedule.ps1); [`docs/INCIDENT_LOG.md`](/D:/Clawdbot_Docker_20260125/docs/INCIDENT_LOG.md); [`quality_incident_report_20260705_moldflow_reports_stopped.md`](/D:/Clawdbot_Docker_20260125/quality_incident_report_20260705_moldflow_reports_stopped.md); [`data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-141_reports_stopped_20260705.md`](</D:/Clawdbot_Docker_20260125/data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-141_reports_stopped_20260705.md>) |
| **Verification** | `tailscale ping 100.87.244.46` returned 4 ms, but TCP probes to `:8111` and `:5682` timed out. Telegram text send returned `ok=True`. `ClawstackCAETrialEngine` was re-created with `cmd.exe` executing `.venv\Scripts\python.exe scripts\cae_te_engine.py`. `.\.venv\Scripts\python.exe scripts\cae_te_engine.py --category resin_fill_vof --dry-run --max-trials 1` passed. A K10-local real `resin_fill_vof` run completed as `FAILED_SHORT_SHOT` with `fill_fraction_pct=51.59`, and `scripts\moldflow_fill_video_telegram.py --trial-id OF-FILL-003-S01 ...` returned `[telegram] sent=True`. |
| **Lessons Learned** | Telegram health is not enough to prove the reporting chain. For Moldflow/OpenFOAM, the status check must include LAVIE service-plane health, K10 scheduled-task launch validity, and an actual VOF artifact send. |
| **Prevention** | Add scheduled task action checks to the CAE health preflight, keep K10 local rescue execution available, and require `:8111`, `:5682`, and task action validation before declaring the Moldflow automation healthy. |

---

# INC-145: Moldflow CAE Studio API restart briefly failed due unsupported host argument

| Field | Detail |
|---|---|
| **Date** | 2026-07-08 JST |
| **Detection** | After adding `/api/solver-landscape`, a restart command launched `scripts/moldflow_cae_studio_api.py --host 127.0.0.1 --port 8776`; endpoint validation returned connection failure. `api.err.log` showed `error: unrecognized arguments: --host 127.0.0.1`. |
| **Impact** | Moldflow CAE Studio API on `:8776` was briefly unavailable during this maintenance action. No data, Docker containers, run directories, or `.env` files were modified. |
| **Root Cause (5 Why)** | **Why1**: Endpoint check failed because the API was not running. **Why2**: The API process exited on startup. **Why3**: `argparse` rejected unsupported `--host`. **Why4**: I assumed a common host/port CLI pattern instead of checking this script's actual CLI. **Why5**: There is no restart helper that validates launch args before stopping the current API. |
| **Fix** | Restarted with `.venv\\Scripts\\python.exe scripts\\moldflow_cae_studio_api.py --port 8776` and updated `api.pid`. |
| **Files / Artifacts** | `quality_incident_report_20260708_moldflow_api_restart_arg.md`; `data/workspace/apps/moldflow_cae_studio/api.err.log`; `data/workspace/apps/moldflow_cae_studio/api.pid` |
| **Verification** | `Invoke-RestMethod http://127.0.0.1:8776/api/solver-landscape` returned schema `clawstack.moldflow_solver_landscape.v1`, `solvers=4`, `backlog=4`, latest proxy run `demo_spread_plate_pointgate_cool_const_20260708`. |
| **Lessons Learned** | Local service restarts need the same care as production restarts: validate supported CLI arguments before stopping a working process. |
| **Prevention** | Check `--help` or reuse the existing launch command before restart. Consider adding a dedicated restart script for Moldflow CAE Studio API. |

---

# INC-142: Moldflow demo run pruned historical run directories because no no-cleanup option existed

| Field | Detail |
|---|---|
| **Date** | 2026-07-08 JST |
| **Detection** | A simple Moldflow demo calculation printed many `[Cleanup] Removed old run directory: ...` lines while executing `scripts/cae_te_remote_trial.py`. |
| **Impact** | The demo calculation completed, but historical run directories under `data/cae_te_workspace/runs` were pruned by the existing CAE engine cleanup path. Source files, `.env`, Docker files, DB files, and the current demo output JSONs were not deleted. |
| **Root Cause (5 Why)** | **Why1**: Old run folders were removed because `_clean_old_runs()` is called before real solver execution. **Why2**: `cae_te_remote_trial.py` did not expose a way to suppress this cleanup for demos. **Why3**: The standard runner was used to validate real OpenFOAM integration. **Why4**: The cleanup behavior is useful for long-running automation but too invasive for ad hoc demos. **Why5**: Demo-safe execution was not encoded as a first-class runner option. |
| **Fix** | Added `--no-cleanup-runs` to `scripts/cae_te_remote_trial.py`, which sets `CAE_SKIP_RUN_CLEANUP=1`. Added a guard in `scripts/cae_te_engine.py::_clean_old_runs()` so cleanup is skipped when that environment flag is set. Added `data/workspace/tests/test_no_cleanup_runs.py` to verify both the default pruning behavior and the preservation behavior. |
| **Files** | `scripts/cae_te_remote_trial.py`; `scripts/cae_te_engine.py`; `data/workspace/tests/test_no_cleanup_runs.py`; `quality_incident_report_20260708_demo_run_cleanup_side_effect.md`; `data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-142_no_cleanup_runs_20260708.md`; `docs/INCIDENT_LOG.md` |
| **Verification** | `python -m py_compile scripts\cae_te_engine.py scripts\cae_te_remote_trial.py data\workspace\tests\test_no_cleanup_runs.py` passed. `python -m unittest data.workspace.tests.test_no_cleanup_runs -v` passed two tests. `python scripts\cae_te_remote_trial.py --help` shows `--no-cleanup-runs`. |
| **Lessons Learned** | A production cleanup policy should not be inseparable from a demonstration or investigation run. Disk protection and evidence preservation need separate switches. |
| **Prevention** | Use `--no-cleanup-runs` for future demonstrations or forensic reruns. Consider making demo launchers default to no cleanup and requiring explicit cleanup for long-running autonomous schedules. |

---

# INC-143: Moldflow fill animation hard-coded the cavity width and could imply unsupported cooling physics

| Field | Detail |
|---|---|
| **Date** | 2026-07-08 JST |
| **Detection** | User observed that the demo fill animation looked like resin advancing as a straight band rather than spreading, and noted that wall-adjacent resin should cool/solidify earlier than the flow front. Code inspection found `scripts/moldflow_fill_video_telegram.py` hard-coded a `100 x 60 x 2 mm` cavity in the renderer while the actual demo blockMesh was `100 x 10 x 2 mm`. |
| **Impact** | The rendered MP4s visually overstated the cavity width and did not clearly disclose that the current `resin_fill_vof` demo is isothermal alpha-only VOF without cooling/solidification. The OpenFOAM run data itself was not changed. |
| **Root Cause (5 Why)** | **Why1**: The visual looked physically suspicious because the renderer used a hard-coded cavity and gate geometry. **Why2**: That hard-coded fallback did not match the Phase 7 generated blockMesh. **Why3**: The renderer did not parse `blockMeshDict` or active inlet patch from the run directory. **Why4**: The demo label did not distinguish alpha-only VOF from thermo/cooling simulation. **Why5**: The animation path was optimized for a legacy PP plate case and had not been promoted to a geometry-aware renderer. |
| **Fix** | Updated `scripts/moldflow_fill_video_telegram.py` to parse `convertToMeters`, vertices, boundary faces, and the active inlet patch from `blockMeshDict` / `0/U`. Added an on-frame label: `VOF alpha only | thermal/solidification: not solved` unless a `T` field exists. Re-rendered the three demo MP4s and resent corrected videos to Telegram. |
| **Files** | `scripts/moldflow_fill_video_telegram.py`; `docs/INCIDENT_LOG.md`; `data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-143_animation_geometry_and_physics_label_20260708.md` |
| **Verification** | `python -m py_compile scripts\moldflow_fill_video_telegram.py` passed. Re-rendering `demo_simple_plate_conservative_20260708` showed the actual narrow `100 x 10 x 2 mm` cavity and the alpha-only/no-solidification label. All three corrected MP4s were regenerated and resent to Telegram with `ok=true`, message IDs 14176-14178. |
| **Lessons Learned** | Visualization can mislead even when solver output is intact. Geometry and physics labels must be derived from the actual run directory, not from legacy assumptions. Isothermal VOF demos must explicitly say that cooling and solidification are not solved. |
| **Prevention** | Keep animation geometry tied to `blockMeshDict` and active boundary conditions. For the next physics upgrade, create a thermo/cooling demo using `resin_fill_cool` or a dedicated solidification proxy rather than implying cooling behavior from alpha-only VOF. |

---

# INC-144: Point-gate Moldflow recalculation improved front shape but still failed validation; cooling CAD case exposed thermo initialization gaps

| Field | Detail |
|---|---|
| **Date** | 2026-07-08 JST |
| **Detection** | User requested recalculation after observing that resin should advance then spread laterally, and that wall-adjacent resin should cool earlier than the flow front. New point-gate VOF runs completed but reported high `alpha_max`; cooling runs failed first on stale alpha field cell count, then placeholder pressure, then `Negative initial temperature T0: -258.647`. A follow-up bounded/constant-viscosity cooling run completed without alpha overshoot. |
| **Impact** | A better diagnostic point-gate VOF animation and a thermal-field partial-fill result were produced. The thermal run is still a proxy/partial-fill demo, not a validated Moldflow-grade filling/solidification model. |
| **Root Cause (5 Why)** | **Why1**: The earlier geometry used a narrow plate and a broad center inlet, so spreading was not naturally visible. **Why2**: The point-gate case needed explicit `gate_width_mm` and width-direction mesh control. **Why3**: The alpha-only VOF setup still produced localized phase-fraction overshoot even with lower velocity and bounded-alpha settings. **Why4**: The cooling template carried mesh-size-specific initial fields and placeholders from a fixed legacy mesh. **Why5**: Thermo/cooling CAD generation had not yet been benchmarked on a widened point-gate cavity with consistent enthalpy/temperature initialization. |
| **Fix** | Added `gate_width_mm` and `mesh_ny` support in `scripts/moldflow_step_case_builder.py`; added a 100 x 40 x 2 mm point-gate sample STEP and gate spec; added `closed_cavity=false` support in `scripts/moldflow_closed_cavity.py`; added optional `bounded_alpha` run-dir stabilization; normalized cooling alpha initial fields and regenerated gate `setFieldsDict`; updated `scripts/moldflow_fill_video_telegram.py` to label vented/closed outlet mode and display the largest connected resin region. |
| **Files** | `scripts/moldflow_step_case_builder.py`; `scripts/moldflow_closed_cavity.py`; `scripts/moldflow_fill_video_telegram.py`; `data/cae_te_workspace/samples/moldflow/cavity_plate_100x40x2.step`; `data/cae_te_workspace/samples/moldflow/gate_spec_point_center_100x40x2.json`; `quality_incident_report_20260708_pointgate_cooling_recalc.md` |
| **Verification** | `py_compile` passed for the modified Python scripts. `demo_spread_plate_pointgate_vof_mid_20260708` completed with fill fraction 48.41%, fill time 0.394312 s, mass balance error 0.19%, but `alpha_max=49.012` and verdict `FAILED`. `demo_spread_plate_pointgate_cool_ready_20260708` failed with `Negative initial temperature T0: -258.647`. After setting `viscosity_model=const`, `demo_spread_plate_pointgate_cool_const_20260708` completed with fill fraction 40.09%, `alpha_max=1.0`, `T_min=333.87 K`, `T_max=511.21 K`; temperature-color MP4 was generated and sent to Telegram with `sent=True`. |
| **Lessons Learned** | A better visual front shape is not the same as solver validation. VOF visualization may need connected-region cleanup, but raw `alpha_max` must remain visible in KPI outputs. Cooling templates must not carry stale nonuniform fields into generated CAD meshes. |
| **Prevention** | Add a cooling CAD precheck for stale nonuniform field sizes and unresolved placeholders. Create a dedicated thermo benchmark before claiming wall-skin solidification behavior. Keep Telegram media blocked when the artifact is a known failed diagnostic rather than a deliverable. |

---

# INC-146: Gmail indexing repeated 401 failures because refresh only ran after stored expiry

| Field | Detail |
|---|---|
| **Date** | 2026-07-11 JST |
| **Detection** | Gmail indexing logged repeated `Gmail access token was rejected` warnings for individual message IDs, followed by one `RemoteDisconnected` warning. Read-only inspection showed that `token.json` contained both access and refresh tokens and claimed an expiry of 20:03 JST, while Gmail rejected the access token before 19:50 JST. |
| **Impact** | Affected Gmail messages were not fetched or indexed during the run. Existing indexed data, Gmail messages, Docker services, `.env`, and credentials were not deleted or rewritten. |
| **Root Cause (5 Why)** | **Why1**: Each message fetch failed because Gmail returned HTTP 401. **Why2**: `gmail_request()` converted 401 directly into an exception. **Why3**: Token refresh occurred only in `gmail_session()` when the locally stored expiry had passed. **Why4**: The design assumed an access token could not be invalidated before its stored expiry. **Why5**: There was no bounded refresh-and-replay path or regression test for early token rejection. The separate connection abort also had no bounded retry. |
| **Fix** | `data/workspace/email_search_index.py` now refreshes and replays once after 401. Idempotent GET/HEAD/OPTIONS calls retry connection errors, timeouts, 429, and selected 5xx responses with exponential backoff and a hard limit of three attempts. Non-idempotent methods retain one attempt. Added `data/workspace/tests/test_email_search_index_gmail_retry.py`. |
| **Verification** | Python compilation passed. Four focused unit tests passed in 0.003 seconds. A read-only Gmail `users/me/profile` request succeeded with `ok=True`, proving the active credential path works; no message body was printed. |
| **Lessons Learned** | Stored OAuth expiry is advisory, not proof that the provider will still accept the token. Authentication recovery and transport recovery require separate, bounded policies. |
| **Prevention** | Keep a single refresh replay for 401, cap transient retries, restrict generic retries to idempotent methods, and never log token values. No external web search was needed because local code, token metadata, HTTP status, and a live read-only API check provided direct evidence. |

---

# INC-147: Dynabook Moldflow MCP preflight used an overlong probe and assumed pytest

| Field | Detail |
|---|---|
| **Date / Detection** | 2026-07-11 JST. `Test-NetConnection` exceeded the 20-second harness limit; a later local test invocation reported `No module named pytest`. |
| **Impact** | Investigation delay only. Dynabook remained unreachable at `100.98.133.40:5683`; Moldflow was not started and no remote state changed. |
| **Root Cause (5 Why)** | Diagnostic commands and test runners were selected before verifying their bounded duration and availability. The workflow lacked a dependency-free first gate. |
| **Fix** | Switched to a five-second `.NET TcpClient` probe and standard-library `unittest`. Added a read-only, fail-closed MCP readiness bridge and isolated deployment scripts. |
| **Files** | `data/workspace/moldflow_bridge/moldflow_mcp_server.py`; `install_dynabook_mcp.ps1`; `start_moldflow_mcp.ps1`; `test_moldflow_mcp_server.py`; `quality_incident_report_20260711_moldflow_mcp_preflight.md`; Obsidian mirror. |
| **Verification** | TCP and HTTP each ended within five seconds and reported unreachable. Contract tests passed 2/2 in 0.049 seconds; Python and PowerShell syntax passed. MCP 1.28.1 initialize/list-tools returned all three readiness tools. |
| **Lessons / Prevention** | Probe availability with dependency-free bounded methods. Never equate a locally prepared package with remote readiness. Keep analysis disabled until real 32-bit Synergy COM validation passes. Web search was unnecessary because private-host state and local dependency evidence were decisive. |

---

# INC-148: Windows PID liveness bug allowed concurrent Gmail backfills and token races

| Field | Detail |
|---|---|
| **Date** | 2026-07-12 JST |
| **Detection** | Repeated Gmail 401 and connection-aborted warnings led to process inspection. Two `run_priority_gmail_backfill.py` instances were active while `email_search_ops.lock` named a different, already-dead PID. |
| **Impact** | Independent workers could access one Gmail mailbox concurrently, overwrite shared token/status JSON, retain stale access tokens, increase 401/429/network-disconnect risk, and leave one worker running without owning the DB-operation lock. Existing Gmail messages and the SQLite DB were preserved. |
| **Root Cause (5 Why)** | **Why1**: Gmail access became intermittent because multiple long-running clients shared one mailbox and token file. **Why2**: A later backfill removed a lock held by a live earlier process. **Why3**: Windows liveness used `os.kill(pid, 0)`, which was treated as a portable existence test. **Why4**: Windows requires a native process-handle check for this use. **Why5**: Tests covered stale/corrupt locks but not live Windows owners, ownership-safe release, or concurrent token refresh. |
| **Fix** | `email_db_lock.py` now uses Windows `OpenProcess`, supports dedicated lock paths, and only removes a lock when its exact owner payload still matches. `email_search_index.py` now writes JSON via temporary file plus `os.replace`, serializes token refresh with a dedicated lock, and adopts a token refreshed by another worker instead of refreshing again. |
| **Verification** | Ten focused tests passed. The unlocked orphan PID 6048 was stopped; a single logical backfill was restarted under a parent/child Python launcher pair with lock owner PID 35796. Gmail `users/me/profile` read-only request succeeded with 284047 messages. |
| **Lessons Learned** | Cross-platform PID probes are correctness and safety primitives. A DB lock does not protect token state if stale detection can delete a live owner's lock. |
| **Prevention** | Test Windows live/dead PID behavior, owner-only release, atomic JSON replacement, and bounded token refresh. Keep one logical Gmail backfill plus the incremental daemon; avoid independently launching duplicate full backfills. |

---

# INC-149: Dynabook Moldflow MCP could confirm mesh but not the existing injection gate

| Field | Detail |
|---|---|
| **Date / Detection** | 2026-07-16 JST. The read-only MCP inspector confirmed the active Fusion mesh, but returned `GATE_INSPECTION_SUPPORTED=false` after the user had set a gate in Synergy. |
| **Impact** | Gate placement could not initially be independently verified through MCP. No study, mesh, gate, material, or analysis state was changed. |
| **Root Cause (5 Why)** | **Why1**: the inspector had no gate getter. **Why2**: Moldflow 2010 exposes injection locations as NDBC records and has no direct API getter. **Why3**: guessing an unverified COM member was intentionally prohibited. **Why4**: the Autodesk-supported UDM-export workaround had not yet been implemented. **Why5**: the first bridge version covered mesh summary only. Replacing the Python file also did not replace the already-listening PID 14208. |
| **Fix** | Extended `moldflow_inspect_active_study` to export the active model to a temporary UDM, parse NDBC types 40000/40002/40003, map gate node IDs to coordinates, and delete the UDM. Replaced only the verified port-8765 owner. |
| **Verification** | `py_compile`, five unit tests, and `git diff --check` passed. Remote SHA-256 matched. Live MCP returned `READ_ONLY=true`, mesh `Completed`, 3,635 nodes, 7,278 triangles, one gate at node 2 and (-50.0000007451, 2.7391463518, 23.8075219095), cleanup error 0, no analysis, and no new Study. |
| **Lessons / Prevention** | Use the documented UDM/NDBC route, never an invented getter. Verify the live response after deployment; file-hash equality alone does not prove the running server was replaced. |

---

# INC-150: Moldflow copy-only AutoFix initially rejected the correct duplicate name

| Field | Detail |
|---|---|
| **Date / Detection** | 2026-07-16 JST. The first copy-only AutoFix trial duplicated and opened `Moldflow_study (copy 2)`, but failed closed because `StudyDoc.StudyName` returned `moldflow_study_(copy_2).sdy`. |
| **Impact** | The first repair call did not run. The original and duplicate meshes were unchanged during the failed trial. |
| **Root Cause (5 Why)** | Project item names retain spaces and parentheses, while SDY filenames normalize them to underscores. The identity gate compared only case and the `.sdy` suffix. The API behavior was not captured by the initial contract test. |
| **Fix** | Canonicalized both names by removing `.sdy` and all non-alphanumeric characters. Added an explicit `reuse_active_copy` path so the existing duplicate could be repaired without creating another copy. |
| **Verification** | Five local tests passed. Remote SHA-256 matched. The retry verified `moldflow_study_(copy_2).sdy`, executed `MeshEditor.AutoFix()` once, returned 580 removed overlaps/intersections, and saved successfully. `analysis_started=false`. |
| **Lessons / Prevention** | Treat project display names and SDY filenames as separate representations. All write tools must verify canonical identity and fail before mutation on mismatch. Remaining mesh quality is not proven because post-repair `GetMeshSummary` still timed out. |

---

# INC-151: Dynabook Moldflow MCP mesh automation crossed VPN, COM, bitness, and asynchronous-status boundaries

| Field | Detail |
|---|---|
| **Date / Detection** | 2026-07-17 JST. The user asked Codex to continue an STL-imported `Moldflow_study (copy)` through meshing and gate placement entirely through MCP. Initial health checks failed because K10 Tailscale was `NoState`; later the 8766 controller found an incompatible remote-agent API, so the verified legacy bridge at `100.98.133.40:8765/mcp` was extended instead. |
| **Impact** | MCP control was restored and a 3.0 mm Fusion mesh was started on the verified copy. Moldflow reported `MeshStatus=Running` and visible progress reached 30%. No original study, material, gate, or analysis was changed. Gate placement remains pending until the mesh completes. |
| **Root Cause (5 Why)** | Why1: MCP initially could not reach Dynabook because K10 Tailscale was not initialized. Why2: the hardened 8766 API and controller were version-misaligned, while the older 8765 bridge remained the proven operational path. Why3: restarts first used global Python without the `mcp` package and then bound only to localhost or rejected the Tailscale Host header. Why4: Synergy COM was registered only in the 64-bit registry view and a normally launched Synergy instance rejected automation; a clean 64-bit Automation session was required. Why5: `StudyDoc.MeshNow(False)` is asynchronous, but the first tool treated immediate zero elements as failure instead of preserving `Running` as an accepted intermediate state. |
| **Fix** | Added `moldflow_mesh_active_study_copy` and `moldflow_set_gate_active_study_copy`, canonical study-name gates, copy-only flags, explicit node validation, write-enable gating, bounded COM retries, and selectable VBS bitness. The two new operations use 64-bit cscript. Deployment uses the bridge virtual environment, Tailscale IP bind, SHA-256 verification, and exact process identity. |
| **Files** | `data/workspace/moldflow_bridge/moldflow_mcp_server.py`; `data/workspace/moldflow_bridge/test_moldflow_mcp_server.py`; `docs/quality_incident_report_20260717_dynabook_moldflow_mcp_mesh_gate.md`; `data/state/Obsidian Vault/60_PC_Logs/Moldflow_INC-151_MCP_mesh_gate_20260717.md`; `data/workspace/memory/trouble_history.md`; `data/workspace/memory/success_cases.md` |
| **Verification** | Seven focused unit tests passed; `py_compile` and `git diff --check` passed. Remote SHA-256 matched `9C9D55DADF10AD9A6C0ECB24A998ECC30B6CEDFF88D238594FC3851480285278`. Live MCP listed both new tools. A 64-bit COM state probe returned Version 2010, active project/study, PlotManager, and metric units. The mesh command matched `moldflow_study_(copy).sdy`, returned `MESH_NOW_ERROR=0`, and Moldflow UI progressed to 30%. |
| **Lessons / Prevention** | Verify VPN, service identity, interpreter, bind/Host policy, COM registry view, Windows session, and active-study identity as separate gates. Treat `Running` as progress, not empty-mesh failure. Do not run `check_synergy_com.vbs` during a mesh. Preserve fact vs inference: mesh start is proven; mesh completion and gate placement are not yet proven. |
| **Web knowledge** | Autodesk official documentation confirmed third-party meshes can be imported via UNV/BDF/PAT and still require Moldflow compliance checks. This informs the future external-remesh benchmark but did not alter the live in-progress mesh. |

---
## INC-152: Dynabook Moldflow MCP mesh contention and AutoFix quality gate

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-17 to 2026-07-19 JST. MCP mesh stayed Running for more than two hours; later AutoFix completed but quality remained failed. |
| Impact | Gate placement and Fill analysis could not safely proceed. Original `moldflow_study_3` remained protected. |
| Root Cause (5 Why) | Inspection exported the active UDM while `synmesh` was running; this introduced file contention. Remote MCP restarts could also detach COM from the visible Synergy session. AutoFix reduced defects but could not repair the heavily intersecting mesh. |
| Fix | Bridge 0.5.4 skips `ExportModel` while mesh is Pending/Running; active tools use 64-bit COM; exact-name SaveAs copies and fail-closed quality checks were added. |
| Verification | Copy SaveAs succeeded. AutoFix removed 174 elements. Intersections improved 1201->1052, overlaps 595->529, unoriented 96->95, but `MeshStatus=Failed`; analysis was not started. |
| Lessons | Operation success and engineering acceptance are separate. `AUTOFIX_REMOVED` is not a PASS criterion. MCP and Synergy must share the interactive Windows session. |
| Prevention | Follow `docs/knowledge/dynabook_moldflow_mcp_mesh_autofix_20260719.md`; re-import repaired STL into a fresh Fusion study and prohibit live export during mesh. |

---

## INC-153: Bunny Colony Electron dependency install exceeded the bounded timeout

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-24 JST. The first `npm install` for `games/bunny-colony` exceeded the explicit 120-second command timeout. |
| Impact | The dependency installation and Windows packaging gate were incomplete. No existing application, Docker service, or source ZIP was modified. The timed-out npm child remained alive until explicitly terminated. |
| Root Cause (5 Why) | (1) The install did not return within 120 seconds. (2) Electron/electron-builder have a comparatively large dependency and binary download graph. (3) `npm ping` measured 15.897 seconds even though the registry and cache were valid. (4) A single fixed timeout was used without separating metadata install from Electron binary acquisition. (5) The preflight checked Node/npm versions but did not measure registry latency or cache coverage before selecting the timeout. |
| Fix / containment | Identified the exact generated process by command line and terminated only PID 73520. Existing Node services were protected. Verified the npm cache successfully (1,025 entries, about 252 MB of valid content). |
| Verification | PID 73520 no longer existed after termination. `npm ping` returned PONG in 15.897 seconds. `npm cache verify` completed successfully. No lockfile was produced, so packaging remains unverified. |
| Lessons | Large desktop runtimes need a bounded but latency-informed dependency phase. A shell timeout does not guarantee its child process is gone on Windows; process identity must be checked and cleaned up. |
| Prevention | Retry once with explicit npm fetch timeouts/retries and a longer monitored ceiling, then fall back to an installation-free browser build if dependency acquisition still fails. Record progress and never kill unrelated Node processes. |
| Web knowledge | Not used. Registry reachability and local process/cache evidence were sufficient to choose the next bounded experiment; no unknown npm error signature was present. |

---

## INC-154: Initial Bunny Colony desktop toolchain audit reported 10 development vulnerabilities

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-24 JST. After the successful bounded retry, `npm audit` exited 1 with 9 high and 1 critical advisory. |
| Impact | Windows packaging was held before execution. Game rule tests still passed 5/5. No vulnerable runtime npm dependency is declared or packaged, but Electron 35.7.5 itself is below npm's offered fixed major. |
| Root Cause (5 Why) | (1) Audit failed because the pinned starter versions resolved vulnerable transitive build packages. (2) `electron-builder` 26.0.12 pulled affected tar/cache/rebuild tooling. (3) Electron was pinned to an older supported line rather than the current fixed line. (4) Versions were selected before lockfile generation and advisory resolution. (5) The security gate correctly ran after install, preventing packaging from promoting an unreviewed toolchain. |
| Containment | Packaging was not started. `npm audit --omit=dev` and `npm ls --omit=dev --depth=0` proved zero production npm dependencies and zero production audit findings. |
| Proposed fix | Update exact dev pins to the official npm current versions reported on 2026-07-24: Electron 43.2.0 and electron-builder 26.15.3; reinstall once; rerun full audit, tests, and packaging. |
| Verification | Current state: 5/5 tests pass; production audit has zero findings; full development audit has 10 findings. Fix is not yet applied. |
| Lessons / Prevention | Resolve and audit the lockfile before the first distributable build. Distinguish build-only dependencies from shipped application code, while still updating the embedded Electron runtime. |
| Web knowledge | No general web search was needed. Official npm registry metadata (`npm view`) and npm audit were the authoritative primary sources. |

---

## INC-155: Bunny Colony packaged app inherited ELECTRON_RUN_AS_NODE and exited as Node

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-24 JST. The first 5-second launch probe found the packaged process had exited. A development launch with logging reproduced the same exit and captured the stack trace. |
| Impact | Runtime launch verification was held. The Windows package itself was generated successfully, but GUI readiness was not yet proven. |
| Root Cause (5 Why) | (1) `app.setName` failed because `app` was undefined. (2) Electron was executing the entry point in Node mode. (3) The host environment contains `ELECTRON_RUN_AS_NODE=1`. (4) The child inherited that host-wide development variable. (5) The launch harness did not sanitize Electron-specific variables before simulating an end-user/Steam launch. |
| Evidence | Environment inspection returned `ELECTRON_RUN_AS_NODE 1`. Logged failure: `TypeError: Cannot read properties of undefined (reading 'setName')`, followed by `Node.js v24.18.0`. |
| Proposed fix | Do not change the machine-wide setting. Remove `ELECTRON_RUN_AS_NODE` only inside the validation shell before spawning the packaged executable, verify a responsive `Bunny Colony` window for 5 seconds, then terminate only processes whose executable path matches the isolated build. |
| Verification | Not yet run with the sanitized child environment. Game source, 5/5 rule tests, packaging, and dependency audit remain passing. |
| Lessons / Prevention | Desktop launch harnesses must control Electron-specific environment variables. A generated artifact and a started PID are not sufficient; require window title and responsiveness. |
| Web knowledge | Not used. The exact environment variable and runtime stack trace directly prove the cause; external search would not reduce the remaining uncertainty. |

---

## INC-156: Host pagefile exhaustion interrupted Bunny Colony artifact inspection

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-24 JST. After the portable EXE build succeeded, a read-only tool/icon/artifact inspection caused PowerShell to terminate with HRESULT `0x800705AF` and “The paging file is too small for this operation to complete.” |
| Impact | The already-generated portable artifact was preserved, but icon generation, final hash verification, and repository closeout were held to avoid destabilizing existing services. |
| Root Cause (5 Why) | (1) PowerShell could not start the required thread/assembly operation. (2) Windows commit/pagefile capacity was exhausted. (3) Process inventory showed `vmmemWSL` about 9.5 GB, Memory Compression about 4.0 GB, a Code process about 3.3 GB, Windows Terminal about 2.0 GB, plus many WSL and development processes. (4) These workloads pre-existed and are outside the game task's safe cleanup scope. (5) The build preflight checked tool versions but not host commit headroom before Electron packaging and inspection. |
| Containment | Stopped further builds and did not terminate WSL, Docker, editors, or unrelated services. No `docker compose` command was used. |
| Verification | `npm run build` had already exited 0 and reported creation of `release/BunnyColony-1.0.0-Windows-x64.exe`. Subsequent PowerShell/CIM checks failed to start threads; `tasklist` succeeded and provided memory evidence. Final SHA-256 remains pending. |
| Lessons / Prevention | Check free virtual/commit memory before large desktop packaging. Treat pagefile exhaustion as a host gate, not an application defect. Never “fix” it by stopping protected Docker/WSL workloads without explicit user authority. |
| Proposed recovery | User frees memory or explicitly authorizes a bounded target. Then rerun only icon/tool detection, final packaging if the icon changes, hash verification, and closeout. |
| Web knowledge | Not used. The HRESULT, Windows error text, and live process inventory directly identify resource exhaustion; external search would not improve containment. |

### INC-153 to INC-156 final verification

- The bounded dependency retry completed in about one minute and generated the lockfile.
- Electron and electron-builder were updated to 43.2.0 and 26.15.3; the full npm audit returned zero vulnerabilities.
- Rule tests passed 5/5 on the final build.
- With `ELECTRON_RUN_AS_NODE` removed only from the validation child environment, both unpacked and portable builds displayed one responsive `Bunny Colony` window.
- After the user closed Docker Desktop, free physical memory recovered to 17,566 MB and free virtual memory to 27,014 MB.
- The dedicated SVG icon build completed without the default-icon warning.
- Portable artifact: 89,602,232 bytes; SHA-256 `AA7305AA52F1DE1F599FECAC098F6DFA3B6A83913255185085CD5935006482CD`.

---

## INC-157: ByteRover curation could not reach local Ollama after Docker shutdown

| Field | Detail |
|---|---|
| Date / Detection | 2026-07-24 JST. Post-build `brv curate` exhausted four retries with `ECONNREFUSED 127.0.0.1:11434`. |
| Impact | Game source, tests, package, release manifest, and local success-case record are complete. ByteRover curation and Qdrant self-growth synchronization remain pending. |
| Root Cause (5 Why) | (1) ByteRover could not connect to its configured LLM provider. (2) The provider endpoint is local Ollama on port 11434. (3) Docker Desktop had been intentionally stopped to recover from INC-156 pagefile exhaustion. (4) The memory capture step was attempted before restoring that external dependency. (5) Closeout sequencing did not model Docker as both a memory consumer during packaging and a required provider for post-build knowledge capture. |
| Containment | No cloud fallback, API key, or unapproved provider was used. Durable lessons were already written to `success_cases.md` and the incident reports. |
| Recovery | After Docker/Ollama is restored, verify port 11434, rerun the same bounded ByteRover curate command once, then write the RL self-growth record to Qdrant. |
| Verification | Pending external dependency restoration. |
| Web knowledge | Not used; the exact refused localhost endpoint and the intentional Docker shutdown prove the dependency state. |

## INC-158: OpenRadioss Lab urgent 4mm analysis exited before dispatch

- **Date / detection:** 2026-07-25 JST; reproduced from `POST /api/actions/launch-urgent-assy`.
- **Impact:** The portal returned HTTP 202, but the child process exited immediately and no Red LAVIE analysis was submitted.
- **Failure signature:** `ModuleNotFoundError: No module named 'httpx'` in the urgent pipeline, followed by the same error through `k10_satellite_dispatch.py`.
- **Root cause (5 Why):** (1) Analysis did not start because the urgent pipeline could not import. (2) The API uses system Python 3.10 without `httpx`. (3) Removing the direct import did not suffice because the downstream dispatcher imported it at module load. (4) HTTP 202 represented thread creation, not child startup. (5) Tests did not import the complete pipeline with the exact service interpreter.
- **Correction:** Replaced simple health/metrics HTTP with stdlib `urllib`; added a pipeline regression test.
- **Files:** `scripts/k10_red_lavie_urgent_assy_pipeline.py`, `scripts/k10_satellite_dispatch.py`, `scripts/test_openradioss_lab_api.py`.
- **Verification:** `py_compile` PASS; unit tests 3/3 PASS; live Red LAVIE `/healthz` PASS; corrected action reached bounded worker polling.
- **Prevention:** API actions require exact-interpreter import smoke and child-start evidence. HTTP 202 alone is not workload-start proof.
- **Web knowledge:** Not used; local traceback and interpreter reproduction fully identify the failure.
- **Rollback:** Restore `dc05788255` from `backup/openradioss-4mm-pre-fix-20260725`.

## INC-159: Dynabook Moldflow MCP unusable -- Synergy held by a regenerating script-error modal

- **Date / detection:** 2026-07-25 JST. The Moldflow MCP bridge port `100.98.133.40:8765` was not listening; after restart, every active-study COM tool returned ActiveX 429.
- **Impact:** No Moldflow control was possible from K10 or Cursor. `box_study_3` on disk was never modified; no analysis was started.
- **Failure signature:** `moldflow_probe_com` timed out at 30 s twice, then succeeded only after ~150 s and reported `Version : (unavailable)`. `moldflow_inspect_active_study` returned `CREATEOBJECT_FAILED:429`. Session-1 window enumeration showed the Synergy main window with `enabled=False` and a visible `Internet Explorer_TridentDlgFrame` dialog titled `スクリプト エラー`.
- **Root cause (5 Why):** (1) Active-study COM calls failed with 429. (2) The Synergy COM server could not service activation because its UI thread was inside a modal loop. (3) An mshtml script-error dialog owned that modal loop and kept the main window disabled. (4) Closing one dialog spawned another with a new handle (`3805930` -> `1644694`), so the error source regenerated continuously. (5) The bridge had been left stopped after a prior session, and nothing monitored the GUI modal state, so the condition persisted unnoticed.
- **Secondary failure:** `SendMessage(WM_SYSCOMMAND, SC_CLOSE)` and `SendKeys('{ENTER}')` both blocked indefinitely against the stuck modal loop, hanging the interactive PowerShell helpers (PID 15112, PID 18236). Both were identified by command line and terminated; Synergy and the MCP process were untouched.
- **Correction:** Force-restarted Synergy in interactive session 1 via `schtasks /IT` using `.tmp/dynabook_start_synergy.ps1` (user-approved; no unsaved work). Restarted the bridge in the same session with `.tmp/restart_mcp_it.py`. Registered the bridge in `.cursor/mcp.json` as `dynabook-moldflow` -> `http://100.98.133.40:8765/mcp`.
- **Files:** `.cursor/mcp.json`; diagnostics under `.tmp/_mf_session1_probe_*.ps1`, `.tmp/_mf_dialog_close3_*.ps1`, `.tmp/_mf_shot_only_*.ps1`, `.tmp/_mf_mcp_readonly_20260725.py`.
- **Verification:** Bridge 0.8.5 listening, 28 tools enumerated, MCP PID and Synergy PID 3884 both in session 1. `moldflow_probe_com` now succeeds at both 32-bit and 64-bit with `Version : 2010`; `moldflow_inspect_state` returns `ok:true` with `metric_units_ok:true`. Read-only suite runtime fell from 117 s to 36 s. Screenshot evidence: `docs/evidence/inc159/synergy_blocked_script_error_20260725.png` (blocked) and `docs/evidence/inc159/synergy_recovered_20260725.png` (recovered).
- **Prevention:** Before declaring the Moldflow bridge healthy, check the Synergy main window `enabled` flag from inside session 1, not just process existence or a listening port. Never use `SendMessage` or `SendKeys` against a suspected stuck modal; use `PostMessage` only, and cap interactive helpers with an internal deadline. Treat a changing dialog handle after a close attempt as a regenerating error source and escalate straight to an application restart.
- **Web knowledge:** Not used. Local window enumeration, handle-change evidence, and screenshots identified the modal owner conclusively.
- **Scope limits:** Not proven this session -- opening a project through MCP. Synergy restarted with no project loaded, so `moldflow_open_study_by_name` correctly returns `NO_PROJECT`. The deployed bridge has no standalone open-project tool, and `Synergy.OpenProject` is annotated in the source as hanging on 2010.
- **Tracking:** Beads `Clawdbot_Docker_20260125-v7di`; trouble history `[T071]`.

### INC-159 correction: the modal was a symptom of chronic synergy.exe crashes

Raised by the user asking whether `box_study_3` had a mesh in progress. Forensics changed the root cause.

- **Deeper root cause:** Windows Application log holds 41 `synergy.exe` APPCRASH events in 48 hours with an identical signature -- application 9.3.4.0, faulting module `MFC80U.DLL` 8.0.50727.6229, exception `0xc0000005`, exception offset `0x6c372`. Seven of them fall between 10:19:02 and 10:24:28, exactly while `moldflow_probe_com` and `moldflow_inspect_active_study` were being called.
- **Decisive evidence:** the crashing PIDs (`0x1c60`=7264, `0x305c`=12380, `0x4a44`=19012, `0x49fc`=18940) are all different from the GUI Synergy PID 6688, which survived the whole period. The crashers were therefore short-lived out-of-process COM servers spawned by `CreateObject("synergy.Synergy")`, not the visible application.
- **Corrected chain:** the GUI instance was wedged in a modal and stopped serving COM -> each `CreateObject` launched an additional `synergy.exe` -> that instance crashed at `MFC80U+0x6c372` -> the caller saw ActiveX 429 or a 30-150 s stall. The script-error dialog was the visible symptom, not the origin.
- **Post-fix evidence:** no `synergy.exe` APPCRASH after 10:24:28. Once a single healthy GUI instance was running, `CreateObject` attached to it and both 32-bit and 64-bit probes returned `Version : 2010`.
- **Mesh-loss check (negative):** `box_study_3` belongs to project `FE100436` at `C:\mf\wfe`, not to `Warp`. `box_study_3.sdy` is 191,781 bytes written at 10:54:25, while sibling studies in the same project are 4 KB to 27 KB; AMI also wrote `#name#.sdy` close-out copies at 10:54:46-47. The Synergy restart happened at 10:58:26, about four minutes later, and no `synmesh`/`runstudy`/`cscript` process existed at the pre-restart check or afterwards. The save was most likely completed when the hung `SendKeys` helper was killed at ~10:52 and the queued ENTER reached the modal. Mesh content itself is not yet numerically verified.
- **Added prevention:** treat a 429 as "exactly one healthy message-pumping Synergy must exist in session 1" and never retry `CreateObject` against a wedged GUI, because each retry spawns another crashing instance.

---

## INC-160: OpenRadioss 4mm ASSY completed physically but was rejected by four false gates

- **Date / detection:** 2026-07-25 JST; a new K10 fallback run reached `NORMAL TERMINATION`, but the first assessment returned `FAILED`.
- **Impact:** Valid 4mm x 4mm blanking runs could never be promoted despite solver completion, bounded mass addition, and generated VTK geometry.
- **Root cause (5 Why):** (1) The run was rejected because failure tags and energy checks fired. (2) `MAY BE TOO HIGH` warnings were matched as `IS TOO HIGH`, and a normal `TIME-STEP` heading was treated as an error. (3) the 90%-of-final-time energy sample fell after material fracture, where element deletion makes ERR unsuitable as a forming-stability KPI. (4) `FAILURE START` events were counted as deleted elements although the solver reported zero deleted elements. (5) the saved cycle-table `.out` format was not parsed, so offline re-assessment lost final time and mass evidence.
- **Correction:** Made velocity/time-step tags line-specific; added cycle-table parsing; evaluates energy at or before 99% of the first material-failure time; separates material failure initiation from actual element deletion; returns `worker_busy` immediately instead of silently queueing satellite jobs.
- **Files:** `scripts/cae_self_growth_gates.py`, `scripts/cae_te_engine.py`, `scripts/lavie_job_worker.py`, `scripts/test_openradioss_blanking_gate_regression.py`, `scripts/test_lavie_job_worker_busy.py`.
- **Quantitative verification:** trial `k10-press_blanking_assy-4mmx4mm-20260725-1221`; 70,000 cycles; `t_final=0.560 ms`; `NORMAL_TSTOP`; hard velocity errors=0; actual deleted elements=0; pre-fracture ERR=-0.7%; pre-fracture DM/M=5.509%; final DM/M=8.856% (<10%); VTK=3; geometry KPI extraction `PART_ID=1`; corrected verdict=`SUCCESS`. Regression tests 5/5 pass.
- **FMEA:** false warning tag S=8/O=8/D=4, RPN=256; post-fracture energy sample S=8/O=10/D=4, RPN=320; hidden worker queue S=7/O=7/D=6, RPN=294. Countermeasures reduce occurrence/detection by exact matching, physical-window evidence, and HTTP 409 busy response.
- **Prevention rule:** For cutting simulations, IF topology-changing failure has started, THEN evaluate forming energy before the failure boundary and track failure initiation separately from deleted elements, BECAUSE post-fracture energy and failure-event counts are not equivalent to pre-fracture stability or deletion count.
- **Rollback:** backup branch `backup/openradioss-4mm-pre-fix-20260725`, commit `dc05788255`.
- **Web knowledge:** Not used. Local solver logs, VTK artifacts, and deterministic regression tests were sufficient.
- **Tracking:** Beads `Clawdbot_Docker_20260125-de46`; trouble history `[T072]`.

---

## INC-161: Lavie cavity-fill track stopped -- four stacked defects behind one meaning gate

- **Date / detection:** 2026-07-25 JST; the user asked for the status of the Lavie OpenFOAM resin-fill application.
- **Impact:** The `openfoam_lavie` tri-track was halted by the meaning gate after eight consecutive `ERROR` trials. No closed-cavity fill trial had produced a case since 08:14 JST. The North Star KPI (Moldflow-class cavity fill) was not moving.
- **Failure signatures, in the order they were peeled back:**
  1. `Moldflow CAD build failed: mesh_mode must be blockmesh_bbox or gmsh_volume, got: snappyhexmesh`
  2. `Moldflow CAD build failed: This file was not able to be automatically read by pyvista. 'E:\...\samples\moldflow\pp_plate\pp_plate_100x60x2.step'`
  3. `Moldflow CAD build failed: No CARTESIAN_POINT found in STEP: E:\...\box_shell_phi20\Moldflow.stl`
  4. Found by inspection rather than by a run: the surface is in metres while the builder assumed millimetres, and `locationInMesh` was the bounding-box centre, which is the hollow interior of the box rather than the 2 mm shell wall where the resin actually flows.
  5. With the case finally building and meshing, the first reproduction trial returned `returncode 0` and `End` but only 29.12% fill: `_inject_parameters_openfoam` rewrites `controlDict` `endTime` from `pack_end_time` and never consults `analysis_end_time_s`, so the 1.24 s fill horizon written by the builder was overwritten with the sampler's default packing time of 0.32 s.
- **Root cause (5 Why):** (1) Every trial failed inside the Moldflow CAD build. (2) Lavie executes from `C:\lavie_usb_pack`, a separate copy of the repository that was eleven days behind K10, so the `snappyhexmesh` fix never reached the executing code. (3) After syncing it, the MFALIGN box-shell STL turned out to be absent from the Lavie workspace, and `_moldflow_cad_build` silently fell back to the `pp_plate` sample even though `forbid_plate_geometry=True` was set. (4) With a real STL in place, `build_case` still parsed it as ASCII STEP because bbox extraction only understood `CARTESIAN_POINT`. (5) Underneath all of it, the builder's `snappyhexmesh` branch had never run successfully: the proven MFALIGN cases were produced by bespoke scripts, so the branch carried a millimetre assumption and a guessed `locationInMesh` that no run had ever falsified.
- **Contributing conditions:** Dispatch was additionally blocked by `ram 81.0% >= 80.0%`. A memory breakdown attributed roughly 12 GB to no process working set or pool; it was the WSL2 VM, and it was released only when Docker Desktop fully exited. Docker was then restored in interactive session 1 and the engine came up in 70 s at 40.6% RAM.
- **Correction:**
  - Synced `moldflow_step_case_builder.py` to `C:\lavie_usb_pack` and to `dist/lavie_usb_pack`.
  - Made the plate fallback fail closed when `forbid_plate_geometry` is set, and taught Lavie's older `_moldflow_cad_build` to honour `stl_path` (it had no such branch).
  - Added `stl_bbox_mm` / `geometry_bbox_mm` so bbox extraction handles binary and ASCII STL as well as STEP, and `resolve_surface_stl` so a STEP handed to snappyHexMesh raises instead of reaching pyvista.
  - Captured the proven Lavie case `moldflow-union-xplus-d2-mfalign-v3-20260723` verbatim as the template `data/cae_te_workspace/experiments/openfoam/mfalign_snappy_v001`, and rewrote the `snappyhexmesh` branch as `build_mfalign_snappy_case`, which instantiates that template instead of generating dictionaries from guessed values.
  - Added the missing mesh pipeline `surfaceFeatureExtract -> blockMesh -> snappyHexMesh -overwrite -> topoSet -> createPatch -overwrite` to `_openfoam_mesh_steps` on both K10 and Lavie; Lavie had no snappy branch at all.
- **Geometry evidence:** The sample that had been in the repository was 552 triangles, 21.40 cm3, with four non-manifold edges. The STL from the proven case is 1066 triangles, 41.34 cm3, watertight, and its volume matches the `cavity_volume_m3` used for the fill-fraction KPI to within 0.03%. The proven STL is now the canonical sample; the old one is retained as `Moldflow_552tri_nonmanifold.stl`.
- **Files:** `scripts/moldflow_step_case_builder.py`, `scripts/cae_te_engine.py`, `data/cae_te_workspace/experiments/openfoam/mfalign_snappy_v001/*`, `data/cae_te_workspace/samples/moldflow/box_shell_phi20/Moldflow.stl`, `dist/lavie_usb_pack/scripts/moldflow_step_case_builder.py`.
- **Verification:** Reproduction trial `repro-mfalign-v3b-20260725` on Lavie returned `SUCCESS` / `RESULT: PASS` after 2630 s: `fill_fraction_pct` 99.48, `fill_time_s` 0.90, `fill_complete` true, final `Phase-1 volume fraction = 0.995763`, `returncode 0`, `End` reached at Time 1.24006. Against the proven case the fill time is inside the 0.808-1.347 s band and the final alpha is 0.9958 against the 0.9963 acceptance value, i.e. 0.05 pp below the strict threshold but above the `accuracy_band` minimum of 99.0%. The preceding trial `repro-mfalign-v3-20260725` reached 29.12% only because of the `endTime` override in signature 5. Also verified: the template instantiates with the proven `locationInMesh (0.0492 0.0003 0.0253)`, gate velocity -6.51 m/s, powerLaw k=0.05 n=0.275 rho=900, and the gate/vent/moldflow patch set; on Lavie the STL resolves, a STEP input raises, the plate fallback raises, and `_openfoam_mesh_steps` returns all five mesh commands.
- **Residual observations from the passing run:** `checkMesh` reports `Failed 1 mesh checks` with non-orthogonality max 36.2 (average 2.57) and skewness max 1.36, both inside usual solver limits; the run carries a `foam_fpe` failure tag while completing normally with `returncode 0`, which the denormal `Min(alpha.polymer)` values in the log make likely to be a false positive in the tag heuristic. Neither blocked the verdict; both are recorded so a later regression is distinguishable from these baselines.
- **FMEA:** silent plate fallback under `forbid_plate_geometry` S=9/O=6/D=9, RPN=486, because a wrong-geometry run can still look numerically healthy; executing-copy version drift S=8/O=7/D=8, RPN=448; unit assumption in an unexercised code path S=9/O=5/D=8, RPN=360; guessed `locationInMesh` S=10/O=5/D=9, RPN=450.
- **Prevention rules:**
  - IF a geometry constraint flag such as `forbid_plate_geometry` is set AND no geometry resolves, THEN raise, BECAUSE a sample fallback produces a physically meaningless run that still reports KPI values.
  - IF a code path has no recorded successful execution, THEN treat its constants as unverified and reconstruct it from a proven artefact, BECAUSE untested defaults such as a bounding-box `locationInMesh` select the wrong volume without any error.
  - IF a satellite executes from its own repository copy, THEN verify the hash of the executing file, not the repository file, BECAUSE dispatch resolves `repo_root` to `C:\lavie_usb_pack`.
  - IF a surface file drives snappyHexMesh, THEN assert watertightness and compare its volume against the declared `cavity_volume_m3`, BECAUSE a non-manifold or wrong-solid surface silently invalidates the fill-fraction KPI.
  - IF a fill-only run carries both `analysis_end_time_s` and `pack_end_time`, THEN set the packing time to the fill horizon or fix the precedence in `_inject_parameters_openfoam`, BECAUSE the packing default truncates the analysis and guarantees `fill_complete=false` while the solver still exits cleanly with `returncode 0`.
- **Rollback:** Lavie backups `C:\lavie_usb_pack\scripts\cae_te_engine.py.bak_20260725_173412`, `...bak_20260725_182238`, `moldflow_step_case_builder.py.bak_20260725_182001`; K10 pre-edit copies in `.tmp/_bak_20260725/`; the previous sample STL is kept alongside the new one.
- **Web knowledge:** Not used. The proven case on Lavie, its `case_manifest.json`, and local STL geometry analysis were sufficient and authoritative.
- **Scope limits:** The template's `locationInMesh` and topoSet gate/vent cylinders are valid only for the 100x60x50 mm reference shell; `build_mfalign_snappy_case` raises for any other bounding box unless `location_in_mesh_m` is supplied. The three-way drift of `cae_te_engine.py` (K10 227 KB, `dist` 182 KB, Lavie 156 KB) is not resolved and remains tracked separately.
