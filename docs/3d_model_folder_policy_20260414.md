# 3D Model Folder Policy

Date: 2026-04-14
Status: draft
Purpose: define a lightweight folder layout for future 3D model work on this mini PC

## Recommendation

Use Blender and the existing Portal / three.js / DXF-to-3D flow as the default path.
Keep Unreal as a future heavy tool, not part of the always-on core.

## Proposed Layout

```text
E:\Assets\3D\
  Incoming\
    Meshy\
    DXF\
    STEP\
    STL\
  Working\
    Blender\
    PortalPreview\
    DxfTo3D\
  ExportReady\
    HTML\
    GLB\
    GLTF\
    STL\
    STEP\
  Archive\
    OldVersions\
    Released\
  Cache\
    Blender\
    DDC\
    Temp\
E:\Unreal\
  Engine\
  Projects\
  Cache\
```

## Folder Roles

### `Incoming`

Drop only source assets here.
Do not edit files in place.

Examples:
- Meshy exports
- vendor STEP files
- incoming DXF drawings
- received STL/OBJ/GLB files

### `Working`

Use this for active editing and conversion work.
Keep temporary versions here until the model is ready.

### `ExportReady`

Store the finalized outputs that Portal, HTML viewers, or downstream users can consume.

Examples:
- lightweight HTML viewer outputs
- GLB/GLTF for web preview
- clean STL / STEP handoff files

### `Archive`

Store released or superseded versions here.
This keeps the active work area small and reduces confusion.

### `Cache`

Keep disposable caches out of the working folders.
This is the most important separation for a slow PC.

Examples:
- Blender cache
- DerivedDataCache-style temp data
- temporary conversion scratch files

## Operating Rules

1. Keep one canonical copy of each working model.
2. Do not mix source files and outputs in the same folder.
3. Put `PortalPreview` outputs in a separate folder so the web preview does not become the source of truth.
4. Keep Unreal out of the always-on path.
5. If a model is only being inspected, prefer `ExportReady\GLB` or `ExportReady\HTML` before opening anything heavy.
6. Delete or archive scratch files after each conversion cycle.

## Practical Workflow

```text
Incoming -> Working -> ExportReady -> Archive
```

Recommended day-to-day path:
- import source into `Incoming`
- edit in `Working\Blender`
- export preview into `ExportReady\HTML` or `ExportReady\GLB`
- archive the final version when done

## Why This Layout

This layout matches the current repo reality:
- `dxf2step` and `dxf3d_app` already support lightweight conversion
- Portal and `three.js` already cover quick review
- Unreal is a future add-on, not something to keep always running on a slow mini PC

## Avoid

- putting Unreal projects under the main AI repo root
- storing caches inside source folders
- mixing preview outputs with editable masters
- keeping multiple "latest" copies without clear naming

