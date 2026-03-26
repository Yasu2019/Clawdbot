#!/usr/bin/env python3
"""
model2pdf.py - Convert 3D Model (STEP/STL/OBJ) to Interactive 3D PDF

Converts a 3D model to an interactive PDF that can be viewed in Adobe Acrobat Reader.
Uses custom IDTF generator + IDTFConverter for U3D, then LaTeX media9 for PDF embedding.
"""
import argparse
import os
import subprocess
import tempfile
import sys
import shutil
import textwrap
from pathlib import Path
import numpy as np
import matplotlib

matplotlib.use("Agg")

def run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str, str]:
    """Run command synchronously and return (returncode, stdout, stderr)."""
    sys.stdout.flush()
    sys.stderr.flush()
    p = subprocess.run(
        cmd, 
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE, 
        stderr=subprocess.PIPE, 
        text=True,
        timeout=300  # 5 minute timeout for complex models
    )
    return p.returncode, p.stdout, p.stderr


def run_shell(command: str, cwd: Path | None = None) -> tuple[int, str, str]:
    """Run a shell command and return (returncode, stdout, stderr)."""
    sys.stdout.flush()
    sys.stderr.flush()
    p = subprocess.run(
        command,
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=600,
        shell=True,
    )
    return p.returncode, p.stdout, p.stderr

def ensure_stl(input_path: Path, workdir: Path) -> Path:
    """Convert STEP to STL using Gmsh if needed."""
    if input_path.suffix.lower() == ".stl":
        return input_path
    if input_path.suffix.lower() in [".step", ".stp"]:
        stl_path = workdir / (input_path.stem + ".stl")
        import gmsh
        gmsh.initialize()
        try:
            gmsh.open(str(input_path))
            gmsh.write(str(stl_path))
        finally:
            gmsh.finalize()
        return stl_path
    return input_path


def try_direct_step_pdf(input_path: Path, output_pdf: Path) -> bool:
    """Try an exact STEP->PDF route via an externally supplied converter command.

    Configure with MODEL2PDF_DIRECT_STEP_PDF_CMD, for example:
      some_tool --input "{input_step}" --output "{output_pdf}"

    The command is intended for future ODA / CAD Exchanger style exact B-rep
    conversion tools. If unset or if the command fails, the caller can fall
    back to the mesh-based route.
    """
    template = os.getenv("MODEL2PDF_DIRECT_STEP_PDF_CMD", "").strip()
    if not template or input_path.suffix.lower() not in {".step", ".stp"}:
        return False

    command = template.format(
        input_step=str(input_path),
        output_pdf=str(output_pdf),
        input_dir=str(input_path.parent),
        output_dir=str(output_pdf.parent),
        stem=input_path.stem,
    )
    rc, out, err = run_shell(command, cwd=output_pdf.parent)
    if rc != 0:
        raise RuntimeError(
            "Direct STEP->PDF converter failed. "
            f"Command: {command}\nSTDOUT:\n{out}\nSTDERR:\n{err}"
        )
    return output_pdf.exists()

def mesh_to_obj(mesh_path: Path, obj_path: Path) -> None:
    """Convert input mesh to a simple OBJ file for Asymptote PRC generation.

    The exported display mesh is recentered at the origin and scaled to a
    stable viewing size so models with large absolute CAD coordinates do not
    end up outside the initial 3D PDF camera frustum.
    """
    import trimesh
    mesh = trimesh.load(mesh_path, force='mesh', process=False)
    mesh = mesh.copy()

    center = mesh.bounding_box.centroid
    extents = mesh.bounding_box.extents
    max_extent = float(np.max(extents)) if len(extents) else 0.0

    mesh.apply_translation(-center)
    if max_extent > 0:
        mesh.apply_scale(200.0 / max_extent)

    mesh.export(obj_path, file_type="obj")


