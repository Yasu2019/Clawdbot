# Compose Ownership Memo

Date: 2026-04-16
Status: active memo
Scope: identify which compose files are canonical, domain-local, patch-only, imported, or example-only

## Purpose

This repo has multiple `docker-compose*.yml` files for different reasons.
The risk is not their existence.
The risk is operators or future agents treating the wrong file as the active runtime source.

This memo reduces that ambiguity.

## Classification

### 1. Canonical root stack

Primary files:

- `docker-compose.yml`
- `docker-compose.addons.yml`

Role:

- current top-level Clawstack unified runtime
- the main compose surface for repo-level local operations

Interpretation:

- `docker-compose.yml` is the primary root stack
- `docker-compose.addons.yml` is not the primary runtime definition anymore; it is a deprecated or legacy additive file kept for reference and selective history

Working rule:

- treat `docker-compose.yml` as the main active stack
- do not use `docker-compose.addons.yml` as a starting point for new rollout work unless a change is explicitly about legacy addon history

## 2. Domain-local stack: IATF system

Files:

- `iatf_system/docker-compose.yml`
- `iatf_system/docker-compose.override.yml`
- `iatf_system/docker-compose.production.yml`

Role:

- local stack definitions for the Rails-based IATF domain
- separate from the root Clawstack runtime

Interpretation:

- `iatf_system/docker-compose.yml` is the local development base for that domain
- `iatf_system/docker-compose.override.yml` is a local override layer
- `iatf_system/docker-compose.production.yml` is the production-oriented variant for that domain

Working rule:

- treat these as a self-contained domain compose family
- do not confuse them with the root stack

## 3. Imported legacy stack: clawstack_v2

Files:

- `clawstack_v2/docker-compose.yml`
- `clawstack_v2/docker-compose.learning_engine.patch.yml`

Role:

- imported or inherited stack material from `clawstack_v2`
- used as historical architecture input and selective patch reference

Interpretation:

- `clawstack_v2/docker-compose.yml` is explicitly marked deprecated in its own header and should not be treated as the current repo root runtime
- `clawstack_v2/docker-compose.learning_engine.patch.yml` is patch-only material for that imported stack family

Working rule:

- use these as reference or migration material only
- do not treat them as the active top-level compose entry for this repo

## 4. Imported product-local stack: Open Notebook

Files:

- `clawstack_v2/open-notebook/docker-compose.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-dev.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-full-local.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-ollama.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-single.yml`
- `clawstack_v2/open-notebook/examples/docker-compose-speaches.yml`

Role:

- upstream or product-local runtime material for the imported Open Notebook project
- examples for that subproject, not for the root repo

Working rule:

- treat the top-level Open Notebook compose as product-local reference
- treat all `examples/docker-compose-*.yml` files as example-only
- do not use these as repo-wide runtime guidance

## 5. App-local compose files under workspace apps

Example:

- `data/workspace/apps/minigame_factory/docker-compose.yml`

Role:

- app-local compose for a bounded workspace app

Working rule:

- treat these as app-scoped runtime helpers, not as core infrastructure definitions

## 6. Temp review and package example compose files

Example:

- `tmp_zip_review/AI_完全実装版パック_UTF8_20260411/docker-compose.example.yml`

Role:

- package input or review artifact

Working rule:

- never treat temp review compose files as active runtime sources

## Practical Ownership Table

| File or family | Status | Owner level | Use |
|---|---|---|---|
| `docker-compose.yml` | active | repo root | primary runtime reference |
| `docker-compose.addons.yml` | legacy reference | repo root | historical addon layer, not primary |
| `iatf_system/docker-compose*.yml` | active domain-local | subproject | IATF-only operations |
| `clawstack_v2/docker-compose.yml` | imported deprecated | imported stack | reference only |
| `clawstack_v2/docker-compose.learning_engine.patch.yml` | patch-only | imported stack | reference for selective imported activation |
| `clawstack_v2/open-notebook/docker-compose.yml` | imported product-local | imported subproject | product reference |
| `clawstack_v2/open-notebook/examples/docker-compose-*.yml` | example-only | imported subproject | examples only |
| `data/workspace/apps/*/docker-compose.yml` | app-local | workspace app | bounded local use only |
| `tmp_zip_review/**/docker-compose*.yml` | archive or review input | temp review | never active |

## No-Go Conditions

- do not modify compose files just to reduce counts
- do not merge root and IATF compose families
- do not promote imported example compose files into active repo guidance
- do not use deprecated imported compose files as if they were the current root runtime

## Recommended Next Cleanup

1. add brief ownership notes where operators are likely to start from the wrong file
2. keep root and domain-local compose families clearly separate in docs
3. if future cleanup happens, archive or hide review-temp compose examples before touching active runtime files
