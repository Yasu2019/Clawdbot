# Protocol Adoption Assessment

Date: 2026-04-12
Status: review complete
Scope: evaluate whether the following ZIP packages should be adopted on this mini PC and in this repository

- `AI_完全実装版パック_UTF8_20260411.zip`
- `MarkItDown_Protocol_UTF8_ZIP_v1.zip`
- `hermes_agent_protocol_utf8.zip`
- `karpathy_knowledge_protocol_jp_utf8.zip`
- `arscontexta_protocol_20260411.zip`
- `pro_streamlit_manufacturing_sim_claude_package.zip`
- `DUAL_LLM_PROTOCOL_UTF8_ZIP.zip`
- `ComfyUI_Full_Implementation_UTF8_20260412.zip`
- `obsidian_second_brain_protocol_utf8bom_20260413.zip`
- `K10_Image_Generation_Protocol_v2.zip`


## Summary Decision

| Package | Decision | Why |
|---|---|---|
| `AI_完全実装版パック_UTF8_20260411.zip` | `HOLD` | broad governance and self-improvement layer overlaps with active repo control docs and risks adding more always-on complexity |
| `MarkItDown_Protocol_UTF8_ZIP_v1.zip` | `ADOPT_PARTIAL` | useful as a narrow document-conversion utility if kept CLI-only and read-only at first |
| `hermes_agent_protocol_utf8.zip` | `REFERENCE_ONLY` | architecture assumptions already match existing stack; valuable as design reference, not as a new active layer |
| `karpathy_knowledge_protocol_jp_utf8.zip` | `ADOPT_PARTIAL` | knowledge-organization ideas are useful, but should remain template/reference only, not a second source of truth |
| `arscontexta_protocol_20260411.zip` | `REFERENCE_ONLY` | overlaps with existing knowledge and workflow layers; useful for vault-organization ideas, not as a new canonical system |
| `pro_streamlit_manufacturing_sim_claude_package.zip` | `ARCHIVE / ALREADY_ADOPTED` | package contents are already present in `clawstack_v2/apps/mfg_sim` with matching file hashes |
| `DUAL_LLM_PROTOCOL_UTF8_ZIP.zip` | `REFERENCE_ONLY` | dual-model routing ideas largely overlap with existing LiteLLM/Ollama routing and canonical adoption policy; useful only for narrow prompt/checklist borrowing |
| `ComfyUI_Full_Implementation_UTF8_20260412.zip` | `HOLD` | substantial overlap with existing Lemonade / Stable Diffusion / Portal surfaces; full adoption would add another heavy always-on generation stack on this mini PC |
| `obsidian_second_brain_protocol_utf8bom_20260413.zip` | `ADOPT_PARTIAL` | safe `_ai/`-only Obsidian batch structuring improves note reuse without creating a second canonical memory system |
| `K10_Image_Generation_Protocol_v2.zip` | `ADOPT_PILLAR (v2)` | Intel-optimized local image generation (OpenVINO) specifically tuned for the K10 hardware; zero-cost high-quality path |


## Repo Scan Result

Required overlap scan was completed against the areas named in `AGENTS.md`.

| Area | Existing implementation | Assessment |
|---|---|---|
| `docker-compose*.yml` | `docker-compose.yml`, `docker-compose.addons.yml`, `clawstack_v2/docker-compose.yml` | core stack already exists; avoid importing another compose-driven framework |
| env / policy files | `AGENTS.md`, `implementation_plan.md`, `.env`, `docs/canonical_routing_and_adoption_20260404.md` | governance and rollout rules are already active here |
| gateway / routing | OpenClaw gateway, LiteLLM routing, Codex/Antigravity policy docs | new routing/governance packs would duplicate control logic |
| benchmark / evaluation | existing assessment docs and rollout rules | new benchmark templates are reference material, not a reason for framework replacement |
| n8n workflows | existing `n8n` stack and workflow references | avoid parallel workflow frameworks |
| portal cards / dashboards | existing portal/hub surfaces and app mesh | do not add duplicate dashboard layers |
| Gmail / RAG / approval policy | email ingest harnesses, Paperless, Qdrant, Langfuse, existing safety rules | repo already has active ingestion and RAG paths |

## Package Assessment

### 1. `AI_完全実装版パック_UTF8_20260411.zip`

Decision: `HOLD`

Observed overlap:

- package contains another adoption protocol, operating rules, architecture doc, example compose, env example, and app-side harness modules such as `archon_harness.py` and `hermes_learning_loop.py`
- these overlap with `AGENTS.md`, `implementation_plan.md`, existing external harnesses, and the current gateway / memory / observability layers

Why not adopt now:

- this mini PC already showed instability from extra watchers and background loops
- the package tends toward another orchestration and self-improvement layer, which increases always-on complexity
- importing its compose/env/harness patterns would create parallel ownership for governance and runtime control

Safe use:

- keep as design reference only when reviewing future harness ideas
- cherry-pick small templates only if they can be applied without adding a daemon, watcher, or second policy layer

No-go conditions:

