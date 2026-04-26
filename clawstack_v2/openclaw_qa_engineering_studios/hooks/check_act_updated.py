import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import sys

def is_safe(p):
    # Skip data directory, .git, and large files
    try:
        parts = p.parts
        if 'data' in parts: return False
        if '.git' in parts: return False
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True

from pathlib import Path

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    act = root / 'ACT.md'
    if not act.exists():
        print('[NG] ACT.md not found.')
        sys.exit(1)
    text = act.read_text(encoding='utf-8', errors='ignore')
    if '作業ログ' not in text or '次に行うこと' not in text:
        print('[NG] ACT.md lacks required sections.')
        sys.exit(1)
    print('[OK] ACT.md exists and has required sections.')