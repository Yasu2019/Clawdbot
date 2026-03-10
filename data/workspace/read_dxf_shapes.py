import ezdxf

doc = ezdxf.readfile(r"D:\Clawdbot_Docker_20260125\data\workspace\Punch_Header and Frame_Hole_20260215.dxf")
for layout_name in ["Model"] + [l.name for l in doc.layouts if l.name != "Model"]:
    layout = doc.layouts.get(layout_name)
    if layout is None: continue
    entities = list(layout)
    print(f"=== Layout: {layout_name} ({len(entities)} entities) ===")
    for e in entities[:100]:
        print(f"  {e.dxftype()} layer={e.dxf.layer}", end="")
        if e.dxftype() == "LINE":
            print(f" ({e.dxf.start.x:.4f},{e.dxf.start.y:.4f})-({e.dxf.end.x:.4f},{e.dxf.end.y:.4f})")
        elif e.dxftype() == "LWPOLYLINE":
            pts = list(e.get_points(format="xy"))
            print(f" pts={len(pts)} closed={e.closed}")
            for p in pts[:20]: print(f"    ({p[0]:.4f}, {p[1]:.4f})")
        elif e.dxftype() == "CIRCLE":
            print(f" c=({e.dxf.center.x:.4f},{e.dxf.center.y:.4f}) r={e.dxf.radius:.4f}")
        elif e.dxftype() == "ARC":
            print(f" c=({e.dxf.center.x:.4f},{e.dxf.center.y:.4f}) r={e.dxf.radius:.4f} a={e.dxf.start_angle:.1f}-{e.dxf.end_angle:.1f}")
        elif e.dxftype() in ("MTEXT", "TEXT"):
            txt = getattr(e.dxf, "text", getattr(e, "text", ""))
            print(f' "{txt}"')
        elif e.dxftype() == "INSERT":
            print(f" block={e.dxf.name} at ({e.dxf.insert.x:.4f},{e.dxf.insert.y:.4f})")
        else:
            print()
