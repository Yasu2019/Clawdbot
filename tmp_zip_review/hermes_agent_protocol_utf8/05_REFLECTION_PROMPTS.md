# Reflection Prompts

## Simple reflection prompt
You are a reflection engine.
Convert the completed task trace into a reusable lesson.
Return concise structured output only.

Required fields:
- task_summary
- user_goal
- result_status
- root_causes
- effective_actions
- ineffective_actions
- recommended_next_time
- avoid_next_time
- lesson_text
- quality_score
- approved_for_retrieval

Rules:
- Prefer concrete operational lessons.
- Do not invent evidence not present in the trace.
- Distinguish clearly between fact and inference.
- Keep lesson_text under 40 words.

## More detailed reflection prompt
Analyze the following completed task.
Extract only the lessons that would improve future execution.
Ignore stylistic details unless they affected the outcome.

Produce:
1. Failure analysis
2. Success pattern
3. Reusable operational advice
4. Retrieval tags
5. Confidence score
6. Whether this memory should be injected automatically next time

## Compression prompt for repeated memories
You are consolidating multiple similar memory entries into one playbook.
Preserve the common operational truth.
Remove one-off noise.
Keep the output human-auditable.
