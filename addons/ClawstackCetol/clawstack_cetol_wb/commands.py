# -*- coding: utf-8 -*-
"""FreeCAD commands for Clawstack CETOL-class workbench."""
from __future__ import annotations

import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .paths import workbench_root

ICON = os.path.join(str(workbench_root()), "resources", "clawstack_cetol.svg")


class _CmdAnalyze:
    def GetResources(self) -> dict:
        return {
            "Pixmap": ICON,
            "MenuText": "Analyze document",
            "ToolTip": "Run CETOL-class stack on the active document (not commercial CETOL)",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        import FreeCADGui as Gui  # type: ignore
        from .panel import show_dock
        dock = show_dock(Gui)
        dock.run()


class _CmdAnimate:
    def GetResources(self) -> dict:
        return {
            "Pixmap": ICON,
            "MenuText": "Play sensitivity",
            "ToolTip": "Oscillate Placement of selection / driver part",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        import FreeCADGui as Gui  # type: ignore
        from .panel import show_dock
        dock = show_dock(Gui)
        dock.play()


class _CmdStop:
    def GetResources(self) -> dict:
        return {
            "Pixmap": ICON,
            "MenuText": "Stop animation",
            "ToolTip": "Restore Placement",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        import FreeCADGui as Gui  # type: ignore
        from .panel import show_dock
        dock = show_dock(Gui)
        dock.stop()


class _CmdLoadDemo:
    def GetResources(self) -> dict:
        return {
            "Pixmap": ICON,
            "MenuText": "Load demo + analyze",
            "ToolTip": "Build two-plate pin demo, then run CETOL-class analysis",
        }

    def IsActive(self) -> bool:
        return True

    def Activated(self) -> None:
        import FreeCADGui as Gui  # type: ignore
        from .demo import build_demo
        from .panel import show_dock
        build_demo()
        dock = show_dock(Gui)
        dock.run()


def register() -> list[str]:
    import FreeCADGui as Gui  # type: ignore
    Gui.addCommand("ClawstackCetol_LoadDemo", _CmdLoadDemo())
    Gui.addCommand("ClawstackCetol_Analyze", _CmdAnalyze())
    Gui.addCommand("ClawstackCetol_Animate", _CmdAnimate())
    Gui.addCommand("ClawstackCetol_Stop", _CmdStop())
    return [
        "ClawstackCetol_LoadDemo",
        "ClawstackCetol_Analyze",
        "ClawstackCetol_Animate",
        "ClawstackCetol_Stop",
    ]
