# Clawstack CETOL-class -- FreeCAD workbench

Portable addon. **Not** Sigmetrix CETOL 6-sigma. **Not** K10/Docker-only.

FreeCAD owns assembly and joints. This workbench reads the active document (solids, cylindrical holes, Assembly `JointType` if present), runs the Clawstack Python stack (vector loop + MSM + TIM analog), shows a dock, and can oscillate a part `Placement` as a sensitivity preview.

## Install on any PC

1. Copy the folder `ClawstackCetol` (this directory) to the FreeCAD Mod path:

   - Windows: `%APPDATA%\FreeCAD\Mod\ClawstackCetol`
   - From this repo (K10): run `scripts/install_freecad_cetol_workbench.ps1`

2. Restart FreeCAD. Workbench list: **Clawstack CETOL**.

3. Fastest try: toolbar **Load demo + analyze**. Then optional **Play sensitivity** on `Strip`.

   Macro alternative: `samples/Load_Clawstack_Demo.FCMacro`. STEP: `samples/C_bracket.STEP`.

## vs commercial CETOL 6 Sigma

Yes -- still behind on embed (Creo/SW), full SOTA cross-partials, GLD tables, CAD TIM, ASME MMC, geometry sensitivity, and 3D golden. See `samples/GAPS_VS_CETOL.md`. 1D golden max_err=0.508% is **not** a CETOL 3D pass.

FreeCAD ships its own Python. Putting packages only in the system `pip` is not enough; this folder must live under FreeCAD `Mod`.

## Optional live engine (K10)

If `CLAWSTACK_CETOL_ROOT` points at the Clawstack repo, the workbench imports `data/workspace` instead of `vendor/`. Otherwise it uses the bundled `vendor/` copies.

## Truth Gate

Results are **UNVALIDATED** vs commercial CETOL. MMC/LMC apply only when that data exists on holes. Animation is a Placement wiggle, not commercial CAD shape perturbation.
