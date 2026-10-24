# OpenFOAM box round-hole case readiness

## Existing verified screening case

A prior OpenFOAM.com 2512 `interFoam -parallel` case exists for an open-top 100 × 60 × 50 mm box with a central 20 mm bottom opening. Its 67,165-cell mesh has a polymer-cavity volume of 4.1325418e-5 m³; the archived `checkMesh` log ends with `Mesh OK`. The archived run used four ranks and reached 5 s. This is historical VOF fill screening, not validation of the modified Foundation 3.0.0 solver or prediction accuracy against a measured part.

The existing input card is explicitly virtual screening data: density 800 kg/m³, kinematic viscosity 0.0712747534 m²/s (implied dynamic viscosity ≈57.02 Pa·s), gate speed 8 m/s and surface tension 0.04 N/m. It is not mapped to a named production PP grade or a machine recipe. The initial field set has `alpha.polymer`, `p_rgh` and `U`, with no temperature field.

## Isolated checkpoint smoke preparation

A separate case copy was prepared from the verified mesh and initial fields. It uses a first segment ending at 0.0001 s and writes every 0.00005 s with `purgeWrite 0`. A restart control uses `startFrom latestTime` and ends at 0.0002 s. Production screening control continues to 5 s with 0.05 s output intervals. The three control files are kept separate so the recovery path can be tested before a longer run.

A run is resumable only after the first segment produces nonempty `alpha.polymer`, `p_rgh` and `U` files at the recorded times and the second segment demonstrably advances from `latestTime` with the same solver binary. Retain the 0.0001 s checkpoint while testing newer output; record file sizes, timestamps, hashes, solver version and case provenance.

## Required for a physically grounded molding analysis

| Input | Present status | Needed for |
|---|---|---|
| Target geometry and mesh | Existing 100 × 60 × 50 mm screening case | Fill-flow smoke and geometry-specific screening |
| Named PP grade and measured Cross-WLF/shear-rate-temperature data | Missing; current card is virtual | Grade-specific filling and pressure loss |
| PVT versus temperature/pressure and density reference | Missing for this case | Packing, gate freeze, mass and shrinkage |
| Heat capacity, conductivity, latent heat/crystallization and mold/coolant boundary data | Missing | Thermal coupling and cooling |
| Machine injection velocity/pressure history, shot size, hold/pack schedule and gate-seal data | Missing | Process-matched filling/packing |
| Measured target part mass, fill-front, pressure/temperature trace or defect observation | Missing | Quantitative validation and tuning |
| Solver build identity and a verified restart trial | Must be refreshed before dispatch | Reproducible safe execution |

The public datasets already curated in the project can test narrow scalar outcomes when the material, geometry and setpoints match. They do not supply the missing target-specific boundary conditions or validate local temperature/pressure fields. Do not convert an unmatched dataset into universal PP coefficients.

## Dispatch gate

Before any run, refresh compute host identity, solver binary/version, old processes/tasks/queues, CPU interval, installed and available memory, disk space, and checkpoint compatibility. Preserve unrelated FEM jobs. Start with the serial checkpoint smoke; only continue the longer screening run after the native restart test passes. Any new material/thermal solver validation is a separate gate from this `interFoam` VOF case.