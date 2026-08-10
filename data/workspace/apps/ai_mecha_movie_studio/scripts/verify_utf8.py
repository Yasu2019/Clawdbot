# -*- coding: utf-8 -*-
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEXT_EXTS = {".py", ".md", ".json", ".txt", ".ts", ".tsx"}
fail = []
count = 0
for p in ROOT.rglob("*"):
    if p.is_file() and p.suffix.lower() in TEXT_EXTS:
        count += 1
        try:
            p.read_text(encoding="utf-8")
        except Exception as e:
            fail.append((p, e))
print(f"UTF-8 check: {count} files")
if fail:
    for p, e in fail:
        print("NG", p, e)
    raise SystemExit(1)
print("OK: すべてUTF-8として正常に読めます。")
