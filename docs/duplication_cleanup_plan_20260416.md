# Duplication Cleanup Plan

Date: 2026-04-16
Status: active cleanup plan
Scope: reduce operationally harmful duplication without deleting useful references

## Goal

This repository does not need blanket deletion.
It needs clearer ownership so operators and future agents can tell:

- what is canonical
- what is only a supporting reference
- what should be archived or hidden from the main path
- what should eventually merge into a thinner entry-point model

## Core Rule

Keep reference material if it helps traceability.
Remove ambiguity where multiple active-looking surfaces claim the same role.

Preferred action order:

1. `canonical`
2. `reference`
3. `merge`
4. `archive`

Do not start with destructive cleanup.
Start by fixing ownership and navigation.

## Duplicate Types

### Safe duplication

These can remain if clearly labeled:

- ZIP source packages
- historical assessments
- extracted temp review material kept outside the active operator path
- example compose files inside third-party or imported projects

### Harmful duplication

These should be reduced:

- multiple active-looking governance documents for the same decision type
- multiple top-level entry points for the same operator task
- multiple "current" compose files without a clear ownership story
- workflow creation and repair scripts whose roles are too similar to distinguish quickly

## Canonical Ownership Map

### Governance

Canonical:

- `AGENTS.md`
- `docs/canonical_routing_and_adoption_20260404.md`

Reference:

- `docs/protocol_adoption_assessment_20260412.md`
- `docs/protocol_package_inventory_20260404.md`
- individual ZIP assessment docs such as Blender and resilient-design reviews

Archive or reference only:

- ZIP packages and extracted ZIP temp folders
- old package-specific protocol bundles that restate current policy

### Refactor / duplication decisions

Canonical:

- `docs/system_refactor_assessment_20260404.md`
- this file

Reference:

- point-in-time package assessments
- narrow task-specific protocol notes under `protocols/`

### Portal and hub navigation

Canonical top-level entry:

- `data/workspace/portal.html`

Supporting ownership memo:

- `docs/canonical_entrypoint_map_20260416.md`
- `docs/operational_surface_rules_20260416.md`
- `docs/featured_surface_inventory_20260416.md`

Top-level support hubs that should stay visible:

- `data/workspace/apps/system_role_map/index.html`
- `data/workspace/apps/operations_toolbox/index.html`

Domain hubs that should remain domain-specific rather than becoming second portals:

- `data/workspace/apps/cmux_hub/index.html`
- `data/workspace/apps/codex_protocol_hub/index.html`
- `data/workspace/apps/three_d_workbench/index.html`
- `data/workspace/apps/ingestion_rag_control_center/index.html`

### Ingestion / Gmail / Paperless / RAG operations

Canonical operator flow:

- overview and next-step routing: `data/workspace/apps/ingestion_rag_control_center/index.html`
- raw Gmail content search: `data/workspace/apps/email_search/index.html`
- learning and backfill status: `data/workspace/apps/learning_memory/index.html`
- system health and RAG observability: `data/workspace/apps/observability_hub/index.html`
- role explanation: `data/workspace/apps/system_role_map/index.html`

Problem:

These pages are all useful, but some of the explanatory copy currently overlaps.

Cleanup direction:

- keep only `ingestion_rag_control_center` as the "where do I start" page for this domain
- keep other pages focused on their narrower responsibilities

### 3D / geometry path

Canonical operator flow:

- lightweight route and folder-first overview: `data/workspace/apps/three_d_workbench/index.html`
- tolerance-focused view: `data/workspace/apps/tolerance_hub/index.html`
- GD&T review: `data/workspace/apps/gdt_overlay_studio/index.html`
- DXF-to-FCStd / DXF-to-STEP protocol entry: `data/workspace/apps/dxf_fcstd_protocol/index.html`

Problem:

There is some navigation overlap, but the tools are not duplicates in the same way as governance docs.

Cleanup direction:

- keep these as distinct domain tools
- avoid adding another top-level 3D portal

### Compose files

Canonical primary stack:

- `docker-compose.yml`
- `docker-compose.addons.yml`

Separate domain stack:

- `iatf_system/docker-compose.yml`
- `iatf_system/docker-compose.override.yml`
- `iatf_system/docker-compose.production.yml`

Imported or example stacks:

- `clawstack_v2/open-notebook/docker-compose.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-*.yml`
- package example compose files in temp review folders

Cleanup direction:

- document which compose files are active, domain-local, imported-example, or patch-only
- do not merge or delete core compose files during this phase
- see `docs/compose_ownership_memo_20260416.md` for the current compose classification

### Workflow scripts

Keep distinct categories:

- creators: `create_*workflow*.py`
- repair / patch: `fix_*workflow.py`, `patch_*workflow.py`, `workflow_healer.py`
- recreation / bulk action: `recreate_workflows.py`, `trigger_n8n_workflows_now.py`
- state snapshots: `*_workflow_status.json`

Problem:

The current folder makes these look flatter than they are.

Cleanup direction:

- document the categories now
- later consider moving them into grouped subfolders if the repo owner wants a structural cleanup

## Priority Table

| Area | Priority | Action | Why |
|---|---|---|---|
| Governance and protocol docs | High | reduce active-looking duplicates | this is the highest confusion risk |
| Portal and operator entry points | High | define one start page per domain | many useful pages exist, but some compete as first-click surfaces |
| Compose inventory | High | label active vs example vs imported | avoids risky mistakes during operations |
| Workflow script landscape | Medium | categorize and document | naming overlap is real, but less dangerous than governance ambiguity |
| 3D and domain hubs | Medium | keep distinct but stop adding more top-level hubs | more overlap risk comes from navigation than implementation |
| ZIP and extracted packages | Low | keep reference labeling consistent | mostly harmless if not treated as active |

## Phase Plan

### Phase 1: done or in progress

- establish one canonical routing and adoption doc
- classify reviewed ZIP packages as reference, candidate, or partial-adoption items
- assess duplicate-heavy areas before changing core runtime files

### Phase 2: next safe moves

- add a compose ownership memo
- add a portal ownership and first-click map
- tighten copy in the ingestion and protocol hubs so each page has one clear role

### Phase 3: optional structural cleanup

- move archive-like or low-traffic pages under a clearer archive or experimental path
- group workflow scripts by category
- retire duplicate-looking operator pages only after links and replacement ownership are clear

## No-Go Conditions

- do not delete ZIP source packages just to reduce counts
- do not change `docker-compose.yml` or protected runtime files as part of documentation cleanup
- do not collapse domain tools into one mega-dashboard
- do not create another new active governance layer while cleaning duplicates

## Practical Rule

When two artifacts look similar, ask:

1. do they own the same decision
2. do they compete as the same operator starting point
3. do they both look active

If yes, keep one canonical and demote the other.
If not, keep both and make the difference easier to see.
