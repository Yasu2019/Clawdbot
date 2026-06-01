"""ParaView batch: VOF alpha.polymer fill front -> PNG (headless)."""
from pathlib import Path

from paraview.simple import (
    ColorBy,
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
MIN_BYTES = 10000


def _pick_vtk_file():
    vtk_dir = Path(case_dir) / "VTK"
    if not vtk_dir.is_dir():
        return None
    candidates = sorted(vtk_dir.glob("**/*.vtk"), key=lambda p: p.stat().st_size)
    if not candidates:
        return None
    for path in reversed(candidates):
        if "internalmesh" in path.name.lower():
            return path
    return candidates[-1]


def _latest_time(reader):
    reader.UpdatePipeline()
    times = list(reader.TimestepValues) if reader.TimestepValues else [0.0]
    t_last = float(times[-1])
    reader.UpdatePipeline(time=t_last)
    view = GetRenderView()
    view.ViewTime = t_last
    return t_last


def _render_source(source, view):
    display = Show(source, view)
    display.SetRepresentationType("Surface")
    for spec in (
        ("CELLS", "alpha.polymer"),
        ("POINTS", "alpha.polymer"),
        ("CELLS", "p_rgh"),
        ("CELLS", "p"),
        ("CELLS", "U", "Magnitude"),
    ):
        try:
            ColorBy(display, spec)
            display.RescaleTransferFunctionToDataRange(True, False)
            break
        except Exception:
            continue
    display.SetScalarBarVisibility(view, True)
    ResetCamera(view)
    Render()
    SaveScreenshot(out_png, view, ImageResolution=[1280, 720])


def _render_openfoam():
    reader = OpenFOAMReader(FileName=foam_file)
    reader.MeshRegions = ["internalMesh"]
    reader.CellArrays = ["alpha.polymer", "U", "p_rgh"]
    _latest_time(reader)
    view = GetRenderView()
    view.ViewSize = [1280, 720]
    view.Background = [0.12, 0.14, 0.18]
    view.OrientationAxesVisibility = 0
    _render_source(reader, view)
    out = Path(out_png)
    return out.exists() and out.stat().st_size >= MIN_BYTES


def _render_vtk():
    vtk_path = _pick_vtk_file()
    if not vtk_path:
        return False
    view = GetRenderView()
    view.ViewSize = [1280, 720]
    view.Background = [0.12, 0.14, 0.18]
    reader = LegacyVTKReader(FileNames=[str(vtk_path)])
    reader.UpdatePipeline()
    _render_source(reader, view)
    out = Path(out_png)
    return out.exists() and out.stat().st_size >= MIN_BYTES


if not _render_openfoam():
    _render_vtk()
