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

PORT_RE = re.compile(r'(?:(?:127\.0\.0\.1|0\.0\.0\.0):)?(\d{2,5}):(\d{2,5})')

def scan(root: Path):
    ports = {}
    for p in root.rglob('*compose*.yml'):
        text = p.read_text(encoding='utf-8', errors='ignore')
        for i, line in enumerate(text.splitlines(), 1):
            m = PORT_RE.search(line)
            if m:
                host = m.group(1)
                ports.setdefault(host, []).append((p, i, line.strip()))
    return {k:v for k,v in ports.items() if len(v) > 1}

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    dup = scan(root)
    if dup:
        print('[NG] Possible host port conflicts:')
        for port, refs in dup.items():
            print(f'PORT {port}')
            for p, i, line in refs:
                print(f'  {p}:{i}: {line}')
        sys.exit(1)
    print('[OK] No duplicate host ports found in compose files.')