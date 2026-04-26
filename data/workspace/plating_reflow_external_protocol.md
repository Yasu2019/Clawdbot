# Plating / Reflow Advanced Analysis External Development Protocol

## 1. Purpose

This document is the handoff protocol for external development support, including work produced by ChatGPT 5.4 under a separate subscription.

The goal is **not** to create a presentation-only visualization.  
The goal is to evolve the current plating/reflow analysis stack toward a **validation-grade engineering tool** that can:

- simulate plating and reflow behavior with stronger physics fidelity,
- compare simulation outputs with measured production data,
- identify where the model is still inaccurate,
- improve confidence in manufacturing parameter decisions,
- and produce ParaView-ready outputs plus pseudo cross-section snapshots.

This protocol must be followed so that any externally generated code can be integrated safely into the current Docker-based repository.

## 2. Current Repository / Runtime Context

Project root:

- `D:\Clawdbot_Docker_20260125`

Primary current implementation:

- [`clawstack_v2/data/work/scripts/plating_quality_analysis.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_quality_analysis.py)

Related validation/report tooling:

- [`clawstack_v2/data/work/scripts/plating_validation_report.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_validation_report.py)
- [`clawstack_v2/data/work/scripts/plating_doe_optimize.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_doe_optimize.py)
- [`clawstack_v2/data/work/scripts/plating_doe_design.R`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_doe_design.R)
- [`clawstack_v2/data/work/scripts/render_fib_like_snapshots.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/render_fib_like_snapshots.py)

Current default config:

- [`clawstack_v2/data/work/config/plating_reflow_defaults.json`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/config/plating_reflow_defaults.json)

Current quality dashboard runtime:

- [`clawstack_v2/docker/quality_dashboard/Dockerfile`](D:/Clawdbot_Docker_20260125/clawstack_v2/docker/quality_dashboard/Dockerfile)

Current case / output storage:

- Cases: [`clawstack_v2/data/work/harness/plating_reflow_lab/cases`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/cases)
- Outputs: [`clawstack_v2/data/work/harness/plating_reflow_lab/outputs`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/outputs)
- DOE runs: [`clawstack_v2/data/work/harness/plating_reflow_lab/doe`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/doe)

## 3. What Is Already Implemented

### 3-1. Thermal solver

The current code already includes:

- 2D transient thermal conduction
- `scikit-fem` based implementation
- VTU / PVD export for ParaView

This part is real FEM, not just a static heuristic.

### 3-2. Plating / reaction side

The current code also includes:

- region-dependent, temperature-sensitive diffusion approximation for Ni / Sn
- simplified interfacial reaction field
- IMC growth proxy
- liquid fraction proxy for Sn during reflow
- recrystallization / crystal-order proxy indicators

However, these are **not yet validation-grade physical models**.

### 3-3. Validation scaffold

Cases can now carry measured values in `case["measurements"]`, and the solver generates:

- automatic predicted-vs-measured comparison
- pass / fail / partial validation summary
- markdown and JSON validation reports

Example files:

- [`plating_validation_demo_20260321.json`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321.json)
- [`plating_validation_demo_20260321_validation_report.md`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321_validation_report.md)

### 3-4. DOE / optimization

The system already has:

- D-optimal DOE generation in R using `AlgDesign`
- repeated execution of the plating/reflow solver
- response-surface-based optimization

Completed example:

- [`doe_prod_20260321`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/doe/doe_prod_20260321)

## 4. Current Model Fidelity: Honest Status

The current analysis is **not yet suitable for final production guarantee**.

Current effective fidelity is:

- thermal: real transient 2D FEM
- diffusion: simplified spatial PDE
- interface reaction: simplified field model
- IMC: simplified derived evolution
- void / adhesion / wetting: reduced-order engineering proxies
- recrystallization / crystal growth: proxy visualization only

What is **not** yet rigorously solved:

- full multiphase diffusion with calibrated material laws
- real molten Sn fluid flow
- free-surface evolution
- real recrystallization kinetics
- real grain growth kinetics
- phase-field or CALPHAD-coupled microstructure evolution
- direct microscope-faithful microstructure prediction

