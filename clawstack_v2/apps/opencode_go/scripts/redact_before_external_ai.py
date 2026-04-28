#!/usr/bin/env python3
import re, sys, pathlib
patterns = [
    (re.compile(r'[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}', re.I), '[EMAIL_REDACTED]'),
    (re.compile(r'(?i)(api[_-]?key|token|password|secret)\s*[:=]\s*[^\s]+'), r'\1=[SECRET_REDACTED]'),
    (re.compile(r'\b\d{5,}\b'), '[NUMBER_REDACTED]'),
]
text = pathlib.Path(sys.argv[1]).read_text(encoding='utf-8', errors='ignore') if len(sys.argv)>1 else sys.stdin.read()
for pat, repl in patterns:
    text = pat.sub(repl, text)
print(text)
