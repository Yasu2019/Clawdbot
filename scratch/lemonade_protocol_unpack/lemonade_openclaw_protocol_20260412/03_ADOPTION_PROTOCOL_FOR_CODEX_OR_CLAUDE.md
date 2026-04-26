# Adoption Protocol for Codex or Claude

## Instruction to receiving agent
You are receiving this protocol as an implementation review pack.
Your job is **not** to blindly install Lemonade.
Your job is to inspect the current environment and decide whether the proposal should be:
- fully adopted
- partially adopted
- held for later

You must inspect:
- existing Docker Compose services
- currently used ports
- existing LiteLLM routing logic
- current OpenClaw Gateway expectations
- Portal app/card duplication risks
- overlap with Ollama, Open WebUI, or other local AI service layers

## Required decision rule
### Choose FULL ADOPTION only if all are true:
- no major port conflicts
- no duplicated production-critical features already working better elsewhere
- Lemonade adds immediate practical multimodal value
- maintenance burden stays acceptable
- rollback path is clear

### Choose PARTIAL ADOPTION if any are true:
- only speech or image functionality is useful now
- OpenAI-compatible API unification is the main value
- current Ollama path should stay untouched for LLM serving
- Lemonade is better introduced as an optional sidecar service

### Choose HOLD if any are true:
- Compose complexity increases too much
- no immediate operational gain exists
- current services already satisfy the use cases safely
- operational observability or rollback is insufficient

## Required deliverables from receiving agent
The receiving agent should produce:
1. conflict report
2. recommended merge scope
3. final compose patch or non-adoption explanation
4. validation checklist results
5. rollback confirmation

## Non-negotiable constraints
- do not break existing OpenClaw operation
- do not overwrite working Ollama configuration without explicit justification
- keep loopback binding where practical
- prefer additive integration over destructive migration
- preserve observability and logging
