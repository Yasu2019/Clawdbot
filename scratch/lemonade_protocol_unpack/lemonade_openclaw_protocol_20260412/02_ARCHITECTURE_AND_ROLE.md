# Architecture and Role Definition

## Current stack understanding
The current environment already has a strong local stack:
- OpenClaw Gateway for orchestration and agent control
- LiteLLM for provider abstraction and routing
- Ollama for local LLM inference
- n8n for workflow automation
- Qdrant and related components for RAG / memory
- Portal apps for operational UI

## Correct role of Lemonade
Lemonade should be treated as:

**A multimodal service layer that exposes OpenAI-compatible APIs**

It is not automatically the best replacement for all existing model-serving functions.

## Recommended architecture

```text
User / VS Code / Portal / n8n
          |
          v
     LiteLLM Router
       /        \
      /          \
  Ollama       Lemonade
 (LLM main)   (speech/image/multimodal)
      \          /
       \        /
        OpenClaw Orchestration
                |
                v
          RAG / Memory / Tools
```

## Functional split
### Ollama should remain primary for:
- main coding assistant models
- Qwen family
- DeepSeek family
- local reasoning-heavy text tasks
- stable existing integrations already in production

### Lemonade should be evaluated for:
- speech-to-text
- text-to-speech
- image generation or visual API unification
- standardized local OpenAI-compatible endpoint strategy
- future NPU-aware experiments on newer hardware

## Strategic benefit
The real benefit is not only raw inference speed.
The bigger benefit is **API consolidation**.

That means tools can point to one normalized style of interface rather than each tool requiring a custom adapter.

## Key design principle
**Parallel introduction first, replacement never first.**
