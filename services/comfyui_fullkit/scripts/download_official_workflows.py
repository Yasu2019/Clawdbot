from __future__ import annotations
import hashlib, json, urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'workflows'
URLS={
 'video_wan2_2_5B_ti2v.json':'https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_wan2_2_5B_ti2v.json',
 'video_hunyuan_video_1.5_720p_i2v.json':'https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_hunyuan_video_1.5_720p_i2v.json',
 'video_hunyuan_video_1.5_720p_t2v.json':'https://raw.githubusercontent.com/Comfy-Org/workflow_templates/refs/heads/main/templates/video_hunyuan_video_1.5_720p_t2v.json',
}

def main()->int:
    OUT.mkdir(parents=True,exist_ok=True)
    for name,url in URLS.items():
        print('取得:',name)
        req=urllib.request.Request(url,headers={'User-Agent':'ComfyUI-FullKit/1.0'})
        with urllib.request.urlopen(req,timeout=60) as r: data=r.read()
        json.loads(data.decode('utf-8'))
        path=OUT/name; path.write_bytes(data)
        print('  保存:',path)
        print('  SHA256:',hashlib.sha256(data).hexdigest())
    return 0
if __name__=='__main__': raise SystemExit(main())
