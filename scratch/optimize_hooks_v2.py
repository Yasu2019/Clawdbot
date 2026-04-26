import os
from pathlib import Path

hooks_dir = Path(r'D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios\hooks')
patch = """
def is_safe(p: Path):
    # Skip data directory and large files
    if 'data' in p.parts: return False
    if '.git' in p.parts: return False
    try:
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True
"""

for p in hooks_dir.glob('*.py'):
    lines = p.read_text(encoding='utf-8').splitlines()
    new_lines = []
    has_patch = False
    for line in lines:
        if "import " in line and not has_patch:
            new_lines.append(patch)
            has_patch = True
        
        if "if p.is_file()" in line:
            indent = line[:line.find("if ")]
            # Replace existing condition or append to it
            if "and is_safe(p)" not in line:
                line = line.replace("if p.is_file()", "if p.is_file() and is_safe(p)")
        
        new_lines.append(line)
    
    p.write_text("\n".join(new_lines), encoding='utf-8')
    print(f"Optimized {p.name}")
