# Validation Checklist

## Technical validation
- [ ] No docker compose syntax errors
- [ ] No port collisions
- [ ] No overwritten existing env names by mistake
- [ ] LiteLLM starts successfully
- [ ] existing default model routes still work
- [ ] Kimi route works only when enabled
- [ ] Langfuse logging still functions
- [ ] n8n workflows can fall back safely

## Security validation
- [ ] Remote Kimi blocked for confidential data
- [ ] secrets are not logged
- [ ] kill switch verified
- [ ] retry/timeout values set
- [ ] no autonomous destructive path exists

## Functional validation
- [ ] batch summarize test passes
- [ ] multi-file code explanation test passes
- [ ] reviewer model catches unsupported claims
- [ ] portal card or status UI reflects failures

## Operational validation
- [ ] SOP documented
- [ ] rollback tested
- [ ] owner assigned
- [ ] alert path tested
