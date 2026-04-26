#!/usr/bin/env python3
"""
Stable Diffusion でアニメキャラ生成
モデル: Lykon/dreamshaper-8 (汎用・アニメ得意)
保存先: /home/node/.codex/ai_models/ (D:\ 576GB空き)
CPU推論 / LCMスケジューラで高速化
"""
import os, torch
os.environ["HF_HUB_CACHE"] = "/home/node/.codex/ai_models/hf_cache"
os.environ["TRANSFORMERS_CACHE"] = "/home/node/.codex/ai_models/hf_cache"

from diffusers import StableDiffusionPipeline, LCMScheduler, DPMSolverMultistepScheduler
from PIL import Image

OUT = "/home/node/clawd/apps/video_factory/output/character_sd.png"
MODEL_ID = "Lykon/dreamshaper-8"

print(f"📥 モデルロード中: {MODEL_ID}")
print(f"   キャッシュ先: /home/node/.codex/ai_models/")

pipe = StableDiffusionPipeline.from_pretrained(
    MODEL_ID,
    torch_dtype=torch.float32,
    safety_checker=None,
    requires_safety_checker=False,
)
pipe = pipe.to("cpu")

# DPMSolverで高速化（20ステップで高品質）
pipe.scheduler = DPMSolverMultistepScheduler.from_config(
    pipe.scheduler.config,
    algorithm_type="dpmsolver++",
    use_karras_sigmas=True,
)

# メモリ節約
pipe.enable_attention_slicing()

PROMPT = (
    "anime style, 18 year old japanese male, heavy metal musician, "
    "spiky black hair with red highlights, intense expression, "
    "dark band t-shirt, silver earring, purple eyes, "
    "dramatic lighting, front facing portrait, "
    "high quality, detailed, manga style, "
    "black background with red glow"
)
NEGATIVE = (
    "lowres, bad anatomy, bad hands, text, error, missing fingers, "
    "extra digit, fewer digits, cropped, worst quality, low quality, "
    "normal quality, jpeg artifacts, signature, watermark, username, "
    "blurry, female, girl, feminine, cute, chibi"
)

print(f"🎨 画像生成中（20ステップ・CPU）...")
print(f"   プロンプト: {PROMPT[:80]}...")

result = pipe(
    prompt=PROMPT,
    negative_prompt=NEGATIVE,
    width=512,
    height=512,
    num_inference_steps=20,
    guidance_scale=7.5,
    generator=torch.manual_seed(42),
)

img = result.images[0]
img.save(OUT)
size_kb = os.path.getsize(OUT) // 1024
print(f"✅ SD画像生成完了: {OUT} ({size_kb}KB)")
