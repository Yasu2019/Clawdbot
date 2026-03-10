
import sys
import os

# Add FreeCAD lib path
sys.path.append("/opt/freecad/usr/lib")
sys.path.append("/opt/freecad/usr/Mod")

import FreeCAD
import Part
import math

STEP_PATH = "/home/node/clawd/inputs/ASSY_Guide.step"

def calculate_gap(solid1, solid2):
    # Calculate minimum distance between two shapes
    dist_res = solid1.distToShape(solid2)
    min_dist = dist_res[0]
    
    print(f"Minimum 3D Distance (Euclidean): {min_dist:.4f} mm")
    
    # Analyze X/Y Gap specifically
    # Bounding Box comparison
    box1 = solid1.BoundBox
    box2 = solid2.BoundBox
    
    print("\n--- Bounding Box Analysis ---")
    print(f"Solid 1 (Punch) X: {box1.XMin:.3f} ~ {box1.XMax:.3f} | Y: {box1.YMin:.3f} ~ {box1.YMax:.3f}")
    print(f"Solid 2 (Frame) X: {box2.XMin:.3f} ~ {box2.XMax:.3f} | Y: {box2.YMin:.3f} ~ {box2.YMax:.3f}")
    
    # Calculate Gaps
    # X Gap: distance between X ranges
    x_gap = 0.0
    if box1.XMax < box2.XMin: x_gap = box2.XMin - box1.XMax
    elif box2.XMax < box1.XMin: x_gap = box1.XMin - box2.XMax
    else: x_gap = 0.0 # Overlap in X projection
    
    # Y Gap
    y_gap = 0.0
    if box1.YMax < box2.YMin: y_gap = box2.YMin - box1.YMax
    elif box2.YMax < box1.YMin: y_gap = box1.YMin - box2.YMax
    else: y_gap = 0.0 # Overlap in Y projection
    
    print(f"\nProjected X Gap: {x_gap:.4f} mm")
    print(f"Projected Y Gap: {y_gap:.4f} mm")
    
    # More detailed Face-to-Face analysis for "Side Gap"
    # Find faces of Solid 1 with normal close to X or Y
    # Find faces of Solid 2 with normal close to -X or -Y
    # Calculate distance between them
    
    print("\n--- Detailed Face Analysis for Side Gaps ---")
    
    def get_face_dist(s1, s2, direction_vec):
        min_face_dist = 999.0
        
        # Filter faces by normal
        faces1 = [f for f in s1.Faces if isinstance(f.Surface, Part.Plane) and abs(f.normalAt(0,0).dot(direction_vec) - 1.0) < 0.1]
        faces2 = [f for f in s2.Faces if isinstance(f.Surface, Part.Plane) and abs(f.normalAt(0,0).dot(direction_vec) + 1.0) < 0.1]
        
        # Check dist
        for f1 in faces1:
            for f2 in faces2:
                d = f1.distToShape(f2)[0]
                if d < min_face_dist:
                     min_face_dist = d
        return min_face_dist

    # X Gap (Normal X)
    x_gap_detailed = get_face_dist(solid1, solid2, FreeCAD.Vector(1,0,0))
    # Check opposite direction too
    x_gap_detailed_neg = get_face_dist(solid1, solid2, FreeCAD.Vector(-1,0,0))
    
    # Y Gap
    y_gap_detailed = get_face_dist(solid1, solid2, FreeCAD.Vector(0,1,0))
    y_gap_detailed_neg = get_face_dist(solid1, solid2, FreeCAD.Vector(0,-1,0))
    
    print(f"X Gap (Detailed): {min(x_gap_detailed, x_gap_detailed_neg):.4f} mm")
    print(f"Y Gap (Detailed): {min(y_gap_detailed, y_gap_detailed_neg):.4f} mm")


try:
    shape = Part.read(STEP_PATH)
    solids = shape.Solids
    
    # User confirmed: 
    # Solid 2 = Punch (Housing)
    # Solid 3 = Frame/Scrap (Thin Sheet)
    
    if len(solids) > 2:
        punch = solids[1] # Index 1 is Solid 2
        frame = solids[2] # Index 2 is Solid 3
        
        print("Analyzing Gap between PUNCH (Solid 2) and FRAME (Solid 3)...")
        calculate_gap(punch, frame)
    else:
        print("Error: STEP file does not contain enough solids.")

except Exception as e:
    print(f"Error: {e}")
