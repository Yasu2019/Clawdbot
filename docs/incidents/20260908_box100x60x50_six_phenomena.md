# Six-phenomena screening result

The corrected 100×60×50 mm box was evaluated with the virtual PP card.

- Filling: partial OpenFOAM thermal run reached `0.0001 s`; phase-1 volume
  fraction `0.0003611` (not full fill).
- Warpage: not computed; requires cooling/shrinkage mapping to structural FEM.
- Sink: not computed; requires packing and local PVT/solidification history.
- Shrinkage: generalized theory screen `-0.5163%` linear strain; not calibrated.
- Air trap: topology screen only; two vent patches exist, but trapped-air
  pressure/temperature is not solved.
- Weld line: arrival-time candidate screen only; no strength prediction.

Temperature-bound events occurred on all 1000 short-run steps, so no listed
phenomenon is promoted as a production prediction. The machine-readable result
is `artifacts/box_roundhole_v5/box100x60x50_six_phenomena_screening.json`.
