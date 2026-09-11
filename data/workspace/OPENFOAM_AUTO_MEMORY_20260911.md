# Auto-memory: OpenFOAM box-roundhole

2026-09-11: Cross-WLF `compressibleInterFoam` and CalculiX coupling audits passed for the circular-gate/four-vent box case. Gate/vent patch contracts and mesh quality passed. Coarse/refined cell counts are 63,993/67,165 (ratio 1.0496), so integral agreement is screening-only; formal spatial convergence remains REVIEW until a third same-CAD mesh or ratio >=1.10 is available. Never claim PASS from identical or insufficiently separated meshes. Virtual material coefficients remain uncalibrated.
