# Qdrant Collection Schema Proposal

## Collection A: docs_knowledge
Purpose:
- document RAG
- manuals
- internal procedures
- notes
- PDFs and parsed text

Example payload fields:
- source_type
- file_name
- document_id
- page
- section
- tags
- created_at
- updated_at

## Collection B: agent_experience
Purpose:
- lessons learned
- prior task outcomes
- troubleshooting memories
- execution heuristics

Example payload fields:
- task_type
- task_summary
- result_status
- context_tags
- quality_score
- freshness_class
- approved_for_retrieval
- timestamp_utc

## Collection C: tool_playbooks
Purpose:
- stable step-by-step procedures
- manually curated best practices
- consolidated memory playbooks

Example payload fields:
- playbook_name
- tool_family
- trigger_conditions
- do_first
- avoid
- validation_steps
- owner
- version

## Embedding strategy
Recommended:
- use the same embedding family for all memory collections only if operationally convenient
- otherwise allow separate embedding models for docs vs experience

## Indexing guidance
Add payload filters for:
- task_type
- approved_for_retrieval
- timestamp range
- quality_score threshold
- environment name
- project name

## Retrieval guidance
Retrieve top-k from experience memory with strong metadata filtering.
Do not let weakly related experience entries dominate the prompt.
