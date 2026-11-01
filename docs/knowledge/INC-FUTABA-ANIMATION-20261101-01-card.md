# INC-FUTABA-ANIMATION-20261101-01 — illustrative roll-path geometry

Observed 2026-11-01 21:49 JST on K10 during a user review of a locally generated technical HTML report. The user identified a mismatch between an illustrative strip curve and roll positions.

Confirmed cause: the original SVG curve used hand-positioned control points independently of roll contact geometry. A schematic disclaimer did not make this inconsistency acceptable. The illustration was not generated from solver results; no solver input or result was changed by the correction.

Correction: preserved prior documents; generated a new revision from one shared geometry definition. The idealized crown-contact example accounts for the displayed half-thickness of the strip, uses source-derived longitudinal roll proportions, and explicitly distinguishes the illustration from actual contact and transient FEM output. Real contact points and strip extrema need not coincide with roll center abscissae when contact angles differ.

Validation: checked all seven idealized crown contacts and zero slope at those vertices; sampled 40,001 positions to check nonpenetration against all roll circles including displayed strip thickness; verified generated and browser-rendered paths match; reviewed browser screenshot. Existing interactive numerical profile readouts still match source data. These checks validate the illustration only, not physical contact or solver accuracy.

Draft FMEA: failure mode misleading schematic contact; effect incorrect interpretation; confirmed cause independent hand-authored geometry; prevention shared geometry; detection contact/tangent/nonpenetration tests and screenshot review. Owner is the document-maintenance agent for this correction. S/O/D and RPN unassessed; residual risk is idealization being mistaken for actual computed contact.

Draft FTA: misleading illustration arises from independent path construction AND missing geometric regression tests. Physical solver error is not established by this presentation defect.

Draft QC process chart: geometry authoring → contact/clearance regression gate → browser/source path equality → visual review → versioned delivery. Failure at any gate blocks presenting the schematic as checked.

Draft Control Plan: on any geometry revision, check each idealized contact, tangent and sampled clearance; verify paths and displayed source ratios; preserve prior versions and correct the illustration if checks fail. Acceptance is consistency with declared schematic construction, not a new engineering tolerance. All seven contacts passed; finite sampling alone is not a proof for arbitrary future curves.

Canonical evidence is retained in the project animation incident note, geometry audit and browser QA records. No raw engineering curves, credentials or unrelated host data are included in this card.


## Follow-up revision2 ? 2026-11-01 22:31 JST
The user identified that a retained feed/cut schematic still showed an opening inconsistent with the numerical candidate, although a separate setting-height panel was correct. Confirmed cause: the specifically referenced animation was not replaced in the prior repair. Replaced that panel with shared model-scale roll coordinates. Verified all seven crown-contact abscissae, selected candidate roll heights, continuous identity/length of the highlighted cut segment and exact source final-section profiles. Through-material and release transition remain declared illustrative interpolations, not solver time history. Four scenarios and three display magnifications pass; browser visual QA found and fixed desktop clipping before delivery. Prevention: validate the specific user-reported panel and the entire visible output, not only a new auxiliary panel. Solver outputs and previous document revisions preserved.
