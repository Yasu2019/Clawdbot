# Quality Incident: Moldflow STL has non-manifold bottom perimeter

- Date: 2026-07-19 JST
- Goal: Use the supplied 100 x 60 x 50 mm, 2 mm wall-thickness model for Main LAVIE OpenFOAM resin filling with a 2 mm gate.
- Input: `C:\Users\yasu\OneDrive\デスクトップ\Moldflow.stl`
- Input SHA-256: `68B12F119F2EC194137349432C4B0E224BD98CCD635422B2388D135CB99E9896`

## Observed facts

| Check | Result |
|---|---:|
| Binary STL triangles | 552 |
| Unique undirected edges | 824 |
| Edges shared twice | 820 |
| Boundary edges | 0 |
| Non-manifold edges | 4 |
| Duplicate triangle groups | 0 |
| Signed volume | 42571.941842 mm3 |

All four non-manifold edges are the outer perimeter at `Z=0`:

- `(50,-30,0)` to `(50,30,0)` -- incidence 4
- `(-50,30,0)` to `(50,30,0)` -- incidence 4
- `(-50,-30,0)` to `(50,-30,0)` -- incidence 4
- `(-50,-30,0)` to `(-50,30,0)` -- incidence 4

The requested gate location is the center of the positive-X 60 x 50 mm face: `(50,0,25) mm`; circular diameter 2 mm.

## RCA (5 Whys)

1. The STL topology gate failed because four edges have incidence greater than two.
2. Each failing edge is shared by four faces rather than the two required for a manifold surface.
3. The failing edges coincide with the complete bottom outer perimeter.
4. The bottom and side-wall surface sets were exported as touching shells without a clean Boolean union at their common perimeter.
5. STL export preserved tessellated contact topology rather than one watertight manifold boundary suitable for volume meshing.

## Fishbone summary

- Method: tessellated export without manifold/Boolean-union acceptance gate.
- Model: bottom plate and walls meet as separate surface sets.
- Measurement: prior workflow checked dimensions but not edge incidence.
- Machine/software: the current bbox proxy does not consume the real surface, so this defect was previously hidden.

## FMEA

| Failure mode | Effect | Severity | Detection | Countermeasure |
|---|---|---:|---:|---|
| Four-face bottom edges | `snappyHexMesh` leakage or ambiguous region | 9 | 2 | Repair a disposable copy and require zero non-manifold edges |
| Bbox proxy fallback | Wrong flow domain despite successful run | 10 | 6 | Prohibit bbox proxy for this user-confirmed real-shape case |
| Gate patch without adequate local mesh | Missing/incorrect 2 mm inlet area | 8 | 4 | Refine locally and verify patch area near 3.1416 mm2 |

## Decision rules

- IF `BoundaryEdges != 0` OR `NonManifoldEdges != 0`, THEN do not start the real-geometry OpenFOAM run, BECAUSE the fluid region is not proven meshable.
- IF a user supplies a real STL after reporting a wrong model, THEN do not substitute its bounding box, BECAUSE dimensions alone do not preserve the flow domain.
- IF the gate diameter is 2 mm, THEN verify the final inlet patch area against `pi * 1^2 = 3.1416 mm2` within the declared mesh tolerance.

## Countermeasure plan

1. Preserve the source STL byte-for-byte and work only on a newly named disposable copy.
2. Use the exact OpenFOAM installation on Main LAVIE to run its version-matched surface diagnostics.
3. Repair/merge only the four bottom perimeter junctions; do not globally smooth or rescale the shape.
4. Re-run the dependency-free topology check and OpenFOAM surface check.
5. Create the positive-X circular inlet centered at `(50,0,25) mm`, diameter 2 mm, with local mesh refinement.
6. Require a distinct inlet patch, correct normal direction, nonzero cell volume, mesh-quality pass, and inlet area tolerance before solving.
7. Create a new case name; never overwrite the current analysis.

## Verification

- Geometry: 100 x 60 x 50 mm outer dimensions; declared wall thickness 2 mm; source scale 0.001 m/mm.
- Topology: zero boundary edges and zero non-manifold edges after repair.
- Gate: center `(0.050,0,0.025) m`; diameter 0.002 m; target area 3.1416 mm2.
- Mesh: `checkMesh` completes without fatal errors and inlet patch exists.
- Solver: run only after the mesh gate passes; no bbox proxy accepted as validation.

## Failure signatures

- Edge incidence `> 2`: touching/unmerged shells.
- Missing inlet patch or area near zero: gate selection/refinement failure.
- Inlet area far from 3.1416 mm2: mesh too coarse or incorrect face selection.
- `snappyHexMesh` region leakage: surface remains non-watertight or location-in-mesh is wrong.

## Recovery / rollback

- Delete only the newly named disposable case after resolving its exact path.
- Restore by retaining the original STL hash above and leaving the current LAVIE case untouched.

## Scope limits

- The local checks do not yet prove wall orientation, successful LAVIE meshing, material properties, or solver convergence.
- Signed STL volume is a topology indicator here, not a validated resin cavity volume.

## Web knowledge decision

- External web search is deferred because the installed OpenFOAM version's local command help and diagnostics are the authoritative next source; version-matched behavior must be established on Main LAVIE first.

## Next experiment

- On Main LAVIE, inspect the installed OpenFOAM surface utilities and run a read-only surface check on a disposable uploaded copy.

## Provenance

- Local binary STL inspection on 2026-07-19 JST.
- Related scripts: `scripts/cae_te_engine.py`, `scripts/k10_satellite_cae_dispatch.py`, `scripts/lavie_job_worker.py`.
