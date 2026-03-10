import FreeCAD as App
import Part

def view_matrix(view_type, cx, cy):
    """Return (App.Matrix, ev_pos, ev_neg) that maps DXF-XY plane to 3D view plane.
    All matrices are proper rotations (det=+1) to avoid face-normal inversion.
    front : DXF(x,y,0) -> 3D( x-cx,     0, y-cy)  face in XZ, extrude +/-Y
    top   : DXF(x,y,0) -> 3D( x-cx, y-cy,    0)  face in XY, extrude +/-Z
    right : DXF(x,y,0) -> 3D(    0, x-cx, y-cy)  face in YZ, extrude +/-X
    """
    m = App.Matrix()
    if view_type == 'front':
        m.A11=1;  m.A12=0;  m.A13=0;  m.A14=-cx
        m.A21=0;  m.A22=0;  m.A23=-1; m.A24=0
        m.A31=0;  m.A32=1;  m.A33=0;  m.A34=-cy
        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1
        return m, App.Vector(0, 1, 0), App.Vector(0, -1, 0)
    elif view_type == 'top':
        m.A11=1;  m.A12=0;  m.A13=0;  m.A14=-cx
        m.A21=0;  m.A22=1;  m.A23=0;  m.A24=-cy
        m.A31=0;  m.A32=0;  m.A33=1;  m.A34=0
        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1
        return m, App.Vector(0, 0, 1), App.Vector(0, 0, -1)
    elif view_type == 'right':
        m.A11=0;  m.A12=0;  m.A13=1;  m.A14=0
        m.A21=1;  m.A22=0;  m.A23=0;  m.A24=-cx
        m.A31=0;  m.A32=1;  m.A33=0;  m.A34=-cy
        m.A41=0;  m.A42=0;  m.A43=0;  m.A44=1
        return m, App.Vector(1, 0, 0), App.Vector(-1, 0, 0)
    return None, None, None

def build_slab(dxf_path, view_type, doc_name):
    """Build an infinite slab for one view using analytical B-Rep (no discretize)."""
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
    # Bounding box for centering and extrusion length
    bb = Part.Compound(edges).BoundBox
    cx = (bb.XMax + bb.XMin) / 2
    cy = (bb.YMax + bb.YMin) / 2
    ext = max(bb.XMax - bb.XMin, bb.YMax - bb.YMin, 1.0) * 3
    m, ev_pos, ev_neg = view_matrix(view_type, cx, cy)
    if m is None:
        return None
    ev_pos = App.Vector(ev_pos.x * ext, ev_pos.y * ext, ev_pos.z * ext)
    ev_neg = App.Vector(ev_neg.x * ext, ev_neg.y * ext, ev_neg.z * ext)
    # Sort edges into closed loops then build analytical faces
    try:
        sorted_groups = Part.sortEdges(edges)
    except Exception as e:
        print('sortEdges failed:', e)
        return None
    solids = []
    for group in sorted_groups:
        try:
            wire = Part.Wire(group)
            if not wire.isClosed():
                continue
            # Build face in the original DXF XY-plane
            face_2d = Part.Face(wire)
            # Map to correct 3D view plane (keeps LINE as plane, ARC as cylinder)
            face_3d = face_2d.transformGeometry(m)
            sol_pos = face_3d.extrude(ev_pos)
            sol_neg = face_3d.extrude(ev_neg)
            solids.append(sol_pos.fuse(sol_neg))
        except Exception as e:
            print('Group error for', view_type, ':', e)
    if not solids:
        print('No solids built for', view_type)
        return None
    result = solids[0]
    for s in solids[1:]:
        result = result.fuse(s)
    print('Slab ready for', view_type,
          '- faces:', len(result.Faces), '- volume:', result.Volume)
    return result

views_info = [
    ('front', '/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/View.cleaned.dxf'),
    ('top', '/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/ProjItem001.cleaned.dxf'),
    ('right', '/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/ProjItem.cleaned.dxf'),
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
            print('Intersection ok - faces before cleanup:', len(result.Faces))
            # Step 1: merge coplanar/same-curvature faces
            try:
                cleaned = result.removeSplitter()
                if getattr(cleaned, 'Volume', 0) > 0:
                    result = cleaned
                    print('removeSplitter done - faces:', len(result.Faces))
            except Exception as e:
                print('removeSplitter skipped:', e)
            # Step 2: upgrade SurfaceOfExtrusion -> Plane / Cylinder
            # Reconstruct each face from its ordered vertices as pure 3D lines,
            # so Part.Face() can detect planarity and assign a Plane surface.
            try:
                upgraded_faces = []
                for face in result.Faces:
                    stype = type(face.Surface).__name__
                    if 'Extrusion' in stype:
                        try:
                            pts = [v.Point for v in face.OuterWire.OrderedVertexes]
                            new_edges = [Part.makeLine(pts[i], pts[(i+1) % len(pts)])
                                         for i in range(len(pts))]
                            new_wire = Part.Wire(Part.sortEdges(new_edges)[0])
                            nf = Part.Face(new_wire)
                            upgraded_faces.append(nf)
                        except Exception as fe:
                            print('  face rebuild failed, keeping original:', fe)
                            upgraded_faces.append(face)
                    else:
                        upgraded_faces.append(face)
                shell = Part.Shell(upgraded_faces)
                upgraded = Part.Solid(shell)
                if getattr(upgraded, 'Volume', 0) > 0:
                    result = upgraded
                    ftypes = {type(f.Surface).__name__ for f in result.Faces}
                    print('Face upgrade done - types:', ftypes)
            except Exception as e:
                print('Face upgrade skipped:', e)
            result.exportStep('/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/combined.step')
            print('Reconstruction complete - volume:', result.Volume,
                  '- faces:', len(result.Faces))
        else:
            print('Intersection empty, falling back to compound')
            Part.makeCompound(slabs).exportStep('/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/combined.step')
    except Exception as e:
        print('Intersection failed, compound fallback:', e)
        Part.makeCompound(slabs).exportStep('/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/combined.step')
elif len(slabs) == 1:
    slabs[0].exportStep('/home/node/clawd/apps/dxf2step/jobs/selfcheck5_20260228/combined.step')
    print('Only one slab, exported as-is')
else:
    print('No slabs built - reconstruction failed')
