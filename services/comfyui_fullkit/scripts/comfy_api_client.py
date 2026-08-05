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

# GPU時分割調停(scripts/gpu_arbiter.py)。単一GPUをRL学習/CAEと共有するため、
# 生成中だけリースを保持する。arbiterが無い環境でも動くよう任意依存にしてある。
sys.path.insert(0, str(ROOT.parents[1]/'scripts'))
try:
    import gpu_arbiter
except Exception:
    gpu_arbiter=None

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
    p.add_argument('--lease-wait',type=float,default=0.0,help='GPUリース取得の待ち秒数')
    p.add_argument('--no-lease',action='store_true',help='GPUリースを取らずに実行する')
    a=p.parse_args()

    lease_owner=None
    if gpu_arbiter and not a.no_lease:
        ok,holder=gpu_arbiter.acquire(
            'comfyui', priority=gpu_arbiter.PRIORITY_INTERACTIVE,
            est_vram_mb=int(CFG.get('est_vram_mb',14000)),
            ttl_sec=a.timeout+300, wait_sec=a.lease_wait,
            yield_url=base_free_url(), pid=0, note='comfy_api_client')
        if not ok:
            print(f"GPUリースを取得できません。現保持者={holder.get('owner') if holder else '不明'} "
                  f"期限={holder.get('expires_at') if holder else '-'}")
            print('待つ場合は --lease-wait 600 を付けてください。')
            return 6
        lease_owner='comfyui'
    try:
        return _run(a)
    finally:
        if lease_owner:
            gpu_arbiter.release(lease_owner)

def base_free_url()->str:
    return API_URL.rstrip('/')+'/free'

def _run(a)->int:
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
