# GD&T Codex Knowledge (v6 Integration)

Date: 2026-04-30
Source: `gdt_openclaw_codex_knowledge_transfer_20260430_utf8_bom.zip`

## Core Concepts

### STEP-Face Exact Alignment
True "step_face_exact" status requires more than just a mesh. It must include:
- `face_id` and `axis_id` mapping.
- Provenance tracking (which step file/process produced the data).
- 4-view verification (visual validation from standard orthogonal views).

### Separation of Concerns
1. **CAD Pre-processing**: Extract `face_map.json` from STEP.
2. **GD&T Definition**: Extract `gdt_overlay.json` from PDF/DXF drawings.
3. **Viewer Logic**: Purely data-driven rendering of the above JSONs.
4. **Validation**: Generation of `evidence_report.json`.

## UI/UX Rules
- **Synchronized Highlighting**: Highlight the data card only for the item currently being rendered/inspected in 3D.
- **Progressive Feedback**: Always show a progress bar to prevent perceived UI freezes during large model loads.
- **Classification**: Explicitly classify drawing symbols into Datum, Section, or Detail.

## Failure Catalog (Lessons Learned)
- **Geometry Mismatch**: Mesh-only views without face ID leads to operator confusion when assigning tolerances.
- **Ambiguity**: Ambiguous datum references must be marked as `candidate` or `unverified` for human review.
- **Visual Clutter**: Avoid overwhelming the screen; only show 3D callouts related to the selected face or group.
