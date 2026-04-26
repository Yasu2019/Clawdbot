# Langfuse Integration

## Purpose
Langfuse should not only observe model calls.
It should also become the evidence backbone for reflection.

## What to capture
- task identifier
- model used
- total tokens
- cost
- latency
- tool calls
- user-visible result
- error events
- evaluator result if available

## Reflection trigger options
1. Per task
2. Per conversation
3. Nightly batch
4. Only on failure
5. Only on expensive tasks

Recommended starting mode:
- only on failure
- plus selected high-value successes

## Why this is better initially
It keeps cost low and avoids generating too much low-value memory.

## Suggested evaluator dimensions
- task completion
- factual grounding
- tool efficiency
- recovery quality
- human edit distance if applicable

## Important rule
Reflection should reference trace evidence.
It should not become disconnected storytelling.
