
import sys
import os

# Add clawstack_v2 to path
sys.path.append(r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\work\freecad\tolerance_analysis")
sys.path.append(r"/home/node/clawd/clawstack_v2/data/work/freecad/tolerance_analysis") # For Docker

try:
    import FreeCAD
    import Part
    print("FreeCAD imported successfully.")
except ImportError:
    print("FreeCAD module not found. Ensure this runs in the FreeCAD environment.")
    sys.exit(1)

STEP_PATH = r"D:\Clawdbot_Docker_20260125\data\workspace\inputs\ASSY_Guide.step"

if not os.path.exists(STEP_PATH):
    # Try linux path if running in docker
    STEP_PATH = "/home/node/clawd/inputs/ASSY_Guide.step"

if not os.path.exists(STEP_PATH):
    print(f"File not found: {STEP_PATH}")
    sys.exit(1)

print(f"Loading STEP file: {STEP_PATH}")

try:
    shape = Part.read(STEP_PATH)
    print(f"Shape loaded. Type: {shape.ShapeType}")
    
    # Inspect Solids
    solids = shape.Solids
    print(f"Number of Solids: {len(solids)}")
    
    for i, solid in enumerate(solids):
        print(f"\n--- Solid {i+1} ---")
        print(f"  Volume: {solid.Volume:.2f}")
        print(f"  Center of Mass: {solid.CenterOfMass}")
        bbox = solid.BoundBox
        print(f"  Bounding Box: {bbox.XLength:.2f} x {bbox.YLength:.2f} x {bbox.ZLength:.2f}")
        
    # Inspect Compounds/Structure if possible
    # (STEP often imports as a Compound of Solids)
    
except Exception as e:
    print(f"Error reading STEP: {e}")
