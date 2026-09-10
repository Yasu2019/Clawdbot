# Custom Cross-WLF OpenFOAM run

- Plugin: `libcrossWLFViscosityModel.so`
- Solver: `compressibleInterFoam` OpenFOAM 2512
- Direct fields used by the plugin: `T`, `rho`, and `p`/`p_rgh`
- Momentum model: generalized-Newtonian, Cross-WLF viscosity
- Run: `endTime=0.001 s`, injection speed `0.001 m/s`
- Result: **PASS**; plugin compiled and solver reached `End`
- Temperature and pressure equations converged in the same run

This confirms direct momentum coupling of the custom Cross-WLF model. The
coefficients are virtual screening values and are not a measured material
calibration.
