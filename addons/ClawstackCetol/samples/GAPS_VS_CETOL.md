# CETOL 6 Sigma: CAD add-in skipped; methods vs documented CETOL

Creo / SOLIDWORKS / NX native add-in is **out of scope** (user 2026-08-29).
Host is FreeCAD workbench + web app.

Truth Gate: **UNVALIDATED** vs Sigmetrix on customer assemblies. Do not label commercial parity.

| Area | Documented CETOL 6 Sigma | This stack | Claim |
|---|---|---|---|
| CAD add-in | Creo / SW / NX | Skipped on purpose | n/a |
| Measures | Feature-to-feature | Relative `from`/`to` frames (not world origin) | Match CETOL intent |
| Closed loop | Joint-local `h(x,u)=0` + DLM | Joint-local `Du=-pinv(B)A Dx` on mates | Match Gao/Chase |
| SOTA | Full 2nd MSM + GLD table | Linear+angular MSM, cross cap 32, 4 moments | Table still not Gao 1995 |
| Yield tails | One GLD table | FMKL + Gram-Charlier + Cornish-Fisher + disagreement flag | **Beyond** table-only |
| Multi-CTQ | Typically one CTQ | Joint P(all linear CTQs in spec) Gaussian copula | **Beyond** single-CTQ report |
| Closed-loop MC | Optional MC | Nonlinear modified MC, B frozen, vs SOTA 15% | Independent gate |
| Geometric form | Chase 1996 at joints | Datum flatness + tilt on DieBase | Analog, not CAD face form |
| Process | Rigid CAD only. No station clock, no sheet flex, no cavity fill | Sequential BL→PI→BE transfer + compliant-plate σ + Moldflow shrink handoff (fail-closed / THEORY_PROXY labeled) | **CETOL cannot implement**; UNVALIDATED vs forming/fill |
| MMC / LMC | Y14.5 in solver | Bonus when modifier+size exist | Missing data = INSUFFICIENT |
| Animation | CAD shape perturb | Placement wiggle | Still weaker than CAD shape |
| Golden | CETOL 3D cases | 1D WC/RSS/MC + open-chain Tz/Rx | Not a CETOL 3D pass |