## 5. What We Want Next

The external development target is **incremental realism**, not an unrealistic “solve everything at once” rewrite.

### Stage A: Stronger physics while staying practical

Desired:

- improve Ni / Sn / IMC transient coupling
- improve diffusion coefficients and temperature dependence
- improve interface reaction source term
- improve phase-fraction outputs
- improve calibration against measured values

This stage must remain computationally practical in the current Docker environment.

### Stage B: Validation-grade calibration workflow

Desired:

- define a stable measured-data schema
- fit model coefficients from production measurements
- quantify residual error
- tell the user which outputs are trustworthy and which are not

### Stage C: Better visual outputs

Desired:

- better pseudo cross-section rendering
- stronger differentiation of substrate / Ni / Sn / IMC / molten region
- stage-by-stage snapshots across plating and reflow
- ParaView-ready field outputs that correspond to physical interpretations

## 6. Explicit Deliverables Requested from External Development

External code proposals should aim to deliver the following.

### Deliverable 1: Physics upgrade proposal

Provide a concrete implementation proposal for:

- thermal equation
- Ni transport equation
- Sn transport equation
- IMC evolution equation
- liquid fraction treatment
- recrystallization / microstructure proxy treatment

This must include:

- equations
- assumptions
- required parameters
- expected outputs
- limitations

### Deliverable 2: Code patch plan

Provide a patch plan against:

- [`plating_quality_analysis.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_quality_analysis.py)

The patch plan must say:

- which functions to replace,
- which new functions to add,
- which outputs to preserve,
- how to keep backward compatibility with current JSON / VTU / PVD outputs.

### Deliverable 3: Measured data calibration schema

Provide a recommended measured-data schema for production validation, including fields such as:

- measured peak temperature
- measured TAL
- measured IMC thickness
- measured Ni remaining thickness
- measured Sn remaining thickness
- measured void score or void fraction
- measured wetting score
- measured adhesion metric
- measured warpage / stress proxy if available
- sample ID
- lot ID
- line ID
- profile ID

Prefer JSON-compatible structure that fits into the current `case["measurements"]`.

### Deliverable 4: Calibration / fitting method

Provide a coefficient tuning method for:

- diffusion coefficient factors
- reaction coefficient factors
- liquid-fraction related factors
- empirical scoring factors

The fitting method should be practical in this environment.

Good candidates:

- least squares
- bounded nonlinear fit
- Bayesian optimization only if justified

### Deliverable 5: Acceptance tests

Provide tests that prove the new implementation works.

Required tests:

- no-measurement case still runs
- measurement-filled case produces validation output
- timeline VTU/PVD still generates
- ParaView loadable outputs still exist
- backward-compatible JSON summary still exists

## 7. Constraints

External code must obey the following constraints.

### 7-1. Do not propose a massive platform rewrite

Do **not** propose:

- moving everything to MOOSE immediately
- moving everything to OpenFOAM immediately
- moving everything to a large monolithic solver stack
- introducing a fully separate architecture that abandons the current scripts

Those may be future options, but not the current integration target.

### 7-2. Keep current file-oriented workflow

Must preserve:

- case JSON input
- JSON summary output
- VTU / PVD export
- ParaView compatibility
- Docker-friendly script execution

### 7-3. Avoid breaking current outputs

Current outputs such as:

- `analysis_summary.json`
- `timeline_summary.json`
- `plating_reflow_field.vtu`
- `plating_reflow_timeline.pvd`

must still exist, even if extended.

### 7-4. Prefer incremental patching

Prefer:

- additional helper functions
- modular replacement of specific sections
- optional advanced mode flags

Avoid:

- giant single-file rewrites without migration path

## 8. What “Good” Looks Like

The ideal next-step contribution should achieve all of the following:

- better than current reduced-order behavior
- still executable in the current Docker environment
- produces interpretable ParaView outputs
- supports measured-data validation
- clearly states what remains approximate

The contribution does **not** need to solve true metallurgical microstructure perfectly.

It is acceptable if it honestly says:

- thermal is high confidence,
- diffusion / IMC is medium confidence,
- recrystallization is proxy only.

That is still useful, provided the code is structured and calibrated.

## 9. Recommended Engineering Direction

If the external developer must choose only one path, use this order:

1. strengthen transient thermal + diffusion + reaction coupling
2. add coefficient calibration against measurement
3. improve phase-fraction fields and output semantics
4. improve pseudo-FIB and pseudo-SEM rendering
5. only later consider full flow / phase-field / grain-growth rigor

## 10. Current Known Gaps

These issues are already known and should be treated as active gaps.

- thermal FEM exists, but metallurgy is still approximate
- current validation exists, but only as scaffold
- pseudo-FIB output exists, but it is not real microscope prediction
- current DOE is useful for ranking, not final process guarantee
- some UI code in the quality dashboard is unstable due to prior mojibake and should not be the primary integration target

## 11. Files That External Work Must Read First

Mandatory review set:

- [`clawstack_v2/data/work/scripts/plating_quality_analysis.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_quality_analysis.py)
- [`clawstack_v2/data/work/scripts/plating_validation_report.py`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/scripts/plating_validation_report.py)
- [`clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321.json`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321.json)
- [`clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321_validation_report.md`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/cases/plating_validation_demo_20260321_validation_report.md)
- [`clawstack_v2/data/work/harness/plating_reflow_lab/outputs/plating-20260320-180841/analysis_summary.json`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/outputs/plating-20260320-180841/analysis_summary.json)
- [`clawstack_v2/data/work/harness/plating_reflow_lab/outputs/plating-20260320-180841/timeline_summary.json`](D:/Clawdbot_Docker_20260125/clawstack_v2/data/work/harness/plating_reflow_lab/outputs/plating-20260320-180841/timeline_summary.json)

