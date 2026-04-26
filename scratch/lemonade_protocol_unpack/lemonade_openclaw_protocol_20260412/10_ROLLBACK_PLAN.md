# Rollback Plan

## Rule
Rollback must be simple and fast.

## Rollback steps
1. disable Lemonade route in LiteLLM
2. stop Lemonade container
3. revert compose file patch
4. remove Portal card references if added
5. re-run smoke tests for existing Ollama / OpenClaw paths

## Smoke tests after rollback
- OpenClaw basic chat works
- Ollama model call works
- n8n workflow that previously used Ollama still works
- observability remains normal

## Rollback success condition
System state returns to prior stable behavior without needing deeper repair.
