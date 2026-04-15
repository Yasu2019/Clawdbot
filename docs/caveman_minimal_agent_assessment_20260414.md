# Caveman Minimal Agent Protocol Assessment

Date: 2026-04-14
Status: reference-only / partial integration

## Summary

The Caveman Minimal Agent Protocol is useful as a thin orchestration pattern, but this repo already has active routing, tracing, watchdog, and retrieval layers. The safest path is to keep the package as a reference and borrow only the thin loop shape.

## Overlap Found

- `scripts/telegram_fast_bridge.js` already performs intent routing, tool-like dispatch, and short-lived follow-up memory.
- `data/workspace/rl_growth/examples/python/minimal_loop.py` already shows a compact solve -> review -> improve flow.
- `data/workspace/clawstack_mcp_server.py` and `data/workspace/clawstack_tracing.py` already provide tool and trace patterns.
- `docs/canonical_routing_and_adoption_20260404.md` already requires partial adoption over full framework import.

## Recommendation

- Keep the ZIP as reference material.
- Reuse the thin-loop idea only where it improves debugging or tool traceability.
- Do not add a new always-on agent framework, portal card, or compose service for it.

## Partial Adoption Target

- Add a small reference TypeScript loop that demonstrates:
  - tool registry
  - LLM adapter boundary
  - trace emitter hook
  - bounded max-step loop
- Keep it disconnected from production routing until a concrete use case proves benefit.

## Suggested Placement

- `data/workspace/caveman_minimal_agent_reference.ts`

## Rollback

- Remove the reference file and this assessment note.
- No runtime rollback is needed because nothing is wired into active services.
