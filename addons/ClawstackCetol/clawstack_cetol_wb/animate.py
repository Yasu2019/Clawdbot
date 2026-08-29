# -*- coding: utf-8 -*-
"""Sensitivity pose on FreeCAD Placement (visual only, not CETOL CAD perturbation)."""
from __future__ import annotations

import math
import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .qtcompat import QtCore


class SensitivityAnimator:
    def __init__(self) -> None:
        self._timer = None
        self._saved: dict[str, Any] = {}
        self._objs: list[Any] = []
        self._obj = None
        self._axis = "z"
        self._amp = 2.0
        self._t = 0.0
        self._rot = False

    @property
    def running(self) -> bool:
        return self._timer is not None and self._timer.isActive()

    def stop(self) -> None:
        if self._timer is not None:
            self._timer.stop()
            self._timer = None
        for obj in self._objs:
            name = getattr(obj, "Name", None)
            if name is not None and name in self._saved:
                obj.Placement = self._saved[name]
        self._objs = []
        self._obj = None
        self._saved = {}
        self._t = 0.0

    def start(self, obj: Any, driver: str | None, amp_mm: float = 2.0) -> str:
        return self.start_many([obj] if obj is not None else [], driver, amp_mm)

    def start_many(self, objects: list[Any], driver: str | None, amp_mm: float = 2.0) -> str:
        self.stop()
        objs = [o for o in objects if o is not None]
        if not objs:
            return "no object to animate"
        from .qtcompat import QtCore
        if QtCore is None:
            return "Qt not available (run inside FreeCAD)"
        try:
            import FreeCAD as App  # type: ignore
        except ImportError:
            return "FreeCAD not available"
        self._objs = objs
        self._obj = objs[0]
        for obj in objs:
            self._saved[obj.Name] = App.Placement(obj.Placement)
        self._amp = max(float(amp_mm), 0.2)
        axis, is_rot = _axis_from_driver(driver)
        self._axis = axis
        self._rot = is_rot
        self._timer = QtCore.QTimer()
        self._timer.setInterval(40)
        self._timer.timeout.connect(self._tick)
        self._timer.start()
        labels = "+".join(str(getattr(o, "Label", o.Name)) for o in objs)
        return "animating " + labels + " " + axis + (" rot" if is_rot else " trans")

    def _tick(self) -> None:
        if not self._objs:
            return
        try:
            import FreeCAD as App  # type: ignore
        except ImportError:
            self.stop()
            return
        self._t += 0.12
        mag = math.sin(self._t) * self._amp
        if self._rot:
            deg = mag * 4.0
            if self._axis == "x":
                rot = App.Rotation(App.Vector(1, 0, 0), deg)
            elif self._axis == "y":
                rot = App.Rotation(App.Vector(0, 1, 0), deg)
            else:
                rot = App.Rotation(App.Vector(0, 0, 1), deg)
        else:
            rot = None
            if self._axis == "x":
                delta = App.Vector(mag, 0, 0)
            elif self._axis == "y":
                delta = App.Vector(0, mag, 0)
            else:
                delta = App.Vector(0, 0, mag)
        for obj in self._objs:
            base = self._saved.get(obj.Name)
            if base is None:
                continue
            if self._rot:
                combined = rot.multiply(base.Rotation) if hasattr(rot, "multiply") else rot
                obj.Placement = App.Placement(base.Base, combined)
            else:
                obj.Placement = App.Placement(base.Base + delta, base.Rotation)


def _axis_from_driver(driver: str | None) -> tuple[str, bool]:
    d = str(driver or "").lower()
    if d.endswith("_rx"):
        return "x", True
    if d.endswith("_ry"):
        return "y", True
    if d.endswith("_rz"):
        return "z", True
    if d.endswith("_tx"):
        return "x", False
    if d.endswith("_ty"):
        return "y", False
    return "z", False


def pick_animate_object(doc: Any, driver: str | None) -> Any:
    """Prefer Pin (then Strip) for in-plane drivers; else name match / last solid."""
    objects = list(getattr(doc, "Objects", []) or [])
    solids = []
    for obj in objects:
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        is_null = getattr(shape, "isNull", None)
        if callable(is_null) and is_null():
            continue
        if getattr(shape, "Volume", 0) and float(shape.Volume) > 1e-6:
            solids.append(obj)
    d = str(driver or "")
    dlow = d.lower()
    if "_tx" in dlow or "_ty" in dlow:
        for obj in solids:
            lab = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "").lower()
            if lab == "pin":
                return obj
        for obj in solids:
            lab = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "").lower()
            if lab == "strip":
                return obj
    for obj in solids:
        if obj.Name and obj.Name in d:
            return obj
        if obj.Label and obj.Label.replace(" ", "_") in d:
            return obj
    if len(solids) >= 2:
        return solids[-1]
    return solids[0] if solids else None


def pick_animate_objects(doc: Any, driver: str | None) -> list[Any]:
    """Pin+Strip for in-plane drivers so the float looks like a mate, not one body."""
    primary = pick_animate_object(doc, driver)
    out: list[Any] = []
    if primary is not None:
        out.append(primary)
    dlow = str(driver or "").lower()
    if "_tx" not in dlow and "_ty" not in dlow:
        return out
    objects = list(getattr(doc, "Objects", []) or [])
    for obj in objects:
        lab = str(getattr(obj, "Label", "") or getattr(obj, "Name", "") or "").lower()
        if lab != "strip":
            continue
        if primary is not None and obj is primary:
            continue
        shape = getattr(obj, "Shape", None)
        if shape is None:
            continue
        if getattr(shape, "Volume", 0) and float(shape.Volume) > 1e-6:
            out.append(obj)
            break
    return out
