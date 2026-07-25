# mfalign_snappy_v001

Closed-cavity resin fill template captured verbatim from the proven Lavie case
`moldflow-union-xplus-d2-mfalign-v3-20260723` (interFoam, alpha.polymer 0.9963
at t = 1.24 s, max Courant 0.242).

## Geometry contract

The triSurface is in **metres**, watertight (every edge shared by exactly two
triangles), 1066 triangles, volume 4.13417e-05 m3 which matches the
`cavity_volume_m3` used for the fill-fraction KPI.

Part: box shell 100 x 60 x 50 mm, wall thickness 2.0 mm.
Gate: +X face, centre (50, 0, 25) mm, diameter 2 mm.
Vent: -X face, centre (-50, 0, 25) mm, radius 4 mm.

## Mesh pipeline

    surfaceFeatureExtract
    blockMesh
    snappyHexMesh -overwrite
    topoSet
    createPatch -overwrite
    interFoam

`topoSet` + `createPatch` carve the `gate` and `vent` patches out of the
`moldflow` surface patch with cylinder cuts, so the patch set is
`gate` / `vent` / `moldflow` -- not the `inlet1..walls` set used by the
blockmesh_bbox path.

## Hand-tuned values that must not be re-derived by guesswork

`locationInMesh (0.0492 0.0003 0.0253)` sits inside the 2 mm shell wall, 0.8 mm
in from the +X face, and is deliberately offset from the background grid planes.
The bounding-box centre would select the hollow interior of the box, i.e. the
wrong volume entirely.

`setFieldsDict` is carried over from an earlier plate case and is **not** part of
the proven pipeline; it is kept only for parity with the source case.
