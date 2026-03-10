# BLENDER AUTONOMY PROTOCOL (BAP-2026)

> **Purpose:** Enable Clawdbot to autonomously create 3D assets and render visualizations using Blender.
> **Mechanism:** Python (`bpy`) Scripting -> Background Execution -> Image Verification.

## 1. Roles

- **Brain (Antigravity):** Writes Python Scripts (`build_scene.py`) using the `bpy` API.
- **Brawn (Clawdbot Host):** Executes Blender in Background Mode via CLI.
- **Feedback:** Stdout logs and Rendered Images (`.png`).

## 2. Environment (Verified)

- **Executable:** `C:\Program Files\Blender Foundation\Blender 5.0\blender.exe`
- **Work Dir:** `D:\Clawdbot_Docker_20260125\data\workspace\projects\blender_viz`

## 3. Operational Loop

1. **Generate:** Antigravity writes a Python script (e.g., `render_stress.py`) that imports `bpy`, sets up objects/materials, and triggers a render.
2. **Execute:** Clawdbot runs the script on Host.

    ```powershell
    & "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe" -b -P render_stress.py
    ```

    - `-b`: Background mode (No UI).
    - `-P`: Run Python script.

    > **⚠️ IMPORTANT:** This command MUST be executed on the **Windows Host (PowerShell)**.
    > The Docker Container **CANNOT** run this directly.
    > If you are the Docker Agent: Write the Python script, then **Request Execution** via `notify_user` or ask Antigravity.
3. **Verify:**
    - Check console output for Python errors.
    - Check output directory for expected image (e.g., `//render.png`).

## 4. Key Libraries

- **bpy:** Core Blender Python API.
- **mathutils:** Matrix/Vector math.
- **bmesh:** Advanced mesh manipulation.

## 5. Integration with OpenRadioss/Elmer

- Use `.vtk` or `.obj` import in the Python script to load simulation results before rendering.
