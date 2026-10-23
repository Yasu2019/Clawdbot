# OpenFOAM Foundation 3.0.0 resin solver runtime — verified build

Date: 2026-10-23 (JST)

## Reproducible environment

- Upstream: OpenFOAM Foundation 3.0.0 source pack, official MD5 `fefa399a5c0cbe33fbabb65be17ea617`; locally verified SHA-256 `DA710FB00EA87504F99B2FAD26676A58039964E85E5F389DE7D8996049E0182C`.
- Built with the Trusty 14.04 reference userland and GCC 4.8.4 in an isolated Docker image; runtime network disabled.
- Base image: `clawstack/openfoam-foundation:3.0.0-trusty-source-20261023`, image ID `sha256:b013b6ada9fb665576fc86cc3f0c1110b0ede07f4f05b8e4f3915dec811a2734`.
- Resin solver image: `clawstack/openfoam-foundation:3.0.0-trusty-injmold-20261023`, image ID `sha256:7dd9757de2c8859029a748930479616755ab3071c64b75e675b32e58c3fc3458`.
- Packaged `openInjMoldSim v1.1.1`; executable SHA-256 `198007b370904885e4a50f8f259ccf8c9f9eac64985dd6ccc897553cce3925cb`.

## Verification

`WM_PROJECT_VERSION` reports `3.0.0`; `blockMesh -help`, `simpleFoam -help`, and `openInjMoldSimFimacAba -help` launch; OpenFOAM identifies itself as `OpenFOAM-3.0.0`; linker checks reported no missing shared libraries. The resin solver source compiled in a disposable build directory against this exact runtime.

Initial full-library build failed because `ptscotch.h` was missing. Installing Trusty package `libptscotch-dev` resolved the dependency, after which the full source-library build and standard executables completed. Preserve these dependency and version checks when reproducing.

## Scope and recovery boundary

This validates source compilation and command loading only. No resin case was run. Flow-front accuracy, multi-gate filling, void physics, shrinkage, sink, short shot, weld lines, air traps, thermal/pressure/VOF coupling, moving-mesh gas conservation, and restart/checkpoint behavior remain unvalidated. Before unattended analysis, verify a case-specific native checkpoint, provenance, timestamp, size, known-good checkpoint preservation, and exact resume command. Trusty is obsolete; keep the runtime isolated and network-disabled.
