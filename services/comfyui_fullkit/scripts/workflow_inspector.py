from __future__ import annotations
import argparse,json
from pathlib import Path

def walk(x):
    if isinstance(x,dict):
        for k,v in x.items():
            if k=='models' and isinstance(v,list):
                for m in v:
                    if isinstance(m,dict) and 'name' in m: yield m
            yield from walk(v)
    elif isinstance(x,list):
        for v in x: yield from walk(v)

def main():
    p=argparse.ArgumentParser(); p.add_argument('workflow'); a=p.parse_args()
    d=json.loads(Path(a.workflow).read_text(encoding='utf-8'))
    seen=set()
    for m in walk(d):
        key=(m.get('directory','?'),m['name'])
        if key not in seen:
            seen.add(key); print(f'{key[0]:20} {key[1]}\n  {m.get("url","")}')
if __name__=='__main__': main()
