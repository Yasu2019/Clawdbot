{
    const Switch solveEnergy
    (
        mesh.solutionDict().subDict("PIMPLE").lookupOrDefault<Switch>
        (
            "solveEnergy",
            true
        )
    );

    if (!solveEnergy)
    {
        Info<< "Energy equation disabled for isothermal hydraulic gate" << nl;
        T.correctBoundaryConditions();
        mixture.correctThermo();
        mixture.correct();
    }
    else
    {
    volScalarField TBeforeSolve(T);
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

    const scalar thermalRelaxation
    (
        mesh.solutionDict().subDict("PIMPLE").lookupOrDefault<scalar>
        (
            "thermalRelaxation",
            0.1
        )
    );
    T = TBeforeSolve + thermalRelaxation*(T - TBeforeSolve);

    // Guard the generalized screening case against non-physical thermo
    // inversion while coefficients remain uncalibrated.
    const scalar TminBeforeBound = gMin(T.primitiveField());
    const scalar TmaxBeforeBound = gMax(T.primitiveField());
    const scalar temperatureBoundTolerance = 1e-6;
    if
    (
        TminBeforeBound < 313.15 - temperatureBoundTolerance
     || TmaxBeforeBound > 503.15 + temperatureBoundTolerance
    )
    {
        Info<< "temperatureBound event: min=" << TminBeforeBound
            << " max=" << TmaxBeforeBound << nl;
        T.max(313.15);
        T.min(503.15);
    }

    fvOptions.correct(T);

    mixture.correctThermo();
    mixture.correct();
    }
}
