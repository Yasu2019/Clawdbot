# Virtual candidate video regeneration — 2026-09-10

The air-trap and void render path was changed from the former strict display
condition (`unfilled AND pressure < 0.05 MPa`) to a cumulative, cause-labelled
screening marker:

- air trap: advancing unfilled front weighted toward the far vent-distance end,
  with the derived air-entrapment field;
- void: PVT-shrink, underpack, and thick-section fields combined into a
  persistent candidate marker.

This makes candidates remain visible after the fill front passes. It does not
turn them into measured defect probabilities or prove that a defect exists.

Visual QC of first/middle/final frames confirms:

- air-trap candidate: localized band on the far side and persistent;
- void candidate: visible lower/core gradient and persistent;
- weld, sink, and warpage videos remain available from r10;
- fill video has 101 frames and reaches the filled final state.

Downloads: `C:/Users/yasu/Downloads/box_roundhole_v5_r12_candidate_animations/`
