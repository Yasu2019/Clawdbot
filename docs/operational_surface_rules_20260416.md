# Operational Surface Rules

Date: 2026-04-16
Status: active memo
Scope: align compose ownership, portal navigation, and governance ownership so active-looking surfaces do not drift apart

## Purpose

This repository has many useful surfaces.
The goal is not to reduce everything to one page or one file.
The goal is to stop multiple surfaces from looking equally canonical when they are not.

This memo is the short cross-cutting rule set that connects:

- governance ownership
- portal and app entry points
- compose ownership

## Three Ownership Questions

Before promoting a file, page, or workflow, answer these:

1. does it own a decision
2. does it own a first click
3. does it own a runtime

If the answer is unclear, do not present it as canonical yet.

## Governance Rule

Canonical governance lives in documents, not in scattered portal copy.

Primary governance anchors:

- `AGENTS.md`
- `docs/canonical_routing_and_adoption_20260404.md`
- `docs/duplication_cleanup_plan_20260416.md`

Supporting governance maps:

- `docs/canonical_entrypoint_map_20260416.md`
- `docs/compose_ownership_memo_20260416.md`

Working rule:

- portal and app pages may explain roles
- docs own the final decision about what is canonical

## Portal Rule

Portal surfaces must declare one of four roles:

- primary entry
- detail page
- reference page
- maintenance page

Featured styling should be reserved for:

- repository-wide primary entries
- domain primary entries
- rare, high-frequency launchers that genuinely behave like first-stop surfaces

Featured styling should not be used for:

- reference-only pages
- maintenance-only pages
- deep investigation pages that are not the normal start

Current examples:

- keep featured: `OpenClaw Chat`, `Inbox Uploader`, `Ingestion / RAG Control Center`, `3D Workbench`
- do not feature by default: `Operations Toolbox`, `System Role Map`, `Cmux Hub`, `Learning Memory`, `Email Search`, `AI Strategy Scout`, `Mfg Engineering Simulator`

See `docs/featured_surface_inventory_20260416.md` for the current featured-card rationale.

## Compose Rule

Compose ownership must be explicit before any runtime change.

Working split:

- repo root runtime: `docker-compose.yml`
- domain-local runtime: `iatf_system/docker-compose*.yml`
- imported or example runtime material: `clawstack_v2/**/docker-compose*.yml`, temp review examples

Working rule:

- do not infer runtime authority from filename count
- check the compose ownership memo before changing or invoking a stack

## Cross-Surface Promotion Rule

A new surface may be promoted only if all three of these are true:

1. it does not duplicate an existing first click
2. it has a clear owner category: governance, runtime, domain entry, detail, reference, or maintenance
3. its promotion does not make another canonical surface ambiguous

If any of these fail, use one of these instead:

- keep it as reference
- keep it as detail
- keep it as maintenance-only
- document it first and delay UI promotion

## Quick Decision Grid

| Surface type | Canonical home | UI treatment | Notes |
|---|---|---|---|
| governance decision | docs | link only | docs own the decision |
| repo-wide start page | portal | featured allowed | only one main launcher |
| domain start page | domain app | featured allowed sparingly | one per domain |
| detailed investigation | domain app | normal card | should point back to the start page |
| reference / map | docs or app | normal card | never pretend to be daily first stop |
| maintenance / repair | ops app | normal card | visible but not promoted as daily path |
| runtime definition | compose docs + files | no portal promotion needed | ownership must be documented |

## Current Repository Outcome

As of 2026-04-16:

- governance is anchored in `AGENTS.md` and canonical docs
- portal launch ownership is anchored in `docs/canonical_entrypoint_map_20260416.md`
- compose ownership is anchored in `docs/compose_ownership_memo_20260416.md`
- maintenance surfaces remain available but should not compete visually with normal first-click paths

## Follow-Up Rule

When editing a launcher card, make the role explicit in the description before changing the styling.
When editing a compose file, confirm ownership in docs before touching runtime behavior.
When adding a governance note, link it back to the canonical docs instead of creating another parallel authority.
