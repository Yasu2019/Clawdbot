
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
    # Reliable headless loading
    shape = Part.Shape()
    shape.read(STEP_FILE)
    
    solids = shape.Solids
    print(f"Found {len(solids)} solids.")

    for i, solid in enumerate(solids):
        vol = solid.Volume
        
        # Name Heuristics (Updated)
        name = f"unknown_{i}"
        
        if vol > 8000:
            name = "Guide_Base"         # 10175
        elif 4000 < vol < 8000:
            name = "Frame"              # 5256
        elif 200 < vol < 300:
            name = "Strip"              # 219
        elif 50 < vol < 200:
            name = "Punch_or_Small"     # TBD
        elif vol < 50:
            name = f"Terminal_{i}"      # 12
        else:
            name = f"Solid_{i}_Vol_{int(vol)}"

        filename = os.path.join(OUTPUT_DIR, f"{name}.obj")
        
        # Avoid overwrite collision
        if os.path.exists(filename) and "Terminal" not in name:
             filename = os.path.join(OUTPUT_DIR, f"{name}_{i}.obj")

        print(f"Exporting {name} (Vol: {vol:.1f}) -> {os.path.basename(filename)}")
        
        # Mesh Conversion
        m = Mesh.Mesh()
        # High quality tessellation: 
        # Angular=0.05 rad (~3 deg), Linear=0.005mm
        raw = solid.tessellate(0.005) 
        # API: tessellate returns (Vertices, Indices)
        # Vertices is list of Vector
        # Indices is list of (i1, i2, i3) tuples
        
        # Manual reconstruction to be safe with all versions
        verts, faces = raw
        for f in faces:
            m.addFacet(verts[f[0]], verts[f[1]], verts[f[2]])
            
        m.write(filename)

    print("Export Complete.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
