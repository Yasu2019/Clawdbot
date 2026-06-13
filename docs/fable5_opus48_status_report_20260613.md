# Fable5 Sprint Status Report (Opus 4.8 Handover)

**Date:** 2026-06-13 (JST)  
**Author:** Cursor Agent (Composer) — implementation session  
**Audience:** Opus 4.8 / user  
**North Star (T019):** Press-part 3D -> Moldflow-class cavity fill + Cetol tolerance + OpenRadioss blanking/bending -> progressive-die development

---

## 1. Executive Summary

| Area | Status | Notes |
|------|--------|-------|
| **part_manifest.json contract** | DONE | Golden: `tp-dxf-44920df6` |
| **Cross-pillar E2E (Tolerance + Moldflow + OR)** | **DONE (policy-clean)** | `fable5_e2e_20260613_222614` SUCCESS x2 |
| **Moldflow @ main LAVIE** | DONE | `resin_fill_cad` VOF ~40s SUCCESS |
| **OpenRadioss @ red_lavie** | **DONE** | `RED-OR-8a5dc779` + E2E `press_blanking` on red_lavie |
| **Cetol Hub manifest bridge + UI** | DONE | API + Step 8 UI @ `:8004`; **L2 GD&T proxy** (5 dims golden) |
| **IATF Visual QA / gate_registry** | DONE (Phase C core) | Checklist + fail-closed; vision runner wired (consent-gated) |
| **GD&T L2 proxy (Cetol path)** | DONE | `merged_tolerance_dims` + Hub + growth_domain |
| **GD&T / L10 full PMI engine** | NOT STARTED | Opus design-only defer (3D PMI import) |
| **Red LAVIE fleet ops** | DONE | worker :5682 + OR image + monitor :8111 + Startup VBS |

**Verdict:** Fable5 Top 1-3 + Phase B/C **implementation-complete**. Policy-clean E2E with `--require-red-lavie` **verified** (`policy_degraded: false`).

---

## 2. Completed Work (Evidence)

### 2.1 Fable5 E2E — policy-clean production run

**Run ID (canonical):** `fable5_e2e_20260613_222614`  
**Report:** `data/cae_te_workspace/runs/fable5_e2e_20260613_222614/fable5_e2e_report.json`

| Step | Host | Verdict |
|------|------|---------|
| manifest_validate | K10 | OK |
| tolerance | K10 | PASS (`geometry_source=measured`, L2 GDT) |
| resin_fill_cad | **main LAVIE** | SUCCESS (~40s, `resin_fill_vof`) |
| press_blanking | **red_lavie** | SUCCESS (~24s, `geometry_source=manifest`) |

**Earlier degraded run:** `fable5_e2e_20260613_180556` (OR on K10 fallback while red offline).

**Red LAVIE OR standalone:** `RED-OR-8a5dc779` SUCCESS (22.6s).

**Command:**

```powershell
python scripts/fable5_manifest_e2e.py --timeout 900
python scripts/fable5_manifest_e2e.py --require-red-lavie --timeout 900
```

### 2.2 OpenRadioss STEP shell (golden)

- Trial: `OR-BLANK-001-S01` style path via `step_shell` + `OPENRADIOSS_PREFER_STEP_SHELL=1`
- Manifest: `data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json`

### 2.3 Fleet documentation

- Canonical: `docs/fleet_job_allocation_20260613.md`
- Linked from `docs/claude_code_fable5_evolution_brief.md` section 11-F

### 2.4 Cetol Hub (Phase B)

**Container:** `progressive_die_hub` @ http://127.0.0.1:8004

| Endpoint | Purpose |
|----------|---------|
| `POST /api/tolerance-stack/preview-manifest` | Load manifest -> rows |
| `POST /api/tolerance-stack/from-manifest` | Load + run WC/RSS/MC |
| `POST /api/tolerance-stack/upload-manifest` | File upload |

**UI:** Step 8 tab — "part_manifest.json を読込" + Golden manifest button

**CLI bridge:**

```powershell
python scripts/tolerance_manifest_hub_bridge.py data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json
python scripts/tolerance_manifest_hub_bridge.py ... --post-hub default
```

**Verified:** API returns **5 dims** (3 nominal + 2 GD&T proxy); MC Cpk computed (2026-06-13 rebuild).

**L2 GD&T fields:** `include_gdt`, `gdt_dim_count`, `maturity_level=L2_gdt_proxy`

**CLI:**

```powershell
python scripts/tolerance_manifest_hub_bridge.py ... --no-gdt   # L1 nominal-only
```

### 2.5 IATF Visual QA (Phase C)

| Change | File |
|--------|------|
| Checklist integration (50 deterministic rules, pre_mp4 subset) | `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa.py` |
| gate_registry stages: before_tts / before_render / before_mp4 | `run_host.py` |
| Script QA + production design fail-closed before TTS | `run_host.py` |
| 401/429 no auto-approve | `ai_visual_reviewer.py` |
| Duplicate Visual QA on frame-resume path fixed | `run_host.py` |
| Consent-gated AI vision_checks batch | `visual_qa_vision_runner.py` + `visual_qa.py` |

**Env flags:**

- `IATF_VIDEO_SCRIPT_QA_REQUIRED=1` (default)
- `IATF_VISUAL_QA_STRICT_RESOLUTION=0` (default; set 1 for 1280x720 hard check)
- `IATF_PRODUCTION_STILL_QA_REQUIRED=0` (optional G45 strict)
- `IATF_VISION_QA_ENABLED=1` + `IATF_VISION_QA_CONSENT=1` (required for cloud vision batch)

---

