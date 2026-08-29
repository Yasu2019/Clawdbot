# -*- coding: utf-8 -*-
"""FreeCAD GUI workbench entry (portable; not K10 Docker)."""
from __future__ import annotations

import os
import sys

_ROOT = os.path.dirname(__file__)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
_VENDOR = os.path.join(_ROOT, "vendor")
if _VENDOR not in sys.path:
    sys.path.insert(0, _VENDOR)

ICON = os.path.join(_ROOT, "resources", "clawstack_cetol.svg")


class ClawstackCetolWorkbench(Workbench):  # noqa: F821 -- FreeCAD injects Workbench
    MenuText = "Clawstack CETOL"
    ToolTip = "CETOL-class tolerance (not Sigmetrix CETOL 6-sigma)"
    Icon = ICON

    def Initialize(self) -> None:
        from clawstack_cetol_wb import commands
        cmds = commands.register()
        self.appendToolbar("Clawstack CETOL", cmds)
        self.appendMenu("Clawstack CETOL", cmds)

    def GetClassName(self) -> str:
        return "Gui::PythonWorkbench"


Gui.addWorkbench(ClawstackCetolWorkbench())
