"""ParaView batch: OpenFOAM/VTK -> PNG (headless). Prefer foamToVTK output when present."""
from pathlib import Path

from paraview.simple import (
    ColorBy,
    GetColorTransferFunction,
    GetRenderView,
    LegacyVTKReader,
    OpenFOAMReader,
    Render,
    ResetCamera,
    SaveScreenshot,
    Show,
)

import sys

case_dir = sys.argv[1]
out_png = sys.argv[2]
foam_file = f"{case_dir}/case.foam"
MIN_BYTES = 10_000


def _pick_vtk_file():
    vtk_dir = Path(case_dir) / "VTK"
    if not vtk_dir.is_dir():
        return None
    candidates = sorted(vtk_dir.glob("**/*.vtk"), key=lambda p: p.stat().st_size)
    if not candidates:
        return None
    for path in reversed(candidates):
        name = path.name.lower()
        if "internalmesh" in name and "boundary" not in name:
            return path
    return candidates[-1]


def _color_surface(display, view) -> None:
    specs = (
        ("POINTS", "p"),
        ("CELLS", "p"),
        ("POINTS", "U", "Magnitude"),
        ("CELLS", "U", "Magnitude"),
    )
    for spec in specs:
        try:
            ColorBy(display, spec)
            field = spec[1]
            lut = GetColorTransferFunction(field)
            display.RescaleTransferFunctionToDataRange(True, False)
            lut.RescaleTransferFunctionToDataRange(True, False)
            return
        except Exception:
            continue
    display.AmbientColor = [0.2, 0.35, 0.55]
    display.DiffuseColor = [0.3, 0.55, 0.85]
    display.Specular = 0.2


def _render_source(source, view) -> None:
    display = Show(source, view)
    display.SetRepresentationType("Surface")
    display.SetScalarBarVisibility(view, True)
    _color_surface(display, view)
    ResetCamera(view)
    Render()
    SaveScreenshot(out_png, view, ImageResolution=[1280, 720])


def _render_vtk() -> bool:
    vtk_path = _pick_vtk_file()
    if not vtk_path:
        return False
    view = GetRenderView()
    view.ViewSize = [1280, 720]
    view.Background = [0.12, 0.14, 0.18]
    view.OrientationAxesVisibility = 0
    reader = LegacyVTKReader(FileNames=[str(vtk_path)])
    reader.UpdatePipeline()
    _render_source(reader, view)
    out = Path(out_png)
    return out.exists() and out.stat().st_size >= MIN_BYTES


def _render_openfoam() -> bool:
    reader = OpenFOAMReader(FileName=foam_file)
    reader.MeshRegions = ["internalMesh"]
    reader.CellArrays = ["U", "p"]
    reader.UpdatePipeline()
    times = list(reader.TimestepValues) if reader.TimestepValues else [0.0]
    t_last = float(times[-1])
    reader.UpdatePipeline(time=t_last)
    view = GetRenderView()
    view.ViewSize = [1280, 720]
    view.Background = [0.12, 0.14, 0.18]
    view.ViewTime = t_last
    view.OrientationAxesVisibility = 0
    _render_source(reader, view)
    out = Path(out_png)
    return out.exists() and out.stat().st_size >= MIN_BYTES


if not _render_vtk():
    _render_openfoam()
