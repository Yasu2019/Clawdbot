#!/usr/bin/env python3
from pathlib import Path
import argparse, html, re

def md_to_basic_html(md: str) -> str:
    lines = []
    for line in md.splitlines():
        if line.startswith('# '): lines.append(f"<h1>{html.escape(line[2:])}</h1>")
        elif line.startswith('## '): lines.append(f"<h2>{html.escape(line[3:])}</h2>")
        elif line.startswith('- '): lines.append(f"<li>{html.escape(line[2:])}</li>")
        elif line.strip() == '': lines.append('')
        else: lines.append(f"<p>{html.escape(line)}</p>")
    return "\n".join(lines)

ap = argparse.ArgumentParser()
ap.add_argument('markdown')
ap.add_argument('--out', default='manual.html')
args = ap.parse_args()
md = Path(args.markdown).read_text(encoding='utf-8')
body = md_to_basic_html(md)
html_doc = f"""<!doctype html><html lang='ja'><head><meta charset='utf-8'>
<title>Auto Manual</title><style>body{{font-family:sans-serif;line-height:1.7;margin:40px;max-width:1100px}}h1{{border-bottom:3px solid #333}}h2{{border-left:6px solid #666;padding-left:10px}}p,li{{font-size:15px}}@media print{{body{{margin:15mm}}}}</style></head><body>{body}</body></html>"""
Path(args.out).write_text(html_doc, encoding='utf-8')
print(args.out)
