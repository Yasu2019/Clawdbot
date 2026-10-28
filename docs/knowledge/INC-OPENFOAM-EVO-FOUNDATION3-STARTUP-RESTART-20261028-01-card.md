# OpenFOAM custom boundary-condition and restart startup card

Incident: `INC-OPENFOAM-EVO-FOUNDATION3-STARTUP-RESTART-20261028-01`

For the custom Foundation 3.0.0 molding solver:

- Put required custom-library declarations in the effective `system/controlDict` actually passed to the solver. A template or alternate `controlDict0` does not load the library.
- Verify the custom library matches the solver's OpenFOAM/compiler build, its hash is the expected one, and `ldd` resolves dependencies under the exact runtime `LD_LIBRARY_PATH`.
- A serial restart using relative material tables must run with the case directory as the current working directory, even when `-case` is supplied.
- Before resuming, preserve and hash-check a complete solver-native time directory, confirm solver/plugin version and decomposition layout, retain `purgeWrite 0`, then require the log to show the expected latest time and a later written time.
- A successful short startup/restart demonstrates runtime operability only. It does not establish polymer filling, weld-line, void, shrinkage, or product accuracy.

Validated once: Foundation 3.0.0 serial run from 0 to 2e-6 and native latest-time continuation from 2e-6 to 3e-6; all checkpoint manifests passed. Longer, MPI, physical-property, and product validation remain open.


2026-10-28 runtime update: fresh current-source Foundation 3.0.0 build on EVO passed 552/552 source checks. Serial run completed 0→1e-6 and native latestTime restart 1e-6→2e-6; two 24-file SHA-verified checkpoints retained. Attempt01 root execution failed coded-boundary policy; attempt02 missing case cwd failed relative table lookup; attempt03 corrected both. Case is a 153,600-cell thin 2D channel, not the 100×60×50 mm box. Smoke/restart only; physical accuracy and continuity residual cause remain unverified/UNKNOWN. Evidence: openfoam-evo-current-build-20261028-1438 README and runtime-evidence-attempt03.
