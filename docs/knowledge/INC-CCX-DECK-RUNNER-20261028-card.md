# INC-CCX-DECK-RUNNER-20261028: reviewed numerical workflow card

Observed 2026-10-28 11:18-11:28 Asia/Tokyo, isolated development on K10; Beads orca-local-e0i. No production workload stopped, changed or deleted. No private material data or emails are included here.

Symptoms: CalculiX2.16 rejected a long floating-point node-coordinate field. A generated POSIX shell runner used CRLF and reported ambiguous redirect. A sliced runner without fail-fast exited zero although no solver solution was produced. Separate nonlinear transport/contact pilots subsequently failed convergence; numerical root cause UNKNOWN.

Confirmed corrections: coordinate formatting uses12 significant digits; shell written as explicit LF bytes; sliced invocation uses sh-e. Before dispatch, validate numeric mesh field widths<=20, positive initial element orientation, LF and fail-fast. These gates passed for the revised pilot and four prepared (not dispatched) screening decks. Input validation is not physical validation.

Native restart: matching2.16 manual states FREQUENCY counts STEPS, not increments. Simple restart smoke write/read succeeded and final ASCII displacement matched uninterrupted two-step output (maximum difference0). A completed contact-closure checkpoint exists, but complete moving-contact restart/pass-through qualification remains open. Keep previous known-good checkpoint and exact input/binary/thread provenance. Never equate file existence, process exit0, a failed .frd, or elapsed time with convergence or an optimum.

FMEA draft: malformed or failed run falsely accepted -> invalid engineering recommendation. Causes: field formatting/CRLF/fail-fast confirmed; convergence cause UNKNOWN. Detection controls above; physical verification remains open. Owner unassigned; S/O/D/RPN unassessed.

FTA draft: invalid recommendation = OR(input execution failure; numerical convergence failure; unverified physical assumptions). Only listed formatting/runner branches confirmed. No production defect root cause established.

QC process draft: import/hash -> deck checks -> parser/solver completion -> native restart equivalence -> contact/transport/unload convergence -> mesh/physical verification -> optimization -> measured trial. Failure stops downstream ranking.

Control Plan draft: each deck/runner/stage requires input gates, successful solver log/converged state, valid native checkpoint and numerical checks; reject incomplete solutions. Keep failed evidence and correct in a new version. Owner unassigned. Implemented gates tested; controls for moving-contact physics not yet validated. No approved process limits changed.

Canonical restricted evidence: D:/Clawdbot_Docker_20260119/artifacts/nu0701_leveler_20261028/STATUS.md. Raw outputs remain there. This is historical evidence, not live telemetry. Revision1 records development failures and verified input controls; does not claim numerical/physical recovery.

## Revision2, 2026-10-28 13:23 JST

A separate reduced beam/fiber/contact implementation was screened; this does not establish that the original solid transport convergence failure was fixed. Constitutive monotonic-curve reproduction, directional force/tangent checks, incremental-potential checks for several mixed hardening fractions, and bitwise checkpoint continuation checks passed. These are implementation checks, not experimental process validation.

New control: exclude a result from engineering ranking when virgin flow replacement is incomplete, cumulative plastic strain exceeds the supplied hardening range, released-tail curvature is not uniform at the declared numerical resolution, or it belongs to an earlier rejected transport discretization. A converged coarse optimum must be checked with spatial and through-thickness refinement; observed coarse/fine differences prevent claiming an optimum merely from solver convergence. Keep actual magnitudes and input geometry in restricted project evidence. Limits for a real process remain those approved for that process; no new factory acceptance limit is set here.

FMEA/FTA update: add false optimum caused by discretization or extrapolation as an unresolved risk branch. QC/Control Plan update: require explicit screening/mesh-validated/machine-qualified labels, actual read-back of checkpoints, and separate parameter assumptions from measurements. Controls for result classification were implemented; moving-contact physical qualification remains open. ByteRover status at13:22 JST reported Session expired / Space not connected; no login or new store was created.


## Revision3, 2026-10-28 15:58 JST

Source inspection of the exact bundled CalculiX2.16 implementation identified an inconsistency in plcopy.f: after the >200-point isotropic-table interpolation branch, it unconditionally sets plconloc(802)=200.5, which incplas.f interprets as a kinematic-table count. Causality for the transport failure is still under test. The preliminary array-overflow hypothesis was ruled out by the explicit interpolation path. Preserve this distinction between source evidence and a verified failure cause.

A supervised controlled diagnostic preserves the original material data and geometry, changes only the table representation to at most200 original knots, and quantifies the maximum piecewise-linear interpolation error. It passed the earlier feed stopping location; full-stage completion and physical qualification are still pending at this observation. Existing unrelated calculations and failed-run evidence remain intact. Native closure checkpoint and a separate known-good copy were verified before feed restart. No unattended recovery claim is made for an incomplete stage.

FMEA/FTA revision: include material-table conversion as a suspected numerical-failure branch; retain contact, boundary and constitutive-integration alternatives. Owner unassigned; risk ratings unassessed. QC/Control Plan revision: inspect the solver's actual table transformation, preserve original curve/hash, quantify approximation error, and verify full stage/checkpoint and equilibrium before promoting a result. A passed earlier stopping location alone is insufficient evidence of repair. Canonical restricted investigation: solid_convergence_1552/INVESTIGATION.md under the project evidence directory above.


## Revision4, 2026-10-28T16:02:32.892454+09:00
The controlled solid/contact diagnostic completed the entire declared feed stage: solver Job finished, exit0, no plastic-integration error. Native closure and subsequent feed checkpoints were written, hashed and retained; local evidence read-back and graph retrieval passed. This validates the bounded table-representation workaround for that diagnostic only. The conversion inconsistency is still a suspected cause rather than an isolated proof, since the table representation changed slightly. Full machine-model passage, unload, mesh qualification and production optimum remain open. QC stage completion gate passed; FMEA/FTA alternatives and physical Control Plan gate remain open. Canonical completed_audit.json is linked by the restricted investigation note.
