# EML Preprocess For Paperless

## Goal
Preprocess `.eml` files outside Paperless and generate ingestible companion files.

## Inputs
- Source: `clawstack_v2/data/paperless/consume/email/**/*.eml`

## Outputs
- Text summaries: `clawstack_v2/data/paperless/consume/email_generated/txt/**`
- HTML renderings: `clawstack_v2/data/paperless/consume/email_generated/html/**`
- Extracted attachments: `clawstack_v2/data/paperless/consume/email_generated/attachments/**`
- PDF renderings: `clawstack_v2/data/paperless/consume/email_generated/pdf/**`
- Local knowledge summaries: `clawstack_v2/data/paperless/consume/email_generated/knowledge/**`

## State
- Status: `data/state/email_preprocess/harness_status.json`
- Processed fingerprints: `data/state/email_preprocess/state.json`
- Enrichment status: `data/state/email_enrich/harness_status.json`
- Enrichment fingerprints: `data/state/email_enrich/state.json`

## Commands
- Full run:
  `powershell -ExecutionPolicy Bypass -File scripts/start_eml_preprocess_for_paperless.ps1`
- Full pipeline:
  `powershell -ExecutionPolicy Bypass -File scripts/start_eml_full_pipeline.ps1`
- Enrichment only:
  `powershell -ExecutionPolicy Bypass -File scripts/start_eml_enrich_for_paperless.ps1`
- Enrichment background:
  `powershell -ExecutionPolicy Bypass -File scripts/start_eml_enrich_background.ps1`
- Limited run:
  `powershell -ExecutionPolicy Bypass -File scripts/start_eml_preprocess_for_paperless.ps1 50`
- Status:
  `powershell -ExecutionPolicy Bypass -File scripts/check_eml_preprocess_for_paperless.ps1`
  `powershell -ExecutionPolicy Bypass -File scripts/check_eml_enrich_for_paperless.ps1`
  `powershell -ExecutionPolicy Bypass -File scripts/check_eml_pipeline.ps1`

## Notes
- Original `.eml` files are not deleted.
- Reprocessing is skipped when file size and mtime are unchanged.
- This implementation generates `TXT`, `HTML`, `PDF`, and extracts attachments.
- Local summary generation uses `qwen3:8b` via Ollama on the host.
- ByteRover should receive only pipeline and runbook knowledge, not raw mail contents.
- Output paths are shortened with hashes to avoid Windows path-length failures on deep mail folders and long attachment names.

## Latest Run Result
- Date: `2026-03-12`
- Full backlog processed locally without external APIs.
- Status summary:
  - total candidates: `12,291`
  - generated in the final full run: `12,271`
  - skipped as already processed: `20`
