import os
from pathlib import Path

hooks_dir = Path(r'D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios\hooks')
patch = "import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\n"

for p in hooks_dir.glob('*.py'):
    content = p.read_text(encoding='utf-8')
    if "sys.stdout = io.TextIOWrapper" not in content:
        p.write_text(patch + content, encoding='utf-8')
        print(f"Patched {p.name}")