def obj_to_prc(obj_path: Path, prc_path: Path) -> None:
    """Generate a PRC file from OBJ using Asymptote."""
    asy_path = prc_path.with_suffix(".asy")
    asy_path.write_text(
        textwrap.dedent(
            f"""
            settings.outformat="prc";
            settings.prc=true;
            import obj;
            import three;
            size(10cm,0);
            currentprojection=orthographic(3,2,4);
            draw(obj("{obj_path.name}", rgb(0.80,0.80,0.82)));
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    rc, out, err = run(["asy", asy_path.name], cwd=asy_path.parent)
    generated_prc = asy_path.with_suffix(".prc")
    if rc != 0 or not generated_prc.exists():
        raise RuntimeError(f"Asymptote PRC generation failed: {err or out}")
    shutil.move(str(generated_prc), str(prc_path))

def obj_to_pdf(obj_path: Path, pdf_path: Path) -> None:
    """Generate a 3D PDF with embedded PRC directly via Asymptote."""
    asy_path = pdf_path.with_suffix(".asy")
    asy_path.write_text(
        textwrap.dedent(
            f"""
            settings.outformat="pdf";
            settings.prc=true;
            import obj;
            import three;
            size(12cm,0);
            currentprojection=orthographic(3,2,4);
            draw(obj("{obj_path.name}", rgb(0.80,0.80,0.82)));
            """
        ).strip()
        + "\n",
        encoding="utf-8",
    )

    rc, out, err = run(["asy", asy_path.name], cwd=asy_path.parent)
    generated_pdf = asy_path.with_suffix(".pdf")
    if rc != 0 or not generated_pdf.exists():
        raise RuntimeError(f"Asymptote PDF generation failed: {err or out}")
    shutil.move(str(generated_pdf), str(pdf_path))


def create_outline_preview_pdf(mesh_path: Path, preview_pdf: Path) -> None:
    """Create a separate static outline-friendly preview PDF.

    The preview intentionally draws only silhouette-like edges and sharp
    feature edges, not the full triangle mesh wireframe.
    """
    import trimesh
    import matplotlib.pyplot as plt
    from matplotlib.backends.backend_pdf import PdfPages
    from mpl_toolkits.mplot3d.art3d import Line3DCollection, Poly3DCollection

    mesh = trimesh.load(mesh_path, force="mesh", process=False).copy()
    mesh.merge_vertices()
    center = mesh.bounding_box.centroid
    extents = mesh.bounding_box.extents
    max_extent = float(np.max(extents)) if len(extents) else 0.0
    mesh.apply_translation(-center)
    if max_extent > 0:
        mesh.apply_scale(200.0 / max_extent)

    vertices = np.asarray(mesh.vertices, dtype=np.float64)
    faces = np.asarray(mesh.faces, dtype=np.int64)

    elev = 22.0
    azim = -58.0
    elev_r = np.deg2rad(elev)
    azim_r = np.deg2rad(azim)
    view_dir = np.array([
        np.cos(elev_r) * np.cos(azim_r),
        np.cos(elev_r) * np.sin(azim_r),
        np.sin(elev_r),
    ])
    view_dir = view_dir / np.linalg.norm(view_dir)

    face_normals = np.asarray(mesh.face_normals, dtype=np.float64)
    facing = face_normals @ view_dir

    unique_edges = np.asarray(mesh.edges_unique, dtype=np.int64)
    edge_use_count = np.bincount(mesh.edges_unique_inverse, minlength=len(unique_edges))
    boundary_mask = edge_use_count == 1

    adjacency_edges = np.asarray(mesh.face_adjacency_edges, dtype=np.int64)
    adjacency = np.asarray(mesh.face_adjacency, dtype=np.int64)
    adjacency_angles = np.asarray(mesh.face_adjacency_angles, dtype=np.float64)

    silhouette_edges = []
    sharp_edges = []

    for edge, pair, angle in zip(adjacency_edges, adjacency, adjacency_angles):
        f0, f1 = pair
        d0 = facing[f0]
        d1 = facing[f1]
        crosses_silhouette = (d0 >= 0 > d1) or (d1 >= 0 > d0)
        is_sharp = angle > np.deg2rad(18.0) and (d0 >= 0 or d1 >= 0)
        if crosses_silhouette:
            silhouette_edges.append(edge)
        elif is_sharp:
            sharp_edges.append(edge)

    boundary_edges = unique_edges[boundary_mask]

    def edge_segments(edges: np.ndarray) -> list[np.ndarray]:
        if len(edges) == 0:
            return []
        return [vertices[idx] for idx in edges]

    boundary_segments = edge_segments(boundary_edges)
    silhouette_segments = edge_segments(np.asarray(silhouette_edges, dtype=np.int64))
    sharp_segments = edge_segments(np.asarray(sharp_edges, dtype=np.int64))

    fig = plt.figure(figsize=(8.27, 11.69))
    ax = fig.add_subplot(111, projection="3d")
    poly = Poly3DCollection(
        vertices[faces],
        facecolor=(0.92, 0.93, 0.95, 0.92),
        edgecolor="none",
        linewidth=0.0,
        antialiased=False,
    )
    ax.add_collection3d(poly)
    if sharp_segments:
        ax.add_collection3d(
            Line3DCollection(
                sharp_segments,
                colors=[(0.25, 0.25, 0.28, 0.65)],
                linewidths=0.8,
            )
        )
    if boundary_segments:
        ax.add_collection3d(
            Line3DCollection(
                boundary_segments,
                colors=[(0.05, 0.05, 0.08, 0.95)],
                linewidths=1.3,
            )
        )
    if silhouette_segments:
        ax.add_collection3d(
            Line3DCollection(
                silhouette_segments,
                colors=[(0.05, 0.05, 0.08, 0.95)],
                linewidths=1.2,
            )
        )
    ax.view_init(elev=elev, azim=azim)
    ax.set_proj_type("ortho")
    span = np.ptp(vertices, axis=0)
    ax.set_box_aspect(span if np.all(span > 0) else (1, 1, 1))
    ax.set_axis_off()
    ax.set_title("Outline Preview", fontsize=18, pad=18)
    fig.text(
        0.5,
        0.06,
        "Static preview for edge readability. Interactive 3D remains in the separate 3D PDF file.",
        ha="center",
        va="center",
        fontsize=10,
        color="#444444",
    )
    fig.tight_layout(rect=(0.03, 0.08, 0.97, 0.96))

    with PdfPages(preview_pdf) as pdf:
        pdf.savefig(fig)
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser(description="Convert 3D model to interactive 3D PDF")
    ap.add_argument("input_model", type=Path, help="Input 3D model file (STEP/STL/OBJ/PLY)")
    ap.add_argument("output_pdf", type=Path, help="Output PDF file path")
    args = ap.parse_args()

    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # Step 0: Prefer an exact STEP->PDF route when an external converter is
        # configured. This is the path intended for future direct B-rep PRC/PDF
        # tools such as ODA/CAD Exchanger integrations.
        exact_pdf = td / "direct_step.pdf"
        if try_direct_step_pdf(args.input_model, exact_pdf):
            args.output_pdf.write_bytes(exact_pdf.read_bytes())
            print(
                f"PDF created via direct STEP route: {args.output_pdf} "
                f"({args.output_pdf.stat().st_size} bytes)"
            )
            return

        # Step 1: Ensure we have an STL
        stl_path = ensure_stl(args.input_model, td)

        # Step 2: Convert mesh to OBJ
        obj_path = td / (stl_path.stem + ".obj")
        mesh_to_obj(stl_path, obj_path)

        # Step 3: Let Asymptote generate a PDF with embedded PRC directly.
        built_pdf = td / "model.pdf"
        obj_to_pdf(obj_path, built_pdf)
        os.sync()
        if not built_pdf.exists():
            raise RuntimeError("Asymptote did not generate PDF")

        preview_pdf = args.output_pdf.with_name(args.output_pdf.stem + "_outline_preview.pdf")
        create_outline_preview_pdf(stl_path, preview_pdf)

        args.output_pdf.write_bytes(built_pdf.read_bytes())
        print(f"PDF created: {args.output_pdf} ({args.output_pdf.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
