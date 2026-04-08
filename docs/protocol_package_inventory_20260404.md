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
| `codex_protocol_package_report_template_utf8bom.zip` | ZIP | useful execution template, but not a governance source |
| `contextbudget_protocol_utf8bom_ascii_v2.zip` | ZIP | supports context discipline; canonical ownership remains elsewhere |
| `agent_harness_protocol_20260404_ascii_utf8bom.zip` | ZIP | supports harness thinking, but repo constraints already live in `AGENTS.md` |
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
| `claude_agent_skills_protocol_utf8safe_20260404.zip` | ZIP | partial-adopt at best; broad provider-centered framework would overlap with active layers |
| `gemma4_protocol_utf8safe_20260403.zip` | ZIP | model-specific operational policy candidate |
| `glm5v_turbo_acceptance_package_utf8_ascii.zip` | ZIP | acceptance pack candidate, not shared governance |
| `gdt_failure_record_for_codex_utf8_bom.zip` | ZIP | targeted workflow package candidate |
| `full_protocol.zip` | ZIP | too ambiguous to promote without overlap review |
| `local_llm_supervision_protocol_complete.zip` | ZIP | potentially useful for local model governance, but not promoted |
| `local_llm_supervision_protocol_complete_utf8_bom.zip` | ZIP | duplicate variant of the same candidate package |

## Archive

| Item | Type | Why |
|---|---|---|
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
