# Implementation Protocol

## Goal
Add Hermes-style self-improvement to an existing agent stack without breaking current production behavior.

## Phase 1: Passive observation only
Do not let memory modify agent behavior yet.
First capture:
- task summary
- tool sequence
- final result
- success/failure
- cost
- latency
- notable errors

Output:
- structured trace records
- no automatic prompt injection yet

## Phase 2: Reflection generation
After each meaningful task or session, generate a reflection object.

Reflection should answer:
- What was the user trying to achieve?
- What worked?
- What failed?
- Why did it fail?
- What should be repeated next time?
- What should be avoided next time?
- Which tools/models were best suited?

## Phase 3: Controlled memory retrieval
For selected task classes only, inject retrieved lessons into the prompt.
Start with:
- recurring coding tasks
- recurring environment troubleshooting
- repetitive document workflows
- common automation tasks

Avoid early injection for:
- creative writing
- sensitive reasoning
- high-stakes actions without review

## Phase 4: Confidence gating
Only inject memory when:
- similarity score is high enough
- memory freshness is acceptable
- lesson quality score is above threshold
- the lesson is not contradicted by newer evidence

## Phase 5: Consolidation
Merge repeated similar memories into compact playbooks.
Example:
- recurring Docker port conflict fixes
- repeated Ollama timeout workarounds
- common Qdrant dimension mismatch resolution steps

## Operational rule
The system must be able to answer:
"Why was this lesson injected?"
If not, the memory mechanism is too opaque.

## Safety rule
Never let unreviewed reflection objects automatically rewrite core system files in early stages.

## Data retention rule
Keep raw traces and derived lessons separately.
Raw traces are evidence.
Derived lessons are interpretation.
