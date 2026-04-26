# PDCA Lab

Thin local UI for Phase 1 PDCA feedback-loop status.

## Data source

- `../../pdca_lab/state/status.json`
- `../../pdca_lab/state/prompt_registry.json`
- `../../pdca_lab/state/promotion_audit.jsonl`

## Harness

- `python data/workspace/pdca_feedback_phase1.py init`
- `python data/workspace/pdca_feedback_phase1.py capture --input-json data/workspace/pdca_lab/examples/capture_sample.json`
- `python data/workspace/pdca_feedback_phase1.py refresh`
