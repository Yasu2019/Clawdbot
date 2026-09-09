# 4ベント修正版 full-fill QC

## 計算

- Case: `artifacts/box_roundhole_v5/open_top_shell_vent4_r15_case3`
- Mesh: corrected 0.001 SI scaling, 67,165 tetra cells
- Vent contract: 4 x φ3 mm at the opposite x face
- Solver: OpenFOAM interFoam, 4 MPI ranks, 0–5 s
- Status: `End`, no numerical divergence

## Fill verification

VTK cell field inspection at the final snapshot:

- Overall mean alpha.polymer: 1.0000
- x=80–100 mm mean alpha.polymer: 1.0000
- x=80–100 mm cells with alpha >= 0.5: 100%

The prior 2-vent case was 54.2% in the same opposite-face band; it is not used
as the corrected result.

## Visual QC and delivery

Initial, middle, and final frames were visually inspected. The corrected video
shows the front reaching and filling the opposite face. ASCII-only Telegram
caption was used; video delivery succeeded.

Video: `artifacts/box_roundhole_v5/box100x60x50_vent4_fullfill.mp4`

This remains a virtual-material screening result. Weld-line output is a
location proxy and does not claim weld strength or production validation.
