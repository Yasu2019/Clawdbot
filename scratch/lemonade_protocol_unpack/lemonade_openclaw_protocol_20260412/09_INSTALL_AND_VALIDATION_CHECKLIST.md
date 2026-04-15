# Install and Validation Checklist

## Pre-check
- [ ] Review current docker compose files
- [ ] Review current port usage
- [ ] Review existing LiteLLM configuration
- [ ] Review OpenClaw assumptions for provider endpoints
- [ ] Confirm no Portal card duplication problem

## Install phase
- [ ] Add Lemonade as sidecar service only
- [ ] Bind to loopback if possible
- [ ] Add healthcheck
- [ ] Mount persistent data path if needed
- [ ] Start service without changing Ollama routing

## Validation phase
- [ ] health endpoint responds
- [ ] one chat-like request succeeds if supported
- [ ] one multimodal request succeeds if supported
- [ ] LiteLLM can route to Lemonade intentionally
- [ ] n8n test workflow succeeds
- [ ] Portal card can display status

## Safety gate
- [ ] Existing Ollama-based flows remain working
- [ ] Existing OpenClaw behavior remains working
- [ ] Logs are reviewable
- [ ] rollback steps are tested

## Final adoption output
The receiving agent must record:
- actual benefits observed
- conflicts found
- whether full, partial, or hold was selected
