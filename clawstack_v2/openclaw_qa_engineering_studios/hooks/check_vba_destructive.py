import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import re

def is_safe(p):
    # Skip data directory, .git, and large files
    try:
        parts = p.parts
        if 'data' in parts: return False
        if '.git' in parts: return False
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True

import sys
from pathlib import Path

DANGER = re.compile(r'\b(Kill|DeleteFile|\.Delete\b|ClearContents|Clear\b|SaveAs|ActiveWorkbook\.Save|DROP|DELETE\s+FROM|UPDATE\s+)\b', re.I)

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits=[]
    for ext in ['*.bas','*.cls','*.frm','*.vba','*.txt','*.md']:
        for p in root.rglob(ext):
            text = p.read_text(encoding='utf-8', errors='ignore')
            for i,line in enumerate(text.splitlines(),1):
                if DANGER.search(line): hits.append((p,i,line.strip()))
    if hits:
        print('[WARN] Potential destructive VBA/file operation found:')
        for p,i,line in hits[:100]: print(f'{p}:{i}: {line}')
        sys.exit(2)
    print('[OK] No obvious destructive VBA/file operations found.')