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

COMMON_NAMES = ['observability', 'quality', 'tolerance', 'kinematics', 'paperless', 'rag', 'gdt', 'workstudy']

def scan(root: Path):
    app_dirs = []
    for apps in root.rglob('apps'):
        if apps.is_dir():
            for child in apps.iterdir():
                if child.is_dir():
                    app_dirs.append(child.name.lower())
    dup = sorted({n for n in app_dirs if app_dirs.count(n) > 1})
    suspicious = sorted({n for n in app_dirs if any(c in n for c in COMMON_NAMES)})
    return dup, suspicious

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    dup, suspicious = scan(root)
    if dup:
        print('[NG] Duplicate Portal app directory names:')
        for n in dup:
            print(' ', n)
        sys.exit(1)
    print('[OK] No duplicate app directory names found.')
    if suspicious:
        print('[INFO] Existing related Portal apps detected:')
        for n in suspicious:
            print(' ', n)