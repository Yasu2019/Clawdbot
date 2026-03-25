#!/usr/bin/env python3
"""
model2pdf.py - Convert 3D Model (STEP/STL/OBJ) to Interactive 3D PDF

Converts a 3D model to an interactive PDF that can be viewed in Adobe Acrobat Reader.
Uses custom IDTF generator + IDTFConverter for U3D, then LaTeX media9 for PDF embedding.
"""
import argparse
import subprocess
import tempfile
import sys
import os
import shutil
from pathlib import Path
import numpy as np

# Path to the template file
TEMPLATE_PATH = Path(__file__).parent / "media9_template.tex"

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

def mesh_to_idtf(mesh_path: Path, idtf_path: Path) -> None:
    """Convert mesh to IDTF format using trimesh and custom IDTF generator."""
    import trimesh
    mesh = trimesh.load(mesh_path, force='mesh')
    vertices = mesh.vertices
    faces = mesh.faces
    
    if hasattr(mesh, 'vertex_normals'):
        normals = mesh.vertex_normals
    else:
        normals = np.zeros_like(vertices)
        normals[:, 2] = 1.0

    lines = [
        'FILE_FORMAT "IDTF"',
        'FORMAT_VERSION 100',
        '',
        'NODE "MODEL" {',
        '    NODE_NAME "Mesh"',
        '    PARENT_LIST {',
        '        PARENT_COUNT 1',
        '        PARENT 0 {',
        '            PARENT_NAME "<NULL>"',
        '            PARENT_TM {',
        '                1.0 0.0 0.0 0.0',
        '                0.0 1.0 0.0 0.0',
        '                0.0 0.0 1.0 0.0',
        '                0.0 0.0 0.0 1.0',
        '            }',
        '        }',
        '    }',
        '    RESOURCE_NAME "Mesh"',
        '}',
        '',
        'RESOURCE_LIST "MODEL" {',
        '    RESOURCE_COUNT 1',
        '    RESOURCE 0 {',
        '        RESOURCE_NAME "Mesh"',
        '        MODEL_TYPE "MESH"',
        '        MESH {',
        f'            FACE_COUNT {len(faces)}',
        f'            MODEL_POSITION_COUNT {len(vertices)}',
        f'            MODEL_NORMAL_COUNT {len(vertices)}',
        '            MODEL_DIFFUSE_COLOR_COUNT 0',
        '            MODEL_SPECULAR_COLOR_COUNT 0',
        '            MODEL_TEXTURE_COORD_COUNT 0',
        '            MODEL_BONE_COUNT 0',
        '            MODEL_SHADING_COUNT 1',
        '            MODEL_SHADING_DESCRIPTION_LIST {',
        '                SHADING_DESCRIPTION 0 {',
        '                    TEXTURE_LAYER_COUNT 0',
        '                    SHADER_ID 0',
        '                }',
        '            }',
        '            MESH_FACE_POSITION_LIST {',
    ]
    
    for face in faces:
        lines.append(f'                {face[0]} {face[1]} {face[2]}')
    lines.append('            }')
    lines.append('            MESH_FACE_NORMAL_LIST {')
    for face in faces:
        lines.append(f'                {face[0]} {face[1]} {face[2]}')
    lines.append('            }')
    lines.append('            MESH_FACE_SHADING_LIST {')
    for _ in faces:
        lines.append('                0')
    lines.append('            }')
    lines.append('            MODEL_POSITION_LIST {')
    for v in vertices:
        lines.append(f'                {v[0]:.6f} {v[1]:.6f} {v[2]:.6f}')
    lines.append('            }')
    lines.append('            MODEL_NORMAL_LIST {')
    for n in normals:
        lines.append(f'                {n[0]:.6f} {n[1]:.6f} {n[2]:.6f}')
    lines.extend([
        '            }',
        '        }',
        '    }',
        '}',
        '',
        'RESOURCE_LIST "SHADER" {',
        '    RESOURCE_COUNT 1',
        '    RESOURCE 0 {',
        '        RESOURCE_NAME "DefaultShader"',
        '        SHADER_MATERIAL_NAME "DefaultMaterial"',
        '        SHADER_ACTIVE_TEXTURE_COUNT 0',
        '    }',
        '}',
        '',
        'RESOURCE_LIST "MATERIAL" {',
        '    RESOURCE_COUNT 1',
        '    RESOURCE 0 {',
        '        RESOURCE_NAME "DefaultMaterial"',
        '        MATERIAL_AMBIENT 0.2 0.2 0.2',
        '        MATERIAL_DIFFUSE 0.8 0.8 0.8',
        '        MATERIAL_SPECULAR 0.0 0.0 0.0',
        '        MATERIAL_EMISSIVE 0.0 0.0 0.0',
        '        MATERIAL_REFLECTIVITY 0.1',
        '        MATERIAL_OPACITY 1.0',
        '    }',
        '}',
    ])
    
    content = '\n'.join(lines) + '\n'
    with open(idtf_path, 'wb') as f:
        f.write(content.encode('utf-8'))
        f.flush()
        os.fsync(f.fileno())

