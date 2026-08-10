# -*- coding: utf-8 -*-
"""登録済みComfyUI APIワークフローを、トークン置換して投入するCLI。

例:
  python scripts/run_comfy_workflow.py workflows/smoke/comfyui_sd15_txt2img_api.json \
      --set CKPT_NAME=v1-5-pruned-emaonly.safetensors --set WIDTH=256 --wait

  # 投入せず、不足モデル等を事前検証だけする
  python scripts/run_comfy_workflow.py workflows/scail2/scail2_wan_api.json --preset scail2 --check-only
"""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from mecha_studio.adapters import comfyui  # noqa: E402

# 型を保ったまま置換されるよう、数値は数値で書く
PRESETS = {
    "sd15": {
        "CKPT_NAME": "v1-5-pruned-emaonly.safetensors",
        "POSITIVE_PROMPT": "a mecha robot standing in a city street, cinematic lighting",
        "NEGATIVE_PROMPT": "blurry, low quality, watermark",
        "WIDTH": 256,
        "HEIGHT": 256,
        "SEED": 12345,
        "STEPS": 6,
        "CFG": 7.0,
        "FILENAME_PREFIX": "mecha_studio_smoke",
    },
    "sdxl": {
        "CKPT_NAME": "sd_xl_base_1.0.safetensors",
        "POSITIVE_PROMPT": "a mecha robot standing in a city street, cinematic lighting",
        "NEGATIVE_PROMPT": "blurry, low quality, watermark",
        "WIDTH": 1024,
        "HEIGHT": 1024,
        "SEED": 12345,
        "STEPS": 20,
        "CFG": 7.0,
        "FILENAME_PREFIX": "mecha_studio_sdxl",
    },
    "scail2": {
        "DIFFUSION_MODEL": "wan2.2_animate_14B_bf16.safetensors",
        "WEIGHT_DTYPE": "default",
        "SHIFT": 8.0,
        "TEXT_ENCODER": "umt5_xxl_fp8_e4m3fn_scaled.safetensors",
        "VAE_MODEL": "wan_2.1_vae.safetensors",
        "CLIP_VISION_MODEL": "clip_vision_h.safetensors",
        "POSITIVE_PROMPT": "a mecha robot walking, consistent character, cinematic",
        "NEGATIVE_PROMPT": "blurry, distorted limbs, flicker",
        "REFERENCE_IMAGE": "example.png",
        "POSE_VIDEO": "pose_reference.mp4",
        "WIDTH": 512,
        "HEIGHT": 896,
        "LENGTH": 81,
        "POSE_STRENGTH": 1.0,
        "SEED": 12345,
        "STEPS": 20,
        "CFG": 1.0,
        "FPS": 16.0,
        "FILENAME_PREFIX": "mecha_studio_scail2",
    },
}


def _coerce(text: str):
    """--set の値を JSON として解釈し、数値・真偽値は型を保つ。"""
    try:
        return json.loads(text)
    except ValueError:
        return text


def main(argv=None):
    ap = argparse.ArgumentParser(description="ComfyUI APIワークフローを投入する")
    ap.add_argument("workflow", help="APIフォーマットのワークフローJSON")
    ap.add_argument("--preset", choices=sorted(PRESETS), help="既定トークン値のプリセット")
    ap.add_argument("--set", action="append", default=[], metavar="KEY=VALUE", help="トークン値の上書き")
    ap.add_argument("--base-url", default=comfyui.DEFAULT_BASE)
    ap.add_argument("--check-only", action="store_true", help="投入せず、置換と事前検証だけ行う")
    ap.add_argument("--wait", action="store_true", help="完了まで待って出力を回収する")
    ap.add_argument("--timeout", type=int, default=1800)
    ap.add_argument("--dest", help="出力の保存先ディレクトリ")
    args = ap.parse_args(argv)

    mapping = dict(PRESETS.get(args.preset, {}))
    for item in args.set:
        if "=" not in item:
            ap.error(f"--set は KEY=VALUE 形式です: {item}")
        k, v = item.split("=", 1)
        mapping[k] = _coerce(v)

    wf_path = Path(args.workflow)
    if not wf_path.is_absolute():
        wf_path = ROOT / wf_path

    if not comfyui.health(args.base_url):
        print(f"ComfyUIに接続できません: {args.base_url}")
        return 2

    try:
        rendered = comfyui.render_workflow(wf_path, mapping)
    except comfyui.ComfyError as e:
        print("トークン置換に失敗しました:", e)
        return 2

    problems = comfyui.validate_workflow(rendered, base_url=args.base_url)
    print(f"ワークフロー: {wf_path.name}")
    print(f"トークン: {len(comfyui.find_tokens(json.loads(wf_path.read_text(encoding='utf-8'))))} 個を置換")
    if problems:
        print(f"事前検証: NG（{len(problems)}件）")
        for p in problems:
            print("  -", p)
    else:
        print("事前検証: OK（このComfyUIで実行可能）")

    if args.check_only:
        return 1 if problems else 0
    if problems:
        print("問題があるため投入しません。--check-only で内容を確認してください。")
        return 1

    try:
        result = comfyui.run_workflow(
            wf_path, mapping, base_url=args.base_url, validate=False,
            wait=args.wait, timeout=args.timeout, dest_dir=args.dest,
        )
    except comfyui.ComfyError as e:
        print("投入/実行に失敗しました:", e)
        return 2

    print("prompt_id:", result["prompt_id"])
    for o in result.get("outputs", []):
        print(f"  出力 node {o['node_id']} {o['kind']}: {o['filename']}  {o['url']}")
    for s in result.get("saved", []):
        print("  保存:", s)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
