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

## Revision2: recommendation withheld after final numerical checks

Observed2026-10-31 JST. A two-stage full-crossed D-optimal campaign was completed, but a fitted minimum failed direct numerical verification. Narrowing the design improved fit without establishing accuracy. Mesh refinement then reversed the sign of residual curvature in a test condition; alternative uncalibrated cyclic assumptions also changed the response. Width-dependent behavior is outside the beam model. A machine-setting recommendation was withheld. The underlying discretization/contact contribution is UNKNOWN.

FMEA/FTA/QC/Control Plan rev3: compare signed curvature, not only unsigned sag; distinguish steady-flow convergence from mesh convergence; test the surrogate against direct FEM and record error in physical output units; retain material/width limitations. These gates prevented an unsupported optimum claim, but did not fix the underlying model accuracy. Preserve checkpoints and unrelated work. No production qualification or approved tolerance is inferred.

## Revision3: fail-fast admission and complete recovery controls

Observed2026-10-31 JST in authorized model improvement. A separate shell preflight failure did not prevent a subsequent small verification process from starting. Admission and child execution now share one Python process with checked return codes; a negative integration test confirmed the forbidden child was absent. No unrelated job was stopped or data deleted.

An initialized state was skipped by checkpoint deduplication based only on transport position. Deduplication now includes initialization state. Full physical and boundary arrays reproduce bitwise after restore and advance; a cut-release stage restart also matched uninterrupted execution. Failed cases and predecessor checkpoints were retained. A test-harness dimensional error was corrected separately from solver physics.

Finite-width bending, analytic material/plate/contact checks and cut-release verification were added. These software checks do not establish physical calibration or mesh convergence. FMEA/FTA/QC/Control Plan rev4: admission failure must prevent dispatch; distinguish initialized and uninitialized states; verify every history and boundary array plus solver/runtime provenance; gate recommendations on mesh and physical evidence. S/O/D, RPN and production limits remain unassessed. Numeric optimal settings remain withheld. Root cause of the original mesh-dependent curvature reversal remains UNKNOWN.
