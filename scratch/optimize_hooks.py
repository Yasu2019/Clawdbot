import os
from pathlib import Path

hooks_dir = Path(r'D:\Clawdbot_Docker_20260125\clawstack_v2\openclaw_qa_engineering_studios\hooks')
patch = """
def is_safe(p: Path):
    if 'data' in p.parts: return False
    if p.stat().st_size > 1024 * 1024: return False
    return True
"""

for p in hooks_dir.glob('*.py'):
    lines = p.read_text(encoding='utf-8').splitlines()
    new_lines = []
    in_scan = False
    for line in lines:
        if "def scan(root: Path):" in line:
            new_lines.append(patch)
            new_lines.append(line)
            in_scan = True
        elif in_scan and "if p.is_file()" in line:
            indent = line[:line.find("if ")]
            new_lines.append(f"{indent}if p.is_file() and is_safe(p) and p.suffix.lower() in TARGET_EXT:")
        else:
            new_lines.append(line)
    p.write_text("\n".join(new_lines), encoding='utf-8')
    print(f"Optimized {p.name}")
