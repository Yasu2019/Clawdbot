# HOST TOOLS MANUAL (Clawdbot Control Protocol)

> **Purpose:** This document defines the standard operating procedures (SOP) for Clawdbot to control engineering software installed on the Windows Host.
> **Protocol:** "Brain & Brawn" - Antigravity (Brain) writes the scripts/commands; Clawdbot (Brawn) executes them on the Host.

---

## 1. ElmerFEM (Solver)

- **Executable:** `C:\Program Files\Elmer 26.1-Release\bin\ElmerSolver.exe`
- **Grid Tool:** `C:\Program Files\Elmer 26.1-Release\bin\ElmerGrid.exe`
- **Env Setup:** `$env:Path += ";C:\Program Files\Elmer 26.1-Release\bin"`

### Standard Actions

**A. Convert Mesh (Gmsh -> Elmer)**

```powershell
ElmerGrid 14 2 [mesh_file].msh -autoclean
```

**B. Run Solver**

```powershell
ElmerSolver [case_file].sif
```

---

## 2. ParaView (Visualization)

- **Executable:** `C:\Program Files\ParaView 6.0.1\bin\pvpython.exe`
- **Usage:** Headless script execution for image generation.

### Standard Actions

**A. Run Visualization Script**

```powershell
& "C:\Program Files\ParaView 6.0.1\bin\pvpython.exe" [script].py
```

---

## 3. Blender (3D Modeling & Rendering)

- **Executable:** `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`
- **Usage:** High-quality rendering, 3D modification.

### Standard Actions

**A. Headless Render (Image)**

```powershell
& "..." -b [file].blend -o //render_output/frame_##### -F PNG -f 1
```

**B. Run Python Script (Modeling/Setup)**

```powershell
& "..." -b -P [script].py
```

*Note: Scripts can import `bpy` to manipulate scenes programmatically.*

---

## 4. Unity (Real-time Simulation)

- **Executable:** `C:\Program Files\Unity\Hub\Editor\6000.3.6f1\Editor\Unity.exe`
- **Project Path:** `D:\Clawdbot_Docker_20260125\data\workspace\projects\unity_viz` (Proposed)

### Standard Actions

**A. Run Headless Batch Mode (Execute Method)**

```powershell
& "..." -batchmode -nographics -projectPath "[Path]" -executeMethod [ClassName.MethodName] -quit -logFile "[Path]\unity.log"
```

*Use this to trigger C# scripts that load VTK/CSV data and take screenshots or run sims.*

---

## ⚠️ Safety Rules

1. **No Window Focus Stealing:** Always try to run with `-b` (Blender) or `-batchmode` (Unity) or `pvpython` (ParaView) to avoid popping up windows on the user's desktop.
2. **Resource Limits:** Check user activity before rendering. If user is "Active", limit thread count.
