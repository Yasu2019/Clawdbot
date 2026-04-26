# Target Architecture

## High-level architecture

1. User/UI Layer
- OpenClaw Gateway
- Portal cards
- Optional n8n forms/webhooks

2. Orchestration Layer
- LiteLLM Proxy
- n8n workflow engine
- OpenClaw tool routing / MCP server

3. Intelligence Layer
- Kimi K2.6 worker endpoint
- Claude Code or other reviewer model
- local Ollama fallback models

4. Knowledge Layer
- Qdrant
- Infinity embeddings
- Paperless ingestion
- Docling extraction

5. Observability Layer
- Langfuse
- portal observability hub
- container logs

## Recommended task routing
### Route to Kimi
- many documents
- many source files
- first-pass summarization
- codebase indexing/extraction
- agentic subtasks
- large-context preprocessing

### Route to reviewer model
- final decision memo
- final customer email draft
- final compliance wording
- risky code change review
- change approval summary

### Route to local Ollama fallback
- offline-only mode
- private quick summaries
- non-critical helper tasks
- degraded mode when cloud or Kimi unavailable

## Data flow example for QA document review
1. Paperless ingests PDF
2. Docling extracts text/markdown
3. Qdrant stores embeddings
4. n8n triggers review job
5. Kimi reads retrieved chunks + task spec
6. Kimi produces findings and draft actions
7. reviewer model checks accuracy and tone
8. result posted to portal / report / email draft

## Deployment boundary principle
- Keep external access off by default
- Bind services to 127.0.0.1 where possible
- Keep secrets in .env only, never hardcode
- Keep a kill-switch for Kimi workflows
