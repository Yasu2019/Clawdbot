# -*- coding: utf-8 -*-
"""Headless VTK -> PNG / MP4 for Impact FEM (vtk + matplotlib, mesh connectivity preserved)."""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.collections import PolyCollection
from matplotlib import cm

VON_MISES_FIELDS = ["von_mises_stress_cell", "von_mises_stress"]
FIELD_SPECS = [
    (VON_MISES_FIELDS, "vonmises", "Von Mises"),
    (["displacement_magnitude", "Displacement"], "displacement", "Displacement"),
    (["PEEQ_cell", "PEEQ"], "peeq", "PEEQ"),
]
IMPACT_CAMERA_PRESETS = ("iso", "top", "side", "front")


def _ensure_xyz(pts: np.ndarray) -> np.ndarray:
    pts = np.asarray(pts, dtype=float)
    if pts.ndim != 2 or pts.shape[0] == 0:
        raise ValueError("empty point array")
    if pts.shape[1] >= 3:
        return pts[:, :3]
    if pts.shape[1] == 2:
        return np.column_stack([pts[:, 0], pts[:, 1], np.zeros(pts.shape[0])])
    raise ValueError(f"unsupported point shape: {pts.shape}")


def project_view(pts3: np.ndarray, preset: str) -> tuple[np.ndarray, tuple[str, str]]:
    """Orthographic projection for FEM Impact animation presets."""
    preset = str(preset or "top").strip().lower()
    x, y, z = pts3[:, 0], pts3[:, 1], pts3[:, 2]
    if preset == "top":
        return np.column_stack([x, y]), ("X", "Y")
    if preset == "side":
        return np.column_stack([x, z]), ("X", "Z")
    if preset == "front":
        return np.column_stack([y, z]), ("Y", "Z")
    if preset == "iso":
        # Rotate the XY footprint as well as exposing Z.  Mixing only X/Z
        # leaves a thin plate looking almost identical to the top view.
        u = (x - y) * 0.8660254037844386
        v = (x + y) * 0.5 - z
        return np.column_stack([u, v]), ("U", "V")
    return np.column_stack([x, y]), ("X", "Y")


def load_vtk(path: Path):
    import vtk
    from vtk.util.numpy_support import vtk_to_numpy

    reader = vtk.vtkDataSetReader()
    reader.SetFileName(str(path))
    reader.ReadAllScalarsOn()
    reader.ReadAllVectorsOn()
    reader.Update()
    ds = reader.GetOutput()
    if ds is None or ds.GetNumberOfPoints() == 0:
        raise RuntimeError("empty vtk dataset")
    return ds, vtk, vtk_to_numpy


def pick_scalar(ds, vtk_to_numpy, names: list[str]):
    cd = ds.GetCellData()
    pd = ds.GetPointData()
    for name in names:
        arr = cd.GetArray(name) if cd else None
        assoc = "cell"
        if arr is None and pd:
            arr = pd.GetArray(name)
            assoc = "point"
        if arr is not None:
            return name, vtk_to_numpy(arr), assoc
    return None, None, None


def _extract_triangle_polys(poly) -> np.ndarray:
    """Triangulate VTK surface cells (tri + quad) for matplotlib PolyCollection."""
    tris: list[list[int]] = []
    n_cells = poly.GetNumberOfCells()
    for i in range(n_cells):
        cell = poly.GetCell(i)
        ids = [cell.GetPointId(j) for j in range(cell.GetNumberOfPoints())]
        if len(ids) == 3:
            tris.append(ids)
        elif len(ids) == 4:
            tris.append([ids[0], ids[1], ids[2]])
            tris.append([ids[0], ids[2], ids[3]])
    if not tris:
        return np.zeros((0, 3), dtype=int)
    return np.asarray(tris, dtype=int)


def _surface_mesh(ds, vtk, vtk_to_numpy, field_names: list[str]) -> tuple[np.ndarray, np.ndarray, np.ndarray, str] | None:
    """Extract 2D surface triangles + per-face scalar (preserves Impact mesh topology)."""
    surf = vtk.vtkDataSetSurfaceFilter()
    surf.SetInputData(ds)
    surf.Update()
    poly = surf.GetOutput()

    name, values, assoc = pick_scalar(poly, vtk_to_numpy, field_names)
    if values is None:
        name, values, assoc = pick_scalar(ds, vtk_to_numpy, field_names)
    if values is None or name is None:
        return None

    pts = vtk_to_numpy(poly.GetPoints().GetData())
    pts = _ensure_xyz(pts)

    polys = _extract_triangle_polys(poly)
    if polys.size == 0:
        return None

    if assoc == "cell":
        cd = poly.GetCellData().GetArray(name)
        cell_vals = vtk_to_numpy(cd) if cd is not None else np.asarray(values, dtype=float)
        face_vals_list: list[float] = []
        n_cells = poly.GetNumberOfCells()
        for ci in range(n_cells):
            cell = poly.GetCell(ci)
            npts = cell.GetNumberOfPoints()
            val = float(cell_vals[ci]) if ci < cell_vals.size else float("nan")
            if npts == 3:
                face_vals_list.append(val)
            elif npts == 4:
                face_vals_list.extend([val, val])
        face_vals = np.asarray(face_vals_list, dtype=float)
        if face_vals.size != polys.shape[0]:
            return None
    else:
        pt_vals = np.asarray(values, dtype=float)
        face_vals = np.mean(pt_vals[polys], axis=1)

    return pts, polys, face_vals, name


