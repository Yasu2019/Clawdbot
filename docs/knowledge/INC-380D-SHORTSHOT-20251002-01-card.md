# 380D cover short-shot incident (sanitized)

Evidence review and exploratory CAE on 2026-11-23: The 2025-10-02 report shows a Cover B short shot between gates 1 and 2, around one-third along the pictured part. It attributes the event to valve 1 air-solenoid trouble/sluggish opening; cause and delay duration are not independently verified.

Two 76Case-derived tetra fill runs completed with a 10 s native checkpoint interval. Gate-1 delay 0.20 s gave 13.807 mm³ residual unfill; 0.50 s sensitivity gave 34.562 mm³. Both placed the residual at the far STEP Y-end, not at the reported G1–G2 region near image fraction 0.325. The calculated and reported positions do not match.

This is an exploratory model mismatch, not physical validation or proof against the valve-1 hypothesis. Gate XYZ/orientation and hot-runner transform remain provisional; gate diameter is assumed; cooling layout, cavity-wall temperature, and event-specific pressure profile are not fully represented. Full input hashes, run provenance, and limitations are in the canonical record and local run manifest. Production validation remains open.

Canonical record: `docs/knowledge/INC-380D-SHORTSHOT-20251002-01.md`.

## 2026-11-25 JST — INC-380D-VOLCAP-20261125

A compressible filling solver applied its net-front-volume limit only when a trapped-air model existed. Turning that model off silently increased the volume placed in the cavity. The earlier unvented comparison is withdrawn. The corrected analysis applies the cap for compressible flow in both solver entry points, rejects nonconservative histories before publishing a successful summary, and checks cumulative inlet volume through the run. Replaying the old output reproduces the failure; boxed reference data and a capped diagnostic pass. Use the versioned v3 report for the corrected comparison. Production defect causation and mesh convergence remain unverified. Related record: INC-380D-SHORTSHOT-20251002-01.
