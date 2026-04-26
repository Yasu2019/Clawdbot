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

PATTERNS = [
    re.compile(r'Bearer\s+[A-Za-z0-9._\-]{20,}', re.I),
    re.compile(r'(api[_-]?key|secret|password|token)\s*[:=]\s*["\']?[A-Za-z0-9._\-]{16,}', re.I),
    re.compile(r'sk-[A-Za-z0-9]{20,}', re.I),
]

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits=[]
    for p in root.rglob('*'):
        if p.is_file() and is_safe(p) and p.suffix.lower() not in {'.png','.jpg','.jpeg','.gif','.zip','.exe','.dll'}:
            text = p.read_text(encoding='utf-8', errors='ignore')
            for i,line in enumerate(text.splitlines(),1):
                if any(rx.search(line) for rx in PATTERNS): hits.append((p,i,line.strip()))
    if hits:
        print('[NG] Possible secret leak found:')
        for p,i,line in hits[:50]: print(f'{p}:{i}: {line[:160]}')
        sys.exit(1)
    print('[OK] No obvious secrets found.')