"""post_processor.py — 超リアル化3段後処理パイプライン

Stage A: SD img2img (ローカルOpenVINO Docker) — 3Dレンダー → 実写調
Stage B: PIL画質強化 — シャープネス・コントラスト・彩度
Stage C: Lanczos 2x アップスケール — 2K → 4K相当

SDサービスが応答しない場合はStage Bから継続する（フォールバック設計）。
two_pass=True の場合: 背景のみSDで写実化しキャラを保護して合成する。
"""
from __future__ import annotations

import base64
import json
import sys
import time
import urllib.error
import urllib.request
from io import BytesIO
from pathlib import Path
from typing import Optional

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]

from PIL import Image, ImageEnhance, ImageFilter

SD_BASE_URL    = "http://localhost:8101"
SD_IMG2IMG_URL = f"{SD_BASE_URL}/img2img"
SD_OUTPUT_URL  = f"{SD_BASE_URL}/output"

# 写実化プロンプト — 3Dレンダー調を実写写真調に変換する
PHOTOREALISM_PROMPT = (
    "photorealistic urban Japan city street, Shibuya Tokyo, dark asphalt road, "
    "gray concrete office buildings, cinematic photography, street level perspective, "
    "natural sunlight midday, Canon EOS R5 35mm f/5.6, ultra detailed textures, 8k uhd, "
    "atmospheric depth, realistic building facades, urban environment"
)
NEGATIVE_PROMPT = (
    "cartoon, anime, 3D render, CGI, plastic, artificial, low quality, "
    "watermark, logo, blurry, deformed, bad anatomy, overexposed, "
    "sandy desert, sand, light ground, empty plaza, parking lot, rooftop, barren"
)


# ══════════════════════════════════════════════════════════════
# 公開API
# ══════════════════════════════════════════════════════════════

