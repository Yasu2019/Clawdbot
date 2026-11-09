# INC-380D-HIDDEN-LINE-THROUGH-CUT-20261109-01

Observed 2026-11-09T11:31:12.403843+09:00 (JST). Scope: current authorized CAD/viewer correction.

Confirmed defects: hidden DXF projections interpreted as through holes, uniform axial extrusion replacing true side profiles, partial-outline orientation acceptance, and inconsistent axial signs between orthographic views. Native solid validity and zero static overlap alone did not prove drawing conformity. Preserve explicit encoding and linetype, reconstruct blind features/lands/true heights from notes and views, and validate the entire outline and independent mating parts.

Correction candidate includes source-derived die/holder geometry and four newly admitted punches. Four punch admissions passed exact source-profile and native mating checks. Seven die/stripper conflicts at inherited empty-tool datums and additional missing components remain; do not describe tooling as complete, manufacture-ready, forming-validated or FEM-validated.

Bounded mesh export reached its own address-space cap; recovered with per-part hashed checkpoints and short isolated batches without raising resource limits or stopping other work.53 expected mesh checkpoints completed. All earlier evidence preserved.

Draft FMEA: incorrect projected geometry -> invalid tooling; prevention/view-depth interpretation, detection/independent source and mating gates; ratings unassessed. FTA: confirmed import/height/orientation/axial-sign branches, unresolved seating/remaining-part branches. QC: encoding/linetype -> orthographic native shape -> dimensional section gate -> exact placement and mating -> mesh -> viewer. Control Plan: repeat changed-part gates per revision; preserve and expose unresolved conflicts; documentation alone does not establish effectiveness.

Canonical restricted evidence is recorded locally in the matching incident note. No unrelated job stopped/deleted/reused.