## 3. Remaining (Next Phase — Not Blocking Fable5 Sprint)

### 3.1 Red LAVIE operational stability (not code)

- Worker/monitor Startup VBS registered on DESKTOP-DERCN1N
- On reboot: verify `http://127.0.0.1:5682/healthz` and `:8111/metrics`
- K10 recovery: `python scripts/k10_red_lavie_auto_recovery.py`
- Runbook: `docs/troubleshooting/red_lavie_stability_why_offline.md`

### 3.2 GD&T L10 full Cetol-class engine

- **L2 proxy DONE:** holes/datums from manifest + bbox pitch fallback; wired to Hub, bridge, `growth_domain_runners`, `tolerance_stackup_engine.analyze_stack_from_manifest_dict`
- **L4 scaffold DONE (2026-06-13):** `scripts/step_pmi_gdt_extract.py` — STEP text PMI read (cylinders -> holes); `--enrich-pmi-from-step` on hub bridge; design doc `docs/fable5_gdt_l10_design.md`
- **L10 deferred:** full 3D assembly stack + statistical Cp/Cpk + factory KPI (Opus design review)

### 3.3 IATF vision_checks (AI layer)

- **Runner wired:** `visual_qa_vision_runner.py` invoked after contact sheet in `visual_qa.py`
- **Production consent ON (K10 .env):** `IATF_VISION_QA_ENABLED=1` + `IATF_VISION_QA_CONSENT=1` + `docker-compose.iatf-video.yml` env passthrough
- **Smoke:** `python scripts/iatf_vision_qa_smoke.py` — Gemini vision batch runs (fail-closed on non-IATF image)

### 3.4 LAVIE script sync

- **Fixed:** `build_lavie_pack_sync_command` in `k10_sync_cae_experiments_to_lavie.py` (no nested powershell / no experiments folder check)
- Moldflow E2E still works via **inline manifest params** when sync not run

---

## 4. Architecture (Physics Split — Confirmed)

| Solver | Categories | Primary host |
|--------|------------|--------------|
| OpenFOAM | `resin_fill_*` | main LAVIE |
| OpenRadioss | `press_blanking`, `press_bending`, ... | red LAVIE (fallback K10) |
| Cetol proxy | tolerance stack | K10 + Hub UI |
| Shared contract | `part_manifest.json` | ThinkPad -> all pillars |

---

## 5. Key Files (Implementation Index)

| Path | Role |
|------|------|
| `scripts/fable5_manifest_e2e.py` | Cross-pillar orchestrator |
| `scripts/fable5_red_lavie_or_rerun.py` | Red LAVIE OR rerun |
| `scripts/tolerance_manifest_hub_bridge.py` | CLI -> Hub |
| `scripts/cae_te_engine.py` | Manifest enrich + Moldflow CAD build |
| `scripts/cae_workload_router.py` | Fleet routing |
| `data/workspace/cae_workload_router.yaml` | Policy |
| `clawstack_v2/docker/progressive_die_hub/` | Hub server + UI |
| `clawstack_v2/apps/iatf_video_factory/run_host.py` | IATF pipeline gates |
| `data/workspace/apps/dxf2step/part_geometry_contract.py` | Manifest + GDT L2 dims |
| `data/workspace/tolerance_stackup_engine.py` | Stack + `analyze_stack_from_manifest_dict` |
| `data/workspace/growth_domain_runners.py` | Tolerance proxy with merged GDT |
| `clawstack_v2/apps/iatf_video_factory/pipeline/visual_qa_vision_runner.py` | Consent-gated vision QA |
| `scripts/red_lavie_start_monitor.ps1` | Minimal monitor start (PS 5.1 safe) |
| `scripts/red_lavie_bootstrap_from_k10.ps1` | One-shot download+bringup from K10 |
| `scripts/setup_monitor_node.ps1` | Monitor deploy (step 2 netstat bug fixed) |
| `scripts/k10_sync_lavie_scripts_to_lavie.py` | LAVIE pack sync (fixed command) |
| `docs/fleet_job_allocation_20260613.md` | Fleet reference |

---

## 6. Verification Checklist (Copy-Paste)

```powershell
# Fleet health (Fable5)
python scripts/fable5_fleet_health_check.py --json --write

# E2E (allows K10 OR fallback)
python scripts/fable5_manifest_e2e.py --timeout 900

# E2E strict (requires red_lavie)
python scripts/fable5_manifest_e2e.py --require-red-lavie --timeout 900

# Red LAVIE OR only
python scripts/fable5_red_lavie_or_rerun.py

# Hub manifest
python scripts/tolerance_manifest_hub_bridge.py data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json --post-hub default

# Manifest validate
python scripts/part_geometry_contract.py --validate data/workspace/thinkpad_dxf2step_history/tp-dxf-44920df6/part_manifest.json
```

---

## 7. Beads / Issues

| ID | Title | Status |
|----|-------|--------|
| Clawdbot_Docker_20260125-zng | Fleet MD + E2E | CLOSED |
| Clawdbot_Docker_20260125-1ah | Phase2 E2E A | CLOSED |
| Clawdbot_Docker_20260125-4p9 | Red LAVIE online -> rerun OR | CLOSED |

---

## 8. Recommendation for Opus 4.8

1. **Do not re-implement** Top 1-3 contract/Moldflow/OR shell — verified on main LAVIE + red_lavie.
2. **Next sprint:** GD&T **L10** PMI import design review; IATF vision QA with consent + cost cap.
3. **Ops:** keep red_lavie Startup VBS + periodic `k10_red_lavie_connectivity_watch --once`.

---

*End of report.*
