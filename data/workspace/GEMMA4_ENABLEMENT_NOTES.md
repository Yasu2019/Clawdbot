# Gemma 4 Enablement Notes

## What Was Added

- Experimental protocol for low-risk local routing
- Readiness validator
- LiteLLM overlay template with placeholder tags
- Overlay renderer for exact Gemma 4 Ollama tags

## Current State

- Default routing is unchanged
- Gemini remains primary
- Gemma 4 is `ready_when_pulled`

## Enablement Flow

1. Make sure Ollama is reachable again.
2. Verify the exact local Gemma 4 tag names.
3. Render a ready overlay:

```powershell
python data\workspace\activate_gemma4_local_aliases.py --small-tag "<exact-small-tag>" --main-tag "<exact-main-tag>"
```

4. Review:
   [litellm_config.gemma4.ready.yaml](D:/Clawdbot_Docker_20260125/data/state/litellm_config.gemma4.ready.yaml)
5. Only then merge or mount the ready overlay into LiteLLM.

## Safety Rule

Do not point any default route to Gemma 4 until:

- Ollama is reachable
- real tags are verified
- low-risk task quality is checked
- no core app regression is observed
