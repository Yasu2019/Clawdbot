# Moldflow-Class Solver Landscape And Internal Benchmark Plan

Date: 2026-07-08 JST

## Conclusion

Resin-flow solvers do exist. The mature category is commercial injection-molding CAE: Autodesk Moldflow, Moldex3D, SIGMASOFT Virtual Molding, and similar systems. OpenFOAM is not a drop-in Moldflow replacement; it is a CFD toolbox that can support proxy and research implementations when meshing, rheology, thermal, packing, cooling, defect KPIs, and validation are added by us.

## Source Handling

Use only legal public information.

- `direct_free`: official public pages, open documentation, open papers, open repositories.
- `paid_or_subscription`: commercial solver products and paid manuals; use only metadata unless authorized access exists.
- `manual_review`: registration-only or license-unclear sources.
- `no_go`: no paywall bypass, credential misuse, DRM bypass, or copying proprietary material databases.

## Solver Map

| Solver | Type | Access | Role In This Project |
|---|---|---|---|
| Autodesk Moldflow | Commercial | paid_or_subscription | L10 benchmark target and terminology reference |
| Moldex3D | Commercial | paid_or_subscription | Alternative benchmark for true-3D flow, weldline, short shot, air trap, thermal/warpage scope |
| SIGMASOFT Virtual Molding | Commercial | paid_or_subscription | Reference for full-mold thermal-cycle simulation scope |
| OpenFOAM interFoam / compressibleInterFoam | Open-source toolbox | direct_free | Internal proxy foundation; requires our own case setup and validation |

## Current Internal Status

Latest improved thermal proxy:

- Trial: `demo_spread_plate_pointgate_cool_const_20260708`
- Scope: partial-fill thermal proxy
- Fill fraction: 40.09%
- `alpha_max`: 1.0
- Temperature range: 333.87 K to 511.21 K
- Video: `data/cae_te_workspace/results/images/demo_spread_plate_pointgate_cool_const_20260708_temperature.mp4`

This is a valid improvement over the prior unstable demo, but it is not yet Moldflow-grade validation.

## Benchmark KPIs

- Fill-front pattern: straight initial gate advance, then lateral spreading.
- Bounded alpha: `0 <= alpha.polymer <= 1.05`.
- Thermal gradient: wall/mold-adjacent region cooler than melt/front proxy.
- Mass balance: `mass_balance_err_pct <= 5` for VOF proxy runs.
- Commercial correlation: at least one authorized commercial or measured reference case before L10 claims.

## Immediate Backlog

1. `MF-BENCH-001`: Add precheck for generated cooling cases.
2. `MF-BENCH-002`: Make safe thermal proxy defaults visible in CAE Studio.
3. `MF-BENCH-003`: Define commercial correlation record schema.
4. `MF-BENCH-004`: Benchmark WLF thermo path separately.

## References

- Autodesk Moldflow: https://www.autodesk.com/products/moldflow/overview
- Moldex3D Flow: https://www.moldex3d.com/products/software/moldex3d/flow/
- SIGMASOFT: https://www.sigmasoft.de/
- OpenFOAM interFoam: https://doc.openfoam.com/2306/tools/processing/solvers/rtm/multiphase/interFoam/
- OpenFOAM numerical schemes: https://www.openfoam.com/documentation/user-guide/6-solving/6.2-numerical-schemes
