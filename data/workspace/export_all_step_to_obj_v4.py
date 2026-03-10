
import FreeCAD
import Part
import Mesh
import os

# Paths
WORKSPACE_DIR = "/home/node/clawd"
STEP_FILE = os.path.join(WORKSPACE_DIR, "inputs", "ASSY_Guide.step")
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

    # Sort by volume desc
    solids.sort(key=lambda s: s.Volume, reverse=True)

    for i, solid in enumerate(solids):
        vol = solid.Volume
        
        # Heuristics based on sorted volume
        # 1. Guide Base (Largest ~10k)
        # 2. Frame (Next ~5k)
        # 3. Strip (~200)
        # 4. Terminals (<50)
        
        name = f"unknown_{i}"
        
        if vol > 8000:
            name = "Guide_Base"         
        elif 4000 < vol < 8000:
            name = "Frame"              
        elif 100 < vol < 1000:
            # Check dimensions if needed, but volume is good enough
            name = "Strip"
        elif 50 < vol < 100:
             name = "Punch_Block"
        elif vol < 50:
            name = f"Terminal_{i}"  
        else:
            name = f"Solid_{int(vol)}"

        filename = os.path.join(OUTPUT_DIR, f"{name}.obj")
        
        # Avoid overwrite collision
        if os.path.exists(filename) and "Terminal" not in name:
             filename = os.path.join(OUTPUT_DIR, f"{name}_{i}.obj")

        print(f"Exporting {name} (Vol: {vol:.1f}) -> {os.path.basename(filename)}")
        
        # Mesh Conversion
        m = Mesh.Mesh()
        raw = solid.tessellate(0.01) # High quality
        verts, faces = raw
        for f in faces:
            m.addFacet(verts[f[0]], verts[f[1]], verts[f[2]])
            
        m.write(filename)

    print("Export Complete.")

except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
