# n8n Integration Plan

## Primary idea
Use Lemonade where multimodal input or output improves automation.

## Candidate workflows
### 1. Voice memo to structured task
- microphone or uploaded audio
- Lemonade STT
- OpenClaw or LLM cleanup
- n8n routes into task, note, or QA workflow

### 2. Shop-floor spoken inspection memo
- worker speaks issue
- STT converts to text
- LLM normalizes to defect template
- data stored or forwarded

### 3. Image-assisted report pipeline
- image input
- Lemonade-compatible image endpoint if practical
- summarize and push into workflow

## Design rule
Use n8n only after confirming endpoint compatibility and latency are acceptable.

## Minimal first-phase n8n scope
1. HTTP Request node to Lemonade health endpoint
2. HTTP Request node to one supported API endpoint
3. simple response normalization node
4. fallback branch to Ollama/OpenClaw if Lemonade fails

## Success criterion
- no workflow hangs
- predictable error messages
- fallback path works
