# System Refactor Assessment

Date: 2026-04-04
Scope: repository-wide refactor necessity check for Docker, Portal, protocol, routing, and app layers

## Conclusion

This repository does not currently need a full system-wide refactor.

It does need a targeted consolidation pass.

Recommended stance:

- `REFACTOR_NOW`: protocol and routing documentation layer
- `MERGE`: portal and hub entry-point layer
- `HOLD`: core Docker and stable service wiring
- `HOLD`: workflow engine replacement or broad framework replacement

The current risk is not primarily "broken architecture".
The current risk is "too many overlapping control surfaces".

## Why This Is The Right Level

Observed repo pattern:

- Many protocol ZIPs and reference docs exist alongside active project rules.
- The Portal has many app entry points and hub-style pages.
- Routing and orchestration guidance already exists in multiple places.
- `AGENTS.md` explicitly prefers extension, partial adoption, and non-invasive rollout over large replacement.

This means a full refactor would carry high coordination risk while solving the wrong problem.
The highest-value move is to reduce duplicated guidance and duplicated entry points first.

## Inventory Memo

### 1. Core governance already exists

Existing sources already define safety and adoption rules:

- `AGENTS.md`
- `implementation_plan.md`
- `data/workspace/CODEX_PROTOCOL_REFERENCE.md`
- `data/workspace/apps/cmux_hub/index.html`
- `data/state/workspace/protocols/context_budget_protocol_20260404.md`

### 2. Portal surface is broad

The Portal app layer already contains many hubs and tool pages, including:

- `cmux_hub`
- `codex_protocol_hub`
- `operations_toolbox`
- `observability_hub`
- `learning_memory`
- `qms_audit`
- domain-specific hubs such as `dxf_fcstd_protocol`, `gdt_overlay_studio`, `kinematics_hub`

This is useful, but it increases navigation and ownership ambiguity.

### 3. Docker core is protected on purpose

`AGENTS.md` explicitly says core files such as `docker-compose.yml` should not be changed casually.
That matches the current repo condition: additive patches and host-side harnesses are safer than a deep compose rework.

## Decision Table

| Area | Decision | Why | Recommended action |
|---|---|---|---|
| Protocol / routing docs | REFACTOR_NOW | Clear overlap across AGENTS, Codex protocol docs, cmux routing, and new ZIP packages | Create one canonical routing policy and demote the rest to references |
| Portal / hub entry points | MERGE | Many app landing pages are useful but scattered | Create a thinner top-level navigation model and group pages by function |
| Skills / handoff packages | MERGE | Valuable in narrow roles, but broad framework replacement would duplicate existing control layers | Keep focused skills, avoid replacing the active project-wide layer |
| Core Docker compose | HOLD | High blast radius and protected by repo rules | Only make targeted fixes with explicit implementation plans |
| Stable service wiring | HOLD | Existing services appear additive rather than fundamentally blocked | Improve observability and ownership before restructuring |
| n8n / automation landscape | HOLD | Can grow messy, but replacement is riskier than controlled cleanup | Prefer workflow audit and retirement list over engine changes |
| IATF / app domain internals | TARGETED ONLY | Some domains already benefited from focused refactors | Continue service extraction where pain is concrete |

## What Should Be Refactored Now

### A. Canonical control layer

Create a single canonical document for:

- routing policy
- escalation rules
- review triggers
- adoption status
- no-go conditions

Everything else should become one of:

- reference
- example
- archive
- package input

### B. Portal entry model

Reduce the number of "first places to click".

Preferred top-level groups:

- Operations
- Protocols
- Quality
- Geometry / CAD
- Observability
- Archive / Experimental

This is a navigation refactor, not a UI rewrite.

### C. Ownership map

Define which layer owns which decision:

- `AGENTS.md`: non-negotiable operating constraints
- canonical routing doc: agent/task assignment rules
- Portal: discovery and operator navigation
- skills: narrow execution accelerators
- ZIP packages: importable handoff bundles, not primary governance

## What Should Not Be Refactored Yet

### A. Full Docker redesign

Do not start with:

- compose service split/merge campaign
- cross-container renaming
- new orchestration backbone
- broad container replacement

That is high risk and not justified by the current evidence.

### B. Full framework replacement

Do not replace the current project control model with:

- a Claude-centered global framework
- a new workflow engine
- a new portal system
- a second parallel governance layer

This repo already has those responsibilities covered.

## Practical Trigger Rules

Use `full refactor` only if at least two of these become true:

- the same feature is maintained in multiple active implementations
- small changes require touching many unrelated layers
- conflicting rules between governance documents cause repeated mistakes
- portal discovery becomes materially slower than direct path usage
- rollback or incident handling is blocked by ambiguous ownership

Today, the stronger case is for consolidation, not overhaul.

## Recommended Sequence

### Phase 1

- Write one canonical routing and adoption document
- Mark overlapping ZIP packages and protocol docs as `reference` or `candidate`
- Define a short do-not-duplicate rule for new protocol additions

### Phase 2

- Simplify Portal top-level navigation
- Group existing apps by functional domain
- Move low-traffic or proposal-only pages under archive or experimental sections

### Phase 3

- Audit active automations and hubs for duplicates
- Retire or hide unneeded surfaces
- Reassess whether any Docker or service-level refactor is still necessary

## No-Go Conditions

Stop and reassess if a proposed refactor:

- requires broad `docker-compose.yml` edits without a new implementation plan
- creates another parallel routing or policy layer
- replaces a working system without benchmark or operational evidence
- increases hidden automation before read-only observability is improved

## Short Answer

The system needs a governance-and-entry-point refactor, not a full architectural rewrite.
Start with routing policy, protocol ownership, and Portal consolidation.
Keep core Docker and stable service wiring mostly intact unless a concrete failure pattern justifies deeper change.
