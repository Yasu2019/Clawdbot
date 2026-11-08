# INC-SUS-SURFACE-20261108-01 — theoretical screening follow-up

Observed 2026-11-08 JST. Sanitized methodological findings only. Customer identity, production dimensions, private correspondence and yields are excluded.

Finite-volume transport with an assumed pinned evaporating drop reproduced perimeter accumulation of slowly diffusing particles. Fixed-width perimeter-band integrals stabilized with grid refinement, while the pointwise maximum did not. Reject the maximum as an unsupported local-thickness/visibility prediction. This model stops before complete drying and does not solve precipitation, adsorption or optical appearance.

A linear Galerkin diffusion FEM for an ideal stagnant overlap gap agreed with an analytical solution after spatial and temporal refinement. A consistent-mass startup exhibited nonphysical oscillation under a sudden boundary condition; a positivity gate caught it. Mass lumping restored the required monotonicity. A separate verification gate initially conflated temporal convergence with cancellation of spatial and temporal error; comparing against a fine-time solution on the same grid corrected that test. Failed artifacts were preserved.

Both custom solvers verified native immutable checkpoint generations with source/config/version checks, plus zero-difference restart equivalence and successful separate-process CLI resume. Runs were bounded, attended, serial and small. Mathematical screening completion is distinct from product validation.

Faraday-law oxidation examples use assumed current density and finite foreign-iron inventory. They do not establish corrosion onset, actual kinetics, corrosion-product phase, stainless substrate attack or visible color. Product chemistry and process measurements are still required.

FMEA/FTA/QC/Control Plan follow-up requires positivity, conservation, fixed-observable convergence, same-grid time refinement, recovery provenance and explicit source-versus-assumption labeling. These controls were checked for the narrow models; production corrective effectiveness remains unverified.
