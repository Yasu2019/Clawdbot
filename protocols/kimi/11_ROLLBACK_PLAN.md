# Rollback Plan

## Rollback trigger examples
- repeated timeouts
- output quality unacceptable
- routing leakage risk
- unexpected cost spikes
- worker flow breaks existing tasks

## Immediate rollback steps
1. Set KIMI_ENABLED=false
2. Restart affected routing services
3. Disable dependent n8n workflows
4. Revert compose/env changes from snapshot
5. Confirm default model routes still work
6. Review logs and incident notes

## Principle
Rollback must be possible in minutes, not hours.
Avoid invasive changes until Phase 1 is stable.