def compute_camera_params(stl_path: Path) -> tuple[float, float, float, float]:
    """Compute 3D camera parameters from mesh bounding box.
    Returns (coo_x, coo_y, coo_z, roo) where coo is the model center
    and roo is the camera distance that fits the model in the viewport.
    """
    import trimesh
    mesh = trimesh.load(str(stl_path), force='mesh')
    center = mesh.bounding_box.centroid
    diagonal = float(np.linalg.norm(mesh.bounding_box.extents))
    # roo = distance from camera to model center.
    # Using diagonal * 2.0 ensures the full model fits within ~28deg half-FOV.
    roo = max(diagonal * 2.0, 1.0)
    return float(center[0]), float(center[1]), float(center[2]), roo


def main():
    ap = argparse.ArgumentParser(description="Convert 3D model to interactive 3D PDF")
    ap.add_argument("input_model", type=Path, help="Input 3D model file (STEP/STL/OBJ/PLY)")
    ap.add_argument("output_pdf", type=Path, help="Output PDF file path")
    args = ap.parse_args()

    args.output_pdf.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as td:
        td = Path(td)

        # Step 1: Ensure we have an STL
        stl_path = ensure_stl(args.input_model, td)

        # Step 2: Compute camera parameters from mesh bounding box
        coo_x, coo_y, coo_z, roo = compute_camera_params(stl_path)
        print(f"Camera: coo=({coo_x:.3f}, {coo_y:.3f}, {coo_z:.3f}), roo={roo:.3f}")

        # Step 3: Convert mesh to IDTF
        idtf_path = td / (stl_path.stem + ".idtf")
        mesh_to_idtf(stl_path, idtf_path)

        # Step 4: Convert IDTF to U3D
        u3d_path = td / (stl_path.stem + ".u3d")
        rc, out, err = run(["IDTFConverter", "-input", str(idtf_path), "-output", str(u3d_path)])
        os.sync()

        if not u3d_path.exists():
            raise RuntimeError(f"IDTFConverter failed: {err}")

        # Step 5: Generate .tex from template with Python string substitution
        tex_content = TEMPLATE_PATH.read_text(encoding='utf-8')
        tex_content = tex_content.replace("__MODEL_U3D__", u3d_path.name)
        tex_content = tex_content.replace("__COO_X__", f"{coo_x:.4f}")
        tex_content = tex_content.replace("__COO_Y__", f"{coo_y:.4f}")
        tex_content = tex_content.replace("__COO_Z__", f"{coo_z:.4f}")
        tex_content = tex_content.replace("__ROO__", f"{roo:.4f}")
        tex_path = td / "model.tex"
        tex_path.write_text(tex_content, encoding='utf-8')

        # Step 6: Compile PDF with pdflatex (no -halt-on-error to allow PDF generation)
        run(["pdflatex", "-interaction=nonstopmode", tex_path.name], cwd=td)

        built_pdf = td / "model.pdf"
        if not built_pdf.exists():
            raise RuntimeError("pdflatex did not generate PDF")

        # Copy output
        args.output_pdf.write_bytes(built_pdf.read_bytes())
        print(f"PDF created: {args.output_pdf} ({args.output_pdf.stat().st_size} bytes)")

if __name__ == "__main__":
    main()
