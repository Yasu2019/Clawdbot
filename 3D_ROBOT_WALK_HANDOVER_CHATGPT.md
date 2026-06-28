# Humanoid Robot Bipedal Walk Rigging & Animation Handover Report

This document summarizes the current status, detailed history, technical findings, and remaining bugs of the bipedal robot autorigging project, to be handed over to ChatGPT for further debugging and architecture refinement.

---

## 1. Project Overview & Environment

* **Target Model:** Humanoid Robot composed of 37 separate GLB mesh parts (`robot_0_part0.glb` to `robot_0_part36.glb`).
* **Environment:** 
  * OS: Windows 11
  * Blender Version: **Blender 5.1** (Stable, headless batch execution)
  * Script Cwd: `D:\AI\PartPacker`
  * Output directory: `D:\AI\PartPacker\output\flow_big_parts_strict_pvae_20260628_025827\`
* **Current Core Script:** [robot_parts_walk_preview.py](file:///C:/Users/yasu/.gemini/antigravity/brain/82bad97c-e9b8-4c76-ba48-d3981bae6771/scratch/robot_parts_walk_preview.py)
* **Goal:** Generate a realistic, seamless bipedal walk cycle animation (72 frames, 24 FPS) where the mecha meshes rotate cleanly without joints separating (dislocating) or remaining static.

---

## 2. Walkthrough of Version History (v1 - v14)

### Phase 1: Bounding Box Era (v1 - v10)
* **Approach:** Automatically computed joint pivots using the overall bounding boxes of classified meshes.
* **Failures:** 
  * **Joint Dislocation:** Wide accessory meshes (such as the shoulder shield `part3` and spiked shoulder pad `part2`) shifted the calculated bounding box center outward. This placed the rotation pivots (head of bones) far outside the actual joint geometry, causing the arms/legs to fly off (dislocate) during rotation.
  * **Visual Decoys:** In early versions, synthetic spheres (`JointCap`) were spawned to hide the gaps, causing visual clutter.
* **Outage Bug:** Keyframes were inserted via `keyframe_insert`, but in render outputs, the limbs remained completely vertical and static.

### Phase 2: Pivot Calibration & Render Loop Fix (v11 - v13)
* **Bypassing Blender 5.1 Slotted Action Bug:** 
  * **Discovery:** Blender 5.1's new animation system ("Slotted Actions") breaks legacy Python keyframe evaluation when actions are not bound to active slots.
  * **Fix:** Stopped using keyframes entirely. Implemented a **Direct Pose Evaluation Render Loop**:
    ```python
    for frame in range(FRAME_START, FRAME_END + 1):
        bpy.context.scene.frame_set(frame)
        # Calculate angles manually...
        # Set pose_bone.rotation_euler directly...
        bpy.context.view_layer.update()
        bpy.ops.render.render(write_still=True)
    ```
    This successfully forced the arms to swing in the rendered frames.
* **Physical Joint Center Calibration (v13):**
  * Identified the true joint centers of the GLB parts in Blender space:
    * **Left Hip Pivot (Hip Block `part32` center):** `(-0.2576, -0.1534, -0.1449)`
    * **Left Knee Pivot (Overlap zone):** `(-0.2576, -0.1534, -0.3615)`
    * **Left Shoulder Pivot (Shoulder Ball `part28` center):** `(-0.3184, 0.0509, 0.6014)`
  * Removed all synthetic `JointCap` decores. The joint gap dislocation was solved geometrically.

### Phase 3: Thigh Binding Fix & The Remaining Outage (v14)
* **The Thigh Binding Bug:**
  * **Discovery:** Thigh meshes (`part34.glb` and `part35.glb`) have a Z-coordinate center around `Z = -0.31`. In the automatic height classifier, this fell below the `35%` height threshold (`nz = 0.34`), causing the thigh meshes to be classified as **`LowerLeg`** (脛).
  * **Result:** The thigh meshes were bound via armature deform to the `LowerLeg_L/R` bones instead of `UpperLeg_L/R` bones, leaving the thighs static at the hip joint while the knees bent awkwardly.
* **v14 Fix:** Hardcoded overrides (`FINAL_OVERRIDES` and `PIVOT_OVERRIDES`) to map `part34.glb` and `part35.glb` directly to `UpperLeg_L` and `UpperLeg_R`.
* **Current Issue:** Even in `v14`, the thigh meshes at the hips are **still observed as not swinging forward/backward in the Telegram render outputs**.

---

## 3. Current Mesh-to-Bone Binding Implementation

The current script binds imported GLB parts to the generated armature using **Armature Modifiers + Vertex Groups (Skinning)**:

```python
for bone_name, objs in bone_parts_final_map.items():
    for obj in objs:
        # Save world matrix & bake transform to mesh vertices
        world_matrix = obj.matrix_world.copy()
        obj.parent = None
        obj.data.transform(world_matrix)
        obj.matrix_world = mathutils.Matrix.Identity(4)
        
        # Parent to Armature Object
        obj.parent = arm_obj
        obj.matrix_parent_inverse = arm_obj.matrix_world.inverted()
        
        # Create vertex group named after bone and assign weight 1.0
        obj.vertex_groups.clear()
        vg = obj.vertex_groups.new(name=bone_name)
        vertices_indices = [v.index for v in obj.data.vertices]
        if vertices_indices:
            vg.add(vertices_indices, 1.0, 'REPLACE')
            
        # Bind Armature Modifier
        mod = obj.modifiers.new(name="ArmatureDeform", type='ARMATURE')
        mod.object = arm_obj
        mod.use_vertex_groups = True
