# INC-380D-STEP-MESH-FACELOSS-20261112-01

Observed2026-11-12 Asia/Tokyo during authorized STEP review. A valid native solid produced incomplete whole-shape triangulation; functional viewer tests and nonblank pixels passed while a large face was visibly absent. Underlying global mesher/cache/kernel cause UNKNOWN. Source CAD and failed output preserved. Independent cleaned per-face tessellation, native/mesh face-area checks and stable signed-volume comparison corrected the review display without changing source geometry.

Controls: distinguish CAD validity, triangulation completeness and UI functionality. Check each face's mesh area; compute signed volume in float64 after recentering large world coordinates; inspect multiple actual views and bind acceptance to the current artifact hash. Scope-check earlier artifacts before modifying them. A missing displayed face does not prove missing CAD material or source corruption.

FMEA: misleading apparent missing material from unchecked triangulation; ratings unassessed, engineering owner unassigned. FTA: invalid input OR incomplete mesh OR indexing OR unstable metrics OR inadequate visual gate; confirm observed branches only. QC: pin source -> native check -> mesh metrics -> multiple views -> preserve failure -> scoped correction -> quantitative/visual readback. Control Plan: hold mesh acceptance on mismatch, retain originals, validate corrected faces and current artifact; documentation alone is insufficient. Display gates are not manufacturing tolerances or forming qualification.

Shared card excludes raw engineering files, dimensions, mail and credentials. Local/queued synchronization is separate from verified remote readback.
