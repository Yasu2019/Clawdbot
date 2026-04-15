# Rollout Plan

## Stage 0: Baseline
Existing stack runs normally.
No self-improvement behavior yet.

## Stage 1: Logging only
Duration:
- about 1 to 2 weeks of normal usage

Success criteria:
- traces captured reliably
- error categories visible
- no user-facing regressions

## Stage 2: Reflection only
Enable offline or background reflection generation.
Still no prompt injection.

Success criteria:
- reflections are mostly accurate
- quality scoring is stable
- obviously bad lessons are rare

## Stage 3: Limited injection
Restrict to one or two safe task classes.

Success criteria:
- fewer repeated mistakes
- no obvious hallucinated lessons
- measurable improvement in task recovery

## Stage 4: Playbook consolidation
Convert repeated lessons into durable operational playbooks.

Success criteria:
- prompt size becomes more efficient
- repeated troubleshooting speeds up
- human reviewers trust the stored guidance

## Stage 5: Broad deployment
Expand to more workflows only after clear evidence of value.
