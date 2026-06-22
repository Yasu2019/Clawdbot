# JPEG To 3D Mecha Rig System

This is the target system for robot JPEG/PNG -> part-level 3D candidate -> mechanical rig.

## Best Combination

Use generators only for candidate geometry:

- Primary candidate generator: PartPacker, because it is part-level by design.
- Fallback candidate generator: existing PartCrafter/Kaggle or any local GLB/FBX.
- Canonical rig contract: `projects/AtsugiMechaCity/mecha_rig_spec.py`.
- Rig application: `projects/AtsugiMechaCity/mecha_rig_builder.py`.
- Failure gates: `qc_joint_separation.py`, geometric QA in the builder, and human visual review.

Do not let PartPacker become a second canonical rig pipeline. It should only feed candidate inventory and mesh files into `clawstack.mecha_rig_spec.v1`.

## Safe First Run

No external download:

```powershell
python projects/AtsugiMechaCity/jpeg_to_mecha_rig_orchestrator.py
```

Convert an existing PartPacker-style `inventory.json` into a rig spec:

```powershell
python projects/AtsugiMechaCity/jpeg_to_mecha_rig_orchestrator.py `
  --inventory D:/path/to/inventory.json
```

Run local Blender build only after a candidate model and valid spec exist:

```powershell
python projects/AtsugiMechaCity/jpeg_to_mecha_rig_orchestrator.py `
  --execute `
  --inventory D:/path/to/inventory.json `
  --candidate D:/path/to/candidate.fbx
```

## Promotion Gate

The pipeline is not considered successful until:

- `mecha_rig_spec.v1` validates.
- Flagged segments are reviewed or locked.
- Blender build report says `ok=true`.
- Preview image passes visual review.
- Joint separation QC passes on the rigged blend.

Telegram or publishing is allowed only after these gates pass.