def _vtk_time_key(path: Path) -> float:
    m = re.search(r"_surface_([0-9.]+)\.vtk$", path.name, re.I)
    if m:
        return float(m.group(1))
    m = re.search(r"_([0-9.]+)\.vtk$", path.name)
    return float(m.group(1)) if m else 0.0


def list_impact_surface_vtks(run_dir: Path, *, max_frames: int = 24) -> list[Path]:
    """Surface VTK time series only (same naming as ThinkPad impact PNG script)."""
    run_dir = run_dir.resolve()
    vtks = sorted(run_dir.glob("*_surface_*.vtk"), key=_vtk_time_key)
    if len(vtks) < 2:
        vtks = sorted(run_dir.glob("**/*_surface_*.vtk"), key=_vtk_time_key)
    if len(vtks) > max_frames:
        step = max(1, len(vtks) // max_frames)
        vtks = vtks[::step][:max_frames]
    return vtks


def render_mesh_frame(
    pts: np.ndarray,
    polys: np.ndarray,
    face_vals: np.ndarray,
    out_png: Path,
    *,
    title: str,
    field_name: str,
    vtk_name: str,
    vmin: float | None = None,
    vmax: float | None = None,
    xlim: tuple[float, float] | None = None,
    ylim: tuple[float, float] | None = None,
    camera_preset: str = "top",
    axis_labels: tuple[str, str] | None = None,
) -> bool:
    """Draw Impact surface using VTK triangle connectivity (no Delaunay retriangulation)."""
    pts2 = project_view(_ensure_xyz(pts), camera_preset)[0]
    verts = pts2[polys]
    xlab, ylab = axis_labels or project_view(_ensure_xyz(pts), camera_preset)[1]
    fig, ax = plt.subplots(figsize=(12, 9), dpi=100)
    norm = plt.Normalize(vmin=vmin, vmax=vmax)
    coll = PolyCollection(
        verts,
        array=face_vals,
        cmap="viridis",
        norm=norm,
        edgecolors="none",
        antialiased=True,
    )
    ax.add_collection(coll)
    ax.set_aspect("equal")
    if xlim:
        ax.set_xlim(xlim)
    if ylim:
        ax.set_ylim(ylim)
    else:
        ax.autoscale()
    fig.colorbar(cm.ScalarMappable(norm=norm, cmap="viridis"), ax=ax, label=title)
    ax.set_title(f"{vtk_name} / {field_name} [{camera_preset}]")
    ax.set_xlabel(xlab)
    ax.set_ylabel(ylab)
    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_png, bbox_inches="tight")
    plt.close(fig)
    return True


def render_png(
    vtk_path: Path,
    out_png: Path,
    field_names: list[str],
    title: str,
    *,
    camera_preset: str = "top",
) -> bool:
    ds, vtk, vtk_to_numpy = load_vtk(vtk_path)
    mesh = _surface_mesh(ds, vtk, vtk_to_numpy, field_names)
    if mesh is None:
        print(f"[warn] no field in {vtk_path.name} for {field_names}")
        return False
    pts, polys, face_vals, name = mesh
    ok = render_mesh_frame(
        pts,
        polys,
        face_vals,
        out_png,
        title=title,
        field_name=name,
        vtk_name=vtk_path.name,
        vmin=float(np.nanmin(face_vals)),
        vmax=float(np.nanmax(face_vals)),
        camera_preset=camera_preset,
    )
    if ok:
        print(f"[impact-vtk-png] {out_png}", flush=True)
    return ok


