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

KEYWORDS = ['IATF', '16949', '適合', '不適合', '監査', '条項']
EVIDENCE_WORDS = ['エビデンス', '根拠', '記録', '証拠', '確認方法']

if __name__ == '__main__':
    root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    warnings = []
    for p in root.rglob('*.md'):
        text = p.read_text(encoding='utf-8', errors='ignore')
        if any(k in text for k in KEYWORDS) and not any(e in text for e in EVIDENCE_WORDS):
            warnings.append(p)
    if warnings:
        print('[WARN] IATF/audit related files may lack evidence wording:')
        for p in warnings:
            print(' ', p)
    else:
        print('[OK] IATF/audit files include evidence-related wording or no target found.')