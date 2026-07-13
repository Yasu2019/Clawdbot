# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

def main() -> int:
    output = Path(sys.argv[1])
    rows = []
    user32 = ctypes.windll.user32
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    seen: set[int] = set()

    def record(hwnd: int, parent: int = 0) -> None:
        if int(hwnd) in seen:
            return
        seen.add(int(hwnd))
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        title = ctypes.create_unicode_buffer(1024)
        class_name = ctypes.create_unicode_buffer(256)
        user32.GetWindowTextW(hwnd, title, len(title))
        user32.GetClassNameW(hwnd, class_name, len(class_name))
        rows.append({
            "handle": int(hwnd),
            "parent": int(parent),
            "process_id": int(pid.value),
            "class_name": class_name.value,
            "title": title.value,
            "visible": bool(user32.IsWindowVisible(hwnd)),
            "enabled": bool(user32.IsWindowEnabled(hwnd)),
        })
    def visit_child(hwnd: int, parent: int) -> bool:
        record(hwnd, parent)
        return True

    def visit(hwnd: int, _lparam: int) -> bool:
        record(hwnd)
        child_callback = callback_type(visit_child)
        user32.EnumChildWindows(hwnd, child_callback, hwnd)
        return True

    callback = callback_type(visit)
    user32.EnumWindows(callback, 0)
    output.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
