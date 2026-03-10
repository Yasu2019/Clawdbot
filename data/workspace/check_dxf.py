"""More detailed DXF analysis - extract DIMENSION start/end points and compute distances"""
import math

lines = open(r"D:\Clawdbot_Docker_20260125\data\workspace\Punch_Header and Frame_Hole_20260215.dxf", "r").readlines()

print("=== DIMENSION entities (full detail) ===")
for i in range(len(lines)):
    if lines[i].strip() == "DIMENSION" and i > 0 and lines[i-1].strip() == "0":
        print(f"\n--- DIMENSION at line {i} ---")
        data = {}
        j = i
        while j < min(i+120, len(lines)):
            code = lines[j].strip()
            val = lines[j+1].strip() if j+1 < len(lines) else ""
            if code in ["10","20","30","11","21","31","13","23","33","14","24","34","42","1","2","70"]:
                data[code] = val
                print(f"  Code {code}: {val}")
            if j > i+5 and code == "0":
                break
            j += 1
        
        # Compute distance between definition points if available
        if "13" in data and "23" in data and "14" in data and "24" in data:
            x1, y1 = float(data["13"]), float(data["23"])
            x2, y2 = float(data["14"]), float(data["24"])
            dist = math.sqrt((x2-x1)**2 + (y2-y1)**2)
            dx = abs(x2 - x1)
            dy = abs(y2 - y1)
            print(f"  ** Distance: {dist:.4f} (dx={dx:.4f}, dy={dy:.4f})")

# Also scan for LINE entities near known punch/hole geometry - look at ENTITIES section
print("\n\n=== Searching for geometry near Punch/Hole area ===")
# Let's look at the layer info too
print("\n=== Layers in DXF ===")
for i in range(len(lines)):
    if lines[i].strip() == "LAYER" and i > 0 and lines[i-1].strip() == "0":
        # Get layer name
        for j in range(i, min(i+20, len(lines))):
            if lines[j].strip() == "2":
                print(f"  Layer: {lines[j+1].strip()}")
                break
