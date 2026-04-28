#!/usr/bin/env python3
import re, sys, pathlib
patterns = [
    (r'[A-Z]{2,}-?\d{3,}', '[PART_NO]'),
    (r'[\w\.-]+@[\w\.-]+', '[EMAIL]'),
    (r'\b\d{2,3}\.\d{1,4}\b', '[NUM]'),
]
def redact(s):
    for pat, repl in patterns:
        s = re.sub(pat, repl, s)
    return s
if len(sys.argv) < 2:
    print('usage: redact_for_external_ai.py input.txt > redacted.txt')
    sys.exit(1)
print(redact(pathlib.Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore')))
