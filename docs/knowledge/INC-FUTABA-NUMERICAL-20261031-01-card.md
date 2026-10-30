# INC-FUTABA-NUMERICAL-20261031-01: conditional leveller FEM verification

Observed 2026-10-31 06:20-06:27 JST on K10, during authorized development.
No production machine fault inferred. Unrelated jobs and data preserved.

The first isolated 7-roll beam initialization exhausted its Newton iteration
limit before producing a result. A seed compatibility gate then rejected identical
roll coordinates represented as Python tuples versus JSON lists. Both failures
were retained and corrected locally: sufficient initial opening/natural shape,
larger iteration budget, canonical JSON comparison without removing provenance
checks. Recovery checks reproduce all four native state arrays bitwise.

Initial one-pass predictions were misleading: residual curvature was still
changing as material history circulated through the coupled contact solution.
Continuing transport to a verified steady state removed the spatial variation.
At one fixed setting, 1mm and 0.5mm mesh predictions differ by approximately
0.017mm over a 75mm strip after steady-state continuation. This is a numerical
comparison, not proof of physical accuracy or an approved acceptance threshold.

FMEA rev1: numerical initialization, metadata false mismatch, premature result
ranking; effects failed jobs or unsupported settings; detection native restart,
completion, steady-state and mesh checks. Owner current authorized session;
S/O/D and RPN unassessed. Residual risks: cyclic law and machine calibration.
FTA rev1: unsupported recommendation can follow from failed/incomplete solve,
unverified state transfer, lack of steady state, or uncalibrated physical model.
Only observed numerical branches are confirmed; physical causes remain unknown.
QC chart rev1: source identity -> native recovery proof -> full transport ->
steady-state and mesh comparison -> conditional report; failed gate holds ranking.
Control Plan rev1: verify code/input/runtime identity and all-state recovery for
each solver revision; verify transport/mesh convergence before reporting settings.
Product tolerance and physical process validation require their own evidence.

Canonical restricted evidence: project artifacts/futaba_ur300_20261031/study_v1/
NUMERICAL_VERIFICATION.md, logs, result JSON and versioned checkpoints.
No raw mail, personal details, tokens or unrelated engineering data in this card.
