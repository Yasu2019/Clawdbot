# Cross-WLF OpenFOAM transport plug-in

This plug-in implements the `generalizedNewtonianViscosityModel` runtime
interface. It reads `T`, `rho`, and `p`/`p_rgh` from the case and evaluates

`eta0(T,p) = D1 exp(-A1 (T-D2-D3 p)/(A2+T-D2))`

followed by the Cross shear-thinning law. It returns kinematic viscosity to the
momentum transport model, so the value is recalculated from the current
temperature, pressure, and strain rate during every correction.

The OpenFOAM 2512 library was compiled successfully in the development
container and loaded by `compressibleInterFoam` in the custom test case. The
case reached `End` without a fatal error.

Build inside the matching OpenFOAM container:

```sh
source /usr/lib/openfoam/openfoam2512/etc/bashrc
wmake libso
```

The case must load `libcrossWLFViscosityModel.so` and select
`viscosityModel crossWLFViscosityModel` under the generalized-Newtonian
laminar model. Coefficients are virtual screening values until replaced by
measured rheology.
