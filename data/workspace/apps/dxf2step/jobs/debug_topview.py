import Part, FreeCAD

# Reproduce top view edges from ProjItem001 (from test.dxf analysis)
# cx=148.5, cy=70
cx, cy = 148.5, 70.0

raw_lines = [
    ((128.5,60.0),(138.5,60.0)),
    ((138.5,60.0),(138.5,70.0)),
    ((138.5,70.0),(128.5,70.0)),
    ((128.5,70.0),(128.5,60.0)),
    ((138.5,60.0),(168.5,60.0)),
    ((168.5,60.0),(168.5,80.0)),
    ((168.5,80.0),(128.5,80.0)),
    ((128.5,80.0),(128.5,70.0)),
]

edges_3d = []
for (sx,sy),(ex,ey) in raw_lines:
    p1 = FreeCAD.Vector(sx-cx, sy-cy, 0)
    p2 = FreeCAD.Vector(ex-cx, ey-cy, 0)
    if (p2-p1).Length > 1e-6:
        edges_3d.append(Part.makeLine(p1, p2))

print('Edges:', len(edges_3d))
groups = Part.sortEdges(edges_3d)
print('sortEdges groups:', len(groups))

for i, g in enumerate(groups):
    first_v = g[0].Vertexes[0].Point
    last_v = g[-1].Vertexes[-1].Point
    closed = (first_v - last_v).Length < 1e-4
    print('Group %d: %d edges, closed=%s' % (i, len(g), closed))
    try:
        w = Part.Wire(g)
        print('  Wire isClosed:', w.isClosed())
        f = Part.Face(w)
        print('  Face area:', round(f.Area, 1))
    except Exception as ex:
        print('  FAILED:', ex)
