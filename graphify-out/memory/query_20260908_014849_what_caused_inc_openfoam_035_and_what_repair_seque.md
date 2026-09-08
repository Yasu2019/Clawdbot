---
type: "query"
date: "2026-09-08T01:48:49.572012+00:00"
question: "What caused INC-OPENFOAM-035 and what repair sequence was selected?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["polymerInterFoam", "p_rgh", "Cross-WLF", "Tait"]
---

# Q: What caused INC-OPENFOAM-035 and what repair sequence was selected?

## Answer

The primary trigger is impulsive flux-inconsistent startup: internal U=0 conflicts with an instantaneous 0.05 m/s gate in a high-density-ratio compressible cavity. The first temperature excursion at 1.200192e-7 s precedes Courant collapse; later air velocity reaches about 483.5 m/s and p_rgh about 272 kPa. The incomplete screening energy equation is a secondary amplifier, and Cross-WLF/Tait are not conservatively coupled. Use an isothermal ramped hydraulic gate, then a conservative enthalpy gate, then independently validate and couple rheology/EOS, require two clean repetitions, and start a new generation; never resume R1-R5.

## Outcome

- Signal: useful

## Source Nodes

- polymerInterFoam
- p_rgh
- Cross-WLF
- Tait