- any proposal that adds a new always-on daemon, loop, dashboard, memory collection, or compose-controlled subsystem
- any proposal that competes with `AGENTS.md` or canonical adoption docs

### 2. `MarkItDown_Protocol_UTF8_ZIP_v1.zip`

Decision: `ADOPT_PARTIAL`

Observed overlap:

- touches document ingestion and Paperless/OpenClaw integration ideas
- repo already has Paperless and email/document ingest flows, so full integration would be duplicative

Why partial adoption is justified:

- MarkItDown is a tool, not a governance layer
- it can improve local document normalization with lower risk if used as a manual or batch CLI step
- it does not require a second portal, workflow engine, or long-running agent

Safe integration point:

- start with read-only local CLI conversion only
- keep outputs in a clearly bounded staging path
- do not wire it directly into Paperless, Gmail, or automated ingest until usefulness is proven

No-go conditions:

- no auto-send or auto-import path on first rollout
- no new watcher or daemon around document folders
- no compose changes for this package without a separate approved plan

Recommended phase:

1. small manual pilot on a few representative files
2. compare conversion quality and operator effort
3. only then consider optional integration into an existing ingest script

### 3. `hermes_agent_protocol_utf8.zip`

Decision: `REFERENCE_ONLY`

Observed overlap:

- explicitly assumes OpenClaw, LiteLLM, Ollama, Qdrant, Langfuse, Paperless/RAG, and Docker are already present
- this is almost the same architecture this repo already operates

Why it should stay reference-only:

- the package itself says adoption is optional and proposal-based
- most of its value is in schema/checklist language, not in introducing a second active system
- promoting it would mostly rename or duplicate mechanisms we already have

Safe use:

- consult for memory-schema or rollout-checklist ideas
- borrow isolated checklist items only when they fit current ownership boundaries

No-go conditions:

- do not create a parallel Hermes runtime, workflow layer, or Qdrant memory hierarchy just to match the pack

### 4. `karpathy_knowledge_protocol_jp_utf8.zip`

Decision: `ADOPT_PARTIAL`

Observed overlap:

- package centers on knowledge-vault organization with Obsidian, Claude Code, and RAG-adjacent workflows
- repo already has `.brv/context-tree`, `knowledge`, Paperless, and Qdrant-backed knowledge paths

Why partial adoption is justified:

- foldering, templates, and note-taking conventions can improve human readability
- this can be adopted without adding runtime load if treated as documentation structure guidance only

Safe integration point:

- reuse template ideas, naming rules, or folder conventions where they help operator workflow
- keep current repo docs and existing knowledge stores as the source of truth

No-go conditions:

- do not introduce a second canonical knowledge vault
- do not require Obsidian as the mandatory operator path
- do not mirror the same facts into multiple active stores without a clear reason

### 5. `arscontexta_protocol_20260411.zip`

Decision: `REFERENCE_ONLY`

Observed overlap:

- package centers on Obsidian Vault usage, Claude Code workflows, markdown knowledge structure, wiki links, MOC-style organization, and agent-facing commands/hooks
- repo already has `.brv/context-tree`, `knowledge`, Paperless, Qdrant, Obsidian-related operator paths, and active governance docs

Why it should stay reference-only:

- it introduces another strong opinion about where human knowledge should live and how agents should navigate it
- on this repo, those ownership boundaries already exist across ByteRover context, current docs, Paperless, and Qdrant-backed retrieval
- promoting it would risk creating a second canonical knowledge-management layer

Safe use:

- borrow note-organization ideas, naming conventions, or linking patterns where they improve operator readability
- treat it as a documentation/reference method, not as a replacement for current repo memory ownership

No-go conditions:

- do not make Obsidian Vault the required source of truth for the whole repo
- do not add a second mandatory agent command layer if current skills and docs already cover the role
- do not mirror the same operating facts into multiple canonical stores

### 6. `pro_streamlit_manufacturing_sim_claude_package.zip`

Decision: `ARCHIVE / ALREADY_ADOPTED`

Observed overlap:

- package contains `app.py`, `requirements.txt`, `README.md`, `CLAUDE_PROTOCOL_JA.md`, and sample CSVs
- those files match the existing `clawstack_v2/apps/mfg_sim` app exactly

Verification result:

- `app.py` SHA256 matches existing `clawstack_v2/apps/mfg_sim/app.py`
- `README.md` SHA256 matches existing `clawstack_v2/apps/mfg_sim/README.md`
- `CLAUDE_PROTOCOL_JA.md` SHA256 matches existing `clawstack_v2/apps/mfg_sim/CLAUDE_PROTOCOL_JA.md`
- `requirements.txt` contents match existing `clawstack_v2/apps/mfg_sim/requirements.txt`

Why no new adoption is needed:

- this is not a new framework candidate for the repo
- it is a packaged copy of an app that is already present
- further adoption work would only duplicate inventory and create confusion about ownership

Safe use:

- keep as distributable archive/reference for the existing `mfg_sim` app
- if future improvements are needed, update `clawstack_v2/apps/mfg_sim` directly rather than treating the ZIP as a separate source

