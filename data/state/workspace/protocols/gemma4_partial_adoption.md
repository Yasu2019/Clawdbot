# Gemma 4 Partial Adoption Protocol

## Purpose

Add Gemma 4 to the stack as an experimental local model path without replacing the current cloud-first routing.

## Default Stance

- Use `ADOPT_PARTIAL` by default.
- Keep `google/gemini-2.5-flash` as the primary model.
- Treat Gemma 4 as a local cost-saving and low-risk acceleration path.

## Good First Use Cases

- Summarization of local notes or documents
- Structured extraction from PDFs, emails, or markdown
- Classification and tagging
- RAG answer drafting before human review
- Lightweight code explanation and draft generation

## Do Not Route Here First

- Final customer-facing wording
- High-stakes quality conclusions
- Compliance or legal interpretation
- Final RCA / FMEA / FTA conclusions without review
- Approval-sensitive workflow decisions

## Rollout Order

1. Verify that a real `gemma4` model exists in Ollama.
2. Enable LiteLLM aliases only after verification.
3. Start with read-only and draft-only tasks.
4. Measure quality against existing Gemini or Qwen routes.
5. Promote only if the benchmark is acceptable and no regression appears.

## Validation Checklist

- Does Ollama actually expose a `gemma4` tag?
- Does LiteLLM alias routing work end-to-end?
- Does the response quality match the intended low-risk task?
- Is latency acceptable on the current MiniPC?
- Does it avoid regressions in Qdrant, n8n, Paperless, and Portal-linked flows?

## Decision Labels

- `ADOPT`
  Safe enough for the target task set and verified locally.
- `ADOPT_PARTIAL`
  Enable only for low-risk and draft-oriented tasks.
- `HOLD`
  Keep documented, but do not activate yet.

## Current Project Rule

Until a real Gemma 4 Ollama tag is detected locally, keep the integration in `ready_when_pulled` state and do not switch any default route.
