# Hermes-Style Self-Improving Agent Protocol Pack

This package is designed to minimize mojibake risk:
- All filenames use ASCII only.
- All text files are UTF-8 encoded.
- Markdown is used as the primary format.
- JSON/YAML examples are included in plain text.

## Purpose
This pack helps convert an existing local AI stack into a Hermes-style self-improving agent system.

## Assumed starting environment
- OpenClaw or equivalent general-purpose agent runtime
- LiteLLM router
- Ollama local models
- Qdrant vector database
- Langfuse observability
- Paperless / Docling / RAG pipeline already present or planned
- Docker / WSL2 based local operation

## Package contents
- 01_EXECUTIVE_SUMMARY.md
- 02_TARGET_ARCHITECTURE.md
- 03_IMPLEMENTATION_PROTOCOL.md
- 04_MEMORY_SCHEMA.json
- 05_REFLECTION_PROMPTS.md
- 06_QDRANT_COLLECTION_SCHEMA.md
- 07_LANGFUSE_INTEGRATION.md
- 08_OLLAMA_AND_LITELLM.md
- 09_AUTOMATION_WORKFLOWS.md
- 10_ROLLOUT_PLAN.md
- 11_ACCEPTANCE_CHECKLIST.md
- 12_CODEX_OR_CLAUDE_HANDOFF.md

## Important policy
Adoption is not mandatory.
The receiving Codex or Claude instance should evaluate each item and decide whether to adopt, modify, or reject it.
This pack is a proposal, not a forced implementation.
