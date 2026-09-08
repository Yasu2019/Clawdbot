# Moldflow-style 3D animation output

The corrected OpenFOAM isothermal time series was exported with `foamToVTK`
for 0.0005–0.003 s and rendered as a 3-D VTK animation. The VTK snapshots
contain `alpha.polymer`, `T`, `p`, `p_rgh`, `U`, `rho`, and `etaCrossWLF`.

Output:

`artifacts/box_roundhole_v5/box100x60x50_moldflow_fill_animation.mp4`

The current MP4 colors the polymer volume fraction (`alpha.polymer`) and labels
the snapshots as screening output. Temperature, pressure, velocity, viscosity,
and density are available in the VTK snapshots for additional field-specific
animations. Warpage, sink, shrinkage, air-trap, and weld-line overlays remain
surrogate/diagnostic layers until the full pack/cool and structural handoff is
completed.
