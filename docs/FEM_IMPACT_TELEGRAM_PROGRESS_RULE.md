# FEM Impact Telegram Progress Rule

Updated: 2026-07-26 JST
Beads: `Clawdbot_Docker_20260125-vdf0`, `Clawdbot_Docker_20260125-tryd`

## Goal

Notify Telegram once at FEM Impact analysis start and once at every 5% from
5% through 95%, without stopping or slowing the solver. The existing final
delivery remains responsible for 100%.

## Context and observed facts

- Solver host: ThinkPad L590.
- K10 orchestrator: `scripts/k10_tri_track_cae_orchestrator.py`.
- Monitor: `scripts/fem_impact_progress_telegram.py`.
- Impact input declares the simulation range as `run from <start> to <end>`.
- Result names contain simulation time, for example
  `*_surface_0.001500.vtk`.
- The active 2026-07-25 forming run had no VTK yet when monitoring was attached;
  therefore its initial notification is text and later notifications use images.

## Decision rule

IF a FEM Impact job starts, THEN launch one monitor using the same trial ID,
case directory, input name, and declared end time, BECAUSE the monitor can
derive deterministic progress from VTK simulation time without interrogating
or interrupting the Java solver.

Each stage is persisted only after Telegram reports success. A restarted
monitor reads this state and must not resend a completed stage.

## Procedure

1. Send the 0% start message once.
2. Poll ThinkPad every 30 seconds for the latest matching surface VTK.
3. Calculate `100 * vtk_time / end_time`.
4. At the first observation at or above each 5% milestone from 5% through 95%,
   copy that VTK to K10, render a Von Mises PNG with the `iso` oblique camera,
   and send it once. The oblique projection rotates the XY footprint and exposes
   Z so that thin plates are visibly different from the top view.
5. Persist state under `data/workspace/fem_impact_progress/<trial_id>.json`.
6. Never stop, signal, or renice the solver from the progress monitor.

## Verification

- Python compilation passes for both scripts.
- The active-run state shows `sent: [0]`, `running: true`, and no error.
- Pass for later stages: state contains each of `5`, `10`, ... `95` once and
  the corresponding `stage_<percent>_vtk` path.

## Failure signatures and recovery

- `latest_vtk: null`: solver has not emitted its first VTK; continue polling.
- `SCP failed`: retain the unsent stage and retry on the next poll.
- `renderer produced no PNG`: verify VTK completeness and local VTK package.
- Telegram failure: do not mark the stage sent; retry.
- Rollback: stop only the monitor process. It is independent of `run.Impact`.

## Scope limits

Progress is simulation-time progress, not an estimate of wall-clock completion.
The monitor does not claim convergence or final quality before the normal QC.
