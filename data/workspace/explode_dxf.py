
import ezdxf
import sys
from ezdxf.math import BoundingBox2d

dxf_path = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\製品抜きガイド.dxf"
output_path = dxf_path.replace(".dxf", "_exploded.dxf")

try:
    doc = ezdxf.readfile(dxf_path)
    print(f"DXF Version: {doc.dxfversion}")
    
    msp = doc.modelspace()
    print(f"Entities in Modelspace (Before): {len(msp)}")
    
    # Analyze INSERTs
    inserts = [e for e in msp if e.dxftype() == 'INSERT']
    print(f"Found {len(inserts)} INSERT entities.")
    for ins in inserts:
        print(f"  - Block Name: {ins.dxf.name}")

    # Explode
    print("Exploding INSERTs...")
    for ins in inserts:
        try:
            ins.explode()
        except Exception as ex:
            print(f"  Explode failed: {ex}")
            
    print(f"Entities in Modelspace (After): {len(msp)}")
    
    # Recalculate Bounding Box
    points = []
    for e in msp:
        etype = e.dxftype()
        try:
            if etype == 'LINE':
                points.append((e.dxf.start.x, e.dxf.start.y))
                points.append((e.dxf.end.x, e.dxf.end.y))
            elif etype == 'CIRCLE' or etype == 'ARC':
                points.append((e.dxf.center.x, e.dxf.center.y))
                points.append((e.dxf.center.x + e.dxf.radius, e.dxf.center.y))
        except:
            pass
            
    if points:
        bbox = BoundingBox2d(points)
        print(f"Bounding Box: Min({bbox.extmin.x:.2f}, {bbox.extmin.y:.2f}) - Max({bbox.extmax.x:.2f}, {bbox.extmax.y:.2f})")
    
    doc.saveas(output_path)
    print(f"Saved exploded DXF to: {output_path}")

except Exception as e:
    print(f"ERROR: {e}")