No-go conditions:

- do not fork this into a second manufacturing simulator app unless there is a clearly different scope
- do not maintain ZIP and repo app as competing active sources

### 7. `DUAL_LLM_PROTOCOL_UTF8_ZIP.zip`

Decision: `REFERENCE_ONLY`

Observed overlap:

- package focuses on a two-stage local LLM operating pattern: a fast first-response model followed by a stronger reasoning/final-answer model
- repo already has active routing ownership in `docs/canonical_routing_and_adoption_20260404.md`
- runtime model-routing building blocks already exist in `data/state/litellm_config.yaml` through local `qwen` and `gemma` aliases on top of Ollama/LiteLLM

Why it should stay reference-only:

- the package is primarily a protocol/checklist/prompt bundle, not a net-new implementation layer
- its core idea is already compatible with the current stack, so promoting it would mostly duplicate guidance rather than add capability
- turning it into another active routing policy would violate the current one-canonical-routing-layer rule

Safe use:

- borrow small prompt or checklist refinements when they improve model-selection clarity for operators
- use it as a compact reference when reviewing local-fast versus local-strong routing tradeoffs
- keep any future adoption bounded to documentation or existing routing comments, not a new daemon, dashboard, or control layer

No-go conditions:

- do not introduce a second project-wide routing/governance document based on this ZIP
- do not add always-on routing middleware or another orchestration layer just to mirror the package structure
- do not replace existing LiteLLM/OpenClaw routing without benchmark evidence that the new policy materially improves quality or latency

### 8. `ComfyUI_Full_Implementation_UTF8_20260412.zip`

Decision: `HOLD`

Observed overlap:

- package proposes a new `comfyui` service, a `prompt_orchestrator`, a Portal card, and optional `n8n` integration
- repo already has multimodal/image-generation surfaces through `docker-compose.yml` `lemonade`, Portal image-generation cards, and an existing `Stable Diffusion WebUI` entry
- package explicitly spans image, video, audio, and 3D generation, which overlaps with current multimodal and media-oriented operator surfaces

Why it should stay on hold:

- on this mini PC, a new always-on generation stack would add GPU/VRAM, disk, port, and maintenance load at the exact layer that has already been sensitive to resource pressure
- the package is well-structured for staged adoption, but its default full shape still introduces another orchestration layer and another Portal surface before proving local benefit
- the repo already has active multimodal routing and dashboard concepts, so full adoption would likely create operator confusion and duplicate ownership

When partial adoption could be justified:

- a narrowly bounded, manual-only pilot of `ComfyUI` itself
- localhost-only binding
- no `n8n` automation on first rollout
- no new always-on `prompt_orchestrator` unless benchmark evidence shows better prompt quality than existing local routing paths

Safe integration point:

- if future need appears, test `ComfyUI` as an optional sidecar on a new compose override or separate compose file
- keep it manual/read-only first, focused on a single image-generation use case
- defer Portal-card promotion until uptime, resource cost, and output usefulness are proven

No-go conditions:

- do not enable the full stack by default on this mini PC
- do not add image/video/audio/3D generation layers all at once
- do not introduce another always-on orchestrator and dashboard layer without benchmark evidence and a clear ownership story versus Lemonade/OpenClaw/Portal

## Recommended Adoption Path

Only two packages are worth limited adoption work on this machine:

1. `MarkItDown_Protocol_UTF8_ZIP_v1.zip`
   Safe target: manual CLI-only conversion pilot
2. `karpathy_knowledge_protocol_jp_utf8.zip`
   Safe target: doc/template/reference usage only

The other two should remain non-active references until a future need appears and a separate implementation plan justifies them.
`DUAL_LLM_PROTOCOL_UTF8_ZIP.zip` should also remain a non-active reference unless a future benchmark shows that one of its prompt/checklist ideas improves the current routing behavior.
`ComfyUI_Full_Implementation_UTF8_20260412.zip` should remain on hold unless there is a tightly bounded need for local image generation that current Lemonade / Stable Diffusion surfaces cannot satisfy.

## Final Recommendation

For this mini PC, avoid any adoption that adds:

- new background daemons
- folder watchers
- duplicate workflow engines
- duplicate dashboards
- a second governance layer
- automatic write/import behavior before a read-only trial

Current best path:

- keep `AI_完全実装版パック_UTF8_20260411.zip` on hold
- keep `hermes_agent_protocol_utf8.zip` as reference-only
- allow a narrow `MarkItDown` pilot
- allow `karpathy` template borrowing only
- keep `arscontexta_protocol_20260411.zip` as reference-only
- treat `pro_streamlit_manufacturing_sim_claude_package.zip` as an archive of the already-present `mfg_sim` app
- keep `DUAL_LLM_PROTOCOL_UTF8_ZIP.zip` as reference-only, with at most narrow prompt/checklist borrowing into existing routing docs
- keep `ComfyUI_Full_Implementation_UTF8_20260412.zip` on hold, with at most a future localhost-only manual pilot of `ComfyUI` itself
