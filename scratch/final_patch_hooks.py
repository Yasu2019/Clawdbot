import os, sys, io
from pathlib import Path

hooks_dir = Path(r'D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios\hooks')
patch_head = "import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')\n"
patch_body = """
def is_safe(p):
    # Skip data directory, .git, and large files
    try:
        parts = p.parts
        if 'data' in parts: return False
        if '.git' in parts: return False
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True
"""

for p in hooks_dir.glob('*.py'):
    lines = p.read_text(encoding='utf-8').splitlines()
    new_lines = [patch_head]
    inserted_body = False
    for line in lines:
        if ("import " in line or "from " in line) and not inserted_body:
            new_lines.append(line)
            new_lines.append(patch_body)
            inserted_body = True
        elif "if p.is_file()" in line:
            new_lines.append(line.replace("if p.is_file()", "if p.is_file() and is_safe(p)"))
        else:
            new_lines.append(line)
    
    p.write_text("\n".join(new_lines), encoding='utf-8')
    print(f"Final Patched {p.name}")
