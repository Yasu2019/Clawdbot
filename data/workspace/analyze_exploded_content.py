
import ezdxf
import sys

dxf_path = r"D:\Clawdbot_Docker_20260125\clawstack_v2\data\paperless\consume\Guide\製品抜きガイド_exploded.dxf"

try:
    doc = ezdxf.readfile(dxf_path)
    print(f"DXF Version: {doc.dxfversion}")
    
    msp = doc.modelspace()
    print(f"Entities in Modelspace: {len(msp)}")
    
    entity_counts = {}
    for e in msp:
        etype = e.dxftype()
        entity_counts[etype] = entity_counts.get(etype, 0) + 1
    
    print(f"Entity Types: {entity_counts}")
    
    # Check for Paper Space content
    print("\n--- Paper Space (Layouts) ---")
    for layout_name in doc.layout_names():
        if layout_name == 'Model': continue
        layout = doc.layout(layout_name)
        print(f"Layout '{layout_name}': {len(layout)} entities")
        l_counts = {}
        for e in layout:
            etype = e.dxftype()
            l_counts[etype] = l_counts.get(etype, 0) + 1
        print(f"  Types: {l_counts}")

except Exception as e:
    print(f"ERROR: {e}")
