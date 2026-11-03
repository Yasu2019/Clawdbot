# RULE-OBJECTIVE-FOLLOWTHROUGH-20261103

User instruction, recorded 2026-11-03 23:37 JST. Applies to all authorized tasks, including downloads, application installation and FEM/CAE. Related incidents: INC-K10-FLUX-SILENT-IDLE-20261103-01 and INC-FEM-TERMINATION-UNATTENDED-20261103.

If work stops before the user's objective is achieved, the agent MUST implement an appropriate improvement, verify its effect, and continue autonomous investigation/improvement toward the objective. Merely recording the incident, creating a script, launching a process, registering a watcher or observing exit0 does not achieve the objective. Repeated failure must lead to a reviewed change, not the same unsupported retry.

Define acceptance evidence before dispatch. Preserve partial outputs and verified checkpoints. Inspect live ownership/processes/queues/tasks before recovery. Use an owned bounded supervisor and an independent finite liveness/terminal watcher for unattended stages. Report ACTIVE, HELD, INCOMPLETE and COMPLETE separately. COMPLETE requires the actual requested artifact/service/result, verified from current authoritative evidence. A future URL or a saved status is not current service readiness.

On an unsuccessful terminal transition: preserve exact error/evidence, make failure visible, classify the cause as verified/hypothesized/UNKNOWN, implement and validate a safe correction, and continue within the existing authorization. Retries must be bounded and provenance-aware. For an external/authentication/safety/approval blocker, explicitly report the precise blocker and required input; do not silently idle or represent a blocked state as progress. Do not promise future chat notification without a real supported mechanism. Notification accepted and user read are distinct states.

This rule does not authorize stopping/deleting/reusing unrelated legacy work, overriding user approval gates, weakening security/physical limits or blind-retrying numerical failures. Preserve all checkpoint, CPU/RAM, disk identity, storage-retention and route-classification rules. If an autonomous step requires unavailable user authorization, complete independent safe work and request the exact missing authorization with its source.

## FMEA policy control

Failure mode: premature disengagement while objective is unmet. Effect: silent idle/user wait. Causes: missing acceptance gate, finite worker exit without continuation/alert, dispatch conflated with result. Controls: objective-level acceptance checks, owned recovery, independent finite watcher and visible terminal status. Owner: active task agent; validation is case-specific. S/O/D/RPN unassessed.

## FTA policy control

Top event: unmet objective silently abandoned. AND: objective incomplete AND no effective continuation/escalation. OR branches of incomplete objective: transfer/compute/application failure, admission-held stage, missing validation. Branch evidence must be recorded per incident; this policy does not prove root causes.

## QC process chart policy control

Objective/acceptance → live admission/ownership/recovery checks → execute/supervise → inspect artifacts/service → if incomplete, diagnose/correct/validate/continue → only then COMPLETE or explicit evidenced blocker. Records link the same incident ID in Beads, canonical Markdown and destination receipts.

## Control Plan policy control

Characteristics: objective acceptance, liveness, numerical/artifact validity, terminal notice. Method/timing: task-specific checks before dispatch, during finite execution and at every terminal transition. Limit: requested acceptance criteria, not invented generic limits. Reaction: preserve evidence, implement/validate improvement, continue authorized recovery or explicitly escalate a real blocker. Recording alone is not proof of prevention. Each destination is reported as readback-verified, saved-unverified, pending, failed or unattempted.
