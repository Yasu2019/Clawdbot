
import sys
import os

# Add FreeCAD lib path
sys.path.append("/opt/freecad/usr/lib")
sys.path.append("/opt/freecad/usr/Mod")

import FreeCAD
import Part
import Mesh

STEP_PATH = "/home/node/clawd/inputs/ASSY_Guide.step"
OUTPUT_DIR = "/home/node/clawd/report_assets/3d_models"

if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

try:
    print(f"Loading STEP: {STEP_PATH}")
    shape = Part.read(STEP_PATH)
    solids = shape.Solids
    
    # Mapping based on previous analysis
    # Solid 2 (Index 1) = Punch
    # Solid 3 (Index 2) = Frame
    # Solid 4 (Index 3) = Strip (Reinforcement Plate) - wait, user said "Strip Product Pitch", maybe Solid 3 is Frame and Solid 4 is product?
    # User said: "4 products are assembled in the holes of 3 frame (scrap)."
    # So Solid 3 = Frame, Solid 4..17 = Products (Reinforcement Plates)
    
    parts_to_export = [
        {"name": "frame", "solid": solids[2], "color": (0.8, 0.8, 0.8)}, # Gray
        {"name": "punch", "solid": solids[1], "color": (0.3, 0.6, 1.0)}, # Blue
        {"name": "product_1", "solid": solids[3], "color": (1.0, 0.8, 0.0)} # Gold (First product)
    ]
    
    for p in parts_to_export:
        print(f"Exporting {p['name']}...")
        # Tessellate
        mesh = Mesh.Mesh()
        # deviation=0.01mm for good quality
        mesh.addFacets(p["solid"].tessellate(0.01))
        
        out_path = os.path.join(OUTPUT_DIR, f"{p['name']}.obj")
        mesh.write(out_path)
        print(f"Saved to {out_path}")

    print("Export complete.")

except Exception as e:
    print(f"Error: {e}")
