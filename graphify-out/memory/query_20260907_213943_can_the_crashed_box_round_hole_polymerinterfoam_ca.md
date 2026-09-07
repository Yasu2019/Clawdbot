---
type: "query"
date: "2026-09-07T21:39:43.372220+00:00"
question: "Can the crashed box/round-hole polymerInterFoam case safely resume from latestTime?"
contributor: "graphify"
outcome: "useful"
source_nodes: ["polymerInterFoam", "p_rgh", "controlDict"]
---

# Q: Can the crashed box/round-hole polymerInterFoam case safely resume from latestTime?

## Answer

No. The mesh used millimetre magnitudes as metres and p_rgh used inconsistent atmospheric datums. All checkpoints were already nonphysical. SI-corrected recovery trials still violated temperature or timestep acceptance gates, so the full run remains HOLD after three attempts. Use the minimal SI conservation benchmark before any new full run.

## Outcome

- Signal: useful

## Source Nodes

- polymerInterFoam
- p_rgh
- controlDict