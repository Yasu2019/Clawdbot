# Try this sample first

## Fastest (workbench already installed)

1. Restart FreeCAD.
2. Workbench **Clawstack CETOL**.
3. Toolbar: **Load demo + analyze**.
4. Optional: select `Strip` in the tree, **Play sensitivity**.

You should see two plates, two holes, a pin, then the dock with Cpk / cross-table / coupling. Status stays **UNVALIDATED** vs commercial CETOL.

## Same demo as a macro

`Load_Clawstack_Demo.FCMacro` -- Macro -> Execute. Then Analyze document.

## Real STEP (C bracket)

`C_bracket.STEP` -- File -> Open. Then Analyze. This is the same bracket used in the web app.

## Browser (already on K10)

http://localhost:8088/apps/cetol6sigma/index.html?v=20260829j  
Pick `TOTEM_C_BRACKET_DEMO_10`.
