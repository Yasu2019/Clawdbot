# K10 Failover Proxy AI Partial Deploy RCA

Date: 2026-06-28 JST

## Summary

K10 failover proxy AI read-only harness was implemented in `scripts/k10_failover_proxy_ai.py`.
Deployment and read-only plan generation succeeded on Main LAVIE and ThinkPad, but failed on G3 and Red LAVIE.

## Impact

- Main LAVIE: deployed and generated read-only failover plan.
- ThinkPad: deployed and generated read-only failover plan.
- G3 Plus: not deployed. `exec_bridge` returned HTTP 500 even for simple `{"cmd":"cmd /c echo ..."}`.
- Red LAVIE: not deployed. `/healthz` was reachable, but shell jobs timed out even for `cmd /c echo`.

No Docker stack, CAE production job, or destructive action was started.

## Evidence

- `python scripts/k10_failover_proxy_ai.py status --nodes g3 red_lavie lavie thinkpad --json`
  - G3 health endpoint OK.
  - Red LAVIE job_worker `/healthz` OK.
  - Main LAVIE job_worker OK.
  - ThinkPad job_worker OK.
- `python scripts/k10_failover_proxy_ai.py run-plans --nodes lavie thinkpad --no-ollama --json`
  - Main LAVIE wrote `C:\clawstack_satellite\data\failover_proxy_ai\lavie_failover_plan_20260628_233336.md`.
  - ThinkPad wrote `/home/yasu/clawstack_satellite/data/failover_proxy_ai/thinkpad_failover_plan_20260628_233336.md`.

## 5 Why

1. Why was full 4-node deployment not completed?
   - G3 and Red LAVIE remote execution paths failed.
2. Why did G3 fail?
   - Its n8n `exec_bridge` returned HTTP 500 for minimal commands.
3. Why did Red LAVIE fail?
   - Its job_worker health endpoint responded, but shell job POSTs did not return before timeout.
4. Why was this not caught earlier?
   - The precheck verified health endpoints, but health did not prove command execution.
5. Why is this risky?
   - K10 failover depends on command execution, not only heartbeat visibility.

## FMEA

| Failure mode | Effect | Severity | Detection | Countermeasure |
|---|---|---:|---|---|
| G3 exec_bridge HTTP 500 | Cannot act as failover trigger host | High | Simple echo command | Repair/redeploy G3 exec_bridge workflow separately |
| Red LAVIE worker shell timeout | Cannot install/read-only planner | High | Simple echo shell job | Restart or repair Red LAVIE job_worker separately |
| Health endpoint only check | False readiness | Medium | Deployment failure | Add command-execution preflight |

## Countermeasures

1. Keep `scripts/k10_failover_proxy_ai.py status` as readiness only, not deployment proof.
2. Add or use a command-execution preflight before declaring failover readiness.
3. Repair G3 `exec_bridge` in a separate, explicit n8n maintenance step.
4. Repair Red LAVIE shell job path before making it the first proxy AI node.
5. Keep proxy AI in read-only mode until all four target nodes pass echo, deploy, and plan-generation checks.

## Current Safe State

Read-only proxy planning works on Main LAVIE and ThinkPad.
G3 and Red LAVIE are blocked for remote execution and should not be relied on for failover until repaired.
