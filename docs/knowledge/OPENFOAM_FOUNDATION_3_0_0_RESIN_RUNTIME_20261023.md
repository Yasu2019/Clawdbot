# OpenFOAM Foundation 3.0.0 resin solver runtime — verified build

Date: 2026-10-23 (JST)

## Pinned runtime

- OpenFOAM Foundation 3.0.0 source pack, official MD5 `fefa399a5c0cbe33fbabb65be17ea617`; verified SHA-256 `DA710FB00EA87504F99B2FAD26676A58039964E85E5F389DE7D8996049E0182C`.
- Trusty 14.04 reference userland, GCC 4.8.4, isolated Docker runtime with networking disabled.
- Base image: `clawstack/openfoam-foundation:3.0.0-trusty-source-20261023-entrypointfix2`; ID `sha256:03df89f2849490a6e93ed95cf838b92d7f569a0422b10a22c3cd2ebae1e6454e`.
- Resin solver image: `clawstack/openfoam-foundation:3.0.0-trusty-injmold-20261023-fix3`; ID `sha256:b9022b856747ceeaa89f87acb727b5a78fbd4da8f4fcabd3a1f3defc15782538`.
- Packaged `openInjMoldSim v1.1.1`; binary SHA-256 `198007b370904885e4a50f8f259ccf8c9f9eac64985dd6ccc897553cce3925cb`.

## Compatibility checks

The final entrypoint saves the solver argv, clears positional arguments before sourcing Foundation `etc/bashrc`, and then executes the saved command. This keeps solver switches out of `FOAM_SETTINGS`. The wrapper check observed empty `FOAM_SETTINGS`, `WM_PROJECT_VERSION=3.0.0`, and `blockMesh`, `simpleFoam`, and `openInjMoldSimFimacAba` on PATH. The safe `simpleFoam -help -noFunctionObjects` and custom solver `-help -noFunctionObjects` probes pass. The custom solver's shared libraries resolve when checked through the initialized environment.

The first full-library build exposed a missing `ptscotch.h`; installing Trusty `libptscotch-dev` resolved it. The current resin solver source compiled against this exact Foundation runtime in a disposable directory from a read-only source mount.

## Recovery and validation boundary

This verifies source compilation, runtime initialization, command lookup, and shared-library loading only. No resin case was run. Flow-front accuracy, multi-gate filling, void physics, shrinkage, sink, short shot, weld lines, air traps, thermal/pressure/VOF coupling, moving-mesh gas conservation, and restart/checkpoint behavior remain unvalidated. Before unattended analysis, verify a case-specific native checkpoint, provenance, timestamp, size, preservation of a known-good checkpoint, and exact resume command. Trusty is obsolete; keep the runtime isolated and network-disabled.
