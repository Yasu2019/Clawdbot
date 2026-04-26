# Ollama and LiteLLM Strategy

## Goal
Use local models for cheap reflection and cloud models for higher-risk reasoning.

## Recommended split
Local models:
- reflection
- summarization of traces
- memory compression
- tag generation
- batch consolidation

Cloud models:
- complex planning
- user-facing high-stakes synthesis
- ambiguous troubleshooting
- nuanced judgment tasks

## LiteLLM routing policy concept
Example logic:
- if job_type == "reflection" and context <= threshold: local
- if job_type == "memory_compression": local
- if job_type == "final_user_response" and confidence low: cloud
- if job_type == "critical_diagnosis": cloud or best available

## Failure handling
If local model quality is insufficient:
- mark reflection as low confidence
- do not auto-inject
- optionally escalate to cloud review

## Practical warning
A cheap reflection model that produces many bad lessons can damage the system more than having no reflection at all.
Quality gating matters.
