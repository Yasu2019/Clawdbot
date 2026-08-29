# -*- coding: utf-8 -*-
"""Dock widget: results + run / animate (not commercial CETOL)."""
from __future__ import annotations

import sys
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .qtcompat import QtCore, QtWidgets
from .animate import SensitivityAnimator, pick_animate_objects
from .extract import extract_from_freecad_document
from .run_analysis import analyze_manifest

_ANIM = SensitivityAnimator()


def _fmt_model(model: dict[str, Any]) -> str:
    msm = model.get("msm") or {}
    sota = (model.get("msm_sota") or {}).get("loop_sota") or {}
    coup = model.get("measure_coupling") or {}
    table = model.get("cross_table") or {}
    joints = model.get("freecad_assembly_joints") or []
    lines = [
        "Clawstack CETOL-class -- NOT Sigmetrix CETOL 6-sigma",
        "status: " + str((model.get("truth_gate") or {}).get("status") or "UNVALIDATED"),
        "",
        "Cpk MSM 1D: " + str(msm.get("Cpk")),
        "yield GC / GLD: " + str(msm.get("yield_rate")) + " / " + str(msm.get("yield_rate_gld")),
        "loop SOTA sigma: " + str(sota.get("sigma"))
        + " cross=" + str(sota.get("cross_pairs"))
        + (" full" if sota.get("full_cross") else " topN"),
        "loop SOTA Cpk / GLD yield: " + str(sota.get("Cpk")) + " / " + str(sota.get("yield_rate_gld")),
        "constraint: " + str(((model.get("tim") or {}).get("constraint_state") or {}).get("status")
                            or (model.get("constraint_state") or {}).get("status"))
        + " DLM=" + ("on" if (model.get("closed_loop") or {}).get("applied") else "off")
        + " jointY=" + str((model.get("joint_ctq_yield") or {}).get("yield_joint")),
        "cetol-cannot process RSS: " + str(((model.get("cetol_cannot") or {}).get("progressive_die") or {}).get("rss_process_mm"))
        + " flex=" + str(((model.get("cetol_cannot") or {}).get("compliant") or {}).get("sigma_mm"))
        + " fill=" + str(((model.get("cetol_cannot") or {}).get("moldflow") or {}).get("status")),
        "",
        "CAD joints found: " + str(len(joints)),
    ]
    for j in joints[:12]:
        lines.append("  " + str(j.get("sequence")) + ". " + str(j.get("cad_joint_type") or j.get("kind"))
                     + "  " + str(j.get("from")) + " -> " + str(j.get("to")))
    lines.append("")
    lines.append("CTQ coupling:")
    for mid, info in coup.items():
        st = (info or {}).get("status")
        mx = (info or {}).get("max_contribution")
        lines.append("  " + str(mid) + ": " + str(st) + " max=" + str(mx))
    lines.append("")
    mids = []
    for row in table.values():
        if isinstance(row, dict):
            mids = list(row.keys())
            break
    lines.append("Cross-table (contributor x CTQ contribution):")
    lines.append("  " + "\t".join(["name"] + mids))
    ranked = sorted(
        table.items(),
        key=lambda kv: -float(((kv[1] or {}).get("gap_z")) or 0.0),
    )
    for name, row in ranked[:18]:
        if not isinstance(row, dict):
            continue
        cells = [("%0.1f%%" % (float(row.get(m) or 0) * 100.0)) for m in mids]
        lines.append("  " + str(name) + "\t" + "\t".join(cells))
    tim = model.get("tim") or {}
    lines.append("")
    lines.append("TIM analog unused_1d=" + str(tim.get("unused_count"))
                 + " MMC_applied=" + str(tim.get("mmc_applied_count")))
    for f in (model.get("advisor") or [])[:8]:
        lines.append("advisor: " + str(f.get("code")) + " -- " + str(f.get("text")))
    return "\n".join(lines)


class CetolDock(QtWidgets.QDockWidget):
    def __init__(self, gui_module: Any) -> None:
        super().__init__("Clawstack CETOL-class")
        self.gui = gui_module
        self._model: dict[str, Any] | None = None
        w = QtWidgets.QWidget()
        lay = QtWidgets.QVBoxLayout(w)
        note = QtWidgets.QLabel(
            "Portable workbench. Assembly/constraints = FreeCAD. "
            "Stack = Clawstack engine. Not commercial CETOL."
        )
        note.setWordWrap(True)
        lay.addWidget(note)
        btn_row = QtWidgets.QHBoxLayout()
        self.btn_run = QtWidgets.QPushButton("Analyze document")
        self.btn_anim = QtWidgets.QPushButton("Play sensitivity")
        self.btn_stop = QtWidgets.QPushButton("Stop")
        btn_row.addWidget(self.btn_run)
        btn_row.addWidget(self.btn_anim)
        btn_row.addWidget(self.btn_stop)
        lay.addLayout(btn_row)
        self.status = QtWidgets.QLabel("Ready")
        lay.addWidget(self.status)
        self.out = QtWidgets.QPlainTextEdit()
        self.out.setReadOnly(True)
        lay.addWidget(self.out)
        self.setWidget(w)
        self.btn_run.clicked.connect(self.run)
        self.btn_anim.clicked.connect(self.play)
        self.btn_stop.clicked.connect(self.stop)

    def run(self) -> None:
        try:
            import FreeCAD as App  # type: ignore
        except ImportError:
            self.status.setText("Not inside FreeCAD")
            return
        doc = App.ActiveDocument
        if doc is None:
            self.status.setText("Open a document (Part / Assembly) first")
            return
        try:
            man = extract_from_freecad_document(doc)
            self._model = analyze_manifest(man)
            self.out.setPlainText(_fmt_model(self._model))
            n_h = len(((man.get("features") or {}).get("holes") or []))
            n_j = len(man.get("freecad_assembly_joints") or [])
            self.status.setText("OK holes=%s joints=%s (UNVALIDATED vs CETOL)" % (n_h, n_j))
        except Exception as exc:
            self.status.setText("FAIL")
            self.out.setPlainText(str(type(exc).__name__) + ": " + str(exc))

    def play(self) -> None:
        try:
            import FreeCAD as App  # type: ignore
            import FreeCADGui as Gui  # type: ignore
        except ImportError:
            self.status.setText("Not inside FreeCAD")
            return
        doc = App.ActiveDocument
        if doc is None:
            self.status.setText("No document")
            return
        if self._model is None:
            self.run()
        driver = None
        if self._model:
            driver = (self._model.get("sensitivity_animation") or {}).get("driver")
        sel = Gui.Selection.getSelection()
        objs = list(sel) if sel else pick_animate_objects(doc, driver)
        msg = _ANIM.start_many(objs, driver)
        self.status.setText(msg)

    def stop(self) -> None:
        _ANIM.stop()
        self.status.setText("animation stopped")


_DOCK: CetolDock | None = None


def show_dock(gui_module: Any) -> CetolDock:
    global _DOCK
    main = gui_module.getMainWindow()
    if _DOCK is None:
        _DOCK = CetolDock(gui_module)
        area = getattr(QtCore.Qt, "RightDockWidgetArea", None)
        if area is None:
            area = QtCore.Qt.DockWidgetArea.RightDockWidgetArea
        main.addDockWidget(area, _DOCK)
    _DOCK.show()
    _DOCK.raise_()
    return _DOCK