def build_impact_mp4(
    run_dir: Path,
    mp4_path: Path,
    frame_dir: Path,
    *,
    field_names: list[str] | None = None,
    fps: int = 4,
    max_frames: int = 24,
    camera_preset: str = "top",
) -> tuple[Path | None, Path | None, dict[str, Any]]:
    """Build FEM Impact MP4 with fixed axes + global color scale (prevents model collapse in video)."""
    import shutil
    import subprocess

    field_names = field_names or VON_MISES_FIELDS
    vtks = list_impact_surface_vtks(run_dir, max_frames=max_frames)
    meta: dict[str, Any] = {
        "vtk_count": len(vtks),
        "frames_ok": 0,
        "frames_failed": 0,
        "camera_preset": camera_preset,
    }
    if len(vtks) < 2:
        meta["error"] = "need_at_least_2_surface_vtks"
        return None, None, meta

    meshes: list[tuple[Path, np.ndarray, np.ndarray, np.ndarray, str]] = []
    all_vals: list[float] = []
    xmins: list[float] = []
    xmaxs: list[float] = []
    ymins: list[float] = []
    ymaxs: list[float] = []

    for vtk_path in vtks:
        try:
            ds, vtk, vtk_to_numpy = load_vtk(vtk_path)
            mesh = _surface_mesh(ds, vtk, vtk_to_numpy, field_names)
            if mesh is None:
                meta["frames_failed"] += 1
                continue
            pts, polys, face_vals, name = mesh
            meshes.append((vtk_path, pts, polys, face_vals, name))
            all_vals.extend(face_vals.tolist())
            pts2 = project_view(_ensure_xyz(pts), camera_preset)[0]
            xmins.append(float(np.min(pts2[:, 0])))
            xmaxs.append(float(np.max(pts2[:, 0])))
            ymins.append(float(np.min(pts2[:, 1])))
            ymaxs.append(float(np.max(pts2[:, 1])))
        except Exception as exc:
            meta["frames_failed"] += 1
            print(f"[impact-vtk-mp4] skip {vtk_path.name}: {exc}", flush=True)

    if len(meshes) < 2:
        meta["error"] = "mesh_extract_failed"
        return None, None, meta

    vmin = float(np.nanmin(all_vals))
    vmax = float(np.nanmax(all_vals))
    if vmax <= vmin:
        vmax = vmin + 1.0
    pad_x = max(1e-6, (max(xmaxs) - min(xmins)) * 0.02)
    pad_y = max(1e-6, (max(ymaxs) - min(ymins)) * 0.02)
    xlim = (min(xmins) - pad_x, max(xmaxs) + pad_x)
    ylim = (min(ymins) - pad_y, max(ymaxs) + pad_y)

    if frame_dir.exists():
        shutil.rmtree(frame_dir, ignore_errors=True)
    frame_dir.mkdir(parents=True, exist_ok=True)

    axis_labels = project_view(_ensure_xyz(meshes[0][1]), camera_preset)[1]
    frames: list[Path] = []
    for i, (vtk_path, pts, polys, face_vals, name) in enumerate(meshes):
        fp = frame_dir / f"frame_{i:04d}.png"
        ok = render_mesh_frame(
            pts,
            polys,
            face_vals,
            fp,
            title="Von Mises",
            field_name=name,
            vtk_name=vtk_path.name,
            vmin=vmin,
            vmax=vmax,
            xlim=xlim,
            ylim=ylim,
            camera_preset=camera_preset,
            axis_labels=axis_labels,
        )
        if ok:
            frames.append(fp)
            meta["frames_ok"] += 1
            print(f"  fem frame {i + 1}/{len(meshes)} {vtk_path.name}", flush=True)
        else:
            meta["frames_failed"] += 1

    min_ok = max(2, int(len(vtks) * 0.9))
    if len(frames) < min_ok:
        meta["error"] = f"insufficient_frames {len(frames)}/{len(vtks)}"
        return None, None, meta

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        meta["error"] = "ffmpeg_missing"
        return None, None, meta

    mp4_path.parent.mkdir(parents=True, exist_ok=True)
    list_file = frame_dir / "frames.txt"
    with list_file.open("w", encoding="utf-8") as f:
        for fr in frames:
            f.write(f"file '{fr.as_posix()}'\n")
            f.write(f"duration {1.0 / fps:.4f}\n")
        f.write(f"file '{frames[-1].as_posix()}'\n")
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_file),
            "-vf",
            "scale=trunc(iw/2)*2:trunc(ih/2)*2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(mp4_path),
        ],
        capture_output=True,
        text=True,
        timeout=180,
        encoding="utf-8",
        errors="replace",
    )
    list_file.unlink(missing_ok=True)
    if proc.returncode != 0 or not mp4_path.exists() or mp4_path.stat().st_size < 5000:
        meta["error"] = "ffmpeg_failed"
        return None, None, meta

    meta["vmin"] = vmin
    meta["vmax"] = vmax
    meta["size_mb"] = round(mp4_path.stat().st_size / (1024 * 1024), 3)
    return mp4_path, frame_dir, meta


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("vtk_path", type=Path)
    parser.add_argument("out_dir", nargs="?", type=Path)
    parser.add_argument("--camera", choices=IMPACT_CAMERA_PRESETS, default="top")
    args = parser.parse_args()
    vtk_path = args.vtk_path.resolve()
    out_dir = args.out_dir.resolve() if args.out_dir else vtk_path.parent
    specs = FIELD_SPECS
    made = 0
    for fields, suffix, label in specs:
        out = out_dir / f"{vtk_path.stem}_{suffix}.png"
        try:
            if render_png(vtk_path, out, fields, label, camera_preset=args.camera):
                made += 1
        except Exception as exc:
            print(f"[warn] {suffix}: {exc}", flush=True)
    print(f"[impact-vtk-png] png_count={made}", flush=True)
    return 0 if made else 1


if __name__ == "__main__":
    raise SystemExit(main())
