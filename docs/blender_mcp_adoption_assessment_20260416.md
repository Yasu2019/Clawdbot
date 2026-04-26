# Blender MCP Adoption Assessment

Date: 2026-04-16
Status: review complete
Scope: evaluate `Blender_MCP_HONKI_Protocol_20260416.zip` for safe use on this mini PC and in this repository

## Summary Decision

Decision: `ADOPT_PARTIAL`

Why:

- the package matches the current repo preference for staged, low-risk adoption
- it correctly treats Blender MCP as a Windows-native, isolated evaluation target rather than a first-class Docker service
- full adoption would overlap with existing 3D, Portal, and protocol-governance layers
- this machine is already sensitive to background load, and Blender MCP includes arbitrary Python execution risk

## Repo Scan Result

Required overlap scan was completed against the areas named in `AGENTS.md`.

| Area | Existing implementation | Assessment |
|---|---|---|
| `docker-compose*.yml` | `docker-compose.yml`, `docker-compose.addons.yml`, `clawstack_v2/docker-compose.yml`, `iatf_system/docker-compose.yml` | do not introduce Blender MCP as another always-on compose service |
| env / policy files | `AGENTS.md`, `implementation_plan.md`, `docs/canonical_routing_and_adoption_20260404.md` | governance already exists; this ZIP must not become a second active control layer |
| gateway / routing code | OpenClaw gateway, LiteLLM routing, local MCP usage already present | keep Blender MCP outside the routing core at first |
| benchmark scripts / acceptance logic | existing package-assessment docs and adoption rules | this ZIP's tests are useful as local acceptance checks, not as a reason for immediate promotion |
| portal cards / dashboards | existing Portal, 3D preview paths, and app surfaces | avoid a duplicate Blender-facing Portal card on first rollout |
| 3D / visualization stack | `docs/3d_model_folder_policy_20260414.md`, Portal, three.js, DXF-to-3D flows, Blender noted in Dockerfiles | this is an extension of the current 3D path, not a blank-space addition |
| MCP / desktop config risk | existing Codex, VS Code, Antigravity, and Claude-adjacent tooling | avoid mutating shared MCP config until single-machine evaluation succeeds |

## Observed Package Intent

The ZIP is a practical evaluation pack, not a drop-in implementation layer.

Useful parts:

- isolated evaluation flow
- explicit `adopt / partial / hold` decision framing
- security emphasis around arbitrary Python execution
- lightweight integration ideas such as links or helper scripts instead of deep embedding

Overlapping parts:

- protocol and adoption-governance language overlaps with current repo policy docs
- 3D workflow proposals overlap with the current Blender plus Portal plus DXF-to-3D direction
- acceptance and reporting templates overlap with the repo's existing assessment pattern

## Environment Findings

Current host findings:

- `blender` command not found
- `uv` command not found
- `python`, `code`, and `codex` are available
- Windows 11, Docker Desktop, WSL2, and existing local AI infrastructure are already present

Implication:

- this is not ready for direct integration
- the safest next step is a sandboxed Windows-native evaluation only

## Decision Rationale

Why `ADOPT_PARTIAL` is the right level:

1. The package is directionally aligned with the repo's current safety posture.
2. It would be premature to wire Blender MCP into Docker, OpenClaw, or Portal before proving local stability.
3. Existing 3D assets already cover the day-to-day lightweight review path, so Blender MCP should justify itself as an optional authoring tool.
4. Arbitrary Python execution plus external asset handling means the first rollout must remain isolated and operator-visible.

Why not `ADOPT` now:

- Blender itself is not confirmed installed on this host
- no isolated Blender MCP environment has been validated yet
- no benchmark or user-value evidence exists yet for this machine
- deep integration would add complexity before proving utility

Why not `HOLD`:

- the package is concrete and bounded
- it maps cleanly to a low-risk manual pilot
- it may add value for explanatory 3D scenes and customer-facing visuals once isolated evaluation is ready

## Safe Adoption Boundary

Adopt now:

- documentation and decision record
- a dedicated sandbox folder outside the repo
- manual, Windows-native evaluation planning

Do not adopt now:

- new Docker services
- always-on daemons or watchers
- OpenClaw core routing changes
- Portal card publication
- shared MCP config mutation for every client
- automatic asset download or automatic file-writing workflows

## Sandbox Path

Prepared evaluation root:

- `D:\AI_Sandbox\blender_mcp_eval`
- `D:\AI_Sandbox\blender_mcp_eval\backup`
- `D:\AI_Sandbox\blender_mcp_eval\configs`
- `D:\AI_Sandbox\blender_mcp_eval\downloads`
- `D:\AI_Sandbox\blender_mcp_eval\samples`
- `D:\AI_Sandbox\blender_mcp_eval\outputs`
- `D:\AI_Sandbox\blender_mcp_eval\logs`

## Recommended Next Steps

Phase 1:

- confirm Blender installation source and version
- install or prepare a clean Python toolchain for Blender MCP evaluation
- identify which MCP client should be used first on this machine

Phase 2:

- install Blender MCP only in the sandbox path
- keep configs and logs under `D:\AI_Sandbox\blender_mcp_eval`
- run only minimal acceptance tests such as object creation, rename, color, camera, light, save, and PNG output

Phase 3:

- test one narrow business sample
- record latency, stability, and operator effort
- only then decide whether helper scripts or a Portal link are worth adding

## No-Go Conditions

- any proposal that changes `docker-compose.yml` or other protected core runtime files for first rollout
- any proposal that makes Blender MCP an always-on resident service
- any proposal that points first-run testing at production `.blend` files or shared business folders
- any proposal that writes API keys or unreviewed config into repo-managed files
- any proposal that bypasses manual review for Python-executing actions

## Final Recommendation

Treat `Blender_MCP_HONKI_Protocol_20260416.zip` as a strong `partial-adoption` candidate.
Use it as an isolated Windows-native evaluation guide and keep it out of the repo's active governance and always-on runtime path until local proof exists.
