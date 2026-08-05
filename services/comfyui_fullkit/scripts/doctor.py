from __future__ import annotations
import json, os, platform, shutil, socket, subprocess, sys
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # P023

ROOT=Path(__file__).resolve().parents[1]
SETTINGS=ROOT/'config'/'settings.json'

def cmd(args:list[str])->str:
    try:
        return subprocess.check_output(args, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace', timeout=15).strip()
    except Exception as e:
        return f'取得失敗: {e}'

def port_in_use(host:str,port:int)->bool:
    with socket.socket() as s:
        s.settimeout(1.0)
        return s.connect_ex((host,port))==0

def main()->int:
    print('=== ComfyUI環境診断 (Clawstack融合版) ===')
    print('OS:', platform.platform())
    print('Python:', sys.version.replace('\n',' '))
    print('実行場所:', ROOT)
    total, used, free=shutil.disk_usage(ROOT)
    print(f'空き容量: {free/1024**3:.1f} GB / 合計 {total/1024**3:.1f} GB')
    print('\n--- NVIDIA GPU ---')
    print(cmd(['nvidia-smi','--query-gpu=name,memory.total,driver_version','--format=csv,noheader']))
    if not SETTINGS.exists():
        print('config/settings.json が見つかりません。'); return 1

    cfg=json.loads(SETTINGS.read_text(encoding='utf-8'))
    comfy=Path(cfg['comfyui_root'])
    print('\n--- ComfyUI本体 ---')
    print('root:', comfy)
    print('存在:', comfy.exists())
    print('main.py:', (comfy/'main.py').exists())
    print('models:', (comfy/'models').exists())
    print('extra_model_paths.yaml:', (comfy/'extra_model_paths.yaml').exists(),
          '(未生成なら scripts/setup_model_paths.py を実行)')

    print('\n--- 実行Python (GPUランタイム) ---')
    py=cfg.get('comfyui_python')
    if py and Path(py).exists():
        print('python:', py)
        print(cmd([py,'-c','import torch;print("torch",torch.__version__,"cuda_available",torch.cuda.is_available(),"cuda",torch.version.cuda)']))
    else:
        print('comfyui_python 未設定または不在:', py)

    print('\n--- モデル保管先 ---')
    store=Path(cfg.get('model_store_root') or (comfy/'models'))
    print('store:', store, '存在:', store.exists())
    probe=store if store.exists() else Path(store.anchor or ROOT.anchor)
    try:
        t,u,f=shutil.disk_usage(probe)
        print(f'保管先ドライブ空き: {f/1024**3:.1f} GB / 合計 {t/1024**3:.1f} GB')
    except OSError as e:
        print('容量取得失敗:', e)

    print('\n--- ポート排他 (8188) ---')
    api=cfg.get('api_url','http://127.0.0.1:8188')
    host=api.split('//')[-1].split(':')[0]
    port=int(api.rsplit(':',1)[-1].rstrip('/'))
    busy=port_in_use(host,port)
    print(f'{host}:{port} 使用中:', busy)
    if busy:
        print('  → 既にComfyUIが起動中です。Docker CPU版(services/comfyui)とネイティブGPU版の')
        print('    二重起動は無言でCPU実行になるため禁止。どちらが動いているか確認すること。')

    print('\n判定目安: SDXLのみ=約7GB、Wan2.2 5B一式=約17GB、両方で約24GBの空きが必要。')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
