
import ezdxf
import sys
from ezdxf.math import BoundingBox2d

dxf_path = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\製品抜きガイド.dxf"

try:
    doc = ezdxf.readfile(dxf_path)
    print(f"DXF Version: {doc.dxfversion}")
    
    # Header Info
    if '$INSUNITS' in doc.header:
        print(f"Units: {doc.header['$INSUNITS']}")
    else:
        print("Units: Not defined")
        
    # Layers
    layers = [layer.dxf.name for layer in doc.layers]
    print(f"Layers ({len(layers)}): {', '.join(layers[:10])} ...")
    
    # Modelspace stats
    msp = doc.modelspace()
    print(f"Entities in Modelspace: {len(msp)}")
    
    entity_counts = {}
    points = []
    
    for e in msp:
        etype = e.dxftype()
        entity_counts[etype] = entity_counts.get(etype, 0) + 1
        
        try:
            if etype == 'LINE':
                points.append((e.dxf.start.x, e.dxf.start.y))
                points.append((e.dxf.end.x, e.dxf.end.y))
            elif etype == 'CIRCLE' or etype == 'ARC':
                points.append((e.dxf.center.x, e.dxf.center.y))
                # Add points on circumference roughly
                points.append((e.dxf.center.x + e.dxf.radius, e.dxf.center.y))
                points.append((e.dxf.center.x - e.dxf.radius, e.dxf.center.y))
                points.append((e.dxf.center.x, e.dxf.center.y + e.dxf.radius))
                points.append((e.dxf.center.x, e.dxf.center.y - e.dxf.radius))
            elif etype == 'LWPOLYLINE':
                # Simplified point extraction
                with e.points() as p:
                    for pt in p:
                        points.append((pt[0], pt[1]))
        except Exception:
            pass

    print(f"Entity Types: {entity_counts}")
    
    if points:
        bbox = BoundingBox2d(points)
        print(f"Bounding Box: Min({bbox.extmin.x:.2f}, {bbox.extmin.y:.2f}) - Max({bbox.extmax.x:.2f}, {bbox.extmax.y:.2f})")
        print(f"Center: ({bbox.center.x:.2f}, {bbox.center.y:.2f})")
        print(f"Size: ({bbox.size.x:.2f}, {bbox.size.y:.2f})")
    else:
        print("No geometry points found for bounding box.")

except Exception as e:
    print(f"ERROR reading DXF: {e}")
