# OpenFOAM mesh convergence decision

The box-roundhole Cross-WLF `compressibleInterFoam` pair passes solver, alpha, viscosity, integral, CalculiX, patch-contract, and mesh-quality checks. Coarse/refined cell counts are 63,993/67,165, ratio 1.0496. Integral differences are below 1e-3, but the minimum resolution ratio is 1.10; therefore formal spatial convergence is REVIEW, not PASS. Preserve the circular gate/four-vent patch contract and generate a third same-CAD mesh before promotion.
