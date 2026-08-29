# -*- coding: utf-8 -*-
"""PySide / PySide2 / PySide6 shim for FreeCAD 0.21 / 1.x / 2.x."""
from __future__ import annotations

import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

QtCore = None
QtGui = None
QtWidgets = None

try:
    from PySide6 import QtCore, QtGui, QtWidgets  # type: ignore
except Exception:
    try:
        from PySide2 import QtCore, QtGui, QtWidgets  # type: ignore
    except Exception:
        try:
            from PySide import QtCore, QtGui  # type: ignore
            try:
                from PySide import QtWidgets  # type: ignore
            except Exception:
                QtWidgets = QtGui  # type: ignore
        except Exception:
            QtCore = None
            QtGui = None
            QtWidgets = None
