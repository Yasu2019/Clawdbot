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

FORBIDDEN = re.compile(r"\b(INSERT|UPDATE|DELETE|DROP|ALTER|TRUNCATE|MERGE|CREATE\s+TABLE)\b", re.I)
TARGET_EXT = {'.bas', '.cls', '.frm', '.vbs', '.ps1', '.py', '.sql', '.md', '.txt'}

def scan(root: Path):
    hits = []
    for p in root.rglob('*'):
        if p.is_file() and is_safe(p) and p.suffix.lower() in TARGET_EXT:
            try:
                text = p.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if FORBIDDEN.search(line):
                    hits.append((p, i, line.strip()))
    return hits

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    hits = scan(root)
    if hits:
        print('[NG] SQL write/destructive keywords found:')
        for p, i, line in hits[:100]:
            print(f'{p}:{i}: {line}')
        sys.exit(1)
    print('[OK] No SQL write/destructive keywords found.')