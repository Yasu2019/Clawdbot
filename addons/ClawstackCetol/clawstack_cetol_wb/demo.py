# -*- coding: utf-8 -*-
"""Build an immediate-try two-plate + pin demo inside FreeCAD (no K10)."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

DEMO_DOC_NAME = "ClawstackCetolDemo"
HOLE_XY = ((20.0, 20.0), (60.0, 20.0))
PLATE = (80.0, 40.0, 4.0)
STRIP_T = 2.0
PIN_R = 2.85
HOLE_R_BASE = 3.05
HOLE_R_STRIP = 3.10


def build_demo(doc=None):
    """Create DieBase + Strip + Pin with two through-holes. Returns the document."""
    import FreeCAD as App  # type: ignore
    import Part  # type: ignore

    if doc is None:
        doc = App.newDocument(DEMO_DOC_NAME)
    lx, ly, tz = PLATE
    base = Part.makeBox(lx, ly, tz)
    for hx, hy in HOLE_XY:
        cyl = Part.makeCylinder(
            HOLE_R_BASE, tz + 2.0, App.Vector(hx, hy, -1.0), App.Vector(0, 0, 1)
        )
        base = base.cut(cyl)
    obj_base = doc.addObject("Part::Feature", "DieBase")
    obj_base.Label = "DieBase"
    obj_base.Shape = base

    strip = Part.makeBox(lx, ly, STRIP_T)
    strip.translate(App.Vector(0.0, 0.0, tz))
    for hx, hy in HOLE_XY:
        cyl = Part.makeCylinder(
            HOLE_R_STRIP, STRIP_T + 2.0, App.Vector(hx, hy, tz - 1.0), App.Vector(0, 0, 1)
        )
        strip = strip.cut(cyl)
    obj_strip = doc.addObject("Part::Feature", "Strip")
    obj_strip.Label = "Strip"
    obj_strip.Shape = strip

    hx0, hy0 = HOLE_XY[0]
    pin = Part.makeCylinder(
        PIN_R, tz + STRIP_T + 2.0, App.Vector(hx0, hy0, -1.0), App.Vector(0, 0, 1)
    )
    obj_pin = doc.addObject("Part::Feature", "Pin")
    obj_pin.Label = "Pin"
    obj_pin.Shape = pin

    _add_joint_proxy(doc, "J_DieStrip", "Planar", obj_base, obj_strip)
    _add_joint_proxy(doc, "J_PinHole", "Cylindrical", obj_pin, obj_strip)

    doc.recompute()
    try:
        import FreeCADGui as Gui  # type: ignore
        Gui.SendMsgToActiveView("ViewFit")
    except Exception:
        pass
    return doc


def _add_joint_proxy(doc, name, joint_type, obj_from, obj_to):
    """Duck-typed JointType object so extract.py can drive the loop."""
    try:
        obj = doc.addObject("App::FeaturePython", name)
        obj.Label = name
        obj.addProperty("App::PropertyString", "JointType", "Clawstack", "CAD joint kind")
        obj.JointType = joint_type
        obj.addProperty("App::PropertyLink", "Reference1", "Clawstack", "")
        obj.Reference1 = obj_from
        obj.addProperty("App::PropertyLink", "Reference2", "Clawstack", "")
        obj.Reference2 = obj_to
        return obj
    except Exception:
        return None
