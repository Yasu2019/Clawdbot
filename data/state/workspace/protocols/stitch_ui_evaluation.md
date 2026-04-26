# Stitch UI Evaluation Protocol

## Purpose

Use Stitch as a UI design accelerator for OpenClaw and Portal-facing apps.
Do not use Stitch as authority for backend design, permissions, or infrastructure decisions.

## Adoption Policy

Stitch should be used as `partial adoption` by default.

### Good Use Cases

- New Portal card layouts
- Dashboard redesign drafts
- Existing app visual refresh proposals
- Multi-option UI comparison before implementation
- Design-to-code acceleration for static or lightly interactive screens

### Do Not Use Stitch For

- Database schema changes
- Auth or permission logic
- Reverse proxy, compose, or port design
- Backend API contract changes
- Approval-flow business rules

## Standard Workflow

1. Define the user-facing problem in plain language.
2. Generate 2-3 UI options with Stitch.
3. Compare them against the current app and Portal structure.
4. Run a conflict check before implementation.
5. Implement only the approved parts in repo code.

## Conflict Check List

- Does the draft duplicate an existing Portal card or app?
- Does it require new API routes that do not exist?
- Does it conflict with current CSS or JS patterns?
- Does it introduce decorative UI without operational value?
- Does it imply compose, reverse proxy, or env changes?

## Decision Labels

- `ADOPT`
  Safe and useful with no meaningful conflict.
- `ADOPT_PARTIAL`
  Use only the UI structure or selected sections.
- `HOLD`
  Good idea, but not safe or not aligned yet.

## OpenClaw-Specific Rule

Stitch should produce UI proposals.
Codex should remain responsible for implementation, conflict checks, and integration into the existing stack.
