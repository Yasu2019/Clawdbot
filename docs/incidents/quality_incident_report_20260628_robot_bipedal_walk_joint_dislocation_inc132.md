# Quality Incident Report -- Bipedal Robot Walk Joint Dislocation & Animation Outage (INC-132 / T043)

**Date:** 2026-06-28 JST  
**Reporter:** User mechanical review + agent re-audit  

---

## 1. Event summary

During the bipedal robot walk animation trials (`v11` / `v12`), two critical failures occurred:
1. **Joint Dislocation (脱臼):** The thighs separated from the pelvis block and the upper arms detached from the shoulder balls during rotation.
2. **Animation Outage:** The arms and thighs remained completely vertical and static in rendering, showing no forward/backward swing despite joint swing angles being keyframed.

**Root Causes:**
* **Pivot Misalignment:** Pivot calculations relied on mesh bounding boxes, which were warped by accessory armor parts (e.g. shoulder shields, side panel skirts). This shifted the rotation centers away from the actual physical joints (shoulder ball `part28` and hip block `part32`).
* **Blender 5.1 Slotted Actions:** Blender 5.1 introduced a new animation system ("Slotted Actions") that broke compatibility with legacy `keyframe_insert` calls. Keys were created but not evaluated during rendering, freezing the limbs in their default vertical rest pose.

---

## 2. QC process chart (PMP)

| Step | Control point | Standard | Risk if skipped |
|------|---------------|----------|-----------------|
| MECHA-QC01 | Joint Ball Pivot | Pivot must match physical joint ball center, not bounding box bounds | Joint dislocation / parts drift |
| MECHA-QC02 | Vertical Alignment | Upper/lower joints must be vertically aligned in X/Y plane | Diagonal/skewed limbs swing |
| MECHA-QC03 | Animation Evaluation | Direct pose evaluation loop per frame instead of keyframe playback | Blender 5.1 slotted action freeze |
| MECHA-QC04 | Original joint reveal | Eliminate synthetic visual `JointCap` spheres to expose mecha details | Visual clutter / hidden gaps |

---

## 3. FMEA

| Process | Failure mode | Effect | Cause | S | O | D | Countermeasure |
|---------|--------------|--------|-------|---|---|---|----------------|
| RIGGING-01 | Thigh/Shoulder drift | Joint dislocation | Bounding box warped by armor parts | 8 | 6 | 2 | Set pivots to exact physical joint center coordinates |
| RIGGING-02 | Skewed swing planes | Limbs swing diagonally | Offsets in joint X/Y coordinates | 7 | 5 | 3 | Force strict X/Y vertical alignment for limbs |
| RENDER-01 | Limbs static freeze | Direct pose ignored | Blender 5.1 Slotted Action incompatibilities | 9 | 4 | 2 | Implement direct frame-by-frame pose assignment loop |

---

## 4. FTA

**Top event:** Bipedal mecha walk animation fails to swing naturally / joints disjoint.
```
TOP: Mecha walk animation failure
 +- OR: Joint parts drift (thigh/shoulder dislocate)
 |   +- AND: Pivot calculated from box bounds instead of physical sphere center
 +- OR: Limbs remain static/vertical in render
     +- AND: Blender 5.1 Slotted Action ignores legacy keyframe evaluations
```

---

## 5. 5 Why

| Why | Answer |
|-----|--------|
| Why1 | The thighs and arms were not swinging and separated from pelvis/shoulder balls. |
| Why2 | The rotation pivots were offset (e.g. hip pivot was 20cm too high; shoulder was 10cm too low). |
| Why3 | The calculation used bounds of parts which included wide armor/shield extensions. |
| Why4 | Keyframes were recorded but Blender 5.1's new animation system failed to update poses in render. |
| Why5 | Rigging algorithm lacked strict physical joint center calibrations and direct pose evaluation loops. |

**Action:** Map pivots to exact physical joint centers (Hips Z=-0.1449, Shoulder Z=0.6014) and switch to direct pose-assignment rendering.

---

## 6. Fishbone

| Category | Factors |
|----------|---------|
| Man | Agent relied on automatic mesh bounding box calculations without checking physical joints |
| Machine | Blender 5.1 engine upgrade with breaking animation API change (Slotted Actions) |
| Method | Keyframe playback rendering vs direct frame pose assignment |
| Material | Mecha GLB files with distinct joint ball/block components (part16, part28, part32) |
| Environment | Fast Telegram loop review without full 72-frame trajectory check |

---

## 7. Countermeasures

1. **Calibrate pivots:** Hardcode pivots directly to mecha joint centers (Hips `Z = -0.1449` / Shoulder `Z = 0.6014`).
2. **Direct Render:** Direct pose-assignment loop in python bypassing Blender 5.1 slotted action issues.
3. **Clean Assets:** Remove synthetic joint cap spheres to reveal clean mecha components.
