"""
Generate all test DXF files programmatically with ezdxf.
All coordinates in mm, origin at (0,0).
"""
import math
import ezdxf
from pathlib import Path

OUT = Path(__file__).parent / "dxf_files"
OUT.mkdir(exist_ok=True)


def save(doc, name):
    doc.header['$INSUNITS'] = 4  # 4 = mm (prevents FreeCAD 1000x scale)
    path = OUT / f"{name}.dxf"
    doc.saveas(str(path))
    print(f"  Written: {path.name}")
    return path


# ── 1. Simple rectangle 100×60 ────────────────────────────────────────────────
def gen_rect_simple():
    doc = ezdxf.new()
    msp = doc.modelspace()
    pts = [(0,0),(100,0),(100,60),(0,60),(0,0)]
    for i in range(len(pts)-1):
        msp.add_line(pts[i], pts[i+1])
    return save(doc, "rect_simple")


# ── 2. L-shape: outer 80×80, cutout 40×40 from top-right corner ──────────────
def gen_l_shape():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # Outer outline (clockwise) as individual lines so T-junction code fires
    # Bottom: (0,0)→(80,0)
    # Right bottom: (80,0)→(80,40)    ← step at y=40
    # Inner right: (80,40)→(40,40)
    # Inner top: (40,40)→(40,80)
    # Top left: (40,80)→(0,80)
    # Left: (0,80)→(0,0)
    pts = [(0,0),(80,0),(80,40),(40,40),(40,80),(0,80),(0,0)]
    for i in range(len(pts)-1):
        msp.add_line(pts[i], pts[i+1])
    return save(doc, "l_shape")


# ── 3. T-shape: vertical bar 20×80 + horizontal bar 80×20 ────────────────────
def gen_t_shape():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # Draw as two overlapping rectangles (tests T-junction resolution)
    # Vertical: x 30..50, y 0..80
    v = [(30,0),(50,0),(50,80),(30,80),(30,0)]
    # Horizontal: x 0..80, y 30..50
    h = [(0,30),(80,30),(80,50),(0,50),(0,30)]
    for seg in [v, h]:
        for i in range(len(seg)-1):
            msp.add_line(seg[i], seg[i+1])
    return save(doc, "t_shape")


# ── 4. Circle r=30 ────────────────────────────────────────────────────────────
def gen_circle():
    doc = ezdxf.new()
    msp = doc.modelspace()
    msp.add_circle((0, 0), 30)
    return save(doc, "circle")


# ── 5. U-shape: outer 100×80, inner cutout 60×50 (open top) ──────────────────
def gen_u_shape():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # Outer rectangle
    outer = [(0,0),(100,0),(100,80),(0,80),(0,0)]
    for i in range(len(outer)-1):
        msp.add_line(outer[i], outer[i+1])
    # Inner cutout (separate closed loop, slightly inset from top)
    # Inner: x 20..80, y 30..80  (open at top by sharing y=80 edge)
    # Actually make it a closed rectangle inside
    inner = [(20,30),(80,30),(80,80),(20,80),(20,30)]
    for i in range(len(inner)-1):
        msp.add_line(inner[i], inner[i+1])
    return save(doc, "u_shape")


# ── 6. Rounded rectangle 100×60 with R10 corners ─────────────────────────────
def gen_arc_rect():
    doc = ezdxf.new()
    msp = doc.modelspace()
    r = 10
    W, H = 100, 60
    # Straight segments
    msp.add_line((r, 0),    (W-r, 0))      # bottom
    msp.add_line((W, r),    (W, H-r))      # right
    msp.add_line((W-r, H),  (r, H))        # top
    msp.add_line((0, H-r),  (0, r))        # left
    # Arcs at corners: start/end angles in degrees
    msp.add_arc((r,   r),   r, 180, 270)   # bottom-left
    msp.add_arc((W-r, r),   r, 270, 360)   # bottom-right
    msp.add_arc((W-r, H-r), r, 0,   90)    # top-right
    msp.add_arc((r,   H-r), r, 90,  180)   # top-left
    return save(doc, "arc_rect")


# ── 7. Multi-view cube: two layers (front=100×100, top=100×100) ───────────────
def gen_multiview_cube():
    doc = ezdxf.new()
    # Layer 0 "Front" placed at x=0..100, y=0..100
    # Layer 1 "Top" placed at x=0..100, y=110..210  (different Y band)
    for layer_name, y_offset in [("Front", 0), ("Top", 110)]:
        doc.layers.new(layer_name)
        msp = doc.modelspace()
        pts = [(0, y_offset),(100, y_offset),(100, y_offset+100),(0, y_offset+100),(0, y_offset)]
        for i in range(len(pts)-1):
            e = msp.add_line(pts[i], pts[i+1])
            e.dxf.layer = layer_name
    return save(doc, "multiview_cube")


