# YouTube resin-fill animation QC

- Model: round-hole open box, 100 x 60 x 50 mm
- Solver data: corrected four-vent OpenFOAM screening case (`open_top_shell_vent4_r15_case3`)
- Scope: resin filling only (`alpha.polymer`); no warpage, sink, weld-strength, air-trap, or void claim
- Calibration: virtual screening before experimental material/process calibration

## Accepted outputs

1. `box100x60x50_youtube_top_oblique_fill_v4.mp4`
   - 1920 x 1080, 30 fps, 101 simulation snapshots
   - More diagonal elevated view than v2/v3
   - Bottom round hole is visible in first, middle, and final-frame visual checks
   - Opposite face remains visible and the fill reaches the final state

2. `box100x60x50_youtube_hole_flow_closeup_v2.mp4`
   - 1920 x 1080, 30 fps, 101 simulation snapshots
   - Zoomed view centered on the hole region
   - Early snapshots show the advancing alpha front wrapping around the hole; later snapshots show the left/right paths merged into the filled region

## Rejected intermediate

- v3 was rejected because the more aggressive camera angle hid the bottom hole.
