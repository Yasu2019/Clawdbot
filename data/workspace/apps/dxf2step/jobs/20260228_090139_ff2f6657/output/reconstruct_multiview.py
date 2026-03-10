import FreeCAD as App
import Part

def build_slab(dxf_path, view_type, doc_name):
    """Load a cleaned DXF, map edges to 3D view plane, extrude to slab."""
    import importDXF
    doc = App.newDocument(doc_name)
    importDXF.insert(dxf_path, doc_name)
    edges = []
    for obj in doc.Objects:
        if hasattr(obj, 'Shape'):
            edges.extend(obj.Shape.Edges)
    if not edges:
        print('No edges in', dxf_path)
        return None
    # Compute bounding box to find view centre
    xs, ys = [], []
    for edge in edges:
        try:
            for p in edge.discretize(10):
                xs.append(p.x)
                ys.append(p.y)
        except Exception:
            pass
    if not xs:
        return None
    cx = (min(xs) + max(xs)) / 2
    cy = (min(ys) + max(ys)) / 2
    max_dim = max(max(xs) - min(xs), max(ys) - min(ys), 1.0)
    ext_len = max_dim * 3
    if view_type == 'front':
        ev_pos = App.Vector(0, ext_len, 0)
        ev_neg = App.Vector(0, -ext_len, 0)
    elif view_type == 'top':
        ev_pos = App.Vector(0, 0, ext_len)
        ev_neg = App.Vector(0, 0, -ext_len)
    elif view_type == 'right':
        ev_pos = App.Vector(ext_len, 0, 0)
        ev_neg = App.Vector(-ext_len, 0, 0)
    else:
        return None
    try:
        sorted_groups = Part.sortEdges(edges)
    except Exception as e:
        print('sortEdges failed:', e)
        return None
    solids = []
    for group in sorted_groups:
        try:
            pts_list = []
            for edge in group:
                try:
                    pts = edge.discretize(50)
                    for p in pts:
                        x, y = p.x - cx, p.y - cy
                        if view_type == 'front':
                            # DXF(x,y) -> 3D(x, 0, y)  extrude +/-Y
                            pts_list.append(App.Vector(x, 0, y))
                        elif view_type == 'top':
                            # DXF(x,y) -> 3D(x, y, 0)  extrude +/-Z
                            pts_list.append(App.Vector(x, y, 0))
                        elif view_type == 'right':
                            # DXF(x,y) -> 3D(0, -x, y)  extrude +/-X
                            pts_list.append(App.Vector(0, -x, y))
                except Exception:
                    pass
            if len(pts_list) < 3:
                continue
            poly = Part.makePolygon(pts_list + [pts_list[0]])
            wire = Part.Wire(poly.Edges)
            if not wire.isClosed():
                continue
            face = Part.Face(wire)
            sol_pos = face.extrude(ev_pos)
            sol_neg = face.extrude(ev_neg)
            solids.append(sol_pos.fuse(sol_neg))
        except Exception as e:
            print('Group error:', e)
    if not solids:
        print('No solids built for', view_type)
        return None
    result = solids[0]
    for s in solids[1:]:
        result = result.fuse(s)
    print('Slab ready for', view_type, '- volume:', result.Volume)
    return result

views_info = [
    ('front', '/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/View.cleaned.dxf'),
    ('top', '/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/ProjItem001.cleaned.dxf'),
    ('right', '/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/ProjItem.cleaned.dxf'),
]

slabs = []
for idx, (view_type, dxf_path) in enumerate(views_info):
    print('Building slab for', view_type, ':', dxf_path)
    slab = build_slab(dxf_path, view_type, 'slab_' + str(idx))
    if slab is not None:
        slabs.append(slab)
    else:
        print('Slab FAILED for', view_type)

print('Total slabs built:', len(slabs))

if len(slabs) >= 2:
    try:
        result = slabs[0]
        for other in slabs[1:]:
            result = result.common(other)
        vol = getattr(result, 'Volume', 0)
        if vol > 0:
            result.exportStep('/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/combined.step')
            print('Reconstruction complete (intersection), volume:', vol)
        else:
            print('Intersection empty, falling back to compound')
            Part.makeCompound(slabs).exportStep('/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/combined.step')
    except Exception as e:
        print('Intersection failed, compound fallback:', e)
        Part.makeCompound(slabs).exportStep('/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/combined.step')
elif len(slabs) == 1:
    slabs[0].exportStep('/home/node/clawd/apps/dxf2step/jobs/20260228_090139_ff2f6657/output/combined.step')
    print('Only one slab, exported as-is')
else:
    print('No slabs built — reconstruction failed')
