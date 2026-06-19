import sys, io; sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
import sys
from pathlib import Path

COMMON_NAMES = ['observability', 'quality', 'tolerance', 'kinematics', 'paperless', 'rag', 'gdt', 'workstudy']

def is_safe(p):
    try:
        parts = p.parts
        if 'data' in parts: return False
        if '.git' in parts: return False
        if '_archives' in parts: return False
        if '_legacy' in parts: return False
        if 'scratch' in parts: return False
        if 'protocols' in parts: return False
        if 'ZIP_Group' in parts: return False
        if 'backups' in parts: return False
        if p.stat().st_size > 1024 * 1024: return False
    except: return False
    return True

def scan(root: Path):
    app_dirs = []
    todo = [root]
    ignored = {'data', '.git', 'services', 'models', 'node_modules', '.venv', '.gemini', 'backups', '_archives', '_legacy', 'ZIP_Group', 'build', 'dist', 'antigravity', 'scratch', 'protocols', 'tool_attention', 'iatf_system', 'clawstack_v2'}
    while todo:
        curr = todo.pop()
        try:
            for p in curr.iterdir():
                if p.is_dir():
                    if p.name in ignored:
                        continue
                    if p.name.lower() == 'apps':
                        # Found an apps directory! Scan its children
                        for child in p.iterdir():
                            if child.is_dir():
                                app_dirs.append(child.name.lower())
                    else:
                        todo.append(p)
        except Exception:
            continue
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