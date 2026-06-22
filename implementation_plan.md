# Nested Learning Implementation Plan

Date: 2026-03-26
Scope: `OpenClaw_Learning_Protocol_Pack.zip` Phase 1 bootstrap

## Goal

Add a safe first version of a `learning_engine` that can:

- ingest structured case memory
- compare a new case against past similar cases
- capture judgement feedback
- search stored memories

without directly modifying the core `docker-compose.yml` yet.

## Constraints

- Respect `AGENTS.md`: avoid editing core compose until the implementation plan exists.
- Keep current services stable.
- Reuse the existing stack where possible:
  - `qdrant`
  - `litellm`
  - `langfuse`
  - `n8n`
  - `paperless`
  - `docling`
  - `ollama`

## Phase 1 Deliverables

1. New service scaffold at `clawstack_v2/docker/learning_engine`
2. FastAPI endpoints:
   - `GET /health`
   - `POST /ingest/case`
   - `POST /compare/case`
   - `POST /feedback/judgement`
   - `POST /search/memory`
3. Qdrant-backed storage with auto-create collections
4. Deterministic fallback embedding path so the service can run even before model wiring is finished
5. Portal app scaffold at `data/workspace/apps/learning_memory/index.html`
6. Separate compose patch file for later activation

## Out of Scope For This Pass

- Direct edits to the core `clawstack_v2/docker-compose.yml`
- Full Email ingest workflow
- Full CAE/FEM ingest workflow
- Production-grade access control and review workflow
- Cross-org lesson generalization automation

## Success Criteria

- The learning engine code is runnable and syntax-valid
- Core endpoints behave consistently with the protocol pack
- The implementation is additive and reversible
- The repo is ready for a later compose activation step

## Phase 2 Extension Notes

- Add `POST /ingest/quality-issue`
- Add `POST /ingest/improvement-activity`
- Create Qdrant collections for `quality_issue_memory` and `improvement_activity_memory`
- Keep the activation path additive through `clawstack_v2/docker-compose.learning_engine.patch.yml`

## Phase 3 Extension Notes

- Add `POST /ingest/email-message`
- Add `POST /ingest/email-thread`
- Add `POST /compare/email-thread`
- Create Qdrant collections for `email_fact_memory` and `email_thread_memory`
- Keep email ingest compatible with the existing external-harness and n8n patterns

## Phase 4 Extension Notes

- Add `POST /ingest/cae-run`
- Add `POST /compare/cae-run`
- Create Qdrant collection for `cae_run_memory`
- Add an external CAE sync harness so existing solver logs can be summarized without changing core compose
- Extend the CAE sync harness to normalize OpenRadioss logs and OpenFOAM case directories
- Let `idle_ingest_maintenance.py` trigger CAE learning sync when the status file is stale

## 2026-03-28 Operational Hardening Notes

- Clarify that `clawstack_v2/docker-compose.yml` remains the active base compose for the current stack, with additive patch files layered on top.
- Fix maintenance reliability before adding more automation:
  - make `scheduled_report_search.py` tolerant to host/container n8n API base differences
  - make SQLite initialization fall back when WAL is unsupported on mounted storage
  - make `update_cmux_status.py` resolve the repository root robustly from both host and `/workspace` paths
  - make nightly email ingest notifications surface timeout/degraded states instead of always sounding successful
- Resolve latent host port conflicts inside the `tools` profile so the stack is predictable when optional tools are enabled together.
- Add an external Mini PC optimization harness and runbook rather than baking aggressive stop/start behavior into core compose.

## 2026-06-22 PartPacker Blender AutoMecha Kit Adoption Review

Scope: `ZIP_Group/PartPacker_Blender_AutoMecha_Kit_v1.0.zip`

Beads: `Clawdbot_Docker_20260125-30w`

### Meaning Gate

- Physical truth: this is not a CAE solver path. It is a visual/mechanical pre-processing path for image-to-part candidate generation, Blender rigid rigging, driver setup, and pose/collision review.
- Category / solver match: do not route it into Moldflow/OpenRadioss/Cetol pipelines. Treat it as a mecha/robot asset pipeline that may support motion visualization and future robotics experiments.
- KPI / artifact: first useful artifact is a reviewed integration map showing how ZIP outputs can feed `clawstack.mecha_rig_spec.v1`, plus a no-download local smoke test using an existing GLB/FBX candidate.
- Anti-pattern check: no full app duplication, no GPU/PartPacker download loop, no BlenderMCP arbitrary write access outside a sandbox, no Telegram success without visual QA.
- Self-growth: if integration proceeds, record the final adapter pattern in Beads and ByteRover after verification.

### ZIP Inventory Summary

