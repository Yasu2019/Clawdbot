# Email Ingest Knowledge

## Current Paperless Behavior
- `paperless-ngx` does not ingest `.eml` files in this environment.
- The consumer logs `Unknown file extension.` for `.eml`.
- Raw `.eml` files therefore remain under `clawstack_v2/data/paperless/consume/email`.

## Local-Only Workaround
- Use `scripts/eml_preprocess_for_paperless.py`.
- Use `scripts/eml_enrich_for_paperless.py` after preprocessing.
- This script does not call external APIs.
- It generates:
  - `TXT` companions for Paperless ingestion
  - `HTML` renderings for readable archival
  - extracted attachments as separate files
  - `PDF` renderings generated locally with Edge headless print
  - local LLM summaries and action extraction under `knowledge`

## Output Paths
- `clawstack_v2/data/paperless/consume/email_generated/txt`
- `clawstack_v2/data/paperless/consume/email_generated/html`
- `clawstack_v2/data/paperless/consume/email_generated/attachments`
- `clawstack_v2/data/paperless/consume/email_generated/pdf`
- `clawstack_v2/data/paperless/consume/email_generated/knowledge`

## Operational Notes
- Originals are preserved.
- Reprocessing is skipped when mtime and size are unchanged.
- Progress is tracked in `data/state/email_preprocess/harness_status.json`.
- Processed fingerprints are stored in `data/state/email_preprocess/state.json`.
- Long Windows paths can break attachment extraction, so output folders and filenames are hash-shortened.
- Email body content is summarized only with local Ollama, not external APIs.
- ByteRover should store only durable pipeline knowledge, not raw email contents.

## Latest Run
- Full local-only preprocessing completed on 2026-03-12.
- Candidates: `12,291`
- Generated in that run: `12,271`
- Already processed and skipped: `20`
- Current generated files:
  - `TXT`: `13,909`
  - `HTML`: `13,909`
  - extracted attachments: `10,152`

## Enrichment Stage
- `scripts/eml_enrich_for_paperless.py` converts generated HTML into PDF with local Edge headless printing.
- The same stage asks local `qwen3:8b` to produce a concise Japanese summary, key points, action items, tags, and urgency.
- Output state:
  - `data/state/email_enrich/harness_status.json`
  - `data/state/email_enrich/state.json`
- Backlog launcher:
  - `scripts/start_eml_enrich_background.ps1`
  - `scripts/check_eml_pipeline.ps1`

## Recommended Flow
1. Run limited batches first.
2. Confirm generated `TXT/HTML` and attachment extraction.
3. Generate `PDF` and `knowledge` from the preprocessed tree.
4. Run the full backlog in background.
5. Let Paperless ingest the generated `PDF/TXT/HTML` tree instead of raw `.eml`.
