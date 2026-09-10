# Compressible VOF + vent-flow smoke run

- Solver: OpenFOAM 2512 `compressibleInterFoam` in `opencfd/openfoam-dev:latest`
- Mesh: corrected four-vent round-hole box mesh, 67,165 cells
- Run: `endTime=0.01 s`, injection speed `0.005 m/s`
- Result: PASS to `Time = 0.01`; output time directory `0.01/`
- Vent boundaries: `pressureInletOutletVelocity` for `U`, `totalPressure` for pressure, `inletOutlet` for polymer fraction and temperature
- Air: compressible perfect-gas thermo
- Polymer: current OpenFOAM run uses `rhoConst` for numerical stability; `taitPolymerProperties` is recorded as a virtual hook but is **not yet coupled into the solver**
- Therefore this is a genuine compressible-air/VOF/vent-flow run, but not yet the final Tait-compressible-polymer production model.

The run reached the requested end time without a solver crash. The 0.01 s test took about 120 s on the Docker CPU environment.
