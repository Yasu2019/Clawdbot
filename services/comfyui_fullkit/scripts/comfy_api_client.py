from __future__ import annotations
import argparse, json, os, time, urllib.request, uuid
from pathlib import Path

import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # P023

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config/settings.json').read_text(encoding='utf-8'))
# 既存Clawstack連携(clawstack_v2/apps/iatf_video_factory/pipeline/comfyui_upscaler.py)と
# 同じ COMFYUI_URL 環境変数を優先する。
API_URL=os.getenv('COMFYUI_URL', CFG['api_url'])

def post_json(url:str,obj:dict)->dict:
    data=json.dumps(obj).encode('utf-8')
    req=urllib.request.Request(url,data=data,headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=60) as r:return json.loads(r.read())

def get_json(url:str)->dict:
    with urllib.request.urlopen(url,timeout=60) as r:return json.loads(r.read())

def main()->int:
    p=argparse.ArgumentParser()
    p.add_argument('--workflow',default=str(ROOT/'workflows/sdxl_api_basic.json'))
    p.add_argument('--prompt',default='A precision metal stamping factory, cinematic lighting, realistic, highly detailed')
    p.add_argument('--negative',default='low quality, blurry, distorted, text, watermark')
    p.add_argument('--seed',type=int,default=123456789)
    p.add_argument('--timeout',type=int,default=900,help='完了待ちの上限秒。超えたら異常終了する')
    a=p.parse_args()
    wf=json.loads(Path(a.workflow).read_text(encoding='utf-8'))
    wf['6']['inputs']['text']=a.prompt
    wf['7']['inputs']['text']=a.negative
    wf['3']['inputs']['seed']=a.seed
    client=str(uuid.uuid4())
    base=API_URL.rstrip('/')
    result=post_json(base+'/prompt',{'prompt':wf,'client_id':client})
    pid=result['prompt_id']; print('prompt_id:',pid)
    deadline=time.time()+a.timeout
    while True:
        h=get_json(base+'/history/'+pid)
        if pid in h:
            outputs=h[pid].get('outputs',{})
            print(json.dumps(outputs,ensure_ascii=False,indent=2))
            # 生成物の実ファイルパスを出す(目視確認を必須にするため)
            outdir=Path(CFG['comfyui_root'])/'output'
            for node in outputs.values():
                for img in node.get('images',[]):
                    print('生成物:', outdir/img.get('subfolder','')/img['filename'])
            break
        if time.time()>deadline:
            print(f'タイムアウト({a.timeout}秒)。ComfyUI側のログを確認してください。'); return 5
        time.sleep(2)
    return 0
if __name__=='__main__': raise SystemExit(main())
