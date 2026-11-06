# INC-380D-INTERFERENCE-20261107-01 — CAD interference validation

Observed 2026-11-07 JST during authorized assembly repair. This is a sanitized knowledge card; proprietary drawings, geometry, raw logs and credentials are excluded.

Confirmed failure: a CAD assembly pipeline positioned parts from guessed offsets, selected some elevation drawings as plan views, then cut mating plates and tools around those placements. The resulting zero-overlap report did not validate assembly correctness. Some converted parts were drawing frames, and some source pockets were absent from converted plates.

Controls implemented in a separate review workflow: preserve originals; match source and assembly drawing geometry; retain source-derived profiles; restore only documented source features; use rigid placement; prohibit mate-driven fit cuts; report missing/ambiguous parts; independently reopen exported artifacts and check every potentially intersecting pair, shape validity, exceptions and component preservation.

A further export issue was detected by read-back: general geometry transforms changed native curve representation and produced a materially larger volume discrepancy. Native rigid rotations/translations reduced discrepancies to within the numerical uncertainty bound derived from the shapes' stored kernel tolerances and surface areas. This bound concerns export consistency only, not engineering clearance. The initial failed verification was preserved.

At 04:26 JST a limited review subset passed independent FCStd and reimported STEP collision/validity checks. The complete assembly remains INCOMPLETE: ambiguous replacement-part identities require the current BOM/revision, and remaining geometry, axial stack, hardware and stroke have not been certified. No production-ready or complete zero-interference claim is authorized by the subset result.

FMEA/FTA/QC process chart/Control Plan share this incident ID in the restricted canonical note. Numerical solver runs and unrelated legacy jobs were not stopped, reused or restarted. Future builders must fail closed on missing identity, Boolean exceptions, invalid geometry, unverified exports or incomplete coverage; recording this card does not by itself repair a model.

Canonical restricted evidence: project `docs/knowledge/INC-380D-INTERFERENCE-20261107-01.md`. Beads: `orca-local-g0x`. No passwords, tokens, client configuration or raw engineering files are included.
