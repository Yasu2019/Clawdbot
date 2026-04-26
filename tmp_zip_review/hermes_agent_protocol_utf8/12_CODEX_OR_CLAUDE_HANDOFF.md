# Handoff Instructions for Codex or Claude

This package is a proposed protocol for adding Hermes-style self-improvement to an existing local AI stack.

## Required stance
Do not assume every design in this package should be implemented as-is.
Evaluate each component critically.

## You may:
- adopt parts unchanged
- modify parts
- reject parts
- replace parts with better alternatives

## Priorities
1. Preserve system stability
2. Preserve auditability
3. Keep costs reasonable
4. Improve repeated-task performance
5. Avoid fragile over-automation

## Strong recommendations
- implement passive logging first
- keep reflection and raw traces separate
- gate retrieval aggressively at the beginning
- prefer compact playbooks over uncontrolled memory growth

## Explicit non-requirement
A full reinforcement learning stack is not required.
A disciplined reflection-memory-retrieval loop is sufficient for practical gains.

## Desired deliverable from the receiving system
Please return:
- accepted items
- modified items
- rejected items
- rationale
- implementation order
- rollback strategy