# ── 8. Multi-view L-bracket: front=80×60 rect, top=80×60 rect ────────────────
def gen_multiview_lbracket():
    doc = ezdxf.new()
    for layer_name, y_offset in [("Front", 0), ("Top", 70)]:
        doc.layers.new(layer_name)
        msp = doc.modelspace()
        pts = [(0, y_offset),(80, y_offset),(80, y_offset+60),(0, y_offset+60),(0, y_offset)]
        for i in range(len(pts)-1):
            e = msp.add_line(pts[i], pts[i+1])
            e.dxf.layer = layer_name
    return save(doc, "multiview_lbracket")


# ── 9. Semicircle r=30 (arc + straight edge = 4 faces when extruded) ──────────
def gen_semicircle():
    doc = ezdxf.new()
    msp = doc.modelspace()
    r = 30
    msp.add_arc((0, 0), r, 0, 180)      # arc: (30,0) CCW to (-30,0)
    msp.add_line((-r, 0), (r, 0))       # closing flat base
    return save(doc, "semicircle")


# ── 10. Right triangle 60×40 (5 faces when extruded) ─────────────────────────
def gen_right_triangle():
    doc = ezdxf.new()
    msp = doc.modelspace()
    pts = [(0, 0), (60, 0), (0, 40), (0, 0)]
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return save(doc, "right_triangle")


# ── 11. Regular pentagon R=40 (7 faces when extruded) ────────────────────────
def gen_pentagon():
    doc = ezdxf.new()
    msp = doc.modelspace()
    R = 40
    n = 5
    pts = [(R * math.cos(2 * math.pi * i / n),
            R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return save(doc, "pentagon")


# ── 12. Regular hexagon R=40 (8 faces when extruded) ─────────────────────────
def gen_hexagon():
    doc = ezdxf.new()
    msp = doc.modelspace()
    R = 40
    n = 6
    pts = [(R * math.cos(2 * math.pi * i / n),
            R * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pts.append(pts[0])
    for i in range(len(pts) - 1):
        msp.add_line(pts[i], pts[i + 1])
    return save(doc, "hexagon")


# ── 13. Mold Plate with Hole ────────────────────────────────────────────────
def gen_mold_plate_hole():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # Outer (Layer: Plate)
    doc.layers.new("Plate")
    pts = [(0,0),(100,0),(100,100),(0,100),(0,0)]
    for i in range(len(pts)-1):
        e = msp.add_line(pts[i], pts[i+1])
        e.dxf.layer = "Plate"
    # Hole (Layer: Hole) - Worker should subtract this
    doc.layers.new("Hole")
    c = msp.add_circle((50, 50), 20)
    c.dxf.layer = "Hole"
    return save(doc, "mold_plate_hole")


# ── 14. Counterbore (layered pockets) ────────────────────────────────────────
def gen_counterbore_test():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # Main Plate (100x100), thickness defined in test case as 20
    doc.layers.new("Plate")
    pts = [(0,0),(100,0),(100,100),(0,100),(0,0)]
    for i in range(len(pts)-1):
        e = msp.add_line(pts[i], pts[i+1])
        e.dxf.layer = "Plate"
    
    # Large Cap (Φ40, Depth 10)
    doc.layers.new("Hole_Cap_T10")
    c1 = msp.add_circle((50, 50), 20)
    c1.dxf.layer = "Hole_Cap_T10"
    
    # Small Through Hole (Φ20, Depth 20)
    doc.layers.new("Hole_Through_T20")
    c2 = msp.add_circle((50, 50), 10)
    c2.dxf.layer = "Hole_Through_T20"
    
    return save(doc, "counterbore_test")


# ── 15. U-Bend Product (Extrusion profile) ───────────────────────────────────
def gen_u_bend_product():
    doc = ezdxf.new()
    msp = doc.modelspace()
    # U-shape profile: width 60, height 40, thickness 5
    # Outer: (0,40) -> (0,0) -> (60,0) -> (60,40)
    # Inner: (55,40) -> (55,5) -> (5,5) -> (5,40)
    pts = [(0,40),(0,0),(60,0),(60,40),(55,40),(55,5),(5,5),(5,40),(0,40)]
    for i in range(len(pts)-1):
        msp.add_line(pts[i], pts[i+1])
    return save(doc, "u_bend_product")


if __name__ == "__main__":
    print("Generating test DXF files...")
    gen_rect_simple()
    gen_l_shape()
    gen_t_shape()
    gen_circle()
    gen_u_shape()
    gen_arc_rect()
    gen_multiview_cube()
    gen_multiview_lbracket()
    gen_semicircle()
    gen_right_triangle()
    gen_pentagon()
    gen_hexagon()
    gen_mold_plate_hole()
    gen_counterbore_test()
    gen_u_bend_product()
    print("Done.")
