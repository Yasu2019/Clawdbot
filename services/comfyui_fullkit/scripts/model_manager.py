from __future__ import annotations
import argparse, hashlib, json, os, sys, time, urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # P023

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=json.loads((ROOT/'config/settings.json').read_text(encoding='utf-8'))
MODELS=json.loads((ROOT/'config/models.json').read_text(encoding='utf-8'))
COMFY=Path(SETTINGS['comfyui_root'])
# 大容量モデルはF:へ退避する(CLAUDE.md: 100MB超はF:\clawstack_data配下)。
# 未設定なら従来どおりComfyUI配下に置く。
STORE=Path(SETTINGS['model_store_root']) if SETTINGS.get('model_store_root') else COMFY/'models'
LOG=ROOT/SETTINGS.get('download_hash_log','logs/download_hashes.json')

def human(n:int)->str:
    for u in ['B','KB','MB','GB','TB']:
        if n<1024: return f'{n:.1f} {u}'
        n/=1024
    return f'{n:.1f} PB'

def sha256(path:Path)->str:
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''): h.update(b)
    return h.hexdigest()

def download(url:str,dst:Path)->None:
    dst.parent.mkdir(parents=True,exist_ok=True)
    part=dst.with_suffix(dst.suffix+'.part')
    start=part.stat().st_size if part.exists() else 0
    headers={'User-Agent':'ComfyUI-FullKit/1.0'}
    if start: headers['Range']=f'bytes={start}-'
    req=urllib.request.Request(url,headers=headers)
    print(f'取得: {dst.name}  再開位置={human(start)}')
    try:
        with urllib.request.urlopen(req,timeout=int(SETTINGS.get('request_timeout_sec',60))) as r, part.open('ab' if start and r.status==206 else 'wb') as f:
            total=r.headers.get('Content-Length')
            total=int(total)+start if total else None
            done=start
            while True:
                b=r.read(int(SETTINGS.get('download_chunk_mb',8))*1024*1024)
                if not b: break
                f.write(b); done+=len(b)
                print(f'\r  {human(done)}'+(f' / {human(total)}' if total else ''),end='',flush=True)
        print()
        part.replace(dst)
    except KeyboardInterrupt:
        print('\n中断しました。.partから次回再開できます。')
        raise

def record(model:str,path:Path)->None:
    data={}
    if LOG.exists():
        try:data=json.loads(LOG.read_text(encoding='utf-8'))
        except Exception:data={}
    data[str(path)]={'model':model,'bytes':path.stat().st_size,'sha256':sha256(path),'recorded_at':time.strftime('%Y-%m-%d %H:%M:%S')}
    LOG.parent.mkdir(parents=True,exist_ok=True)
    LOG.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

def main()->int:
    p=argparse.ArgumentParser(description='ComfyUI公式モデル管理')
    p.add_argument('action',choices=['list','install','verify'])
    p.add_argument('model',nargs='?')
    a=p.parse_args()
    if a.action=='list':
        for k,v in MODELS.items(): print(f'{k:12} {v["description"]}')
        return 0
    if not a.model or a.model not in MODELS:
        print('モデル名が不正です。listで確認してください。'); return 2
    m=MODELS[a.model]
    if not COMFY.exists():
        print(f'ComfyUI rootが存在しません: {COMFY}\nconfig/settings.jsonを修正してください。'); return 3
    if not m.get('files'):
        print('この項目は手動導入です:',m.get('manual_url','')); return 0
    print('保存先:',STORE,'(ComfyUIからはextra_model_paths.yaml経由で参照)')
    for f in m['files']:
        dst=STORE/f['subdir']/f['filename']
        if a.action=='install':
            if dst.exists(): print('既存:',dst)
            else: download(f['url'],dst)
            record(a.model,dst); print('SHA256記録完了:',dst)
        else:
            if not dst.exists(): print('不足:',dst); continue
            print(dst.name,sha256(dst))
    return 0
if __name__=='__main__': raise SystemExit(main())
