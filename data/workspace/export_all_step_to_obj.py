
import FreeCAD
import Part
import Mesh
import os

# Paths
WORKSPACE_DIR = "/home/node/clawd"
STEP_FILE = os.path.join(WORKSPACE_DIR, "ASSY_Guide.step")
OUTPUT_DIR = os.path.join(WORKSPACE_DIR, "report_assets", "3d_models")

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

print(f"Loading STEP file: {STEP_FILE}")

try:
    # Load STEP
    shape = Part.getShape(STEP_FILE)
    
    # Iterate through solids
    solids = shape.Solids
    print(f"Found {len(solids)} solids.")

    # Naming Map (Heuristic based on volume/position - simplified for now)
    # We will just export ALL solids as solid_0.obj, solid_1.obj, etc.
    # unless we can identify them.
    # From previous context (analyze_punch_frame_gap.py):
    # Punch: Volume ~200-400?
    # Frame/Guide: Largest volume?
    
    for i, solid in enumerate(solids):
        # Create Mesh from Shape
        # Angular deflection 0.1 radians (approx 6 degrees) -> Linear deflection small
        mesh = Mesh.Mesh()
        # raw_mesh = solid.tessellate(0.1) # Simple tessellation
        # mesh.addMesh(raw_mesh)
        
        # Better mesh generation using temporary document feature
        doc = FreeCAD.newDocument()
        obj = doc.addObject("Part::Feature", f"Solid_{i}")
        obj.Shape = solid
        
        # Mesh conversion
        mesh_obj = doc.addObject("Mesh::Feature", f"Mesh_{i}")
        mesh_obj.Mesh = Mesh.Mesh(solid) # Default tessellation
        
        # Decide Name
        vol = solid.Volume
        bbox = solid.BoundBox
        name = f"solid_{i}"
        
        # Heuristics from memory/previous turns
        if vol > 10000: name = f"Guide_Base_{i}"
        elif vol < 500: name = f"Punch_{i}"
        elif 500 <= vol < 2000: name = f"Strip_{i}"
        
        filename = os.path.join(OUTPUT_DIR, f"{name}.obj")
        print(f"Exporting {name} (Vol: {vol:.1f}) to {filename}")
        
        # Export
        Mesh.export([mesh_obj], filename)
        
        del mesh
        FreeCAD.closeDocument(doc.Name)

    print("Export Complete.")

except Exception as e:
    print(f"Error: {e}")
