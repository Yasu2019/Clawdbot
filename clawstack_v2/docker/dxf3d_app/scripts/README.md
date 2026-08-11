# dxf3d_app helper scripts

These are the **canonical copies**. `app.py` invokes them from `/work/scripts/`,
which lives under `clawstack_v2/data/` and is **git-ignored** — that is why both
features silently broke once the deployed copies disappeared.

After changing anything here, redeploy:

```bash
cp clawstack_v2/docker/dxf3d_app/scripts/*.py clawstack_v2/data/work/scripts/
```

| script | runs in | interpreter | invoked by |
|---|---|---|---|
| `dxf23d.py` | `clawstack-unified-antigravity-1` | `/opt/freecad/AppRun freecadcmd` | `convert_fcstd_via_freecad()` |
| `rpcd_or_pdf_to_dxf.py` | `clawstack-unified-dxf3d_app-1` | system `python` | `convert_pdf_or_rpcd_to_dxf_via_gateway()` |

## Environment constraints discovered while wiring these up

- The FreeCAD console binary is **lowercase `freecadcmd`**; the `/usr/local/bin/FreeCADCmd`
  symlink has the wrong case and resolves to nothing, so `AppRun` silently falls
  back to the GUI build and aborts on OpenGL.
- FreeCAD's option parser only forwards script arguments after `--pass`, and
  rejects pass-through tokens starting with `-` — hence the `key=value` form.
- `freecadcmd` imports the script as a module named after the file, so
  `__name__` is never `"__main__"`; `dxf23d.py` therefore runs at import time.
- `dxf3d_app` runs as root while Antigravity runs as uid 1000. FreeCAD writes the
  `.fcstd` itself, so `convert_fcstd_via_freecad()` chmods the job dir to 0777.
- The `docker.io` Debian package does **not** ship the `docker` CLI; `docker-cli`
  is required for the `docker exec` bridge into Antigravity.
