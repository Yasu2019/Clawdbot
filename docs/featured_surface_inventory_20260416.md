# Featured Surface Inventory

Date: 2026-04-16
Status: active UI ownership memo
Purpose: record which launcher cards are intentionally highlighted and why

## Rule

`featured` styling is not a popularity badge.
It is a visibility signal for pages that are either:

- a repository-wide first-stop surface
- a domain first-stop surface
- a very frequent action launcher that behaves like a first-stop tool

If a page is valuable but does not meet one of those roles, keep it visible as a normal card.

## Keep Featured

### `OpenClaw Chat (AI)`
Reason: High-frequency conversational launcher.

### `Inbox Uploader`
Reason: High-frequency action launcher for file ingestion.

### `7-Domain Canonical Starts`
Reason: These are the primary entry points for each functional area as defined in the `canonical_entrypoint_map_20260416.md`.

1. **Operations Toolbox** (Ops)
2. **IATF System (Rails)** (Quality)
3. **3D Workbench** (Geometry)
4. **Radioss Hub** (CAE)
5. **Ingestion / RAG Control Center** (Ingestion)
6. **Learning Memory** (Learning)
7. **AI Content Factory** (Content)

## No Longer Featured
- **Quick Routes Strip**: Redundant when domain starts are clearly highlighted in the main grid.
- **Operations Toolbox (Manual)**: Merged into the 7-domain canonical set.
- **Mfg Engineering Simulator**: Supporting domain tool, not a first-stop launcher.
- **AI Strategy Scout**: Supporting tool under the Learning domain.

## Current Outcome
The featured surfaces are now mapped 1:1 to the canonical functional domains plus the 2 high-frequency action launchers (Chat and Uploader).

