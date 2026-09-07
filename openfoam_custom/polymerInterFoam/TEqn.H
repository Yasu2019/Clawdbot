{
    fvScalarMatrix TEqn
    (
        fvm::ddt(rho, T) + fvm::div(rhoPhi, T) - fvm::Sp(contErr, T)
      - fvm::laplacian(turbulence.alphaEff(), T)
      // Pressure work, viscous heating, and kinetic-energy coupling remain
      // disabled until their polymer calibration and energy balance are
      // independently validated. This screening equation therefore contains
      // only transient storage, bounded advection, and conduction.
     ==
        fvOptions(rho, T)
    );

    TEqn.relax();

    fvOptions.constrain(TEqn);

    TEqn.solve();

    // Guard the generalized screening case against non-physical thermo
    // inversion while coefficients remain uncalibrated.
    T.max(313.15);
    T.min(503.15);

    fvOptions.correct(T);

    mixture.correctThermo();
    mixture.correct();
}
