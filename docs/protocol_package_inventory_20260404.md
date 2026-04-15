# Protocol Package Inventory

Date: 2026-04-04
Status: active inventory
Purpose: classify major protocol docs and ZIP packages into `active`, `reference`, `candidate`, or `archive`

## Classification Rules

- `active`: current primary governance or actively used decision source
- `reference`: useful supporting material, but not the primary control layer
- `candidate`: plausible future adoption material that should not be treated as active yet
- `archive`: historical, duplicate, extracted-temp, or package-internal material that should not be used as a primary source

This inventory is for operational clarity.
It does not replace `AGENTS.md`.

## Active

| Item | Type | Why |
|---|---|---|
| `AGENTS.md` | governance | primary repo safety and adoption constraints |
| `docs/canonical_routing_and_adoption_20260404.md` | routing policy | primary routing and adoption policy |
| `docs/system_refactor_assessment_20260404.md` | assessment | current refactor decision baseline |
| `implementation_plan.md` | plan baseline | active implementation guardrail for protected layers |
| `data/workspace/CODEX_PROTOCOL_REFERENCE.md` | reference hub | active pointer into Codex-oriented protocol usage |

## Reference

| Item | Type | Why |
|---|---|---|
| `agent_routing_protocol_utf8_20260404.zip` | ZIP | overlaps with canonical routing policy; useful as compact handoff |
| `hermes_agent_protocol_utf8.zip` | ZIP | architecture/reference pack that matches the current stack, but should not become a second active layer |
| `DUAL_LLM_PROTOCOL_UTF8_ZIP.zip` | ZIP | useful as a compact dual-model routing reference, but overlaps with existing canonical routing and LiteLLM/Ollama model selection |
| `arscontexta_protocol_20260411.zip` | ZIP | useful for vault organization and markdown workflow ideas, but overlaps with existing knowledge and governance layers |
| `codex_protocol_package_report_template_utf8bom.zip` | ZIP | useful execution template, but not a governance source |
| `contextbudget_protocol_utf8bom_ascii_v2.zip` | ZIP | supports context discipline; canonical ownership remains elsewhere |
| `agent_harness_protocol_20260404_ascii_utf8bom.zip` | ZIP | supports harness thinking, but repo constraints already live in `AGENTS.md` |
| `gemma4_qwen_honki_protocol_utf8.zip` | ZIP | model-routing and performance decision pack; overlaps with existing Gemma 4 partial-adoption policy, so keep as reference only |
| `unreal_native_protocol_20260414.zip` | ZIP | Unreal native deployment guidance; useful as a reference pack, but too heavy to promote on this mini PC and should not become a second active 3D stack |
| `obsidian_open_notebook_protocol_20260403.zip` | ZIP | domain-specific workflow reference |
| `obsidian_skills_codex_protocol_utf8bom_ascii_filenames.zip` | ZIP | narrow workflow reference |
| `OpenClaw_Learning_Protocol_Pack.zip` | ZIP | source package for implemented learning work; no longer primary governance |
| `Stitch_OpenClaw_Protocol_20260403.zip` | ZIP | UI evaluation/supporting package, not active system policy |
| `data/workspace/apps/codex_protocol_hub/index.html` | hub page | discovery surface pointing to active docs |
| `data/workspace/apps/cmux_hub/index.html` | hub page | orchestration reference and operator-facing route map |
| `data/workspace/apps/system_role_map/index.html` | hub page | architecture inventory/reference layer |
| `protocols/audit_check.md` | protocol note | narrow task-specific protocol |
| `protocols/customer_reply.md` | protocol note | narrow task-specific protocol |
| `protocols/mail_todo_extract.md` | protocol note | narrow task-specific protocol |
| `protocols/research_quality.md` | protocol note | narrow task-specific protocol |
| `protocols/root_cause.md` | protocol note | narrow task-specific protocol |

## Candidate

| Item | Type | Why |
|---|---|---|
| `MarkItDown_Protocol_UTF8_ZIP_v1.zip` | ZIP | worth a narrow CLI-only pilot, but full ingest automation would overlap with existing document flows |
| `karpathy_knowledge_protocol_jp_utf8.zip` | ZIP | useful for templates and knowledge organization, but not as a second active knowledge system |
| `ComfyUI_Full_Implementation_UTF8_20260412.zip` | ZIP | potentially useful only as a tightly bounded local image-generation pilot; full stack overlaps with existing Lemonade / Stable Diffusion / Portal surfaces and is too heavy to promote yet |
| `claude_agent_skills_protocol_utf8safe_20260404.zip` | ZIP | partial-adopt at best; broad provider-centered framework would overlap with active layers |
| `gemma4_protocol_utf8safe_20260403.zip` | ZIP | model-specific operational policy candidate |
| `glm5v_turbo_acceptance_package_utf8_ascii.zip` | ZIP | acceptance pack candidate, not shared governance |
| `Caveman_Minimal_Agent_Protocol_UTF8BOM.zip` | ZIP | thin ReAct-style orchestration reference; useful only as a reference-only loop shape or checklist, not a new always-on framework |
| `gdt_failure_record_for_codex_utf8_bom.zip` | ZIP | targeted workflow package candidate |
| `full_protocol.zip` | ZIP | too ambiguous to promote without overlap review |
| `local_llm_supervision_protocol_complete.zip` | ZIP | potentially useful for local model governance, but not promoted |
| `local_llm_supervision_protocol_complete_utf8_bom.zip` | ZIP | duplicate variant of the same candidate package |
| `AI_完全実装版パック_UTF8_20260411.zip` | ZIP | broad orchestration/self-improvement package; high overlap and high risk on this machine, so hold unless future need is clearly bounded |

## Archive

| Item | Type | Why |
|---|---|---|
| `pro_streamlit_manufacturing_sim_claude_package.zip` | ZIP | packaged copy of the already-present `clawstack_v2/apps/mfg_sim` app, so it is not a separate adoption target |
| `_tmp_qms_audit_zip/*` | extracted temp | package internals, not primary sources |
| `_tmp_dxf_fcstd_zip/*` | extracted temp | package internals, not primary sources |
| `_tmp_codex_protocol_report_template/*` | extracted temp | extracted source files for the ZIP |
| `tmp_openclaw_learning_pack/*` | extracted temp | extracted source files for the learning package |
| duplicate encoding variants where one package already covers the same role | package hygiene | keep for preservation, not for active policy |

## Practical Use

When adding a new protocol or ZIP package:

1. decide whether it is governance, supporting reference, or candidate only
2. if it overlaps with an active source, do not mark it active
3. add it here before linking it broadly from Portal or hub pages
4. prefer linking the active doc, not every package variant

## Short Rule

One active governance layer.
Many references are fine.
Candidates stay candidates until explicitly promoted.
Extracted temp files stay out of the primary operator path.