def post_process(
    render_path: Path,
    output_dir: Path,
    config: dict,
    bg_path: Optional[Path] = None,
) -> Path:
    """Blenderレンダーに超リアル化3段処理を適用して最終画像を返す。

    Args:
        render_path: Pass B出力 (render_final.png, Zaku込みRGB)
        output_dir:  後処理済み画像の保存先
        config:      YAMLコンフィグ
        bg_path:     Pass A出力 (render_bg.png, RGBA Zaku=透明) — two_pass時のみ

    Returns:
        最終出力パス (4K相当PNG)
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = config.get("scene", {}).get("name", "scene")
    pp_cfg     = config.get("post_process", {})
    two_pass   = config.get("render", {}).get("two_pass", False) and bg_path is not None and bg_path.exists()

    print(f"\n[PostProcessor] === START: {render_path.name} ===", flush=True)
    if two_pass:
        print(f"[PostProcessor] Mode: TWO-PASS (bg={bg_path.name})", flush=True)
    t0 = time.time()

    # ── Stage A: SD img2img ──────────────────────────────────
    strength   = pp_cfg.get("sd_strength",   0.35)
    steps      = pp_cfg.get("sd_steps",      20)
    max_dim    = pp_cfg.get("max_dimension", 768)
    sd_enabled = pp_cfg.get("sd_enabled", True)

    if two_pass:
        # 背景のみSDで写実化 → Zakuはfull renderから取得して合成
        if sd_enabled:
            bg_strength = pp_cfg.get("sd_strength_bg", 0.45)
            bg_sd = _sd_img2img(bg_path, strength=bg_strength, steps=steps, max_dim=max_dim)
            # SDが縮小した場合に元サイズに復元
            bg_src = Image.open(bg_path)
            if bg_sd.size != bg_src.size:
                bg_sd = bg_sd.resize(bg_src.size, Image.LANCZOS)
                print(f"[PostProcessor] bg_sd restored to {bg_src.size[0]}x{bg_src.size[1]}", flush=True)
        else:
            bg_sd = Image.open(bg_path).convert("RGB")
            print("[PostProcessor] SD img2img skipped (sd_enabled=false)", flush=True)
        img = _composite_two_pass(bg_path, render_path, bg_sd)
    elif sd_enabled:
        img = _sd_img2img(render_path, strength=strength, steps=steps, max_dim=max_dim)
        # SDが縮小処理した場合、元のレンダー解像度に戻してからPIL強化する
        orig = Image.open(render_path)
        orig_w, orig_h = orig.size
        if img.size != (orig_w, orig_h):
            img = img.resize((orig_w, orig_h), Image.LANCZOS)
            print(f"[PostProcessor] SD output restored to: {orig_w}x{orig_h}", flush=True)
    else:
        img = Image.open(render_path).convert("RGB")
        print("[PostProcessor] SD img2img skipped (sd_enabled=false)", flush=True)

    # ── Stage B: PIL画質強化 ─────────────────────────────────
    img = _pil_enhance(img, pp_cfg)

    # ── Stage C: Lanczos 2x アップスケール ──────────────────
    scale      = pp_cfg.get("upscale_factor", 2)
    final_path = output_dir / f"{scene_name}_ultra.png"
    _lanczos_upscale(img, final_path, scale=scale)

    elapsed = time.time() - t0
    print(f"[PostProcessor] === DONE in {elapsed:.1f}s → {final_path.name} ===", flush=True)
    return final_path


def print_post_process_report(final_path: Path, original_path: Path):
    """処理前後の比較サマリーを表示する。"""
    try:
        orig = Image.open(original_path)
        final = Image.open(final_path)
        print(f"\n  [PostProcessor] 超リアル化結果", flush=True)
        print(f"  入力 : {orig.size[0]}x{orig.size[1]} px", flush=True)
        print(f"  出力 : {final.size[0]}x{final.size[1]} px  <- {final_path.name}", flush=True)
        print(f"  Stage A: SD img2img / Stage B: PIL / Stage C: Lanczos 2x", flush=True)
    except Exception:
        pass


def post_process_compare(
    render_path: Path,
    output_dir: Path,
    config: dict,
    bg_path: Optional[Path] = None,
) -> dict:
    """SD img2img と 実写写真合成を両方実行し、横並び比較画像を生成する。

    Returns:
        {
          "sd_path":         SD版 ultra PNG パス (or None),
          "photo_path":      実写版 ultra PNG パス (or None),
          "comparison_path": 横並び比較 PNG パス (or None),
        }
    """
    from photo_bg_compositor import fetch_city_photo, composite_zaku_on_photo

    output_dir.mkdir(parents=True, exist_ok=True)
    scene_name = config.get("scene", {}).get("name", "scene")
    pp_cfg     = config.get("post_process", {})
    pb_cfg     = config.get("photo_bg", {})
    steps      = pp_cfg.get("sd_steps",      20)
    max_dim    = pp_cfg.get("max_dimension", 768)
    scale      = pp_cfg.get("upscale_factor", 2)

    result: dict = {"sd_path": None, "photo_path": None, "comparison_path": None}

    print("\n[PostProcessor] === COMPARE MODE: SD vs Real Photo ===", flush=True)

    # ── Path A: SD img2img ───────────────────────────────────
    print("[PostProcessor] [A] SD img2img path ...", flush=True)
    try:
        sd_img = _run_sd_path(render_path, bg_path, pp_cfg)
        sd_img = _pil_enhance(sd_img, pp_cfg)
        sd_path = output_dir / f"{scene_name}_ultra_sd.png"
        _lanczos_upscale(sd_img, sd_path, scale=scale)
        result["sd_path"] = sd_path
        print(f"[PostProcessor] [A] SD done: {sd_path.name}", flush=True)
    except Exception as e:
        print(f"[PostProcessor] [A] SD path failed: {e}", flush=True)

    # ── Path B: 実写写真合成 ─────────────────────────────────
    print("[PostProcessor] [B] Real photo path ...", flush=True)
    try:
        query   = pb_cfg.get("query", "urban city street intersection")
        sources = pb_cfg.get("sources", "pexels,pixabay")
        photo_cache_dir = output_dir / "photo_cache"
        photo_local = fetch_city_photo(query, photo_cache_dir, sources=sources)

        if photo_local and bg_path and bg_path.exists():
            photo_img = composite_zaku_on_photo(bg_path, render_path, photo_local)
            photo_img = _pil_enhance(photo_img, pp_cfg)
            photo_path = output_dir / f"{scene_name}_ultra_photo.png"
            _lanczos_upscale(photo_img, photo_path, scale=scale)
            result["photo_path"] = photo_path
            print(f"[PostProcessor] [B] Photo done: {photo_path.name}", flush=True)
        else:
            print("[PostProcessor] [B] Photo skipped (no photo or no bg_path)", flush=True)
    except Exception as e:
        print(f"[PostProcessor] [B] Photo path failed: {e}", flush=True)

    # ── 横並び比較画像 ───────────────────────────────────────
    if result["sd_path"] and result["photo_path"]:
        try:
            comp_path = _make_comparison_image(
                result["sd_path"], result["photo_path"],
                output_dir / f"{scene_name}_comparison.png",
                labels=("SD img2img", "Real Photo"),
            )
            result["comparison_path"] = comp_path
            print(f"[PostProcessor] Comparison saved: {comp_path.name}", flush=True)
        except Exception as e:
            print(f"[PostProcessor] Comparison image failed: {e}", flush=True)

    return result


def print_compare_report(result: dict):
    """比較結果サマリーを表示する。"""
    print("\n  [PostProcessor] Compare Results:", flush=True)
    for key, label in [("sd_path", "SD img2img"), ("photo_path", "Real Photo"), ("comparison_path", "Comparison")]:
        path = result.get(key)
        if path:
            print(f"  {label:15} -> {Path(path).name}", flush=True)
        else:
            print(f"  {label:15} -> (skipped)", flush=True)


# ══════════════════════════════════════════════════════════════
# 内部ヘルパー
# ══════════════════════════════════════════════════════════════

def _run_sd_path(
    render_path: Path,
    bg_path: Optional[Path],
    pp_cfg: dict,
) -> Image.Image:
    """SD img2img パスを実行して合成済み Image を返す。

    bg_path が有効なら two_pass 合成、なければ render_path に直接 SD 適用。
    """
    steps   = pp_cfg.get("sd_steps",      20)
    max_dim = pp_cfg.get("max_dimension", 768)
    sd_enabled = pp_cfg.get("sd_enabled", True)

    two_pass = bg_path is not None and bg_path.exists()

    if two_pass:
        if sd_enabled:
            bg_strength = pp_cfg.get("sd_strength_bg", 0.45)
            bg_sd = _sd_img2img(bg_path, strength=bg_strength, steps=steps, max_dim=max_dim)
            bg_src = Image.open(bg_path)
            if bg_sd.size != bg_src.size:
                bg_sd = bg_sd.resize(bg_src.size, Image.LANCZOS)
        else:
            bg_sd = Image.open(bg_path).convert("RGB")
        return _composite_two_pass(bg_path, render_path, bg_sd)
    else:
        if sd_enabled:
            strength = pp_cfg.get("sd_strength", 0.35)
            img = _sd_img2img(render_path, strength=strength, steps=steps, max_dim=max_dim)
            orig_w, orig_h = Image.open(render_path).size
            if img.size != (orig_w, orig_h):
                img = img.resize((orig_w, orig_h), Image.LANCZOS)
            return img
        else:
            return Image.open(render_path).convert("RGB")


def _make_comparison_image(
    left_path: Path,
    right_path: Path,
    output_path: Path,
    labels: tuple = ("Left", "Right"),
) -> Path:
    """2枚の画像を横並びにして比較画像を生成する。"""
    from PIL import ImageDraw, ImageFont

    left  = Image.open(left_path).convert("RGB")
    right = Image.open(right_path).convert("RGB")

    # 同じ高さに揃える
    h = min(left.height, right.height)
    if left.height != h:
        left = left.resize((int(left.width * h / left.height), h), Image.LANCZOS)
    if right.height != h:
        right = right.resize((int(right.width * h / right.height), h), Image.LANCZOS)

    label_h = 48
    canvas = Image.new("RGB", (left.width + right.width, h + label_h), (20, 20, 20))
    canvas.paste(left,  (0,          label_h))
    canvas.paste(right, (left.width, label_h))

    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype("arial.ttf", 32)
    except Exception:
        font = ImageFont.load_default()

    draw.text((left.width // 2 - 80,  8), labels[0], fill=(255, 255, 100), font=font)
    draw.text((left.width + right.width // 2 - 80, 8), labels[1], fill=(100, 200, 255), font=font)

    canvas.save(str(output_path), "PNG")
    return output_path


# ══════════════════════════════════════════════════════════════
# 2パス合成
# ══════════════════════════════════════════════════════════════

def _composite_two_pass(
    bg_path: Path,
    full_path: Path,
    bg_sd: Image.Image,
) -> Image.Image:
    """SD強化背景とZaku込み全体レンダーをアルファマスクで合成する。

    bg_path:   Pass A RGBA (Zaku=alpha 0, 背景=alpha 255)
    full_path: Pass B RGB  (Zaku込み)
    bg_sd:     SDで写実化した背景 RGB
    戻り値:    RGB — 背景=SD写実化 / Zaku=full_path由来
    """
    bg_rgba  = Image.open(bg_path).convert("RGBA")
    full_rgb = Image.open(full_path).convert("RGB")

    # サイズ統一 (bg基準)
    target_size = bg_rgba.size
    if bg_sd.size != target_size:
        bg_sd = bg_sd.resize(target_size, Image.LANCZOS)
    if full_rgb.size != target_size:
        full_rgb = full_rgb.resize(target_size, Image.LANCZOS)

    alpha_mask = bg_rgba.split()[3]  # L mode: 255=背景, 0=Zaku

    # composite(img1, img2, mask): mask=255→img1, mask=0→img2
    composite = Image.composite(bg_sd.convert("RGB"), full_rgb, alpha_mask)
    print(
        f"[PostProcessor] Two-pass composite OK: {target_size[0]}x{target_size[1]}",
        flush=True,
    )
    return composite


# ══════════════════════════════════════════════════════════════
# Stage A: SD img2img
# ══════════════════════════════════════════════════════════════

def _sd_img2img(render_path: Path, strength: float, steps: int, max_dim: int) -> Image.Image:
    """ローカルSD img2imgサービスに送信して写実化。失敗時はオリジナルを返す。"""
    try:
        # 16-bit PNGをRGB変換し、SD UNet互換の64倍数サイズへリサイズ
        src_img = Image.open(render_path).convert("RGB")
        w, h = src_img.size
        if max(w, h) > max_dim:
            scale = max_dim / max(w, h)
            nw = max(64, round(w * scale / 64) * 64)
            nh = max(64, round(h * scale / 64) * 64)
            src_img = src_img.resize((nw, nh), Image.LANCZOS)
            print(f"[PostProcessor] Pre-resized to 64-aligned: {w}x{h} -> {nw}x{nh}", flush=True)
        buf = BytesIO()
        src_img.save(buf, "PNG")
        img_b64 = base64.b64encode(buf.getvalue()).decode()

        payload = json.dumps({
            "prompt":         PHOTOREALISM_PROMPT,
            "negative_prompt": NEGATIVE_PROMPT,
            "image_base64":   img_b64,
            "strength":       strength,
            "steps":          steps,
            "guidance_scale": 1.5,
            "max_dimension":  9999,
        }).encode()

        req = urllib.request.Request(
            SD_IMG2IMG_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        print(f"[PostProcessor] SD img2img: strength={strength}, steps={steps} ...", flush=True)
        with urllib.request.urlopen(req, timeout=600) as resp:
            result = json.loads(resp.read())

        image_id = result.get("image_id", "")
        if not image_id:
            raise ValueError(f"No image_id in SD response: {result}")

        img_req = urllib.request.Request(f"{SD_OUTPUT_URL}/{image_id}")
        with urllib.request.urlopen(img_req, timeout=30) as resp:
            img = Image.open(BytesIO(resp.read())).convert("RGB")

        dur = result.get("duration_sec", "?")
        print(f"[PostProcessor] SD img2img OK ({dur}s) → {image_id}", flush=True)
        return img

    except urllib.error.URLError as e:
        print(f"[PostProcessor] SD img2img service unreachable: {e} → using original", flush=True)
        return Image.open(render_path).convert("RGB")
    except Exception as e:
        print(f"[PostProcessor] SD img2img error: {e} → using original", flush=True)
        return Image.open(render_path).convert("RGB")


# ══════════════════════════════════════════════════════════════
# Stage B: PIL画質強化
# ══════════════════════════════════════════════════════════════

def _pil_enhance(img: Image.Image, pp_cfg: dict) -> Image.Image:
    """シャープネス・コントラスト・彩度・Unsharp maskを適用する。"""
    sharpness = pp_cfg.get("sharpness",  1.40)
    contrast  = pp_cfg.get("contrast",   1.15)
    color     = pp_cfg.get("saturation", 1.20)

    img = ImageEnhance.Sharpness(img).enhance(sharpness)
    img = ImageEnhance.Contrast(img).enhance(contrast)
    img = ImageEnhance.Color(img).enhance(color)
    # Unsharp mask — エッジ・建物ライン・メカディテールを強調
    img = img.filter(ImageFilter.UnsharpMask(radius=1.5, percent=60, threshold=3))
    print(f"[PostProcessor] PIL enhance: sharp={sharpness} contrast={contrast} color={color}", flush=True)
    return img


# ══════════════════════════════════════════════════════════════
# Stage C: アップスケール
# ══════════════════════════════════════════════════════════════

def _lanczos_upscale(img: Image.Image, output_path: Path, scale: int = 2):
    """Lanczos高品質アップスケール。2K→4K(2x)など。"""
    w, h   = img.size
    img_up = img.resize((w * scale, h * scale), Image.LANCZOS)
    img_up.save(str(output_path), "PNG")
    print(f"[PostProcessor] Upscaled: {w}x{h} → {w*scale}x{h*scale} → {output_path.name}", flush=True)
