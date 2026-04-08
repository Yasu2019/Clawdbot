# Canonical Routing And Adoption Policy

Date: 2026-04-04
Status: active
Scope: repository-wide default routing, review, adoption, and ownership rules

## Purpose

This document is the canonical policy for:

- agent/task routing
- review escalation
- protocol adoption decisions
- ownership boundaries between governance layers

Use this document as the primary routing reference.
Other ZIP packages, handoff bundles, and hub pages should be treated as supporting references unless they explicitly replace this file in a future approved change.

## Core Rule

Default operating model:

- Antigravity: planning and decomposition when needed
- Codex: default implementation engine
- Claude-class review: selective high-value review gate

Do not send the same full task and full context to every system by default.

## Routing Rules

### Small tasks

Examples:

- one-file fix
- minor bug
- small config update
- small script adjustment

Default route:

- Codex only
- optional review only if the change is risky

### Medium tasks

Examples:

- several-file feature
- moderate refactor
- app-level wiring
- additive service integration

Default route:

1. Antigravity only if requirements or sequencing are unclear
2. Codex for implementation
3. Claude-class review only on diff or changed files

### Large tasks

Examples:

- new subsystem
- architecture-sensitive workflow
- multi-container change
- production-sensitive operational change

Default route:

1. Antigravity for bounded plan
2. Codex for implementation units
3. Claude-class review at phase boundaries or pre-merge

## Escalation Rules

Escalate to planning when:

- the request is under-specified
- multiple valid paths have different costs or risks
- ownership is unclear
- the implementation path conflicts with existing repo rules

Escalate to review when:

- multiple containers are affected
- rollback is difficult
- security or destructive actions are involved
- the diff is large or hard to reason about
- stable automation or production-sensitive services are touched

Do not escalate when:

- the fix is isolated and obvious
- the review cost is higher than the task impact

## Adoption Rules

Before adopting any new protocol, ZIP, workflow, dashboard, or framework:

1. check for overlap with existing Docker, Portal, n8n, Gmail, DB, routing, and benchmark assets
2. prefer extension over replacement
3. prefer partial adoption over full framework import
4. prefer read-only or observation-first rollout before write automation
5. avoid creating a second active governance layer

## Merge / Hold / Refactor-Now

### Refactor now

- routing and protocol ownership docs
- overlapping handoff and policy bundles
- duplicated agent-assignment guidance

### Merge

- Portal and hub entry points
- narrow skill and handoff packages that fit existing control layers
- documentation that explains already-active systems

### Hold

- core `docker-compose.yml` redesign
- workflow engine replacement
- broad framework replacement
- stable service rewiring without concrete failure evidence

## Ownership Map

### `AGENTS.md`

Owns:

- non-negotiable repo operating constraints
- harness and safety rules
- adoption guardrails
- high-risk restrictions

### Canonical routing policy

Owns:

- default task routing
- escalation triggers
- review triggers
- do-not-route rules
- adoption shorthand for future protocol additions

### Portal and hub pages

Own:

- discovery
- operator navigation
- surfacing active tools and reference docs

Portal pages should not become the primary governance source.

### Skills

Own:

- narrow execution workflows
- project-specific accelerators
- implementation guidance for targeted domains

Skills should not replace the shared repo governance layer.

### ZIP packages and handoff bundles

Own:

- importable handoff material
- reference workflows
- candidate policies under evaluation

They are references unless explicitly promoted.

## Context Budget Rule

Send only the context needed for the current task:

- relevant files
- relevant logs
- acceptance criteria
- known risks

Avoid sending:

- the whole repository
- repeated background on every turn
- unrelated architecture notes

Prefer diffs, summaries, and narrowed file sets over broad context dumps.

## Do-Not-Duplicate List

Do not create new active documents that duplicate:

- agent routing rules already covered here
- adoption criteria already covered in `AGENTS.md`
- Portal navigation lists already covered by Portal hubs
- provider-specific framework rules as a second project-wide standard

If a new package overlaps, mark it as one of:

- `reference`
- `candidate`
- `archive`

not `active`, unless it replaces an older active source through an approved update.

## Rollout Guidance

### Sandbox

- try new routing or protocol additions as reference-only
- verify no overlap with existing active guidance

### Staging

- link the new guidance from existing hubs
- observe whether it reduces confusion and duplicate work

### Production

- promote only after the routing and ownership story is simpler, not more complex
- archive or demote overlapping sources once replacement is confirmed

## Short Policy

Plan only when needed.
Implement with Codex by default.
Use review selectively for high-risk changes.
Prefer extension and partial adoption over replacement.
Keep one active routing policy, not many competing ones.
