# -*- coding: utf-8 -*-
from __future__ import annotations

import ctypes
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def main() -> int:
    target_pid = int(sys.argv[1])
    output = Path(sys.argv[2])
    user32 = ctypes.windll.user32
    matched: list[dict] = []
    after = 0
    while True:
        hwnd = user32.FindWindowExW(0, after, "Internet Explorer_TridentDlgFrame", None)
        if not hwnd:
            break
        pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value == target_pid:
            matched.append({"handle": int(hwnd), "class_name": "Internet Explorer_TridentDlgFrame"})
            break
        after = hwnd
    output.write_text(json.dumps({"pid": target_pid, "matched": matched}, ensure_ascii=False), encoding="utf-8")
    if not matched:
        return 2
    user32.PostMessageW(matched[0]["handle"], 0x0010, 0, 0)  # WM_CLOSE
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
