"""Wan2.2 TI2V 5B でテキストから動画を生成する(T2V)。

16GB VRAM の初期値は 640x384 / 81frames / 20steps / 24fps。
VRAM不足時は 解像度 -> フレーム数 -> steps の順に下げること(docs/02)。

  python scripts/run_wan22_t2v.py
  python scripts/run_wan22_t2v.py --width 832 --height 480 --frames 81 --steps 20
  python scripts/run_wan22_t2v.py --lease-wait 900     # 他ジョブのGPU解放を待つ
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.request
import uuid
from pathlib import Path

sys.stdout.reconfigure(encoding='utf-8', errors='replace')  # P023

ROOT = Path(__file__).resolve().parents[1]
CFG = json.loads((ROOT / 'config/settings.json').read_text(encoding='utf-8'))
API_URL = os.getenv('COMFYUI_URL', CFG['api_url']).rstrip('/')

sys.path.insert(0, str(ROOT.parents[1] / 'scripts'))
try:
    import gpu_arbiter
except Exception:
    gpu_arbiter = None


def post_json(url: str, obj: dict) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(obj).encode('utf-8'),
        headers={'Content-Type': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as r:
        return json.loads(r.read())


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument('--workflow', default=str(ROOT / 'workflows/wan22_t2v_api.json'))
    p.add_argument('--prompt', default=None)
    p.add_argument('--negative', default=None)
    p.add_argument('--seed', type=int, default=20260806)
    p.add_argument('--width', type=int, default=640)
    p.add_argument('--height', type=int, default=384)
    p.add_argument('--frames', type=int, default=81)
    p.add_argument('--steps', type=int, default=20)
    p.add_argument('--fps', type=float, default=24.0)
    p.add_argument('--timeout', type=int, default=7200)
    p.add_argument('--lease-wait', type=float, default=0.0)
    p.add_argument('--no-lease', action='store_true')
    a = p.parse_args()

    wf = json.loads(Path(a.workflow).read_text(encoding='utf-8'))
    if a.prompt:
        wf['6']['inputs']['text'] = a.prompt
    if a.negative:
        wf['7']['inputs']['text'] = a.negative
    wf['3']['inputs']['seed'] = a.seed
    wf['3']['inputs']['steps'] = a.steps
    wf['55']['inputs'].update(width=a.width, height=a.height, length=a.frames)
    wf['57']['inputs']['fps'] = a.fps

    print(f'設定: {a.width}x{a.height} / {a.frames}frames / {a.steps}steps / {a.fps}fps '
          f'/ seed={a.seed}')

    owner = None
    if gpu_arbiter and not a.no_lease:
        ok, holder = gpu_arbiter.acquire(
            'comfyui', priority=gpu_arbiter.PRIORITY_INTERACTIVE,
            est_vram_mb=int(CFG.get('est_vram_mb', 14000)),
            ttl_sec=a.timeout + 600, wait_sec=a.lease_wait,
            yield_url=API_URL + '/free', pid=0, note='run_wan22_t2v')
        if not ok:
            print(f"GPUリースを取得できません。現保持者="
                  f"{holder.get('owner') if holder else '不明'} "
                  f"期限={holder.get('expires_at') if holder else '-'}")
            return 6
        owner = 'comfyui'

    try:
        started = time.time()
        result = post_json(API_URL + '/prompt',
                           {'prompt': wf, 'client_id': str(uuid.uuid4())})
        pid = result['prompt_id']
        print('prompt_id:', pid)
        outdir = Path(CFG['comfyui_root']) / 'output'
        deadline = time.time() + a.timeout
        while True:
            h = get_json(API_URL + '/history/' + pid)
            if pid in h:
                entry = h[pid]
                status = entry.get('status', {})
                if status.get('status_str') == 'error':
                    print('生成エラー:')
                    print(json.dumps(status, ensure_ascii=False, indent=2)[:3000])
                    return 7
                outputs = entry.get('outputs', {})
                print(json.dumps(outputs, ensure_ascii=False, indent=2))
                # 目視確認のため実ファイルパスを出す
                for node in outputs.values():
                    for key in ('images', 'videos', 'gifs'):
                        for item in node.get(key, []):
                            print('生成物:',
                                  outdir / item.get('subfolder', '') / item['filename'])
                print(f'所要: {time.time() - started:.0f} 秒')
                return 0
            if time.time() > deadline:
                print(f'タイムアウト({a.timeout}秒)')
                return 5
            time.sleep(5)
    finally:
        if owner:
            gpu_arbiter.release(owner)


if __name__ == '__main__':
    raise SystemExit(main())
