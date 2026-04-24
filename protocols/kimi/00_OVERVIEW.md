# Kimi K2.6 Integration Protocol for Full Autonomous Operation

## Goal
Integrate Kimi K2.6 into the user's existing Clawstack/OpenClaw local-first environment as a high-throughput autonomous worker model for:
- large-scale document summarization
- multi-file code generation/refactoring
- agent swarm style decomposition
- QA / IATF document review assistance
- batch data analysis orchestration

## User environment assumptions
- Windows 11 Pro host
- Main working directory: D:\Clawdbot_Docker_20260125
- Active stack centered around clawstack_v2
- Docker Desktop + WSL2 backend
- Existing local services likely include:
  - OpenClaw Gateway
  - LiteLLM Proxy
  - Ollama
  - Qdrant
  - Infinity embeddings
  - Paperless-ngx
  - Docling
  - n8n
  - Langfuse
  - Nginx Portal
- Strong preference for loopback-only binding (127.0.0.1)
- Strong preference for privacy and minimizing cloud leakage

## Executive recommendation
Recommended posture:
- Adopt Kimi K2.6 as a specialized worker model, not as the only model
- Keep final approval / final judgment with Claude Code or another stronger reviewer model
- Route sensitive data only to local or self-hosted model endpoints
- Route non-sensitive batch jobs to Kimi only after policy review

## Best-fit role for Kimi
Use Kimi mainly for:
- decomposition-heavy work
- multi-step autonomous tasks
- large context intake
- many-file processing
- tool-using worker tasks

Do NOT use Kimi as the sole authority for:
- final compliance judgment
- final customer-facing legal or regulatory wording
- unchecked production DB modification plans
- safety-critical approvals without human verification

## Recommended deployment modes
Priority order:
1. Local/self-hosted weights if feasible
2. Private on-prem inference server
3. Remote API only for non-confidential workloads

## Core design principle
Use a tiered model architecture:
- Tier A: Kimi worker swarm for scale and throughput
- Tier B: trusted reviewer model for final synthesis
- Tier C: local embedding/RAG for memory retrieval
- Tier D: workflow controls, logging, rollback, and human escalation