```

---

## 4. Technical Hypotheses for ChatGPT to Resolve

ChatGPT should investigate and resolve the following three hypotheses regarding why the thighs are still not rotating in the final render:

### Hypothesis A: Skinning (Armature Modifiers) vs. Rigid Bone Parenting
* **Problem:** Humanoid robots consist of rigid mechanical parts, not organic skin. Baking the world matrix into the mesh data (`obj.data.transform(world_matrix)`) and clearing the object transforms to identity might prevent the Armature Modifier from evaluating properly on these rigid objects, or cause scaling/rotation factors to nullify.
* **Proposed Solution:** Switch to **Direct Bone Parenting (Rigid Binding)** instead of Armature Modifiers.
  ```python
  # Set parent to Armature object and bind directly to the Bone string
  obj.parent = arm_obj
  obj.parent_type = 'BONE'
  obj.parent_bone = bone_name
  
  # Ensure the object local matrix aligns to the bone's rest position
  # to prevent offsets during rotation
  ```

### Hypothesis B: Bone Local Axis and Euler Rotation Conflicts
* **Problem:** The script calculates rotation values for world X-axis swing but applies it via Euler angles directly to the pose bones:
  ```python
  # In pose_at(frame):
  "UpperLeg_L": (upper_leg_L, 0.0, 0.0) # applying directly to Euler X
  
  # In render loop:
  pose_bone.rotation_mode = "XYZ"
  pose_bone.rotation_euler = tuple(math.radians(v) for v in degrees)
  ```
  If the edit bone's roll angle or rest matrix orientation is rotated (non-zero roll), applying rotation directly to local X-axis Euler will swing the leg sideways or cause rotations to cancel out (gimbal lock/constraint issues), resulting in zero visible forward swing.
* **Proposed Solution:** Ensure the edit bone roll is aligned, or convert the world-space rotation to the bone's local space matrix/quaternion properly:
  ```python
  # Use local matrix operations or quaternion rotation
  ```

### Hypothesis C: Parts Classification and Override Completeness
* **Problem:** Other mesh files representing pelvis/skirt details or thigh components might still be bound to the `Hips` or `Root` bone, covering the swinging thigh parts or blocking them from moving.
* **Current Part Map (Vertex Groups in v14):**
  * `geometry_0.026` / `0.027` (Z-center `-0.1449`): bound to `Hips` (pelvis blocks).
  * `geometry_0.028` / `0.029` (Z-center `-0.3136`, `part34`/`part35`): bound to `UpperLeg_L/R`.
  * `geometry_0.016` / `0.017` (Z-center `-0.5652`): bound to `LowerLeg_L/R`.
  Verify if any parts of the thigh are split across multiple meshes and still mapped to `Hips` or `LowerLeg`.

---

## 5. File References

* **Autorigging Script:** [robot_parts_walk_preview.py](file:///C:/Users/yasu/.gemini/antigravity/brain/82bad97c-e9b8-4c76-ba48-d3981bae6771/scratch/robot_parts_walk_preview.py)
* **Latest Walk Video:** [robot_walk.mp4](file:///C:/Users/yasu/.gemini/antigravity/brain/82bad97c-e9b8-4c76-ba48-d3981bae6771/robot_walk.mp4)
* **Latest Keyframe (Frame 10):** [robot_walk_0010.png](file:///C:/Users/yasu/.gemini/antigravity/brain/82bad97c-e9b8-4c76-ba48-d3981bae6771/robot_walk_0010.png)
