# OpenFOAM custom boundary-condition and restart startup card

Incident: `INC-OPENFOAM-EVO-FOUNDATION3-STARTUP-RESTART-20261028-01`

For the custom Foundation 3.0.0 molding solver:

- Put required custom-library declarations in the effective `system/controlDict` actually passed to the solver. A template or alternate `controlDict0` does not load the library.
- Verify the custom library matches the solver's OpenFOAM/compiler build, its hash is the expected one, and `ldd` resolves dependencies under the exact runtime `LD_LIBRARY_PATH`.
- A serial restart using relative material tables must run with the case directory as the current working directory, even when `-case` is supplied.
- Before resuming, preserve and hash-check a complete solver-native time directory, confirm solver/plugin version and decomposition layout, retain `purgeWrite 0`, then require the log to show the expected latest time and a later written time.
- A successful short startup/restart demonstrates runtime operability only. It does not establish polymer filling, weld-line, void, shrinkage, or product accuracy.

Validated once: Foundation 3.0.0 serial run from 0 to 2e-6 and native latest-time continuation from 2e-6 to 3e-6; all checkpoint manifests passed. Longer, MPI, physical-property, and product validation remain open.
