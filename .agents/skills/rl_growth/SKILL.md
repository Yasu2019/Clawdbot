---
name: rl_growth
description: Agent Self-Growth Protocol. Use for self-evaluation, recursive task improvement, and maintaining success/failure memory in Qdrant.
---

# RL Self-Growth Protocol

This skill enables Antigravity to learn from its own outputs and user feedback loops. It utilizes Langfuse for tracing and Qdrant for storing "Success Patterns" and "Failure Countermeasures".

## Core Loop
1. **Execute Task**: Perform the engineering task as requested.
2. **Self-Evaluate**: Review the outcome against defined KPIs (Correctness, Safety, Efficiency).
3. **Generate Improvement**: If the outcome was sub-optimal, generate a "Refined Version" or "Countermeasure".
4. **Store Memory**: Save the tuple (Task Input, Outcome, Score, Improved Logic) to Qdrant.
5. **Retrieve & Apply**: On subsequent similar tasks, search Qdrant for past patterns and inject them into the current prompt/plan.

## Operational Instructions
- When starting a complex task, ALWAYS check the `agent_self_growth_memory` collection in Qdrant for similar past cases.
- After a long session or a task with significant user revision, run a "Self-Growth Routine" to distilled the lessons learned.
- Refer to the full documentation in `d:\Clawdbot_Docker_20260125\.agents\knowledge\rl_growth\` for specific scoring schemas and prompt templates.

## Infrastructure
- **Qdrant Collection**: `agent_self_growth_memory` (Vector: 1536 dim, cosine similarity).
- **Langfuse Tags**: `self-growth`, `rl-loop`.
- **Knowledge Base**: Curated via ByteRover (`brv`).
