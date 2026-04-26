import os
from pathlib import Path

hooks_dir = Path(r'D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios\hooks')
patch = """
def is_safe(p):
    # Skip data directory, .git, and large files
    parts = p.parts
    if 'data' in parts: return False
    if '.git' in parts: return False
    try:
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True
"""

for p in hooks_dir.glob('*.py'):
    lines = p.read_text(encoding='utf-8').splitlines()
    new_lines = []
    inserted = False
    for line in lines:
        new_lines.append(line)
        if ("from pathlib import Path" in line or "import os" in line) and not inserted:
            new_lines.append(patch)
            inserted = True
        
        if "if p.is_file()" in line:
            indent = line[:line.find("if ")]
            if "and is_safe(p)" not in line:
                new_lines[-1] = line.replace("if p.is_file()", "if p.is_file() and is_safe(p)")
    
    p.write_text("\n".join(new_lines), encoding='utf-8')
    print(f"Optimized {p.name}")
