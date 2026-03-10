
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
    shape = Part.getShape(STEP_FILE)
    solids = shape.Solids
    print(f"Found {len(solids)} solids.")

    # Sort solids by volume to help identification
    # (Optional, but good for debugging)
    
    for i, solid in enumerate(solids):
        vol = solid.Volume
        
        # Determine Name
        name = f"unknown_{i}"
        
        # Heuristics based on step_solid_map.md
        if vol > 8000:
            name = "Guide_Base"
        elif 4000 < vol < 8000:
            name = "Frame"
        elif 100 < vol < 1000:
            # Could be Strip or Punch. 
            # Solid 3 is 219.69 (Strip)
            # Solid 2 was 10175 (Guide)
            # Solid 1 was 5256 (Frame)
            # Wait, verify Punch? 
            # If there is no other large block, maybe Punch is small?
            name = "Strip_or_Punch"
            # Let's just call it Strip for now if it matches 200 range
            if 200 < vol < 300:
                name = "Strip"
            else:
                name = "Punch"
        elif vol < 100:
            name = f"Terminal_{i}"
        
        # Unique filename
        filename = os.path.join(OUTPUT_DIR, f"{name}.obj")
        
        # If duplicate name, append index
        if os.path.exists(filename) and "Terminal" not in name:
            filename = os.path.join(OUTPUT_DIR, f"{name}_{i}.obj")

        print(f"Exporting Solid {i} (Vol: {vol:.1f}) -> {os.path.basename(filename)}")
        
        # Create Mesh directly
        # tesselate(tolerance) -> Returns (vertices, faces)
        # We need a Mesh object to write
        m = Mesh.Mesh()
        
        # Use Standard Tessellation
        # angular deflection in radians (0.1 ~= 6 degrees)
        # linear deflection in mm (0.01 mm)
        raw = solid.tessellate(0.01) 
        # API mismatch note: solid.tessellate returns (verts, faces)
        # m.addMesh needs a specific format or we can use the constructor?
        
        # Easiest way:
        # Mesh.Mesh(solid) constructor works in many execution contexts where Part is loaded
        try:
            m = Mesh.Mesh(solid)
        except:
            # Fallback
            facets = []
            vertices, faces = solid.tessellate(0.01)
            for f in faces:
                # f is tuple of indices
                m.addFacet(vertices[f[0]], vertices[f[1]], vertices[f[2]])
        
        m.write(filename)

    print("Export Complete.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
