# CAE fidelity mode ladder (extension, not replacement)

## Policy

- Existing `mesh_mode` / `physics_category` paths remain.
- `fidelity_mode` is an optional overlay for user-selectable speed vs fidelity.
- All modes stay `PROXY_GAP` until a commercial validation gate says otherwise.

## Modes

| id | Speed | Mesh / physics default | Moldflow analogy |
|---|---|---|---|
| `quick` | Fastest | `blockmesh_bbox` + isothermal VOF, coarse | Quick screen |
| `shell_proxy` | Fast | Thin-wall coarse 3D (not FEM shell) | Midplane-like exploration |
| `coarse_3d` | Medium | Coarser snappy + isothermal VOF | 3D fill shape check |
| `thermo_3d` | Slow | snappy + `resin_fill_cool` | Fill+Cool oriented |

Aliases: `fast`→`quick`, `shell`/`midplane`/`hele_shaw`→`shell_proxy`, `coarse`→`coarse_3d`, `thermo`→`thermo_3d`.

## How to select

```bash
# List / write catalog for UI
python scripts/cae_fidelity_mode.py --list --write-catalog

# Dispatch with mode (explicit params still win unless --force in apply API)
python scripts/k10_satellite_cae_dispatch.py --category resin_fill_cad --host lavie \
  --fidelity-mode shell_proxy --params-file path/to/base.json --timeout 3600
```

Or set `"fidelity_mode": "shell_proxy"` inside the params JSON. Catalog file:

`data/workspace/cae_fidelity_modes.json`

## UI note

Portal/dashboard can read the catalog JSON and present a dropdown. No existing mesh modes were removed.
