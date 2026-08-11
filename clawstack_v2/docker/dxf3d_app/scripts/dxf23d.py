"""
dxf23d.py — loops.json -> FreeCAD .fcstd (PartDesign Body / Sketch / Pad)
========================================================================
Runs inside the Antigravity container under FreeCAD's own interpreter:

    /opt/freecad/AppRun freecadcmd /work/scripts/dxf23d.py --pass \
        mode=fcstd in=/work/dxf3d_output/<job>/loops.json \
        out=/work/dxf3d_output/<job>/output.fcstd height=10.0

Arguments are `key=value` pairs because FreeCAD's `--pass` refuses tokens
that start with `-`.

Input JSON: {"loops": [[[x, y], ...], ...]}  — closed 2D contours in mm.
The largest-area loop becomes the outer profile; the rest become holes,
which PartDesign::Pad derives automatically from the sketch wires.

Exit code 0 on success, 1 on failure (message on stderr).
"""

import json
import math
import sys
import traceback

import FreeCAD as App
import Part

MIN_SEG = 1e-6      # drop segments shorter than this (mm)
MIN_LOOP_PTS = 3


def parse_args(argv):
    args = {}
    for token in argv[1:]:
        if token == "--pass" or "=" not in token:
            continue
        key, _, value = token.partition("=")
        args[key.strip().lstrip("-")] = value.strip()
    return args


def load_loops(path):
    with open(path, "r", encoding="utf-8") as fh:
        payload = json.load(fh)
    raw = payload.get("loops") or []
    loops = []
    for loop in raw:
        pts = []
        for pt in loop:
            x, y = float(pt[0]), float(pt[1])
            if pts and math.hypot(x - pts[-1][0], y - pts[-1][1]) < MIN_SEG:
                continue
            pts.append((x, y))
        # close the ring: drop a duplicated final point, the wire closes implicitly
        if len(pts) >= 2 and math.hypot(pts[0][0] - pts[-1][0],
                                       pts[0][1] - pts[-1][1]) < MIN_SEG:
            pts.pop()
        if len(pts) >= MIN_LOOP_PTS:
            loops.append(pts)
    return loops


def _signed_area(pts):
    total = 0.0
    for i in range(len(pts)):
        x0, y0 = pts[i]
        x1, y1 = pts[(i + 1) % len(pts)]
        total += x0 * y1 - x1 * y0
    return total * 0.5


def _wire(pts):
    vectors = [App.Vector(x, y, 0.0) for x, y in pts]
    vectors.append(vectors[0])
    return Part.makePolygon(vectors)


def build_via_partdesign(doc, loops, height):
    """Preferred path: editable Body -> Sketch -> Pad history."""
    import Sketcher  # noqa: F401  (registers the Sketcher::SketchObject type)

    body = doc.addObject("PartDesign::Body", "Body")
    sketch = doc.addObject("Sketcher::SketchObject", "Profile")
    body.addObject(sketch)

    for pts in loops:
        for i in range(len(pts)):
            x0, y0 = pts[i]
            x1, y1 = pts[(i + 1) % len(pts)]
            if math.hypot(x1 - x0, y1 - y0) < MIN_SEG:
                continue
            sketch.addGeometry(
                Part.LineSegment(App.Vector(x0, y0, 0.0), App.Vector(x1, y1, 0.0)),
                False,
            )
    doc.recompute()

    pad = doc.addObject("PartDesign::Pad", "Pad")
    body.addObject(pad)
    pad.Profile = sketch
    pad.Length = height
    pad.Midplane = False
    pad.Reversed = False
    doc.recompute()

    if pad.Shape.isNull() or pad.Shape.Volume <= 0.0:
        raise RuntimeError("Pad produced an empty solid")
    return pad.Shape.Volume, "partdesign"


def build_via_part(doc, loops, height):
    """Fallback: plain Part::Feature solid, still a valid .fcstd."""
    ordered = sorted(loops, key=lambda pts: abs(_signed_area(pts)), reverse=True)
    face = Part.Face(_wire(ordered[0]))
    for pts in ordered[1:]:
        try:
            face = face.cut(Part.Face(_wire(pts)))
        except Exception:
            continue
    solid = face.extrude(App.Vector(0, 0, height))
    obj = doc.addObject("Part::Feature", "Solid")
    obj.Shape = solid
    doc.recompute()
    if solid.Volume <= 0.0:
        raise RuntimeError("extrusion produced an empty solid")
    return solid.Volume, "part"


def main(argv):
    args = parse_args(argv)
    mode = args.get("mode", "fcstd")
    in_path = args.get("in")
    out_path = args.get("out")

    if mode != "fcstd":
        print("unsupported mode: %s (only 'fcstd')" % mode, file=sys.stderr)
        return 1
    if not in_path or not out_path:
        print("usage: --pass mode=fcstd in=<loops.json> out=<file.fcstd> height=<mm>",
              file=sys.stderr)
        return 1
    try:
        height = float(args.get("height", "10"))
    except ValueError:
        print("height must be numeric", file=sys.stderr)
        return 1
    if height <= 0.0:
        print("height must be > 0", file=sys.stderr)
        return 1

    loops = load_loops(in_path)
    if not loops:
        print("no usable closed loops in %s" % in_path, file=sys.stderr)
        return 1

    doc = App.newDocument("dxf3d")
    try:
        volume, method = build_via_partdesign(doc, loops, height)
    except Exception:
        # PartDesign is picky about wire closure; keep the .fcstd deliverable.
        print("PartDesign path failed, falling back to Part::Feature:", file=sys.stderr)
        traceback.print_exc()
        for obj in list(doc.Objects):
            try:
                doc.removeObject(obj.Name)
            except Exception:
                pass
        volume, method = build_via_part(doc, loops, height)

    doc.recompute()
    doc.saveAs(out_path)
    print(json.dumps({
        "ok": True,
        "method": method,
        "loops": len(loops),
        "height_mm": height,
        "volume_mm3": round(volume, 3),
        "out": out_path,
    }, ensure_ascii=False))
    return 0


# freecadcmd imports the script as a module named after the file, so
# `__name__` is never "__main__" — run unconditionally.
try:
    sys.exit(main(sys.argv))
except SystemExit:
    raise
except Exception:
    traceback.print_exc()
    sys.exit(1)
