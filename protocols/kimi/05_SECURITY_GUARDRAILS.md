# Security Guardrails

## Hard rules
1. Never send customer confidential files to remote Kimi API
2. Never send bearer tokens, passwords, or raw secrets to any model
3. Never allow autonomous DB write operations without separate approval gate
4. Never let a model directly run destructive shell commands in production by default
5. Never trust model output as final compliance judgment without verification

## Data classification rules
### Allowed for remote Kimi only if approved
- public documentation
- sanitized examples
- internal low-risk notes with no sensitive identifiers

### Local-only processing
- customer drawings
- audit findings with names or proprietary details
- defect logs traceable to customer or product
- pricing, commercial, procurement, HR, credentials, regulated data

## Technical controls
- keep remote keys in env vars only
- maintain allowlist routing
- redact identifiers before remote calls when possible
- enable per-workflow timeout
- enable token ceilings
- keep request/response logging policy explicit
- keep human escalation on exceptions

## Approval boundaries
Autonomous tasks may:
- summarize
- classify
- cluster
- draft
- retrieve
- propose

Autonomous tasks may NOT directly:
- approve shipment
- alter ERP/MES/SQL production records
- send customer email without review
- change safety-critical settings
- delete source documents

## Minimum logging
Each autonomous run should log:
- timestamp
- workflow name
- model used
- task id
- input classification
- output status
- reviewer verdict