- Size: 60,475 bytes.
- SHA256: `358393607A5E82E5316EF676A02028DAD11ADA33BDD39D457C1692E15C3E845C`.
- Contents: 74 files under `PartPacker_Blender_AutoMecha_Kit/`.
- Included areas: `README_JA.md`, `docs/`, `config/`, `scripts/`, `src/mecha_pipeline/`, `blender_scripts/`, `tests/`, `tools/`.
- ZIP self-test report: `3 passed`, `syntax_errors=[]`.
- Not included: NVIDIA PartPacker source, model weights, Blender, BlenderMCP, PyTorch, Claude Code, or copyrighted image/model assets.

### Duplicate Scan

Existing overlapping assets:

- `projects/AtsugiMechaCity/mecha_rig_spec.py` already defines `clawstack.mecha_rig_spec.v1`, segment assignment, editable bone decisions, joint constraints, and validation.
- `projects/AtsugiMechaCity/mecha_rig_builder.py` already builds Blender armatures, rigid parents meshes, applies joint constraints, handles armor followers, and exports rigged FBX.
- `projects/AtsugiMechaCity/mecha_rig_spec_editor.html` already provides a human review/edit surface for rig spec corrections.
- Existing trouble history includes false-PASS risks for mecha autorig visual QA, so any new pipeline must strengthen QA rather than bypass it.

Adoption judgment: `ADOPT_PARTIAL`, not `ADOPT_NEW`.

Reason: ZIP has useful PartPacker orchestration, candidate ranking, Blender pose/collision scripts, and documentation, but the repo already has a canonical mecha rig contract and builder. A new parallel `mecha_pipeline` would duplicate and fragment the current rig work.

### No-Go Conditions

- Do not edit `docker-compose.yml` or core service files for this adoption.
- Do not run `scripts/02_setup_partpacker.ps1` until external-download consent, timeout, and status logging are in place.
- Do not clone PartPacker or download Hugging Face weights as part of this plan.
- Do not enable BlenderMCP with repo-wide write access.
- Do not treat AABB collision as final engineering clearance.
- Do not mix inferred labels into raw mesh facts; keep auto classification, user edits, and final locked decisions separate.

### Proposed Partial Integration

Phase 0: quarantine review only.

- Extract ZIP into a clearly named review folder, for example `ZIP_Group/review_partpacker_automecha_20260622/`.
- Keep original ZIP unchanged.
- Do not add that extracted folder to runtime paths.
- Run static checks only: file inventory, license notes, Python syntax, PowerShell script review.

Phase 1: adapter design.

- Create a small adapter spec mapping ZIP `inventory.json` / `part_map.auto.json` concepts into `clawstack.mecha_rig_spec.v1`.
- Reuse `projects/AtsugiMechaCity/mecha_rig_spec.py` validation instead of accepting the ZIP schema as canonical.
- Preserve the ZIP distinction between raw inventory, auto classification, reviewed map, and final export.

Phase 2: local smoke path without external downloads.

- Use an existing local GLB/FBX candidate from the current repo, not PartPacker inference.
- Test only Blender import, inventory generation, candidate ranking, and conversion into `clawstack.mecha_rig_spec.v1`.
- Produce artifacts under a run-specific `work/` or diagnostics folder with rollback-friendly stage names.

Phase 3: controlled PartPacker setup, only after approval.

- Wrap `scripts/02_setup_partpacker.ps1` in a host-side harness with explicit timeout, progress/status JSON, and failure logging.
- Require cloud/API/download consent before Hugging Face model weight download.
- Add a retry limit and no-progress detection for long downloads.
- Keep GPU-heavy PartPacker and Blender steps serialized.

Phase 4: promotion gate.

- Promote only if the adapter reduces manual segment labeling effort or improves pose/collision review without increasing false-PASS risk.
- Benchmark against one known current model: RickDias or Zaku segmentation.
- Required checks: visual QA contact sheet, `mecha_rig_spec` validation, builder self-test, and at least one pose/collision report.

### Expected Files For The Next Implementation Pass

Only after this plan is accepted:

- `ZIP_Group/review_partpacker_automecha_20260622/` for quarantined extraction.
- `projects/AtsugiMechaCity/partpacker_to_mecha_rig_spec.py` for a narrow adapter, if the static review supports it.
- `projects/AtsugiMechaCity/tests/test_partpacker_to_mecha_rig_spec.py` or equivalent focused tests.
- Optional docs note under `projects/AtsugiMechaCity/` describing the PartPacker-to-rig-spec bridge.

Protected files remain untouched unless separately approved:

- `docker-compose.yml`
- `clawstack_v2/docker-compose*.yml`
- existing dashboard/portal cards
- existing `mecha_rig_builder.py` behavior except for narrowly tested adapter compatibility
- any `.env` or credential-bearing file

### Rollback

- Quarantine extraction can be removed as a directory without affecting runtime behavior.
- Adapter code will be additive and disabled by default.
- No service activation, scheduled task, Docker profile, or external download occurs until a later approval step.
