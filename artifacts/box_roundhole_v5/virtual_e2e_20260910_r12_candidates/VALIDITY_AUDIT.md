# Candidate display validity audit — 2026-09-10

## Verdict

**Display logic: PASS for virtual screening visualization.**

**Physical defect prediction: NOT VALIDATED.** The fields are proxies and do
not solve compressible cavity air, gas kinetics, or experimentally calibrated
PVT/packing transport.

## Checks performed

- Mesh alignment: quality/void field and OpenFOAM snapshots both contain
  67,165 cells; no broadcasting or remapping error.
- Fill consistency: mean alpha is 0.0 at 0 s, 0.99045 at 0.30 s, and 1.0 at
  5 s. The fill video has 101 frames and reaches the filled final state.
- Pressure consistency: final virtual pressure is 8.62–20.00 MPa; therefore
  the prior `pressure < 0.05 MPa` condition correctly produced no final
  pressure-driven air candidate.
- Air candidate: the new marker is transient-front weighted toward the far
  vent side and accumulated, so it remains visible after the front passes.
  This is a candidate-location visualization, not proof of trapped air.
- Void candidate: combined PVT-shrink/underpack/thick-section field range is
  0–0.2253 (mean 0.0639; 13,769 cells >= 0.1). The displayed gradient is
  therefore numerically consistent with the source fields, but its magnitude
  is not a measured void fraction.
- Visual QC: first/middle/final contact sheets show the far-side air band and
  lower/core void gradient persist without frame-order jumps.

## Required calibration before physical interpretation

Compressible air/vent boundary pressure, gas generation or TGA data, measured
PVT, packing-pressure history, cooling curve, and CT/sectioned-void data.
