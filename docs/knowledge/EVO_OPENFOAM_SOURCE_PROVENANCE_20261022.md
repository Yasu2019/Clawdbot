# OpenFOAM current-source provenance and build gate — 2026-10-22

## Finding

The staged `polymerInterFoam` executable and `libgeneralizedPolymerThermo.so` are dated 2026-09-08. The current modified solver sources are newer: `compressibleInterFoam.C` is dated 2026-10-16 and `TEqn.H` is dated 2026-10-15. A prior link check of the September binary against OpenFOAM v2512 does not establish that the October sources compile or run correctly.

The current C++ thermo test source includes bounded and unbounded Tait-state checks, as well as derivative/property checks. Those later tests have not yet been built or run against the current source. Earlier October 15 test/build evidence applies only to the source snapshot used then.

## Admission decision

Do not use the September binary as validation of current source. Preserve the active OpenRadioss panel analysis and its restart/guard tasks. The current-source build was held after live checks found heavy K10 CPU contention and an active EVO-X2 panel run with unresolved installed-versus-visible RAM capacity. These measurements are time-bound and must be refreshed before any build or solver dispatch.

## Required verification sequence

1. Refresh host reachability, worker, scheduled tasks, active solver processes, host and guest memory, CPU interval samples, and case-specific capacity.
2. Copy the exact modified source into a unique isolated build tree. Record source hashes, OpenFOAM/compiler versions, build paths, and resulting executable/library hashes. Never overwrite the staged binary or the user's working source.
3. Build and run the current C++ thermo regression tests in a bounded environment; retain complete logs and a test-to-source hash manifest.
4. Run the smallest solver integration case only after checking its inputs and solver-native restart procedure. Verify a fresh checkpoint by timestamp and size, then validate field/temperature/pressure behavior and mass/energy balances before broader use.
5. Keep measured-material calibration and production accuracy claims separate from compilation, link checks, and screening-case results.

## Current status

Source/binary provenance mismatch: confirmed. Current-source C++ build/test: pending. Current-source solver integration: pending. Restart compatibility for the rebuilt source: pending. No code or binary was changed in this review. Tracking: Beads `Clawdbot_Docker_20260125-tw5g`.