## 12. External Request Template

Use the following request template when asking ChatGPT 5.4 or another external developer.

---

You are helping upgrade an existing plating / reflow analysis system inside a Python + Docker engineering environment.

Current state:

- transient 2D thermal FEM already exists using `scikit-fem`
- spatial diffusion and simplified interfacial reaction are implemented, but still approximate
- measured-vs-predicted validation scaffold already exists
- ParaView outputs and pseudo-FIB rendering already exist

Primary file:

- `clawstack_v2/data/work/scripts/plating_quality_analysis.py`

Your task:

1. Propose an upgraded but still practical physics model for:
   - thermal
   - Ni diffusion
   - Sn diffusion
   - IMC growth
   - liquid fraction
   - recrystallization / microstructure proxy

2. Provide a concrete patch plan against the current Python structure.

3. Preserve backward compatibility for:
   - JSON summaries
   - VTU/PVD outputs
   - case JSON input
   - validation reporting

4. Provide code-level recommendations, including:
   - new helper functions
   - new parameters to add
   - suggested formulas
   - expected runtime impact
   - what remains approximate

5. Also propose a measured-data calibration workflow for:
   - peak temperature
   - TAL
   - IMC thickness
   - Ni remaining
   - Sn remaining
   - void
   - wetting
   - adhesion

Constraints:

- do not suggest a full rewrite into a separate solver platform
- do not require MOOSE / OpenFOAM / FEniCSx as the only solution
- stay compatible with the current Docker-based script flow
- prefer incremental implementation

Output wanted:

- a detailed engineering proposal
- a patch plan
- if possible, concrete Python code patches

---

## 13. Acceptance Criteria for Returned External Work

Externally produced work is acceptable only if:

- it understands the current state correctly,
- it does not claim that current pseudo-FIB is real microstructure prediction,
- it proposes incremental integration,
- it preserves current artifacts,
- it improves validation-grade capability,
- it distinguishes between real FEM and proxy behavior honestly.

## 14. Final Note

The right target is not “perfect metallurgy in one jump”.  
The right target is:

- stronger transient thermal + diffusion + reaction,
- real validation against measurements,
- clearer trust boundaries,
- and better engineering usefulness.

That is the standard expected from external support.
