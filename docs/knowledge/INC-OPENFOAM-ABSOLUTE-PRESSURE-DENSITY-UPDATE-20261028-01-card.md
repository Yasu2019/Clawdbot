# OpenFOAM pressure-density mass closure — sanitized knowledge card

A source-level absolute-pressure update is implemented in both static and dynamic solver variants. Foundation 3.0.0/GCC 4.8.4 isolated builds passed; both binaries load, 7/7 C++98 kernel suites passed, and the full Python validation passed 79/79. Build provenance and binary hashes are recorded in `artifacts/verification/openfoam-phase-massclosure-build-20261028-1410/README.md`.

A corrected parser recovered 640 diagnostics from the prior short startup log. The p_rgh-coordinate mismatch candidate is not supported as the dominant residual cause in that case: median pressure-only mass delta relative to the preceding thermo/phase mass change is 0.0974%, and reduced-p versus absolute-p prediction differs by at most 4.15e-19 kg. Root cause remains UNKNOWN; phase-thermo/pressure and alpha-source coupling need new runtime evidence.

No fresh resin case was run with the new binaries. The 153,600-cell tutorial case uses an `extWHFTP` temperature boundary library not present in the local image; the prior checkpoint belongs to a different solver binary and was preserved. EVO is reachable by Tailscale, but its SSH host key awaits out-of-band verification. Next: verify host identity, obtain the exact library, re-check live resources/jobs, then run a fresh checkpointed case and separate-process resume. This card is operational evidence, not a molding-accuracy claim.

Canonical evidence: `docs/knowledge/INC-OPENFOAM-ABSOLUTE-PRESSURE-DENSITY-UPDATE-20261028-01.md`.