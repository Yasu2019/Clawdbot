# -*- coding: utf-8 -*-
"""FreeCAD console load (no GUI)."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_VENDOR = os.path.join(_ROOT, "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)
