"""既存ComfyUI本体をGPU(cu128 venv)で起動する。

Docker CPU版(services/comfyui)とネイティブGPU版は同じ8188を使うため、
起動前にポート占有を検査し、使用中なら起動しない(無言のCPU実行を防ぐ)。

  python scripts/start_comfyui_gpu.py            # フォアグラウンド起動
  python scripts/start_comfyui_gpu.py --port 8188
"""
from __future__ import annotations
import argparse, json, socket, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # P023

ROOT=Path(__file__).resolve().parents[1]
CFG=json.loads((ROOT/'config/settings.json').read_text(encoding='utf-8'))

def port_in_use(host:str,port:int)->bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex((host,port))==0

def main()->int:
    api=CFG.get('api_url','http://127.0.0.1:8188')
    default_port=int(api.rsplit(':',1)[-1].rstrip('/'))
    p=argparse.ArgumentParser()
    p.add_argument('--port',type=int,default=default_port)
    p.add_argument('--listen',default='127.0.0.1')
    a=p.parse_args()

    comfy=Path(CFG['comfyui_root'])
    py=Path(CFG.get('comfyui_python',''))
    if not (comfy/'main.py').exists():
        print('ComfyUI本体が見つかりません:',comfy); return 3
    if not py.exists():
        print('GPUランタイムのPythonが見つかりません:',py); return 3
    if port_in_use(a.listen,a.port):
        print(f'{a.listen}:{a.port} は既に使用中です。起動を中止しました。')
        print('Docker CPU版(services/comfyui)が動いている可能性があります。')
        print('  docker ps  で確認し、GPU版を使う場合はCPU版を停止してください。')
        return 4

    cmd=[str(py),'main.py','--listen',a.listen,'--port',str(a.port)]
    print('起動:',' '.join(cmd))
    print('作業ディレクトリ:',comfy)
    print(f'UI: http://{a.listen}:{a.port}')
    return subprocess.call(cmd,cwd=str(comfy))

if __name__=='__main__':
    raise SystemExit(main())
