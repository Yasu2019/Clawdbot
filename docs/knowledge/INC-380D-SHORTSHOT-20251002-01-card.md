# 380D cover short-shot incident (sanitized)

Evidence review and exploratory CAE on 2026-11-23: The 2025-10-02 report shows a Cover B short shot between gates 1 and 2, around one-third along the pictured part. It attributes the event to valve 1 air-solenoid trouble/sluggish opening; cause and delay duration are not independently verified.

Two 76Case-derived tetra fill runs completed with a 10 s native checkpoint interval. Gate-1 delay 0.20 s gave 13.807 mm³ residual unfill; 0.50 s sensitivity gave 34.562 mm³. Both placed the residual at the far STEP Y-end, not at the reported G1–G2 region near image fraction 0.325. The calculated and reported positions do not match.

This is an exploratory model mismatch, not physical validation or proof against the valve-1 hypothesis. Gate XYZ/orientation and hot-runner transform remain provisional; gate diameter is assumed; cooling layout, cavity-wall temperature, and event-specific pressure profile are not fully represented. Full input hashes, run provenance, and limitations are in the canonical record and local run manifest. Production validation remains open.

Canonical record: `docs/knowledge/INC-380D-SHORTSHOT-20251002-01.md`.