
import sys
import os

# Add FreeCAD lib path
sys.path.append("/opt/freecad/usr/lib")
sys.path.append("/opt/freecad/usr/Mod")

import FreeCAD
import Part
import math

STEP_PATH = "/home/node/clawd/inputs/ASSY_Guide.step"

def get_bbox_dim(solid, axis_idx):
    bbox = solid.BoundBox
    if axis_idx == 0: return bbox.XLength
    if axis_idx == 1: return bbox.YLength
    if axis_idx == 2: return bbox.ZLength
    return 0

def analyze_solid(label, solid):
    print(f"\n--- Analyzing {label} ---")
    bbox = solid.BoundBox
    print(f"  BBox: {bbox.XLength:.3f} x {bbox.YLength:.3f} x {bbox.ZLength:.3f}")
    
    # Analyze Faces for parallel pairs (Thinking about Widths/Thicknesses)
    # Simple logic: Iterate faces, find pairs with opposing normals, check distance
    
    faces = solid.Faces
    print(f"  Face Count: {len(faces)}")
    
    # Heuristic: Find dimensions close to target values
    # Targets: Wc=1.635, T=1.000, P=0.495
    targets = [1.635, 1.000, 0.495, 0.200]
    tolerance = 0.05
    
    found_dims = []
    
    # internal loop for unique pairs
    for i in range(len(faces)):
        for j in range(i+1, len(faces)):
            f1 = faces[i]
            f2 = faces[j]
            
            # Check if planar
            if not (isinstance(f1.Surface, Part.Plane) and isinstance(f2.Surface, Part.Plane)):
                continue
                
            n1 = f1.normalAt(0,0)
            n2 = f2.normalAt(0,0)
            
            # Check parallel and opposite
            # dot product ~ -1
            if abs(n1.dot(n2) + 1.0) < 0.01:
                # Distance
                # Project center of f1 onto normal line?
                # Dist = abs( (c2 - c1) . n1 )
                c1 = f1.CenterOfMass
                c2 = f2.CenterOfMass
                dist = abs((c2 - c1).dot(n1))
                
                # Check if matches target
                found = False
                for t in targets:
                    if abs(dist - t) < tolerance:
                        found_dims.append((t, dist, i, j))
                        print(f"  [MATCH] Found dimension close to {t}: {dist:.4f} mm (Faces {i} & {j})")
                        found = True
                
                # Debug scanning for Housing
                if not found and dist < 5.0 and dist > 0.1:
                     print(f"  [SCAN] Found dimension: {dist:.4f} mm (Faces {i} & {j})")

    if not found_dims:
        print("  No target dimensions found in simple parallel scan.")

try:
    shape = Part.read(STEP_PATH)
    solids = shape.Solids
    
    # Solid 1 (Guide/Base?)
    if len(solids) > 0:
        analyze_solid("Solid 1 (Guide/Base Comparison)", solids[0])

    # Solid 2 (Housing?)
    if len(solids) > 1:
        analyze_solid("Solid 2 (Housing Comparison)", solids[1])
        
    # Solid 4 (Terminal?)
    if len(solids) > 3:
        analyze_solid("Solid 4 (Terminal Comparison)", solids[3])
        
except Exception as e:
    print(f"Error: {e}")
